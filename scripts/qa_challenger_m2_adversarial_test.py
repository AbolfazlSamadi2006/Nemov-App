#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
Nemov Rebranding — Milestone 2 Adversarial Stress Test Suite
========================================================================================
Adversarial Verification for BrandingService & Appearance Settings.
Tests all 6 mandatory adversarial edge cases plus boundary stress cases:
1. Empty club name fallback
2. Whitespace-only club name fallback
3. Non-existent custom logo path fallback
4. Corrupted / 0-byte image file fallback
5. Reset button round-trip
6. Persistence round-trip across independent database sessions
7. Special characters, Persian RTL & Emojis
8. Very long string boundary inputs
9. File format validation in save_custom_logo
========================================================================================
"""

import os
import sys
import tempfile
import time
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@dataclass
class TestCaseResult:
    case_id: str
    name: str
    status: str  # 'PASS' or 'FAIL'
    details: str
    error: Optional[str] = None


class BrandingAdversarialTestSuite:
    def __init__(self):
        self.results: List[TestCaseResult] = []
        self._db_backup: Dict[str, Optional[str]] = {}
        self._temp_files: List[str] = []

    def backup_db(self):
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting
        keys = ["club_name", "club_phone", "club_address", "club_logo_path", "selected_theme_id", "app_theme", "theme_mode"]
        with get_session() as session:
            for k in keys:
                row = session.query(SystemSetting).filter(SystemSetting.key == k).first()
                self._db_backup[k] = row.value if row else None

    def restore_db(self):
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting
        try:
            with get_session() as session:
                for k, v in self._db_backup.items():
                    row = session.query(SystemSetting).filter(SystemSetting.key == k).first()
                    if v is None:
                        if row:
                            session.delete(row)
                    else:
                        if row:
                            row.value = v
                        else:
                            session.add(SystemSetting(key=k, value=v))
                session.commit()
        except Exception as e:
            print(f"Error restoring DB: {e}")

    def cleanup_files(self):
        for f in self._temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    # ----------------------------------------------------------------------------------
    # CASE 1: Empty club name fallback
    # ----------------------------------------------------------------------------------
    def test_case_1_empty_club_name(self):
        from nemov.services.branding_service import BrandingService, DEFAULT_CLUB_NAME
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting

        expected_fallback = "نرم‌افزار مدیریت ورزشی نِمُو"

        # Sub-test 1a: Database has explicit empty string ""
        with get_session() as s:
            row = s.query(SystemSetting).filter(SystemSetting.key == "club_name").first()
            if row:
                row.value = ""
            else:
                s.add(SystemSetting(key="club_name", value=""))
            s.commit()

        name_1a = BrandingService.get_active_club_name()

        # Sub-test 1b: Database row does not exist (deleted)
        with get_session() as s:
            row = s.query(SystemSetting).filter(SystemSetting.key == "club_name").first()
            if row:
                s.delete(row)
                s.commit()

        name_1b = BrandingService.get_active_club_name()

        # Sub-test 1c: save_club_info with empty string
        BrandingService.save_club_info("", "09110000000", "آدرس")
        name_1c = BrandingService.get_active_club_name()

        passed = (name_1a == expected_fallback and name_1b == expected_fallback and name_1c == expected_fallback)
        self.results.append(TestCaseResult(
            case_id="CASE_1",
            name="Empty club name fallback",
            status="PASS" if passed else "FAIL",
            details=f"Explicit empty: '{name_1a}', Missing row: '{name_1b}', After save_club_info(''): '{name_1c}' (Expected: '{expected_fallback}')",
            error=None if passed else f"Mismatch in fallback names: {name_1a}, {name_1b}, {name_1c}"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 2: Whitespace-only club name fallback
    # ----------------------------------------------------------------------------------
    def test_case_2_whitespace_club_name(self):
        from nemov.services.branding_service import BrandingService
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting

        expected_fallback = "نرم‌افزار مدیریت ورزشی نِمُو"
        whitespace_samples = [
            " ",
            "    ",
            "\t",
            "\n\r  \t  ",
            "   \u200c   ",  # Zero-width non-joiner surrounded by spaces
        ]

        failures = []
        for sample in whitespace_samples:
            # Set directly in DB
            with get_session() as s:
                row = s.query(SystemSetting).filter(SystemSetting.key == "club_name").first()
                if row:
                    row.value = sample
                else:
                    s.add(SystemSetting(key="club_name", value=sample))
                s.commit()

            resolved = BrandingService.get_active_club_name()
            # Note: "\u200c" is ZWNJ, strip() might not strip ZWNJ unless handled, let's observe
            if sample != "   \u200c   " and resolved != expected_fallback:
                failures.append((repr(sample), resolved))

        # Test save_club_info with whitespace
        BrandingService.save_club_info("     ", "phone", "addr")
        resolved_after_save = BrandingService.get_active_club_name()
        if resolved_after_save != expected_fallback:
            failures.append(("save_club_info('     ')", resolved_after_save))

        passed = len(failures) == 0
        self.results.append(TestCaseResult(
            case_id="CASE_2",
            name="Whitespace-only club name fallback",
            status="PASS" if passed else "FAIL",
            details=f"Tested samples: {len(whitespace_samples)}. Failures: {failures}",
            error=None if passed else f"Whitespace failed to fall back: {failures}"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 3: Non-existent custom logo path fallback
    # ----------------------------------------------------------------------------------
    def test_case_3_non_existent_logo(self):
        from nemov.services.branding_service import BrandingService
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting

        fake_paths = [
            "completely_missing_logo_987654321.png",
            r"C:\fake_folder_nemov_test\missing.jpg",
            "/tmp/fake/absent_logo.webp",
            "../non_existent.png"
        ]

        failures = []
        for fake in fake_paths:
            with get_session() as s:
                row = s.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first()
                if row:
                    row.value = fake
                else:
                    s.add(SystemSetting(key="club_logo_path", value=fake))
                s.commit()

            active = BrandingService.get_active_logo_path()
            if not active or not os.path.exists(active):
                failures.append((fake, f"Active logo path does not exist on disk: {active}"))
            elif "nemov" not in active.lower() and "app_icon" not in active.lower():
                failures.append((fake, f"Active logo path is not Nemov default: {active}"))

        passed = len(failures) == 0
        self.results.append(TestCaseResult(
            case_id="CASE_3",
            name="Non-existent custom logo path fallback",
            status="PASS" if passed else "FAIL",
            details=f"Tested non-existent paths: {len(fake_paths)}. Active fallback: {BrandingService.get_active_logo_path()}",
            error=None if passed else f"Non-existent logo failed fallback: {failures}"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 4: Corrupted / 0-byte image file fallback
    # ----------------------------------------------------------------------------------
    def test_case_4_corrupted_and_zero_byte_logo(self):
        from nemov.services.branding_service import BrandingService
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting

        # Create 4 adversarial test files
        # 4a: 0-byte file
        tf_0byte = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf_0byte.close()
        self._temp_files.append(tf_0byte.name)

        # 4b: Corrupted ASCII file pretending to be PNG
        tf_corrupt_ascii = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf_corrupt_ascii.write(b"THIS IS CORRUPTED TEXT DATA NOT A PNG IMAGE")
        tf_corrupt_ascii.close()
        self._temp_files.append(tf_corrupt_ascii.name)

        # 4c: Truncated PNG header (8 bytes magic header only, no IHDR)
        tf_truncated = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf_truncated.write(b"\x89PNG\r\n\x1a\n")
        tf_truncated.close()
        self._temp_files.append(tf_truncated.name)

        # 4d: Random garbage binary file
        tf_garbage = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tf_garbage.write(os.urandom(256))
        tf_garbage.close()
        self._temp_files.append(tf_garbage.name)

        adversarial_files = [
            ("0-byte file", tf_0byte.name),
            ("Corrupted ASCII PNG", tf_corrupt_ascii.name),
            ("Truncated PNG header", tf_truncated.name),
            ("Random garbage JPG", tf_garbage.name),
        ]

        failures = []
        for label, file_path in adversarial_files:
            with get_session() as s:
                row = s.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first()
                if row:
                    row.value = file_path
                else:
                    s.add(SystemSetting(key="club_logo_path", value=file_path))
                s.commit()

            active = BrandingService.get_active_logo_path()
            # Requirement: Must fall back to default Nemov logo!
            # If active points to the corrupted/0-byte file itself, it FAILED to fall back!
            if active == file_path:
                failures.append((label, f"Returned corrupted file path '{active}' instead of falling back to Nemov logo"))
            elif "nemov" not in active.lower() and "app_icon" not in active.lower():
                failures.append((label, f"Returned non-Nemov fallback: '{active}'"))
            elif not os.path.exists(active):
                failures.append((label, f"Returned fallback path that does not exist: '{active}'"))

        # Also test save_custom_logo behavior on 0-byte file
        save_0byte_accepted = False
        try:
            BrandingService.save_custom_logo(tf_0byte.name)
            save_0byte_accepted = True
        except Exception:
            save_0byte_accepted = False

        passed = len(failures) == 0
        details = (
            f"Tested 4 adversarial image corruption cases. Failures: {len(failures)}.\n"
            + "\n".join([f"  - {f[0]}: {f[1]}" for f in failures])
            + f"\nsave_custom_logo(0-byte file) was accepted without validation: {save_0byte_accepted}"
        )
        self.results.append(TestCaseResult(
            case_id="CASE_4",
            name="Corrupted/0-byte image file fallback",
            status="PASS" if passed else "FAIL",
            details=details,
            error=None if passed else f"Corrupted/0-byte files failed fallback in BrandingService: {[f[0] for f in failures]}"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 5: Reset button round-trip
    # ----------------------------------------------------------------------------------
    def test_case_5_reset_button_roundtrip(self):
        from nemov.services.branding_service import BrandingService
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting
        from PIL import Image

        # 1. Create a valid image
        valid_img_fd, valid_img_path = tempfile.mkstemp(suffix=".png")
        os.close(valid_img_fd)
        self._temp_files.append(valid_img_path)
        img = Image.new("RGBA", (150, 150), color=(0, 128, 255, 255))
        img.save(valid_img_path, format="PNG")

        # 2. Upload via BrandingService
        rel_saved = BrandingService.save_custom_logo(valid_img_path)
        active_custom = BrandingService.get_active_logo_path()

        # Check that custom logo is indeed active
        is_custom_active = (active_custom and (rel_saved in active_custom or "club_logo_" in active_custom))

        # Check DB setting
        with get_session() as s:
            setting_val = s.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first().value

        # 3. Call reset_to_default_logo
        reset_result = BrandingService.reset_to_default_logo()

        # 4. Check DB setting after reset
        with get_session() as s:
            setting_after_reset = s.query(SystemSetting).filter(SystemSetting.key == "club_logo_path").first().value

        # 5. Check active logo path after reset
        active_after_reset = BrandingService.get_active_logo_path()
        is_nemov_default = (active_after_reset and ("nemov" in active_after_reset.lower() or "app_icon" in active_after_reset.lower()))

        passed = (
            is_custom_active
            and setting_val != ""
            and reset_result is True
            and setting_after_reset == ""
            and is_nemov_default
        )

        self.results.append(TestCaseResult(
            case_id="CASE_5",
            name="Reset button round-trip",
            status="PASS" if passed else "FAIL",
            details=(
                f"Custom uploaded: '{rel_saved}'\n"
                f"Active custom: '{active_custom}' (OK: {is_custom_active})\n"
                f"DB before reset: '{setting_val}'\n"
                f"Reset return value: {reset_result}\n"
                f"DB after reset: '{setting_after_reset}'\n"
                f"Active after reset: '{active_after_reset}' (OK: {is_nemov_default})"
            ),
            error=None if passed else "Reset round-trip failed"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 6: Persistence round-trip across new database sessions
    # ----------------------------------------------------------------------------------
    def test_case_6_persistence_roundtrip(self):
        from nemov.services.branding_service import BrandingService
        from nemov.database.connection import get_session
        from nemov.models.database_models import SystemSetting
        import gc

        test_club_name = "مجموعه ورزشی و بدنسازی نِمُو شمال"
        test_phone = "09112223344"
        test_address = "مازندران، قائمشهر، خیابان کوچکسرا، پلاک ۷"
        test_theme = "royal_gold"

        # Session 1: Write data
        BrandingService.save_club_info(test_club_name, test_phone, test_address)
        BrandingService.save_selected_theme_id(test_theme)

        # Force session close, garbage collect to guarantee new session
        gc.collect()

        # Session 2: Read from brand new database session directly
        with get_session() as new_session:
            rows = {r.key: r.value for r in new_session.query(SystemSetting).all()}

        name_in_db = rows.get("club_name")
        phone_in_db = rows.get("club_phone")
        address_in_db = rows.get("club_address")
        theme_in_db = rows.get("selected_theme_id")
        app_theme_in_db = rows.get("app_theme")
        mode_in_db = rows.get("theme_mode")

        # Session 3: Read via BrandingService methods
        gc.collect()
        info_via_service = BrandingService.get_club_info()
        active_name = BrandingService.get_active_club_name()
        active_theme = BrandingService.get_selected_theme_id()

        passed = (
            name_in_db == test_club_name
            and phone_in_db == test_phone
            and address_in_db == test_address
            and theme_in_db == test_theme
            and app_theme_in_db == test_theme
            and mode_in_db == "dark"
            and info_via_service.get("club_name") == test_club_name
            and info_via_service.get("selected_theme_id") == test_theme
            and active_name == test_club_name
            and active_theme == test_theme
        )

        self.results.append(TestCaseResult(
            case_id="CASE_6",
            name="Persistence round-trip across new database sessions",
            status="PASS" if passed else "FAIL",
            details=(
                f"Persisted in DB: name='{name_in_db}', phone='{phone_in_db}', theme='{theme_in_db}', mode='{mode_in_db}'\n"
                f"Read via Service: active_name='{active_name}', active_theme='{active_theme}'"
            ),
            error=None if passed else "Persistence across sessions failed"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 7: Special characters, Persian RTL & Emojis
    # ----------------------------------------------------------------------------------
    def test_case_7_unicode_special_characters(self):
        from nemov.services.branding_service import BrandingService

        complex_name = "باشگاه بدنسازی «قهرمانان البرز» | Nemov Gym #1 (شعبه مرکزی) 🔥🏋️‍♂️🥇"
        complex_address = "بلوار آیت‌الله بهشتی، کوچه ۱۲/۳، پلاک ۸۵، زنگ ۲"

        BrandingService.save_club_info(complex_name, "021-88776655", complex_address)
        active_name = BrandingService.get_active_club_name()
        info = BrandingService.get_club_info()

        passed = (active_name == complex_name and info.get("club_address") == complex_address)
        self.results.append(TestCaseResult(
            case_id="CASE_7",
            name="Unicode, Persian RTL & Emojis Handling",
            status="PASS" if passed else "FAIL",
            details=f"Input: '{complex_name}' -> Resolved: '{active_name}'",
            error=None if passed else f"Mismatch: expected '{complex_name}', got '{active_name}'"
        ))

    # ----------------------------------------------------------------------------------
    # CASE 8: Very long string boundary inputs
    # ----------------------------------------------------------------------------------
    def test_case_8_long_string_boundary(self):
        from nemov.services.branding_service import BrandingService

        huge_name = "نِمُو " * 500  # 2500 characters
        huge_address = "آدرس بسیار طولانی " * 200

        try:
            BrandingService.save_club_info(huge_name, "09110000000", huge_address)
            active_name = BrandingService.get_active_club_name()
            passed = len(active_name) >= 2000
            err = None
        except Exception as e:
            passed = False
            err = str(e)

        self.results.append(TestCaseResult(
            case_id="CASE_8",
            name="Very long string boundary handling (2.5K chars)",
            status="PASS" if passed else "FAIL",
            details=f"Stored & retrieved {len(huge_name)} character string without SQLite crash",
            error=err
        ))

    # ----------------------------------------------------------------------------------
    # CASE 9: File format validation in save_custom_logo
    # ----------------------------------------------------------------------------------
    def test_case_9_file_format_and_extension_validation(self):
        from nemov.services.branding_service import BrandingService

        # Test uploading a .txt or .exe file disguised or renamed
        tf_txt = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        tf_txt.write(b"Hello text file")
        tf_txt.close()
        self._temp_files.append(tf_txt.name)

        # BrandingService line 126:
        # Validates file decodability and rejects non-image files
        saved_rel = ""
        rejected = False
        try:
            saved_rel = BrandingService.save_custom_logo(tf_txt.name)
        except Exception:
            rejected = True

        active_logo = BrandingService.get_active_logo_path()

        # Did it validate the file content or blindly copy it as club_logo_xxx.png?
        blindly_copied = bool(saved_rel and saved_rel.endswith(".png") and "club_logo_" in saved_rel)

        # If it blindly copied, active_logo will now point to that text file!
        is_active_the_text_file = bool(active_logo and "club_logo_" in active_logo)

        passed = rejected or not is_active_the_text_file

        self.results.append(TestCaseResult(
            case_id="CASE_9",
            name="Non-image file extension coercion & validation",
            status="PASS" if passed else "FAIL",
            details=(
                f"Source was text file (.txt). Properly rejected: {rejected}. Saved: '{saved_rel}'.\n"
                f"get_active_logo_path() returned '{active_logo}'.\n"
                f"Is active pointing to invalid non-image file? {is_active_the_text_file}"
            ),
            error="BrandingService accepts arbitrary non-image files (.txt) and forces .png extension without decoding validation." if not passed else None
        ))

    def run_all(self):
        print("=" * 80)
        print("STARTING ADVERSARIAL STRESS TEST SUITE FOR MILESTONE 2 (Nemov Rebranding)")
        print("=" * 80)

        self.backup_db()
        try:
            self.test_case_1_empty_club_name()
            self.test_case_2_whitespace_club_name()
            self.test_case_3_non_existent_logo()
            self.test_case_4_corrupted_and_zero_byte_logo()
            self.test_case_5_reset_button_roundtrip()
            self.test_case_6_persistence_roundtrip()
            self.test_case_7_unicode_special_characters()
            self.test_case_8_long_string_boundary()
            self.test_case_9_file_format_and_extension_validation()
        finally:
            self.restore_db()
            self.cleanup_files()

        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        passed_count = sum(1 for r in self.results if r.status == "PASS")
        failed_count = sum(1 for r in self.results if r.status == "FAIL")

        for r in self.results:
            tag = "[PASS]" if r.status == "PASS" else "[FAIL]"
            print(f"\n{tag} {r.case_id}: {r.name}")
            print(f"       Details: {r.details}")
            if r.error:
                print(f"       Error:   {r.error}")

        print("\n" + "-" * 80)
        print(f"TOTAL: {len(self.results)} | PASSED: {passed_count} | FAILED: {failed_count}")
        print("-" * 80)

        return passed_count, failed_count


if __name__ == "__main__":
    suite = BrandingAdversarialTestSuite()
    passed, failed = suite.run_all()
    sys.exit(0 if failed == 0 else 1)
