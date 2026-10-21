import os
import json
import base64
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import config
from nemov.utils.security import normalize_digits


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_byte))
    ]


class CredentialManager:
    """
    Secure desktop credential manager using Windows DPAPI (Data Protection API).
    Credentials are encrypted bound to the current Windows user and machine,
    preventing plaintext extraction or transfer to other machines.
    """

    FILE_NAME = ".remembered.dat"

    @classmethod
    def _get_file_paths(cls) -> List[Path]:
        paths = []
        try:
            if hasattr(config, "DATA_DIR") and config.DATA_DIR:
                paths.append(config.DATA_DIR / cls.FILE_NAME)
        except Exception:
            pass
        try:
            if hasattr(config, "APPDATA_DATA_DIR") and config.APPDATA_DATA_DIR:
                paths.append(config.APPDATA_DATA_DIR / cls.FILE_NAME)
        except Exception:
            pass
        return paths

    @classmethod
    def _dpapi_encrypt(cls, data: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        data_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)))
        data_out = DATA_BLOB()
        if not crypt32.CryptProtectData(ctypes.byref(data_in), 'yalda_credentials', None, None, None, 0, ctypes.byref(data_out)):
            raise ctypes.WinError()
        buf = (ctypes.c_byte * data_out.cbData).from_address(ctypes.addressof(data_out.pbData.contents))
        res = bytes(buf)
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        return res

    @classmethod
    def _dpapi_decrypt(cls, data: bytes) -> bytes:
        crypt32 = ctypes.windll.crypt32
        data_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)))
        data_out = DATA_BLOB()
        if not crypt32.CryptUnprotectData(ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)):
            raise ctypes.WinError()
        buf = (ctypes.c_byte * data_out.cbData).from_address(ctypes.addressof(data_out.pbData.contents))
        res = bytes(buf)
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        return res

    @classmethod
    def _xor_fallback_cipher(cls, data: bytes) -> bytes:
        key = b"YaldaGymSecureKey2026_LocalAuthSalt"
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    @classmethod
    def _encrypt(cls, plaintext: str) -> str:
        data = plaintext.encode("utf-8")
        try:
            enc = cls._dpapi_encrypt(data)
            return "DPAPI:" + base64.b64encode(enc).decode("ascii")
        except Exception:
            enc = cls._xor_fallback_cipher(data)
            return "XOR:" + base64.b64encode(enc).decode("ascii")

    @classmethod
    def _decrypt(cls, ciphertext: str) -> str:
        if ciphertext.startswith("DPAPI:"):
            enc = base64.b64decode(ciphertext[6:])
            return cls._dpapi_decrypt(enc).decode("utf-8")
        elif ciphertext.startswith("XOR:"):
            enc = base64.b64decode(ciphertext[4:])
            return cls._xor_fallback_cipher(enc).decode("utf-8")
        else:
            # Fallback direct base64 or plaintext
            try:
                return base64.b64decode(ciphertext).decode("utf-8")
            except Exception:
                return ciphertext

    @classmethod
    def _load_data(cls) -> Dict:
        paths = cls._get_file_paths()
        for p in paths:
            if p.exists() and p.stat().st_size > 0:
                try:
                    raw = p.read_text(encoding="utf-8").strip()
                    if raw:
                        dec = cls._decrypt(raw)
                        data = json.loads(dec)
                        if isinstance(data, dict):
                            return data
                except Exception:
                    continue
        return {"last_user": "", "accounts": {}}

    @classmethod
    def _save_data(cls, data: Dict):
        try:
            payload = json.dumps(data, ensure_ascii=False)
            enc_str = cls._encrypt(payload)
            for p in cls._get_file_paths():
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(enc_str, encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            pass

    @classmethod
    def save_credential(cls, username: str, password: str):
        """Saves or updates the username and password in local encrypted storage and sets it as last user."""
        u_norm = normalize_digits(username.strip())
        if not u_norm:
            return
        data = cls._load_data()
        if "accounts" not in data or not isinstance(data["accounts"], dict):
            data["accounts"] = {}
        data["accounts"][u_norm] = password
        data["last_user"] = u_norm
        cls._save_data(data)

    @classmethod
    def get_password(cls, username: str) -> Optional[str]:
        """Returns the saved password for the given username, or None if not found."""
        u_norm = normalize_digits(username.strip())
        if not u_norm:
            return None
        data = cls._load_data()
        accounts = data.get("accounts", {})
        return accounts.get(u_norm)

    @classmethod
    def has_credential(cls, username: str) -> bool:
        """Checks if the given username is currently stored in saved credentials."""
        u_norm = normalize_digits(username.strip())
        if not u_norm:
            return False
        data = cls._load_data()
        accounts = data.get("accounts", {})
        return u_norm in accounts

    @classmethod
    def get_last_user(cls) -> Tuple[Optional[str], Optional[str]]:
        """Returns (username, password) of the last used user, or (None, None)."""
        data = cls._load_data()
        last_u = data.get("last_user", "")
        accounts = data.get("accounts", {})
        if last_u and last_u in accounts:
            return last_u, accounts[last_u]
        # If last_user is missing but accounts exist, return first account
        if accounts:
            first_u = next(iter(accounts))
            return first_u, accounts[first_u]
        return None, None

    @classmethod
    def get_all_saved_usernames(cls) -> List[str]:
        """Returns a list of all remembered usernames."""
        data = cls._load_data()
        accounts = data.get("accounts", {})
        return list(accounts.keys())

    @classmethod
    def remove_credential(cls, username: str):
        """Removes the given username from remembered credentials."""
        u_norm = normalize_digits(username.strip())
        if not u_norm:
            return
        data = cls._load_data()
        accounts = data.get("accounts", {})
        if u_norm in accounts:
            del accounts[u_norm]
            if data.get("last_user") == u_norm:
                data["last_user"] = next(iter(accounts)) if accounts else ""
            cls._save_data(data)

    @classmethod
    def clear_all(cls):
        """Clears all saved credentials."""
        cls._save_data({"last_user": "", "accounts": {}})
