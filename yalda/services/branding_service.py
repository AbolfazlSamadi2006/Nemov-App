#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized Branding Service for Nemov Sports Management Desktop.
Handles club profile data, logo upload/reset, active theme persistence,
and fallback logic for active logo & club name.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import config
from yalda.database.connection import get_session, mark_data_changed
from yalda.models.database_models import SystemSetting
from yalda.utils.image_utils import resolve_image_path

LIGHT_PALETTES = {
    "olympic_white",
    "clinical_cyan",
    "fresh_mint",
    "champagne_gold",
    "soft_orchid",
}

DEFAULT_CLUB_NAME = "نرم‌افزار مدیریت ورزشی نِمُو"
DEFAULT_THEME_ID = "crimson_fury"


class BrandingService:
    """Centralized manager for club branding, logo assets, and visual appearance settings."""

    @staticmethod
    def get_club_info() -> Dict[str, Any]:
        """
        Retrieves all branding settings from the SQLite SystemSetting table.
        Returns a dictionary containing:
        - club_name
        - club_phone
        - club_address
        - club_logo_path
        - selected_theme_id
        - app_theme
        - theme_mode
        """
        info = {
            "club_name": "",
            "club_phone": "",
            "club_address": "",
            "club_logo_path": "",
            "selected_theme_id": DEFAULT_THEME_ID,
            "app_theme": DEFAULT_THEME_ID,
            "theme_mode": "dark",
        }

        try:
            session = get_session()
            try:
                target_keys = [
                    "club_name",
                    "club_phone",
                    "club_address",
                    "club_logo_path",
                    "selected_theme_id",
                    "app_theme",
                    "theme_mode",
                ]
                rows = session.query(SystemSetting).filter(SystemSetting.key.in_(target_keys)).all()
                for r in rows:
                    if r.key in info:
                        info[r.key] = r.value or ""

                # Synchronize theme id if one was stored
                theme = info["selected_theme_id"] or info["app_theme"] or DEFAULT_THEME_ID
                info["selected_theme_id"] = theme
                info["app_theme"] = theme
                if not info["theme_mode"]:
                    info["theme_mode"] = "light" if theme in LIGHT_PALETTES else "dark"

                return info
            finally:
                session.close()
        except Exception:
            # Safe fallback dictionary if database connection or lock fails
            return info

    @staticmethod
    def save_club_info(name: str, phone: str, address: str) -> bool:
        """
        Persists club name, phone, and address into the SQLite SystemSetting table.
        """
        session = get_session()
        try:
            data = {
                "club_name": (name or "").strip(),
                "club_phone": (phone or "").strip(),
                "club_address": (address or "").strip(),
            }
            for k, v in data.items():
                setting = session.query(SystemSetting).filter(SystemSetting.key == k).first()
                if not setting:
                    setting = SystemSetting(key=k, value=v)
                    session.add(setting)
                else:
                    setting.value = v

            session.commit()
            mark_data_changed()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def save_custom_logo(source_image_path: str) -> str:
        """
        Validates and copies source image into config.BRANDING_DIR with a UUID filename,
        mirrors to AppData branding directory, updates club_logo_path in SystemSetting,
        and returns the stored relative filename.
        """
        src = Path(source_image_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source logo image not found: {source_image_path}")
        if src.stat().st_size == 0:
            raise ValueError("Source logo image file is empty (0 bytes).")
        try:
            from PIL import Image
            with Image.open(src) as img:
                img.verify()
        except Exception as e:
            raise ValueError(f"Source logo image is corrupted or invalid: {e}")

        ext = src.suffix.lower() if src.suffix else ".png"
        if ext not in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
            ext = ".png"

        unique_filename = f"club_logo_{uuid.uuid4().hex[:12]}{ext}"

        # Ensure branding directory in runtime data
        branding_dir = getattr(config, "BRANDING_DIR", config.DATA_DIR / "branding")
        branding_dir.mkdir(parents=True, exist_ok=True)
        dest_runtime = branding_dir / unique_filename
        shutil.copy2(str(src), str(dest_runtime))

        # Mirror to AppData for persistent storage across updates
        try:
            appdata_branding = config.APPDATA_DATA_DIR / "branding"
            appdata_branding.mkdir(parents=True, exist_ok=True)
            dest_appdata = appdata_branding / unique_filename
            shutil.copy2(str(src), str(dest_appdata))
        except Exception:
            pass

        # Update database setting
        session = get_session()
        try:
            setting = session.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first()
            if not setting:
                setting = SystemSetting(key="club_logo_path", value=unique_filename)
                session.add(setting)
            else:
                setting.value = unique_filename
            session.commit()
            mark_data_changed()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return unique_filename

    @staticmethod
    def reset_to_default_logo() -> bool:
        """
        Clears club_logo_path in SystemSetting (sets to empty string ""),
        reverting active logo to official bundled Nemov logo.
        """
        session = get_session()
        try:
            setting = session.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first()
            if setting:
                setting.value = ""
            else:
                setting = SystemSetting(key="club_logo_path", value="")
                session.add(setting)
            session.commit()
            mark_data_changed()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_active_logo_path() -> str:
        """
        Returns resolved absolute path to custom logo if set and exists on disk;
        otherwise safely falls back to default official Nemov logo.
        """
        info = BrandingService.get_club_info()
        custom_logo = (info.get("club_logo_path") or "").strip()
        if custom_logo:
            resolved = resolve_image_path(custom_logo)
            if resolved and os.path.exists(resolved) and os.path.isfile(resolved):
                try:
                    if os.path.getsize(resolved) > 0:
                        from PIL import Image
                        with Image.open(resolved) as img:
                            img.verify()
                        return str(Path(resolved).resolve())
                except Exception:
                    # Corrupted, unreadable, or 0-byte image file; fall back to official Nemov logo
                    pass

        # Fallback to official Nemov logos
        candidates = [
            config.BASE_DIR / "resources" / "images" / "nemov_logo.png",
            config.BASE_DIR / "resources" / "icons" / "nemov.ico",
            config.BASE_DIR / "resources" / "images" / "app_icon.png",
            config.BASE_DIR / "resources" / "images" / "logo.png",
        ]
        for cand in candidates:
            if cand.exists() and cand.is_file():
                return str(cand.resolve())

        # Return empty string if no file exists
        return ""

    @staticmethod
    def get_active_club_name() -> str:
        """
        Returns custom club name if non-empty; otherwise returns default
        'نرم‌افزار مدیریت ورزشی نِمُو'.
        """
        info = BrandingService.get_club_info()
        name = (info.get("club_name") or "").strip()
        return name if name else DEFAULT_CLUB_NAME

    @staticmethod
    def get_selected_theme_id() -> str:
        """
        Returns stored theme ID from SystemSetting, defaulting to 'crimson_fury'.
        """
        info = BrandingService.get_club_info()
        theme_id = (info.get("selected_theme_id") or info.get("app_theme") or "").strip()
        return theme_id if theme_id else DEFAULT_THEME_ID

    @staticmethod
    def save_selected_theme_id(theme_id: str) -> bool:
        """
        Persists selected_theme_id and app_theme in SystemSetting,
        and computes corresponding theme_mode ('dark' or 'light').
        """
        tid = (theme_id or DEFAULT_THEME_ID).strip()
        mode = "light" if tid in LIGHT_PALETTES else "dark"

        session = get_session()
        try:
            for k, v in [("selected_theme_id", tid), ("app_theme", tid), ("theme_mode", mode)]:
                setting = session.query(SystemSetting).filter(SystemSetting.key == k).first()
                if not setting:
                    setting = SystemSetting(key=k, value=v)
                    session.add(setting)
                else:
                    setting.value = v
            session.commit()
            mark_data_changed()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Module-level convenience bindings
get_club_info = BrandingService.get_club_info
save_club_info = BrandingService.save_club_info
save_custom_logo = BrandingService.save_custom_logo
reset_to_default_logo = BrandingService.reset_to_default_logo
get_active_logo_path = BrandingService.get_active_logo_path
get_active_club_name = BrandingService.get_active_club_name
get_selected_theme_id = BrandingService.get_selected_theme_id
save_selected_theme_id = BrandingService.save_selected_theme_id
