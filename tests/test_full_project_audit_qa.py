import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestFullProjectAuditQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.db_path = Path(cls.tmp_dir.name) / "audit_test.db"

        import nemov.database.connection as db_conn
        from nemov.models.database_models import Base, User
        from nemov.utils.security import hash_password
        from nemov.auth.authentication import CurrentUser

        cls._orig_engine = db_conn.engine
        cls._orig_session_local = db_conn.SessionLocal

        cls.test_engine = create_engine(
            f"sqlite:///{cls.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(cls.test_engine)
        db_conn.engine = cls.test_engine
        db_conn.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=cls.test_engine, expire_on_commit=False)
        )
        db_conn.check_and_migrate_db()

        s = db_conn.get_session()
        admin_user = User(
            username="admin_audit",
            password_hash=hash_password("Admin@1234"),
            role="admin",
            first_name="مدیر",
            last_name="باشگاه",
            phone="09120000000",
        )
        s.add(admin_user)
        s.commit()
        s.refresh(admin_user)
        s.close()

        cls._orig_user = getattr(CurrentUser, "_user", None)
        CurrentUser.set(admin_user)

    @classmethod
    def tearDownClass(cls):
        import nemov.database.connection as db_conn
        from nemov.auth.authentication import CurrentUser

        try:
            db_conn.SessionLocal.remove()
            cls.test_engine.dispose()
        except Exception:
            pass
        db_conn.engine = cls._orig_engine
        db_conn.SessionLocal = cls._orig_session_local
        CurrentUser._user = cls._orig_user
        cls.tmp_dir.cleanup()

    def _pump(self):
        self.app.processEvents()

    # ------------------------------------------------------------------
    # 1. Core Services End-to-End CRUD on Isolated SQLite DB
    # ------------------------------------------------------------------
    def _ensure_seeded(self):
        if hasattr(self.__class__, "_seeded_ids"):
            return self.__class__._seeded_ids

        from nemov.database.connection import check_and_migrate_db
        from nemov.services.member_service import MemberService
        from nemov.services.workout_service import WorkoutService
        from nemov.services.nutrition_service import NutritionService
        from nemov.services.accounting_service import AccountingService
        from nemov.services.branding_service import BrandingService
        from nemov.utils.jalali_date import get_today_shamsi, add_days_shamsi

        check_and_migrate_db()
        today = get_today_shamsi()
        future_exp = add_days_shamsi(today, 30)

        member = MemberService.create_member({
            "first_name": "آرش",
            "last_name": "تست‌پروژه",
            "phone": "09123456789",
            "gender": "male",
            "birth_date_shamsi": "1378/04/15",
            "height_cm": 178.0,
            "initial_weight_kg": 76.5,
            "membership_type": "12_sessions",
            "registration_date_shamsi": today,
            "membership_start_shamsi": today,
            "membership_expire_shamsi": future_exp,
            "activity_level": "moderately_active",
        })
        self.assertIsNotNone(member.id)
        fetched = MemberService.get_member_by_id(member.id)
        self.assertEqual(fetched.phone, "09123456789")
        self.assertEqual(fetched.status, "active")
        self.assertGreaterEqual(len(MemberService.get_all_members(search_query="آرش")), 1)

        MemberService.update_health_record(member.id, {
            "has_allergy": True,
            "allergy_details": "ندارد",
            "has_medication_restriction": True,
            "medication_restriction_details": "مولتی‌ویتامین",
        })
        hr = MemberService.get_health_record(member.id)
        self.assertIsNotNone(hr)
        self.assertEqual(hr.allergy_details, "ندارد")

        ex = WorkoutService.create_exercise({
            "name_fa": "پرس سینه هالتر تستی",
            "primary_muscle": "chest",
            "equipment": "barbell",
            "description": "اجرای کنترل‌شده",
        })
        wplan = WorkoutService.create_workout_plan(
            {
                "title": "برنامه حجمی تست کامل",
                "goal": "hypertrophy",
                "days_per_week": 1,
                "training_level": "intermediate",
                "is_template": True,
            },
            [{
                "day_number": 1,
                "day_title": "روز ۱: سینه",
                "exercises": [{
                    "exercise_id": ex.id,
                    "sets": "4",
                    "reps": "10",
                    "weight_suggestion": "60",
                    "rest_seconds": "90",
                    "tempo": "2-0-2-0",
                    "trainer_notes": "نکته تستی",
                }],
            }],
        )
        asgn_w = WorkoutService.assign_plan_to_member(member.id, wplan.id)
        self.assertIsNotNone(asgn_w.id)
        self.assertIsNotNone(WorkoutService.get_active_assignment(member.id))

        food = NutritionService.create_food({
            "name_fa": "سینه مرغ گریل",
            "category": "meat",
            "unit": "۱۰۰ گرم",
            "calories": 165,
            "protein_g": 31,
            "carbs_g": 0,
            "fat_g": 3.6,
        })
        nplan = NutritionService.create_nutrition_plan(
            {
                "title": "رژیم پروتئینی تست",
                "goal": "muscle_gain",
                "target_calories": 2500,
                "target_protein": 180,
                "target_carbs": 250,
                "target_fat": 70,
                "is_template": True,
            },
            [{
                "meal_name": "صبحانه",
                "items": [{
                    "food_id": food.id,
                    "amount": "2",
                    "notes": "وعده تستی",
                }],
            }],
        )
        asgn_n = NutritionService.assign_nutrition_plan(member.id, nplan.id)
        self.assertIsNotNone(asgn_n.id)
        self.assertIsNotNone(NutritionService.get_active_assignment(member.id))

        AccountingService.add_tuition_payment(
            member_id=member.id,
            amount=1500000,
            payment_date_shamsi=today,
            payment_type="شهریه دوره ماهانه",
            notes="شهریه آزمایشی",
        )
        AccountingService.add_expense(
            title="خرید دمبل تستی",
            amount=500000,
            expense_date_shamsi=today,
            category="تجهیزات",
            description="هزینه تست",
        )
        summary = AccountingService.get_financial_summary(start_date=today, end_date=today)
        self.assertEqual(int(summary.get("total_income", 0)), 1500000)
        self.assertEqual(int(summary.get("total_expense", 0)), 500000)

        info = BrandingService.get_club_info()
        self.assertIsInstance(info, dict)
        self.assertTrue(bool(BrandingService.get_active_logo_path()))

        self.__class__._seeded_ids = (member.id, wplan.id, nplan.id, today)
        return self.__class__._seeded_ids

    def test_01_services_crud_and_migrations_end_to_end(self):
        self._ensure_seeded()

    # ------------------------------------------------------------------
    # 2. Utilities, Security, PDF & Excel Exports
    # ------------------------------------------------------------------
    def test_02_utilities_security_pdf_and_excel_exports(self):
        import openpyxl
        from nemov.utils.jalali_date import (
            normalize_digits, is_valid_shamsi, shamsi_to_gregorian,
            gregorian_to_shamsi, add_days_shamsi, add_months_shamsi,
        )
        from nemov.utils.bmr_calculator import calculate_bmr_tdee, calculate_age_from_shamsi
        from nemov.utils.duplicate_helper import extract_root_and_number, get_next_numbered_name
        from nemov.utils.security import hash_password, verify_password
        from nemov.pdf.pdf_generator import PDFGenerator
        from nemov.utils.excel_generator import ExcelGenerator
        from nemov.services.member_service import MemberService
        from nemov.services.workout_service import WorkoutService
        from nemov.services.nutrition_service import NutritionService
        from nemov.services.accounting_service import AccountingService

        # Jalali dates
        self.assertEqual(normalize_digits("۱۴۰۵/۰۹/۰۵"), "1405/09/05")
        self.assertTrue(is_valid_shamsi("1403/12/30"))  # 1403 leap year
        self.assertFalse(is_valid_shamsi("1404/12/30"))  # 1404 non-leap
        self.assertFalse(is_valid_shamsi(""))
        g = shamsi_to_gregorian("1405/01/01")
        self.assertEqual(gregorian_to_shamsi(g), "1405/01/01")
        self.assertEqual(add_days_shamsi("1405/01/01", 10), "1405/01/11")
        self.assertEqual(add_months_shamsi("1405/01/01", 1), "1405/02/01")

        # BMR/TDEE
        bmr_m, tdee_m, pal_m, _, _ = calculate_bmr_tdee(180, 75, 25, "male", "moderately_active")
        bmr_f, tdee_f, _, _, _ = calculate_bmr_tdee(165, 60, 25, "female", "lightly_active")
        self.assertGreater(bmr_m, bmr_f)
        self.assertGreater(tdee_m, bmr_m)
        self.assertEqual(pal_m, 1.55)
        self.assertEqual(calculate_bmr_tdee(0, 70)[0], 0)
        self.assertGreaterEqual(calculate_age_from_shamsi("۱۳۷۸/۰۱/۰۱"), 20)

        # Duplicate naming
        self.assertEqual(extract_root_and_number("برنامه حجم (2)"), ("برنامه حجم", 2))
        self.assertEqual(get_next_numbered_name("برنامه حجم", ["برنامه حجم", "برنامه حجم (2)"]), "برنامه حجم (3)")

        # Password hashing & verification (symmetric across Persian, Arabic & English digits)
        h = hash_password("Secret۱۲۳")
        self.assertTrue(verify_password("Secret۱۲۳", h))
        self.assertTrue(verify_password("Secret123", h))
        h2 = hash_password("Pass45٦")
        self.assertTrue(verify_password("Pass۴۵۶", h2))
        self.assertFalse(verify_password("wrong", h))
        self.assertFalse(verify_password("", h))
        self.assertFalse(verify_password(None, h))

        # PDF & Excel generation on seeded records
        member_id, wplan_id, nplan_id, today = self._ensure_seeded()
        member = MemberService.get_member_by_id(member_id)
        wplan = WorkoutService.get_plan_by_id(wplan_id)
        nplan = NutritionService.get_plan_by_id(nplan_id)
        summary = AccountingService.get_financial_summary(start_date=today, end_date=today)
        txns = AccountingService.get_transactions(start_date=today, end_date=today)

        out_dir = Path(self.tmp_dir.name)
        pdf_w = out_dir / "test_workout.pdf"
        pdf_n = out_dir / "test_nutrition.pdf"
        pdf_f = out_dir / "test_finance.pdf"
        xlsx_f = out_dir / "test_finance.xlsx"

        PDFGenerator.generate_workout_pdf(member, wplan, str(pdf_w))
        PDFGenerator.generate_nutrition_pdf(member, nplan, str(pdf_n))
        PDFGenerator.generate_financial_pdf(str(pdf_f), summary=summary, transactions=txns, filter_info={"period": "امروز"})
        ExcelGenerator.generate_financial_excel(str(xlsx_f), summary=summary, transactions=txns, filter_info={"period": "امروز"})

        for p in (pdf_w, pdf_n, pdf_f):
            self.assertTrue(p.exists(), f"Missing generated PDF {p}")
            self.assertGreater(p.stat().st_size, 2000)
            self.assertTrue(p.read_bytes().startswith(b"%PDF-"))

        self.assertTrue(xlsx_f.exists())
        wb = openpyxl.load_workbook(xlsx_f)
        self.assertGreaterEqual(len(wb.sheetnames), 1)
        wb.close()

    # ------------------------------------------------------------------
    # 3. MainWindow Full Page Navigation (All 11 Views) & Theme Switching QA
    # ------------------------------------------------------------------
    def test_03_main_window_all_11_pages_and_themes_qa(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.main_window import MainWindow

        with patch("nemov.views.main_window.MainWindow._start_background_update_check"), \
             patch("nemov.views.sms_view.SmsBalanceThread.start"), \
             patch("nemov.views.sms_view.SmsHistoryThread.start"), \
             patch("nemov.services.sms_service.SmsService.check_and_send_automated_birthdays", return_value=0), \
             patch("nemov.services.sms_service.SmsService.check_and_send_automated_tuitions", return_value=0):
            win = MainWindow()
            win.resize(1320, 820)
            win.show()
            self._pump()

            all_pages = [
                "dashboard", "members", "workouts", "nutrition",
                "templates", "exercises", "foods", "accounting",
                "sms", "backup", "developer",
            ]
            for pid in all_pages:
                win.sidebar.navigate(pid)
                self._pump()
                cur = win.stack.currentWidget()
                self.assertIsNotNone(cur, f"Page {pid} failed to switch into stack")
                self.assertEqual(cur.layoutDirection(), Qt.LayoutDirection.RightToLeft)

            # Theme switching Dark <-> Light with active MainWindow
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            ThemeManager.apply_theme("crimson_fury", self.app)
            self._pump()

            win._bg_update_timer.stop()
            from nemov.services.autosave_service import AutoSaveManager
            from nemov.database.connection import reset_data_changed
            AutoSaveManager.get_instance().stop()
            reset_data_changed()
            win.close()

    # ------------------------------------------------------------------
    # 4. Standalone Core Dialogs Geometry & RTL Verification
    # ------------------------------------------------------------------
    def test_04_dialogs_instantiation_rtl_and_geometry(self):
        from nemov.views.member_form_dialog import MemberFormDialog
        from nemov.views.workout_library_view import ExerciseFormDialog
        from nemov.views.food_library_dialog import FoodFormDialog
        from nemov.views.components.expense_form_dialog import ExpenseFormDialog
        from nemov.views.components.tuition_payment_dialog import TuitionPaymentDialog
        from nemov.views.components.error_dialog import ErrorDialog

        dialogs = [
            MemberFormDialog(),
            ExerciseFormDialog(),
            FoodFormDialog(),
            ExpenseFormDialog(),
            TuitionPaymentDialog(),
            ErrorDialog(parent=None, title="خطا", message="پیام تست خطا", technical_details="جزئیات فنی تست"),
        ]
        for dlg in dialogs:
            dlg.show()
            self._pump()
            self.assertEqual(dlg.layoutDirection(), Qt.LayoutDirection.RightToLeft, f"RTL missing on {type(dlg).__name__}")
            self.assertGreater(dlg.width(), 200)
            self.assertGreater(dlg.height(), 120)
            dlg.close()

    # ------------------------------------------------------------------
    # 5. Packaged Executable & Tests Exclusion Verification
    # ------------------------------------------------------------------
    def test_05_packaged_build_and_installer_integrity(self):
        import config
        ver = config.APP_VERSION if str(config.APP_VERSION).startswith("v") else f"v{config.APP_VERSION}"
        dist_exe = PROJECT_ROOT / "dist" / "Nemov" / "Nemov.exe"
        setup_exe = PROJECT_ROOT / "dist" / f"Nemov_Setup_{ver}.exe"
        leaked_tests_dir = PROJECT_ROOT / "dist" / "Nemov" / "_internal" / "tests"

        self.assertTrue(dist_exe.exists(), "dist/Nemov/Nemov.exe missing")
        self.assertTrue(setup_exe.exists(), f"{setup_exe.name} missing")
        self.assertGreater(setup_exe.stat().st_size, 50_000_000)
        self.assertFalse(leaked_tests_dir.exists(), "tests/ leaked into dist/Nemov/_internal/tests")

    # ------------------------------------------------------------------
    # 6. Regression Verification for All Fixed Audit Findings
    # ------------------------------------------------------------------
    def test_06_audit_fixes_compile_archived_member_phone_ripple_and_warnings(self):
        import py_compile
        import warnings
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import QPoint
        from nemov.views.components.theme_ripple_overlay import ThemeRippleOverlay
        from nemov.services.member_service import MemberService
        from nemov.services.backup_service import BackupService

        # 1) ThemeRippleOverlay compiles & paints cleanly without SyntaxError
        from PyQt6.QtWidgets import QWidget
        ripple_path = PROJECT_ROOT / "nemov" / "views" / "components" / "theme_ripple_overlay.py"
        py_compile.compile(str(ripple_path), doraise=True)
        parent_w = QWidget()
        parent_w.resize(80, 60)
        parent_w.show()
        host = QPixmap(80, 60)
        host.fill(Qt.GlobalColor.black)
        nxt = QPixmap(80, 60)
        nxt.fill(Qt.GlobalColor.white)
        overlay = ThemeRippleOverlay(
            parent_w, old_pixmap=host, new_pixmap=nxt,
            origin=QPoint(40, 30), accent_color="#DC2626", duration_ms=50,
        )
        overlay.radius = 25.0
        self._pump()
        overlay.grab()
        overlay.anim.stop()
        overlay.close()
        parent_w.close()

        # 2) MemberService creates archived member without dates & normalizes Persian/Arabic phone digits
        archived_m = MemberService.create_member({
            "first_name": "سهراب",
            "last_name": "بایگانی",
            "phone": "۰۹۱۲۹۸۷۶۵۴۳",
            "status": "archived",
        })
        self.assertEqual(archived_m.status, "archived")
        self.assertEqual(archived_m.phone, "09129876543")
        self.assertTrue(bool(archived_m.membership_start_shamsi))
        self.assertTrue(bool(archived_m.membership_expire_shamsi))

        updated_m = MemberService.update_member(archived_m.id, {"phone": "٠٩٣٥١١١٢٢٣٣"})
        self.assertEqual(updated_m.phone, "09351112233")

        # 3) Member.trainer_name uses session.get without SQLAlchemy LegacyAPIWarning
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tname = updated_m.trainer_name
            self.assertTrue(bool(tname))
            sa_legacy = [w for w in caught if "LegacyAPIWarning" in type(w.message).__name__ or "Query.get()" in str(w.message)]
            self.assertEqual(sa_legacy, [], f"Unexpected SQLAlchemy LegacyAPIWarning: {sa_legacy}")

        # 4) Dead record_email_backup removed cleanly
        self.assertFalse(hasattr(BackupService, "record_email_backup"))


if __name__ == "__main__":
    unittest.main()
