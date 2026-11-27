import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestMemberSelectionAndAssignFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pump(self):
        self.app.processEvents()

    # ------------------------------------------------------------------
    # 1. SearchableComboBox matching, normalization, manual typing & safety
    # ------------------------------------------------------------------
    def test_01_searchable_combo_box_normalization_manual_typing_and_safety(self):
        from nemov.views.components.searchable_combo_box import SearchableComboBox

        cmb = SearchableComboBox(placeholder="جستجو یا تایپ نام ورزشکار...")
        cmb.addItem("ابوالفضل صمدی", 1)
        cmb.addItem("عرفان نیک خو", 4)
        cmb.addItem("محسن صمدی", 8)
        cmb.set_empty()

        self.assertIsNone(cmb.resolve_current_data())

        # Exact match with Arabic yeh + extra spaces + ZWNJ
        cmb.setEditText("  ابوالفضل\u200cصمدي  ")
        cmb.lineEdit().returnPressed.emit()
        self.assertEqual(cmb.currentData(), 1)
        self.assertEqual(cmb.resolve_current_data(), 1)

        # Unique partial match succeeds cleanly
        cmb.set_empty()
        cmb.setEditText("عرفان")
        self.assertEqual(cmb.resolve_current_data(), 4)
        self.assertEqual(cmb.currentIndex(), 1)

        # Ambiguous partial match ("صمدی" belongs to both ID 1 and ID 8) MUST NOT guess
        cmb.set_empty()
        cmb.setEditText("صمدی")
        self.assertIsNone(cmb.resolve_current_data())

        # Switching text manually from selected item 0 -> invalid text MUST NOT leak stale ID 1
        cmb.setCurrentIndex(0)
        self.assertEqual(cmb.currentData(), 1)
        cmb.setEditText("نام نامعتبر تستی")
        self.assertIsNone(cmb.resolve_current_data())
        self.assertEqual(cmb.currentIndex(), -1)

        # Changing text manually from item 0 to item 1 resolves item 1's ID immediately
        cmb.setCurrentIndex(0)
        cmb.setEditText("عرفان نیک خو")
        self.assertEqual(cmb.resolve_current_data(), 4)
        self.assertEqual(cmb.currentData(), 4)

        cmb.close()

    # ------------------------------------------------------------------
    # 2. WorkoutEditorView: expired/archived member pre-selection & assign
    # ------------------------------------------------------------------
    def test_02_workout_editor_includes_expired_members_and_preselects_from_profile(self):
        from nemov.views.workout_editor_view import WorkoutEditorView

        expired_member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", status="expired",
            membership_type="12_sessions"
        )
        active_member = SimpleNamespace(
            id=8, full_name="محسن صمدی", status="active",
            membership_type="16_sessions"
        )
        archived_member = SimpleNamespace(
            id=99, full_name="ورزشکار بایگانی", status="archived",
            membership_type="8_sessions"
        )
        ex_item = SimpleNamespace(id=10, name_fa="حرکت اسپلیت اسکوات", primary_muscle="legs", description="")

        all_members = [expired_member, active_member, archived_member]
        by_id = {m.id: m for m in all_members}

        with patch("nemov.views.workout_editor_view.MemberService.get_all_members", return_value=all_members), \
             patch("nemov.views.workout_editor_view.MemberService.get_member_by_id", side_effect=lambda mid: by_id.get(mid)), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_exercises", return_value=[ex_item]):

            w_view = WorkoutEditorView()
            # 1) Expired member IS in dropdown (archived is excluded by default)
            self.assertEqual(w_view.combo_member.count(), 2)
            self.assertGreaterEqual(w_view.combo_member.findData(1), 0)
            self.assertEqual(w_view.combo_member.findData(99), -1)

            # 2) Simulate MainWindow.open_new_workout_for_member(1) -> reset_to_new_plan + set_selected_member(1)
            w_view.reset_to_new_plan()
            w_view.set_selected_member(1)
            w_view.show()
            w_view.refresh_editor()
            self._pump()

            self.assertEqual(w_view.combo_member.currentData(), 1)
            self.assertEqual(w_view.combo_member.currentText(), "ابوالفضل صمدی")

            # 3) Add title and exercise, manually clear/re-type Arabic yeh name without clicking popup, click assign
            w_view.txt_title.setText("برنامه حجم")
            _, table = w_view.day_tables[0]
            w_view.add_exercise_row(table, [ex_item])
            table.cellWidget(0, 0).setCurrentIndex(0)

            w_view.combo_member.set_empty()
            w_view.combo_member.setEditText("ابوالفضل صمدي")  # Arabic yeh without popup click

            fake_plan = SimpleNamespace(id=501, title="برنامه حجم")
            with patch("nemov.views.workout_editor_view.WorkoutService.get_member_assignments", return_value=[]), \
                 patch("nemov.views.workout_editor_view.MemberService.get_health_record", return_value=None), \
                 patch("nemov.views.workout_editor_view.WorkoutService.create_workout_plan", return_value=fake_plan) as m_cp, \
                 patch("nemov.views.workout_editor_view.WorkoutService.assign_plan_to_member") as m_ap, \
                 patch("nemov.views.workout_editor_view.QMessageBox.warning") as m_warn, \
                 patch("nemov.views.workout_editor_view.QMessageBox.information") as m_info, \
                 patch.object(w_view, "_handle_unregistered_exercises", return_value=True):
                # Mock IncompletePlanWarningDialog because day 2 & 3 are empty
                with patch("nemov.views.workout_editor_view.IncompletePlanWarningDialog") as m_dlg:
                    m_dlg.return_value.exec.return_value = w_view.DialogCode.Accepted if hasattr(w_view, "DialogCode") else 1
                    from PyQt6.QtWidgets import QDialog
                    m_dlg.return_value.exec.return_value = QDialog.DialogCode.Accepted
                    w_view.assign_plan()

                m_warn.assert_not_called()
                m_cp.assert_called_once()
                m_ap.assert_called_once_with(1, 501)
                m_info.assert_called_once()

            # 4) Even an archived member opened directly from profile gets selected & persists on showEvent/refresh
            w_view.set_selected_member(99)
            w_view.refresh_editor()
            self.assertEqual(w_view.combo_member.currentData(), 99)
            self.assertEqual(w_view.combo_member.currentText(), "ورزشکار بایگانی")

            # 5) Invalid typed member triggers warning & blocks DB write
            w_view.combo_member.set_empty()
            w_view.combo_member.setEditText("ورزشکار ناموجود")
            with patch("nemov.views.workout_editor_view.WorkoutService.assign_plan_to_member") as m_ap, \
                 patch("nemov.views.workout_editor_view.QMessageBox.warning") as m_warn:
                w_view.assign_plan()
                m_warn.assert_called_once()
                m_ap.assert_not_called()

            w_view.close()

    # ------------------------------------------------------------------
    # 3. NutritionEditorView & AssignTemplateDialog: expired member + typed name
    # ------------------------------------------------------------------
    def test_03_nutrition_and_template_assign_handle_expired_and_typed_members(self):
        from nemov.views.nutrition_editor_view import NutritionEditorView
        from nemov.views.templates_manager_view import AssignTemplateDialog

        expired_member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", status="expired",
            height_cm=180.0, initial_weight_kg=75.0, birth_date_shamsi="1380/01/01",
            gender="male", activity_level="moderately_active"
        )
        food_item = SimpleNamespace(
            id=2, name_fa="تخم مرغ", unit="عدد", calories=70,
            protein_g=6, carbs_g=0.5, fat_g=5
        )
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[expired_member]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=expired_member), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=[food_item]):
            n_view = NutritionEditorView()
            n_view.reset_form()
            n_view.set_selected_member(1)
            self.assertEqual(n_view.combo_member.currentData(), 1)
            self.assertEqual(n_view.combo_member_top.currentData(), 1)

            # Manual typing in combo_member_top without touching bottom box resolves on assign
            n_view.txt_title.setText("رژیم کات")
            _, n_table = n_view.meal_tables[0]
            n_view.add_food_row(n_table, [food_item])
            n_table.cellWidget(0, 0).setCurrentIndex(0)

            n_view.combo_member.set_empty()
            n_view.combo_member_top.set_empty()
            n_view.combo_member_top.setEditText("ابوالفضل صمدي")

            fake_nplan = SimpleNamespace(id=701, title="رژیم کات")
            with patch("nemov.views.nutrition_editor_view.NutritionService.get_member_assignments", return_value=[]), \
                 patch("nemov.views.nutrition_editor_view.MemberService.get_health_record", return_value=None), \
                 patch("nemov.views.nutrition_editor_view.NutritionService.create_nutrition_plan", return_value=fake_nplan), \
                 patch("nemov.views.nutrition_editor_view.NutritionService.assign_nutrition_plan") as m_na, \
                 patch("nemov.views.nutrition_editor_view.QMessageBox.warning") as m_warn, \
                 patch("nemov.views.nutrition_editor_view.QMessageBox.information"), \
                 patch.object(n_view, "_handle_unregistered_foods", return_value=True):
                n_view.assign_plan()
                m_warn.assert_not_called()
                m_na.assert_called_once_with(1, 701)
            n_view.close()

        # AssignTemplateDialog MUST include expired member too
        with patch("nemov.views.templates_manager_view.MemberService.get_all_members", return_value=[expired_member]):
            dlg = AssignTemplateDialog("workout", 55, "الگوی تستی")
            self.assertEqual(dlg.combo_member.count(), 1)
            self.assertEqual(dlg.combo_member.findData(1), 0)
            dlg.combo_member.setEditText("ابوالفضل صمدی")
            with patch("nemov.views.templates_manager_view.MemberService.get_health_record", return_value=None), \
                 patch("nemov.views.templates_manager_view.WorkoutService.assign_plan_to_member") as m_wt, \
                 patch("nemov.views.templates_manager_view.QMessageBox.information"):
                dlg.assign()
                m_wt.assert_called_once_with(1, 55, notes=None)
            dlg.close()

    # ------------------------------------------------------------------
    # 4. Visual & Geometry QA for WorkoutEditorView athlete bar
    # ------------------------------------------------------------------
    def test_04_workout_editor_member_bar_geometry_qa(self):
        from nemov.views.workout_editor_view import WorkoutEditorView

        m = SimpleNamespace(id=1, full_name="ابوالفضل صمدی", status="expired", membership_type="12_sessions")
        with patch("nemov.views.workout_editor_view.MemberService.get_all_members", return_value=[m]), \
             patch("nemov.views.workout_editor_view.MemberService.get_member_by_id", return_value=m), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_exercises", return_value=[]):
            view = WorkoutEditorView()
            view.resize(1100, 740)
            view.set_selected_member(1)
            view.show()
            self._pump()

            geom = view.combo_member.geometry()
            self.assertGreaterEqual(geom.width(), 240)
            self.assertGreaterEqual(geom.height(), 32)
            self.assertTrue(view.combo_member.isVisible())
            self.assertTrue(view.combo_member.isEditable())
            self.assertEqual(view.combo_member.currentData(), 1)
            view.close()


if __name__ == "__main__":
    unittest.main()
