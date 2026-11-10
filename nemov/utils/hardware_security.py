import os
import sys
import subprocess
import hashlib
import hmac
from pathlib import Path
from typing import Optional, Dict, List, Tuple

class HardwareSecurity:
    """
    Hardware-locked security, persistent machine anchoring and fingerprinting engine for Nemov.
    Binds the installation to Motherboard Serial, CPU ID, and Windows MachineGuid with
    multi-layer silent fallbacks and resilient local caching.
    Ensures that once a machine is activated, cold reboots, power shutdowns, high load,
    or installer updates never cause accidental deactivation.
    """

    _cached_mb_serial: Optional[str] = None
    _cached_cpu_id: Optional[str] = None
    _cached_hwid: Optional[str] = None

    # Secret salt keys for hardware-bound hashing
    _HW_SALT = b"Yalda_Gym_Master_HW_Salt_2006_Abolfazl"
    _ACTIVATION_SALT = b"Yalda_Gym_Master_Activation_Key_2006_Admin_Abolfazl"

    REGISTRY_APP_KEYS = [r"Software\Nemov", r"Software\YaldaGym"]
    APPDATA_FOLDERS = ["Nemov", "YaldaGym"]

    @classmethod
    def _run_cmd_silent(cls, cmd_list, timeout=10) -> str:
        """Executes a command completely silently (no console window flash) with safe timeout."""
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        try:
            p = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=timeout
            )
            return p.stdout.strip()
        except Exception:
            return ""

    @classmethod
    def get_windows_machine_guid(cls) -> str:
        """
        Retrieves the immutable Windows MachineGuid from HKLM.
        Generated during Windows installation, 100% stable across reboots, shutdowns, and updates.
        Retrieves in 0.05ms without any subprocesses.
        """
        if sys.platform != "win32":
            return ""
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Cryptography"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                val, _ = winreg.QueryValueEx(key, "MachineGuid")
                if val:
                    return str(val).strip()
        except Exception:
            pass
        return ""

    @classmethod
    def _get_cached_hardware_anchor(cls) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Retrieves cached hardware anchor (MB, CPU, HWID) from Windows Registry
        if and only if the current machine's MachineGuid matches the stored anchor.
        """
        if sys.platform != "win32":
            return None, None, None

        current_guid = cls.get_windows_machine_guid()
        if not current_guid:
            return None, None, None

        import winreg
        for key_path in cls.REGISTRY_APP_KEYS:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                    try:
                        stored_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                    except Exception:
                        stored_guid = None

                    # If MachineGuid matches, we can trust the cached hardware profile
                    if stored_guid and str(stored_guid).strip().lower() == current_guid.lower():
                        mb, cpu, hwid = None, None, None
                        try:
                            mb_val, _ = winreg.QueryValueEx(key, "CachedMB")
                            if mb_val and str(mb_val).strip():
                                mb = str(mb_val).strip()
                        except Exception:
                            pass
                        try:
                            cpu_val, _ = winreg.QueryValueEx(key, "CachedCPU")
                            if cpu_val and str(cpu_val).strip():
                                cpu = str(cpu_val).strip()
                        except Exception:
                            pass
                        try:
                            hwid_val, _ = winreg.QueryValueEx(key, "CachedHWID")
                            if not hwid_val:
                                hwid_val, _ = winreg.QueryValueEx(key, "LicenseHWID")
                            if hwid_val and str(hwid_val).strip():
                                hwid = str(hwid_val).strip()
                        except Exception:
                            pass
                        if mb or cpu or hwid:
                            return mb, cpu, hwid
            except Exception:
                continue
        return None, None, None

    @classmethod
    def _save_hardware_anchor_to_registry(cls, mb: Optional[str] = None, cpu: Optional[str] = None, hwid: Optional[str] = None):
        """Saves hardware anchor into Windows Registry for instant cold-boot loading."""
        if sys.platform != "win32":
            return
        guid = cls.get_windows_machine_guid()
        if not guid:
            return

        import winreg
        for key_path in cls.REGISTRY_APP_KEYS:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, guid)
                    if mb:
                        winreg.SetValueEx(key, "CachedMB", 0, winreg.REG_SZ, mb.strip())
                    if cpu:
                        winreg.SetValueEx(key, "CachedCPU", 0, winreg.REG_SZ, cpu.strip())
                    if hwid:
                        winreg.SetValueEx(key, "CachedHWID", 0, winreg.REG_SZ, hwid.strip().upper())
            except Exception:
                pass

    @classmethod
    def get_motherboard_serial(cls) -> str:
        """
        Retrieves Motherboard Serial Number using resilient mechanisms:
        1. Fast in-memory cache
        2. Hardware anchor cache (validated against Windows MachineGuid)
        3. PowerShell Get-CimInstance (timeout=10)
        4. WMIC BaseBoard
        5. Windows Registry (BIOS/BaseBoard)
        6. Product / Model Fallback
        """
        if cls._cached_mb_serial:
            return cls._cached_mb_serial

        # Check Hardware Anchor cache (avoids running slow PowerShell on cold boot)
        cached_mb, _, _ = cls._get_cached_hardware_anchor()
        if cached_mb and cached_mb.lower() not in ["none", "default string", "to be filled by o.e.m.", "0"]:
            cls._cached_mb_serial = cached_mb
            return cached_mb

        serial = ""

        # Method 1: PowerShell Get-CimInstance (Preferred on Win 10/11)
        out = cls._run_cmd_silent([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"
        ], timeout=10)
        if out and out.lower() not in ["none", "default string", "to be filled by o.e.m.", "0"]:
            serial = out.splitlines()[0].strip()

        # Method 2: WMIC Fallback (Compatible with Win 7/8)
        if not serial:
            out = cls._run_cmd_silent(["wmic", "baseboard", "get", "serialnumber"], timeout=6)
            lines = [line.strip() for line in out.splitlines() if line.strip() and "serialnumber" not in line.lower()]
            if lines and lines[0].lower() not in ["none", "default string", "to be filled by o.e.m.", "0"]:
                serial = lines[0]

        # Method 3: Windows Registry Fallback
        if not serial and sys.platform == "win32":
            try:
                import winreg
                key_path = r"HARDWARE\DESCRIPTION\System\BIOS"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
                    for val_name in ["BaseBoardSerialNumber", "SystemSerialNumber"]:
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val and str(val).strip().lower() not in ["none", "default string", "to be filled by o.e.m.", "0"]:
                                serial = str(val).strip()
                                break
                        except Exception:
                            continue
            except Exception:
                pass

        # Final Fallback: if hardware reports a generic string, combine Product and Manufacturer
        if not serial:
            out_prod = cls._run_cmd_silent([
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty Product"
            ], timeout=10)
            serial = f"MB-{out_prod.strip()}" if out_prod.strip() else "MB-STANDARD-SERIAL-2006"

        cls._cached_mb_serial = serial
        cls._save_hardware_anchor_to_registry(mb=serial)
        return serial

    @classmethod
    def get_cpu_id(cls) -> str:
        """
        Retrieves CPU Processor ID using resilient mechanisms:
        1. Fast in-memory cache
        2. Hardware anchor cache (validated against Windows MachineGuid)
        3. PowerShell Get-CimInstance (timeout=10)
        4. WMIC CPU
        5. Windows Registry (CentralProcessor)
        """
        if cls._cached_cpu_id:
            return cls._cached_cpu_id

        # Check Hardware Anchor cache (avoids running slow PowerShell on cold boot)
        _, cached_cpu, _ = cls._get_cached_hardware_anchor()
        if cached_cpu and cached_cpu.lower() not in ["none", "0"]:
            cls._cached_cpu_id = cached_cpu
            return cached_cpu

        cpu_id = ""

        # Method 1: PowerShell Get-CimInstance
        out = cls._run_cmd_silent([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty ProcessorId"
        ], timeout=10)
        if out:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if lines:
                cpu_id = lines[0]

        # Method 2: WMIC CPU
        if not cpu_id:
            out = cls._run_cmd_silent(["wmic", "cpu", "get", "processorid"], timeout=6)
            lines = [line.strip() for line in out.splitlines() if line.strip() and "processorid" not in line.lower()]
            if lines:
                cpu_id = lines[0]

        # Method 3: Windows Registry Fallback
        if not cpu_id and sys.platform == "win32":
            try:
                import winreg
                key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
                    for val_name in ["Identifier", "ProcessorNameString"]:
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val:
                                cpu_id = str(val).strip()
                                break
                        except Exception:
                            continue
            except Exception:
                pass

        if not cpu_id:
            cpu_id = "CPU-STANDARD-ID-2006"

        cls._cached_cpu_id = cpu_id
        cls._save_hardware_anchor_to_registry(cpu=cpu_id)
        return cpu_id

    @classmethod
    def get_machine_hwid(cls) -> str:
        """
        Generates deterministic 16-character cryptographic machine HWID
        bound strictly to Motherboard Serial and CPU Processor ID.
        Format: YALDA-XXXX-XXXX-XXXX-XXXX
        """
        if cls._cached_hwid:
            return cls._cached_hwid

        # Check Hardware Anchor cache for instantaneous startup
        _, _, cached_hwid = cls._get_cached_hardware_anchor()
        if cached_hwid and cached_hwid.startswith("YALDA-"):
            cls._cached_hwid = cached_hwid
            return cached_hwid

        mb = cls.get_motherboard_serial().strip()
        cpu = cls.get_cpu_id().strip()
        raw = f"MB:{mb}|CPU:{cpu}"

        h = hmac.new(cls._HW_SALT, raw.encode("utf-8"), hashlib.sha256).hexdigest().upper()
        hwid = f"YALDA-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"
        cls._cached_hwid = hwid
        cls._save_hardware_anchor_to_registry(mb=mb, cpu=cpu, hwid=hwid)
        return hwid

    @classmethod
    def generate_activation_signature(cls, hwid: str) -> str:
        """
        Generates HMAC-SHA256 signature validating that this specific HWID
        has been activated by the admin.
        """
        clean_hwid = hwid.strip().upper()
        return hmac.new(cls._ACTIVATION_SALT, clean_hwid.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    @classmethod
    def verify_machine_license(cls, saved_signature: str, current_hwid: Optional[str] = None) -> bool:
        """
        Verifies if the saved activation signature matches the current machine's HWID.
        Returns True if hardware matches, False if folder was copied to a different PC.
        Resilient against cold-boot slowdowns via MachineGuid anchor verification.
        """
        if not saved_signature or not str(saved_signature).strip():
            return False

        clean_sig = str(saved_signature).strip().upper()
        hwid = current_hwid or cls.get_machine_hwid()
        expected = cls.generate_activation_signature(hwid)

        # Primary check: direct signature match with current HWID
        if hmac.compare_digest(clean_sig, expected):
            return True

        # Persistent anchor check: if MachineGuid matches this machine and stored HWID matches signature
        persistent_hwid = cls.get_persistent_machine_hwid()
        if persistent_hwid:
            persistent_expected = cls.generate_activation_signature(persistent_hwid)
            if hmac.compare_digest(clean_sig, persistent_expected):
                # Verify that MachineGuid matches the physical machine
                current_guid = cls.get_windows_machine_guid()
                cached_mb, cached_cpu, cached_hwid = cls._get_cached_hardware_anchor()
                if current_guid and (cached_hwid == persistent_hwid or persistent_hwid == hwid):
                    cls._cached_hwid = persistent_hwid
                    return True

        return False

    @classmethod
    def get_hardware_summary(cls) -> Dict[str, str]:
        """Returns readable summary of the current machine's hardware identification."""
        return {
            "motherboard_serial": cls.get_motherboard_serial(),
            "cpu_id": cls.get_cpu_id(),
            "hwid": cls.get_machine_hwid(),
            "machine_guid": cls.get_windows_machine_guid()
        }

    @classmethod
    def _get_persistent_license_file_paths(cls) -> List[Path]:
        """Returns the machine-persistent license file paths in AppData (both Nemov and YaldaGym)."""
        paths = []
        base_appdata = Path(os.environ.get("APPDATA", Path.home()))
        for folder_name in cls.APPDATA_FOLDERS:
            folder = base_appdata / folder_name
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            paths.append(folder / "hardware_license.sig")
        return paths

    @classmethod
    def _get_persistent_license_file_path(cls) -> Path:
        """Backward compatible helper returning primary AppData path."""
        paths = cls._get_persistent_license_file_paths()
        return paths[0]

    @classmethod
    def save_machine_license_persistent(cls, hwid: str, signature: str):
        """
        Persists activation signature to both AppData files and Windows Registry across Nemov & YaldaGym.
        Ensures that when an installer/update extracts a fresh database or overwrites files,
        or when the PC is rebooted/shut down, the machine remains permanently activated.
        """
        clean_hwid = hwid.strip().upper()
        clean_sig = signature.strip().upper()
        guid = cls.get_windows_machine_guid()
        mb = cls._cached_mb_serial or cls.get_motherboard_serial()
        cpu = cls._cached_cpu_id or cls.get_cpu_id()

        # 1. Save to AppData files (Nemov & YaldaGym)
        for p in cls._get_persistent_license_file_paths():
            try:
                p.write_text(f"{clean_hwid}:{clean_sig}:{guid}", encoding="utf-8")
            except Exception:
                pass

        # 2. Save to Windows Registry (Nemov & YaldaGym)
        if sys.platform == "win32":
            try:
                import winreg
                for key_path in cls.REGISTRY_APP_KEYS:
                    try:
                        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                            winreg.SetValueEx(key, "LicenseHWID", 0, winreg.REG_SZ, clean_hwid)
                            winreg.SetValueEx(key, "LicenseSignature", 0, winreg.REG_SZ, clean_sig)
                            if guid:
                                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, guid)
                            if mb:
                                winreg.SetValueEx(key, "CachedMB", 0, winreg.REG_SZ, mb)
                            if cpu:
                                winreg.SetValueEx(key, "CachedCPU", 0, winreg.REG_SZ, cpu)
                            winreg.SetValueEx(key, "CachedHWID", 0, winreg.REG_SZ, clean_hwid)
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    def clear_machine_license_persistent(cls):
        """Clears persistent machine activation from both AppData files and Windows Registry."""
        for p in cls._get_persistent_license_file_paths():
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                import winreg
                for key_path in cls.REGISTRY_APP_KEYS:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                            for val_name in ["LicenseHWID", "LicenseSignature", "CachedHWID"]:
                                try:
                                    winreg.DeleteValue(key, val_name)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    def get_persistent_machine_signature(cls) -> Optional[str]:
        """Reads persistent activation signature from Windows Registry or AppData files."""
        # 1. Try Windows Registry (Nemov then YaldaGym)
        if sys.platform == "win32":
            try:
                import winreg
                for key_path in cls.REGISTRY_APP_KEYS:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                            sig, _ = winreg.QueryValueEx(key, "LicenseSignature")
                            if sig and str(sig).strip():
                                return str(sig).strip().upper()
                    except Exception:
                        continue
            except Exception:
                pass

        # 2. Try AppData files (Nemov then YaldaGym)
        for p in cls._get_persistent_license_file_paths():
            try:
                if p.exists():
                    content = p.read_text(encoding="utf-8").strip()
                    if ":" in content:
                        parts = content.split(":")
                        if len(parts) >= 2 and parts[1].strip():
                            return parts[1].strip().upper()
            except Exception:
                pass

        return None

    @classmethod
    def get_persistent_machine_hwid(cls) -> Optional[str]:
        """Reads persistent activation HWID from Windows Registry or AppData files."""
        # 1. Try Windows Registry (Nemov then YaldaGym)
        if sys.platform == "win32":
            try:
                import winreg
                for key_path in cls.REGISTRY_APP_KEYS:
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                            hwid, _ = winreg.QueryValueEx(key, "LicenseHWID")
                            if hwid and str(hwid).strip():
                                return str(hwid).strip().upper()
                    except Exception:
                        continue
            except Exception:
                pass

        # 2. Try AppData files (Nemov then YaldaGym)
        for p in cls._get_persistent_license_file_paths():
            try:
                if p.exists():
                    content = p.read_text(encoding="utf-8").strip()
                    if ":" in content:
                        parts = content.split(":")
                        if len(parts) >= 1 and parts[0].strip():
                            return parts[0].strip().upper()
            except Exception:
                pass

        return None

    @classmethod
    def is_machine_permanently_activated(cls) -> bool:
        """Checks if this physical machine was previously activated and verified by admin."""
        sig = cls.get_persistent_machine_signature()
        if not sig:
            return False
        return cls.verify_machine_license(sig)
