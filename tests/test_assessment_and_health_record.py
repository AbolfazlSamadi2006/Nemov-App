"""
Unit tests for:
1. AssessmentView pre-filling member height & weight from registration data,
   allowing trainer overrides (+/- editing), preserving defaults on reset,
   refreshing after profile edits, and EditAssessmentDialog fallback.
2. HealthRecord model + SQLite migration + HealthRecordView allergy &
   medication restriction fields, dirty-state tracking, persistence, and ZIP export.
3. PyQt6 visual geometry & RTL QA checks for AssessmentView and HealthRecordView.
"""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session

_APP = QApplication.instance() or QApplication(sys.argv)

from nemov.models.database_models import Base, Member, HealthRecord, PhysicalAssessment
from nemov.views.assessment_view import AssessmentView, EditAssessmentDialog
from nemov.views.health_record_view import HealthRecordView
from nemov.services.member_service import MemberService


class TestAssessmentHeightWeightPrefill(unittest.TestCase):
    """Tests that AssessmentView automatically pre-fills height & weight from Member registration."""

    def setUp(self):
        self.member = SimpleNamespace(
            id=101,
            full_name="سارا کریمی",
            height_cm=168.0,
            initial_weight_kg=64.5,
            birth_date_shamsi="1375/05/10",
            gender="female",
            activity_level="moderately_active",
        )

    def test_assessment_view_prefills_height_and_weight_and_updates_bmr(self):
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=self.member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            view = AssessmentView(101)

        self.assertEqual(view.spin_height.value(), 168.0)
        self.assertEqual(view.spin_weight.value(), 64.5)
        self.assertIn("BMR:", view.lbl_live_bmr.text())
        self.assertNotIn("BMR: -", view.lbl_live_bmr.text())

    def test_trainer_can_modify_prefilled_height_and_weight_and_save(self):
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=self.member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            view = AssessmentView(101)

            # Trainer adjusts prefilled values up or down
            view.spin_height.setValue(169.0)
            view.spin_weight.setValue(62.0)

            with patch("nemov.services.assessment_service.AssessmentService.add_assessment") as mock_add, \
                 patch.object(QMessageBox, "information"):
                view.save_assessment()

            mock_add.assert_called_once()
            saved_payload = mock_add.call_args.args[1]
            self.assertEqual(saved_payload["height_cm"], 169.0)
            self.assertEqual(saved_payload["weight_kg"], 62.0)

            # After save -> reset_form restores member defaults instead of 0.0
            self.assertEqual(view.spin_height.value(), 168.0)
            self.assertEqual(view.spin_weight.value(), 64.5)

    def test_assessment_view_keeps_zero_when_member_has_no_height_or_weight(self):
        empty_member = SimpleNamespace(
            id=102,
            full_name="بدون سایز",
            height_cm=None,
            initial_weight_kg=None,
            birth_date_shamsi=None,
            gender="male",
            activity_level="moderately_active",
        )
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=empty_member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            view = AssessmentView(102)

        self.assertEqual(view.spin_height.value(), 0.0)
        self.assertEqual(view.spin_weight.value(), 0.0)

    def test_refresh_member_defaults_respects_manual_edits(self):
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=self.member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            view = AssessmentView(101)

            # Profile updated in MemberFormDialog; trainer hasn't changed spin_weight manually
            view.spin_height.setValue(172.0)  # manually edited
            updated_member = SimpleNamespace(
                id=101, full_name="سارا کریمی", height_cm=170.0, initial_weight_kg=66.0,
                birth_date_shamsi="1375/05/10", gender="female", activity_level="moderately_active"
            )
            with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=updated_member):
                view.refresh_member_defaults()

        # Unedited weight gets updated default; manually edited height is preserved
        self.assertEqual(view.spin_height.value(), 172.0)
        self.assertEqual(view.spin_weight.value(), 66.0)

    def test_edit_assessment_dialog_falls_back_to_member_height_if_assessment_height_missing(self):
        rec = SimpleNamespace(
            id=5, member_id=101, assessment_date_shamsi="1405/09/05",
            height_cm=None, weight_kg=63.0, body_fat_percentage=22.0,
            neck_circ=None, chest_circ=None, arm_circ=None, abdomen_circ=None,
            waist_circ=None, hip_circ=None, thigh_circ=None,
            before_photo_path=None, after_photo_path=None,
        )
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=self.member):
            dlg = EditAssessmentDialog(rec)
        self.assertEqual(dlg.spin_height.value(), 168.0)
        self.assertEqual(dlg.spin_weight.value(), 63.0)

    def test_assessment_varied_and_boundary_inputs(self):
        # Decimal/boundary height & weight values + invalid <=0 weight save guard
        boundary_member = SimpleNamespace(
            id=103, full_name="ورزشکار مرزی", height_cm=215.0, initial_weight_kg=42.75,
            birth_date_shamsi="1380/11/29", gender="male", activity_level="very_active"
        )
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=boundary_member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            view = AssessmentView(103)

            self.assertEqual(view.spin_height.value(), 215.0)
            self.assertEqual(view.spin_weight.value(), 42.75)

            # Weight lowered to 0 -> blocked cleanly with warning, does not call add_assessment
            view.spin_weight.setValue(0.0)
            with patch("nemov.services.assessment_service.AssessmentService.add_assessment") as mock_add, \
                 patch.object(QMessageBox, "warning") as mock_warn:
                view.save_assessment()
            mock_warn.assert_called_once()
            mock_add.assert_not_called()

            # High valid weight override + lower height override
            view.spin_height.setValue(185.0)
            view.spin_weight.setValue(135.5)
            with patch("nemov.services.assessment_service.AssessmentService.add_assessment") as mock_add, \
                 patch.object(QMessageBox, "information"):
                view.save_assessment()
            self.assertEqual(mock_add.call_args.args[1]["height_cm"], 185.0)
            self.assertEqual(mock_add.call_args.args[1]["weight_kg"], 135.5)


