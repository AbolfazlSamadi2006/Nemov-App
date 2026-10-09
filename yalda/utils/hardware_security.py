import os
import sys
import subprocess
import hashlib
import hmac
from pathlib import Path
from typing import Optional, Dict

class HardwareSecurity:
    """
    Hardware-locked security and machine fingerprinting engine for Yalda Gym.
    Extracts Motherboard Serial and CPU Processor ID with multi-layer silent fallbacks
    (PowerShell CIM, WMIC, Windows Registry) ensuring compatibility across all Windows versions
    without displaying any console windows.
    """

    _cached_mb_serial: Optional[str] = None
    _cached_cpu_id: Optional[str] = None
    _cached_hwid: Optional[str] = None

    # Secret salt keys for hardware-bound hashing
    _HW_SALT = b"Yalda_Gym_Master_HW_Salt_2006_Abolfazl"
    _ACTIVATION_SALT = b"Yalda_Gym_Master_Activation_Key_2006_Admin_Abolfazl"

    @classmethod
    def _run_cmd_silent(cls, cmd_list, timeout=4) -> str:
        """Executes a command completely silently (no console window flash)."""
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
    def get_motherboard_serial(cls) -> str:
        """
        Retrieves Motherboard Serial Number using 3 resilient fallback mechanisms:
        1. PowerShell Get-CimInstance
        2. WMIC BaseBoard
        3. Windows Registry (BIOS/BaseBoard)
        """
        if cls._cached_mb_serial:
            return cls._cached_mb_serial

        serial = ""

        # Method 1: PowerShell Get-CimInstance (Preferred on Win 10/11)
        out = cls._run_cmd_silent([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"
        ])
        if out and out.lower() not in ["none", "default string", "to be filled by o.e.m.", "0"]:
            serial = out.splitlines()[0].strip()

        # Method 2: WMIC Fallback (Compatible with Win 7/8)
        if not serial:
            out = cls._run_cmd_silent(["wmic", "baseboard", "get", "serialnumber"])
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
            ])
            serial = f"MB-{out_prod.strip()}" if out_prod.strip() else "MB-STANDARD-SERIAL-2006"

        cls._cached_mb_serial = serial
        return serial

    @classmethod
    def get_cpu_id(cls) -> str:
        """
        Retrieves CPU Processor ID using 3 resilient fallback mechanisms:
        1. PowerShell Get-CimInstance
        2. WMIC CPU
        3. Windows Registry (CentralProcessor)
        """
        if cls._cached_cpu_id:
            return cls._cached_cpu_id

        cpu_id = ""

        # Method 1: PowerShell Get-CimInstance
        out = cls._run_cmd_silent([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty ProcessorId"
        ])
        if out:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if lines:
                cpu_id = lines[0]

        # Method 2: WMIC CPU
        if not cpu_id:
            out = cls._run_cmd_silent(["wmic", "cpu", "get", "processorid"])
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

        mb = cls.get_motherboard_serial().strip()
        cpu = cls.get_cpu_id().strip()
        raw = f"MB:{mb}|CPU:{cpu}"

        h = hmac.new(cls._HW_SALT, raw.encode("utf-8"), hashlib.sha256).hexdigest().upper()
        hwid = f"YALDA-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"
        cls._cached_hwid = hwid
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
        """
        if not saved_signature:
            return False
        hwid = current_hwid or cls.get_machine_hwid()
        expected = cls.generate_activation_signature(hwid)
        return hmac.compare_digest(saved_signature.strip().upper(), expected.strip().upper())

    @classmethod
    def get_hardware_summary(cls) -> Dict[str, str]:
        """Returns readable summary of the current machine's hardware identification."""
        return {
            "motherboard_serial": cls.get_motherboard_serial(),
            "cpu_id": cls.get_cpu_id(),
            "hwid": cls.get_machine_hwid()
        }

    @classmethod
    def _get_persistent_license_file_path(cls) -> Path:
        """Returns the machine-persistent license file path in AppData."""
        appdata = Path(os.environ.get("APPDATA", Path.home())) / "YaldaGym"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "hardware_license.sig"

    @classmethod
    def save_machine_license_persistent(cls, hwid: str, signature: str):
        """
        Persists activation signature to both AppData file and Windows Registry.
        This ensures that when an installer/update extracts a fresh database or overwrites files,
        the machine remains permanently activated without needing Admin re-login.
        """
        # 1. Save to AppData file
        try:
            p = cls._get_persistent_license_file_path()
            p.write_text(f"{hwid.strip().upper()}:{signature.strip().upper()}", encoding="utf-8")
        except Exception:
            pass

        # 2. Save to Windows Registry
        if sys.platform == "win32":
            try:
                import winreg
                key_path = r"Software\YaldaGym"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, "LicenseHWID", 0, winreg.REG_SZ, hwid.strip().upper())
                    winreg.SetValueEx(key, "LicenseSignature", 0, winreg.REG_SZ, signature.strip().upper())
            except Exception:
                pass

    @classmethod
    def clear_machine_license_persistent(cls):
        """Clears persistent machine activation from both AppData file and Windows Registry."""
        try:
            p = cls._get_persistent_license_file_path()
            if p.exists():
                p.unlink()
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import winreg
                key_path = r"Software\YaldaGym"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, "LicenseHWID")
                    except Exception:
                        pass
                    try:
                        winreg.DeleteValue(key, "LicenseSignature")
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    def get_persistent_machine_signature(cls) -> Optional[str]:
        """Reads persistent activation signature from AppData file or Windows Registry."""
        # 1. Try AppData file
        try:
            p = cls._get_persistent_license_file_path()
            if p.exists():
                content = p.read_text(encoding="utf-8").strip()
                if ":" in content:
                    parts = content.split(":", 1)
                    if len(parts) == 2 and parts[1]:
                        return parts[1].strip()
        except Exception:
            pass

        # 2. Try Windows Registry
        if sys.platform == "win32":
            try:
                import winreg
                key_path = r"Software\YaldaGym"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                    sig, _ = winreg.QueryValueEx(key, "LicenseSignature")
                    if sig:
                        return str(sig).strip()
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
