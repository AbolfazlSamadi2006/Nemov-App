import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QTabWidget, QWidget
from PyQt6.QtCore import Qt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestNutritionEditorFull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pump(self):
        self.app.processEvents()

    def _make_sample_env(self):
        member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", status="expired",
            height_cm=180.0, initial_weight_kg=75.0, birth_date_shamsi="1380/01/01",
            gender="male", activity_level="moderately_active"
        )
        foods = [
            SimpleNamespace(id=10, name_fa="تخم مرغ", unit="عدد", calories=70, protein_g=6, carbs_g=0.5, fat_g=5),
            SimpleNamespace(id=11, name_fa="سینه مرغ", unit="۱۰۰ گرم", calories=165, protein_g=31, carbs_g=0, fat_g=3.6),
            SimpleNamespace(id=12, name_fa="برنج پخته", unit="کفگیر", calories=130, protein_g=2.5, carbs_g=28, fat_g=0.3),
        ]
        return member, foods

    # ------------------------------------------------------------------
    # 1. Fixed Action Toolbar independence across ALL days_mode options
    # ------------------------------------------------------------------
    def test_01_fixed_action_toolbar_independent_across_all_days_modes(self):
        from nemov.views.nutrition_editor_view import NutritionEditorView

        member, foods = self._make_sample_env()
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[member]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=member), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=foods):
            view = NutritionEditorView()
            view.resize(1280, 760)
            view.show()
            self._pump()

            # Initial mode (7_days): standalone toolbar must be visible, outside tabs/cornerWidget
            self.assertIsNone(view.tabs.cornerWidget(Qt.Corner.TopRightCorner))
            for i in range(view.tabs.count()):
                day_tab = view.tabs.widget(i)
                self.assertIsInstance(day_tab, QTabWidget)
                self.assertIsNone(day_tab.cornerWidget(Qt.Corner.TopRightCorner))

            bar_geom_7d = view.table_actions_bar.geometry()
            self.assertLessEqual(bar_geom_7d.x(), 20)  # Anchored at far LEFT edge (سمت چپ بالای جدول)
            # In RTL bar: btn_add_food is leftmost, btn_undo is rightmost among the 3
            self.assertLess(view.btn_add_food.geometry().x(), view.btn_redo.geometry().x())
            self.assertLess(view.btn_redo.geometry().x(), view.btn_undo.geometry().x())

            self.assertEqual(view.btn_add_food.height(), 32)
            self.assertEqual(view.btn_undo.height(), 32)
            self.assertEqual(view.btn_redo.height(), 32)
            self.assertTrue(view.btn_add_food.isVisible())
            self.assertTrue(view.btn_undo.isVisible())
            self.assertTrue(view.btn_redo.isVisible())

            # Test adding food to active day + active meal (Wednesday -> Lunch) in 7_days
            view.tabs.setCurrentIndex(4)  # چهارشنبه
            wed_tab = view.tabs.widget(4)
            wed_tab.setCurrentIndex(2)    # ناهار
            view.btn_add_food.click()
            lunch_tbl = view.meal_tables[4 * 6 + 2][1]
            self.assertEqual(lunch_tbl.rowCount(), 1)

            # Save 7_days QA screenshot
            qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
            qa_dir.mkdir(parents=True, exist_ok=True)
            view.grab().save(str(qa_dir / "nutrition_7days_fixed_toolbar_qa.png"))

            # Switch to all_days ("کلیه روزها (ثابت)") keeping content -> buttons MUST stay at top-left above table!
            with patch("nemov.views.nutrition_editor_view.DaySelectionReductionDialog") as m_red:
                m_red.return_value.exec.return_value = QDialog.DialogCode.Accepted
                m_red.return_value.start_fresh = False
                m_red.return_value.selected_indices = [4]
                idx_all = view.combo_days.findData("all_days")
                view.combo_days.setCurrentIndex(idx_all)
                self._pump()

            self.assertIsNone(view.tabs.cornerWidget(Qt.Corner.TopRightCorner))
            self.assertEqual(view.btn_add_food.height(), 32)
            self.assertEqual(view.btn_undo.height(), 32)
            self.assertEqual(view.btn_redo.height(), 32)
            self.assertTrue(view.btn_add_food.isVisible())
            self.assertTrue(view.btn_undo.isVisible())
            self.assertTrue(view.btn_redo.isVisible())

            # Still anchored at same far-left X & width, aligned cleanly to top-left above the table!
            bar_geom_all = view.table_actions_bar.geometry()
            self.assertEqual(bar_geom_all.x(), bar_geom_7d.x())
            self.assertEqual(bar_geom_all.width(), bar_geom_7d.width())
            self.assertLessEqual(bar_geom_all.y(), 10)
            # No overlap between toolbar on the left and meal tabs on the right
            last_meal_rect = view.tabs.tabBar().tabRect(view.tabs.tabBar().count() - 1)
            meal_tabs_left_in_wrapper = view.tabs.tabBar().mapTo(view.tabs_wrapper, last_meal_rect.topLeft()).x()
            self.assertLess(bar_geom_all.right(), meal_tabs_left_in_wrapper)

            # In all_days mode, clicking btn_add_food adds to active meal tab (e.g. میان‌وعده صبح tab 1)
            view.tabs.setCurrentIndex(1)
            snack_tbl = view.meal_tables[1][1]
            before_rows = snack_tbl.rowCount()
            view.btn_add_food.click()
            self.assertEqual(snack_tbl.rowCount(), before_rows + 1)

            # Trigger calorie warning in all_days & verify Row 1 in overview box is NOT clipped or scrolled away!
            snack_tbl.cellWidget(snack_tbl.rowCount() - 1, 0).setCurrentIndex(0)  # 70 kcal < BMR warning
            self._pump()
            self.assertTrue(view.lbl_cal_warn.isVisible())
            self.assertEqual(view.form_details_curtain.verticalScrollBar().value(), 0)
            vp_rect = view.form_details_curtain.viewport().rect()
            for top_widget in (view.txt_title, view.combo_member_top, view.combo_templates):
                self.assertTrue(top_widget.isVisible())
                self.assertGreaterEqual(top_widget.geometry().y(), 0)
                self.assertLessEqual(top_widget.geometry().bottom(), vp_rect.height())

            view.grab().save(str(qa_dir / "nutrition_alldays_fixed_toolbar_and_header_qa.png"))

            # Undo & Redo buttons remain enabled and functional across mode switch
            self.assertTrue(view.btn_undo.isEnabled())
            view.btn_undo.click()
            self._pump()

            # Also verify remaining modes (training_rest, 2..6 days)
            for mode_key in ("training_rest", "2_days", "3_days", "4_days", "5_days", "6_days"):
                view._prev_days_mode = view.combo_days.currentData()
                view.setup_meal_tabs_with_data(mode_key, None)
                self._pump()
                self.assertEqual(view.btn_add_food.height(), 32)
                self.assertEqual(view.btn_undo.height(), 32)
                self.assertEqual(view.btn_redo.height(), 32)
                self.assertTrue(view.btn_add_food.isVisible())
                self.assertTrue(view.btn_undo.isVisible())
                self.assertTrue(view.btn_redo.isVisible())
                tbl = view.get_current_active_meal_table()
                self.assertIsNotNone(tbl)

            view.close()

    # ------------------------------------------------------------------
    # 2. Overview Box ("مشخصات کلی"): goal factors, macros, TDEE buttons & collapse
    # ------------------------------------------------------------------
    def test_02_overview_box_macros_tdee_goal_and_collapse_accordion(self):
        from nemov.views.nutrition_editor_view import NutritionEditorView

        member, foods = self._make_sample_env()
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[member]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=member), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=foods):
            view = NutritionEditorView()
            view.resize(1280, 760)
            view.show()
            view.set_selected_member(1)
            self._pump()

            # Check initial TDEE and muscle_gain defaults (75kg * 2.2/5.0/1.0 -> 165P / 375C / 75F)
            self.assertGreater(view._current_member_tdee, 0)
            base_tdee = view._current_member_tdee
            self.assertEqual(view.txt_target_p.text(), str(int(round(75.0 * 2.2))))
            self.assertEqual(view.txt_target_c.text(), str(int(round(75.0 * 5.0))))
            self.assertEqual(view.txt_target_f.text(), str(int(round(75.0 * 1.0))))

            # Switching Goal to weight_loss updates factors cleanly
            idx_wl = view.combo_goal.findData("weight_loss")
            view.combo_goal.setCurrentIndex(idx_wl)
            self.assertEqual(view.txt_factor_p.text(), "2.2")
            self.assertEqual(view.txt_factor_c.text(), "2.5")
            self.assertEqual(view.txt_factor_f.text(), "0.8")
            self.assertEqual(view.txt_target_c.text(), str(int(round(75.0 * 2.5))))

            # Manual TDEE buttons +300, +500, -300, -500 and floor clamp at 0
            view.btn_tdee_p300.click()
            self.assertEqual(view._current_member_tdee, base_tdee + 300)
            view.btn_tdee_m500.click()
            self.assertEqual(view._current_member_tdee, base_tdee - 200)
            view.txt_member_tdee.setText("100")
            view._on_manual_tdee_edited("100")
            view.btn_tdee_m500.click()
            self.assertEqual(view._current_member_tdee, 0)

            # Sync TDEE with macro energy button ("اعمال به TDEE")
            expected_macro_kcal = int(view.txt_target_p.text()) * 4 + int(view.txt_target_c.text()) * 4 + int(view.txt_target_f.text()) * 9
            view.btn_sync_tdee.click()
            self.assertEqual(view._current_member_tdee, expected_macro_kcal)

            # Reverse calculation when trainer edits target protein grams
            view.txt_target_p.setText("150")
            view._on_target_macro_edited("protein")
            self.assertEqual(view.txt_factor_p.text(), "2.0")

            # Collapse and expand form accordion updates button & summary label cleanly
            view.toggle_form_collapse()
            self.assertTrue(view.form_details_curtain.is_collapsed())
            self.assertIn("باز کردن", view.btn_toggle_form.text())
            self.assertIn("ابوالفضل صمدی", view.lbl_form_sub.text())
            view.toggle_form_collapse()
            self.assertFalse(view.form_details_curtain.is_collapsed())
            self.assertIn("جمع کردن", view.btn_toggle_form.text())

            view.close()

    # ------------------------------------------------------------------
    # 3. Table calculations, Persian/Arabic numbers, invalid amounts & get_plan_data
    # ------------------------------------------------------------------
    def test_03_meal_table_amounts_calories_custom_food_and_get_plan_data(self):
        from nemov.views.nutrition_editor_view import NutritionEditorView

        member, foods = self._make_sample_env()
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[member]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=member), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=foods):
            view = NutritionEditorView()
            view.txt_title.setText("برنامه تستی کامل")
            view.set_selected_member(1)

            # Switch to all_days and add 2 rows in Breakfast
            view.setup_meal_tabs_with_data("all_days", None)
            view._prev_days_mode = "all_days"
            view.combo_days.blockSignals(True)
            view.combo_days.setCurrentIndex(view.combo_days.findData("all_days"))
            view.combo_days.blockSignals(False)

            tbl = view.get_current_active_meal_table()
            view.btn_add_food.click()
            view.btn_add_food.click()
            self.assertEqual(tbl.rowCount(), 2)

            # Row 0: Select سینه مرغ (165 kcal) with Persian decimal "۲.۵" -> 412.5 -> 412 or 413 kcal
            tbl.cellWidget(0, 0).setCurrentIndex(1)
            tbl.cellWidget(0, 1).setText("۲.۵")
            tbl.cellWidget(0, 3).setText("قبل تمرین")

            # Row 1: Free-text custom food name & invalid text amount -> safe 0 kcal, custom_food_name set
            tbl.cellWidget(1, 0).setCurrentIndex(-1)
            tbl.cellWidget(1, 0).setEditText("معجون خانگی ویژه")
            tbl.cellWidget(1, 1).setText("abc")
            view.update_dynamic_calories()

            expected_kcal = int(round(165 * 2.5))
            self.assertIn(f"{expected_kcal:,}", tbl.cellWidget(0, 2).text())
            self.assertIn("0", tbl.cellWidget(1, 2).text())

            plan_info, meals_data = view.get_plan_data()
            self.assertEqual(plan_info["title"], "برنامه تستی کامل")
            self.assertEqual(plan_info["goal"], "muscle_gain")
            self.assertGreater(plan_info["target_calories"], 0)
            self.assertEqual(len(meals_data), 6)
            breakfast_items = meals_data[0]["items"]
            self.assertEqual(len(breakfast_items), 2)
            self.assertEqual(breakfast_items[0]["food_id"], 11)
            self.assertAlmostEqual(breakfast_items[0]["amount"], 2.5)
            self.assertEqual(breakfast_items[0]["notes"], "قبل تمرین")
            self.assertIsNone(breakfast_items[1]["food_id"])
            self.assertEqual(breakfast_items[1]["custom_food_name"], "معجون خانگی ویژه")
            self.assertEqual(breakfast_items[1]["amount"], 1.0)

            view.close()


if __name__ == "__main__":
    unittest.main()