class TestHealthRecordAllergyAndMedication(unittest.TestCase):
    """Tests DB model, auto-migration, UI loading/saving, and dirty tracking for allergy & medication restriction."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_health.db")
        self.test_engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.TestSession = scoped_session(sessionmaker(bind=self.test_engine, expire_on_commit=False))

    def tearDown(self):
        self.TestSession.remove()
        self.test_engine.dispose()
        self.tmp_dir.cleanup()

    def test_sqlite_migration_adds_allergy_and_medication_columns(self):
        # Create an old-schema health_records table missing the 4 new columns
        with self.test_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE health_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL UNIQUE,
                    has_hypertension BOOLEAN DEFAULT 0,
                    has_diabetes BOOLEAN DEFAULT 0,
                    has_heart_issue BOOLEAN DEFAULT 0,
                    other_medical TEXT
                );
            """))
            conn.commit()

        from nemov.database import connection as db_conn
        with patch.object(db_conn, "engine", self.test_engine), \
             patch.object(db_conn, "SessionLocal", self.TestSession):
            db_conn.check_and_migrate_db()

        cols = [c["name"] for c in inspect(self.test_engine).get_columns("health_records")]
        for required_col in (
            "has_allergy",
            "has_medication_restriction",
            "allergy_details",
            "medication_restriction_details",
        ):
            self.assertIn(required_col, cols)

    def test_health_record_persistence_and_view_load_save_cycle(self):
        Base.metadata.create_all(bind=self.test_engine)
        with self.TestSession() as s:
            m = Member(
                first_name="مهدی", last_name="احمدی", phone="09120001122",
                membership_start_shamsi="1405/09/01", membership_expire_shamsi="1405/10/01"
            )
            s.add(m)
            s.commit()
            member_id = m.id

        with patch("nemov.services.member_service.get_session", self.TestSession):
            view = HealthRecordView(member_id)
            self.assertFalse(view.btn_save.isEnabled())
            self.assertFalse(view.cb_allergy.isChecked())
            self.assertFalse(view.cb_medication_restriction.isChecked())

            # Typing details auto-checks checkbox and marks form dirty
            view.txt_allergy.setPlainText("حساسیت به بادام‌زمینی و پنی‌سیلین")
            view.txt_medication_restriction.setPlainText("منع مصرف داروهای رقیق‌کننده خون و کافئین بالا")

            self.assertTrue(view.cb_allergy.isChecked())
            self.assertTrue(view.cb_medication_restriction.isChecked())
            self.assertTrue(view.btn_save.isEnabled())

            with patch.object(QMessageBox, "information"):
                view.save_data()
            self.assertFalse(view.btn_save.isEnabled())

            # Re-open fresh HealthRecordView and verify persisted data reloads cleanly
            reloaded_view = HealthRecordView(member_id)
            self.assertTrue(reloaded_view.cb_allergy.isChecked())
            self.assertTrue(reloaded_view.cb_medication_restriction.isChecked())
            self.assertEqual(reloaded_view.txt_allergy.toPlainText(), "حساسیت به بادام‌زمینی و پنی‌سیلین")
            self.assertEqual(reloaded_view.txt_medication_restriction.toPlainText(), "منع مصرف داروهای رقیق‌کننده خون و کافئین بالا")

            # Whitespace-only input should NOT falsely check boxes, and unchecking saves cleanly
            reloaded_view.txt_allergy.setPlainText("   \n  ")
            reloaded_view.cb_allergy.setChecked(False)
            self.assertFalse(reloaded_view.cb_allergy.isChecked())
            self.assertTrue(reloaded_view.btn_save.isEnabled())
            with patch.object(QMessageBox, "information"):
                reloaded_view.save_data()

            rec_after = MemberService.get_health_record(member_id)
            self.assertFalse(rec_after.has_allergy)
            self.assertEqual(rec_after.allergy_details, "")
            self.assertTrue(rec_after.has_medication_restriction)

            # Multiline Unicode/Latin details save and export to ZIP package text cleanly
            reloaded_view.txt_allergy.setPlainText("آلرژی فصلی\nLactose + Ibuprofen 400mg")
            with patch.object(QMessageBox, "information"):
                reloaded_view.save_data()

            zip_path = os.path.join(self.tmp_dir.name, "health_pkg.zip")
            with patch("nemov.utils.export_utils.resolve_athlete_export_path", return_value=(zip_path, "test")), \
                 patch.object(QMessageBox, "information"):
                reloaded_view.export_medical_package()

            import zipfile
            with zipfile.ZipFile(zip_path, "r") as zf:
                report = zf.read("نظرات_و_سوابق_پزشکی_مربی.txt").decode("utf-8-sig")
            self.assertIn("آلرژی / حساسیت: بله", report)
            self.assertIn("Lactose + Ibuprofen 400mg", report)
            self.assertIn("محدودیت دارویی: بله", report)
            self.assertIn("منع مصرف داروهای رقیق‌کننده خون", report)


class TestAssessmentAndHealthVisualQA(unittest.TestCase):
    """Verifies layout geometry, RTL alignment, and non-clipping on modified tabs."""

    def test_assessment_and_health_views_geometry_and_rtl(self):
        fake_member = SimpleNamespace(
            id=1, full_name="تست", height_cm=180.0, initial_weight_kg=80.0,
            birth_date_shamsi="1372/01/01", gender="male", activity_level="moderately_active"
        )
        fake_rec = SimpleNamespace(
            has_hypertension=False, has_diabetes=False, has_heart_issue=False,
            has_allergy=True, has_medication_restriction=True,
            allergy_details="تست آلرژی", medication_restriction_details="تست دارویی",
            other_medical="", knee_injury="", back_injury="",
            shoulder_injury="", wrist_injury="", exercise_limitations=""
        )

        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=fake_member), \
             patch("nemov.services.assessment_service.AssessmentService.get_member_assessments", return_value=[]):
            av = AssessmentView(1)
            av.resize(1024, 720)
            av.show()
            _APP.processEvents()
            self.assertEqual(av.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertGreater(av.spin_height.width(), 0)
            self.assertGreater(av.spin_weight.width(), 0)
            av.close()

        with patch("nemov.services.member_service.MemberService.get_health_record", return_value=fake_rec), \
             patch("nemov.services.member_service.MemberService.get_medical_documents", return_value=[]):
            hv = HealthRecordView(1)
            hv.resize(1024, 720)
            hv.show()
            _APP.processEvents()
            self.assertEqual(hv.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertTrue(hv.cb_allergy.isVisible())
            self.assertTrue(hv.cb_medication_restriction.isVisible())
            self.assertGreater(hv.txt_allergy.height(), 20)
            self.assertGreater(hv.txt_medication_restriction.height(), 20)
            hv.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
