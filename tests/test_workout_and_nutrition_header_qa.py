import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QGroupBox, QLabel
from PyQt6.QtGui import QFontDatabase, QFontMetrics
from PyQt6.QtCore import Qt, QPoint, QRect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestWorkoutAndNutritionHeaderQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for fp in (
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Regular.ttf",
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Bold.ttf",
        ):
            if fp.exists():
                QFontDatabase.addApplicationFont(str(fp))

    def _pump(self):
        self.app.processEvents()

    def test_01_workout_editor_header_layout_proportions_uniform_height_and_member_sync(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.workout_editor_view import WorkoutEditorView

        ThemeManager.apply_theme("crimson_fury", self.app)
        members = [
            SimpleNamespace(id=1, full_name="ابوالفضل صمدی تبار با نام خانوادگی بسیار طولانی جهت تست عرض", status="expired", membership_type="16_sessions"),
            SimpleNamespace(id=2, full_name="محسن صمدی", status="active", membership_type="12_sessions"),
        ]
        ex_item = SimpleNamespace(id=5, name_fa="اسکات هالتر", primary_muscle="legs", description="")

        with patch("nemov.views.workout_editor_view.MemberService.get_all_members", return_value=members), \
             patch("nemov.views.workout_editor_view.MemberService.get_member_by_id", side_effect=lambda mid: next((m for m in members if m.id == mid), None)), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_exercises", return_value=[ex_item]):
            view = WorkoutEditorView()
            view.resize(1280, 760)
            view.show()
            self._pump()

            # 1) Form box objectName matches assign_plan_box (black base bg + grey input fields)
            form_box = next(
                gb for gb in view.findChildren(QGroupBox)
                if "مشخصات کلی برنامه تمرینی" in gb.title()
            )
            self.assertEqual(form_box.objectName(), "assign_plan_box")

            # 2) Subtitle word "بانک" removed from Templates label & placeholder
            lbl_texts = [lbl.text() for lbl in form_box.findChildren(QLabel)]
            self.assertTrue(any("الگوهای آماده:" in t for t in lbl_texts))
            self.assertFalse(any("الگوهای آماده بانک" in t for t in lbl_texts))
            self.assertNotIn("بانک", view.combo_templates.itemText(0))

            # 3) Uniform 32px height across every top form box & combo
            controls = (
                view.txt_title,
                view.combo_member_top,
                view.combo_templates,
                view.combo_goal,
                view.combo_days,
                view.combo_level,
            )
            for ctrl in controls:
                self.assertEqual(ctrl.height(), 32)
                self.assertTrue(ctrl.isVisible())

            # 4) Row 1 (Title + Member) above Row 2 (Templates + Goal + Days + Level)
            self.assertLess(view.txt_title.geometry().bottom(), view.combo_templates.geometry().top())
            self.assertEqual(view.txt_title.geometry().y(), view.combo_member_top.geometry().y())
            self.assertEqual(view.combo_templates.geometry().y(), view.combo_goal.geometry().y())
            self.assertEqual(view.combo_goal.geometry().y(), view.combo_days.geometry().y())
            self.assertEqual(view.combo_days.geometry().y(), view.combo_level.geometry().y())

            # In RTL, Row 1 right side is txt_title, left side is combo_member_top
            self.assertGreater(view.txt_title.geometry().x(), view.combo_member_top.geometry().x())
            # Both have generous room for long program names & long athlete names
            self.assertGreaterEqual(view.txt_title.width(), 380)
            self.assertGreaterEqual(view.combo_member_top.width(), 280)

            # Row 2 RTL ordering: templates rightmost -> goal -> days -> level leftmost
            self.assertGreater(view.combo_templates.geometry().x(), view.combo_goal.geometry().x())
            self.assertGreater(view.combo_goal.geometry().x(), view.combo_days.geometry().x())
            self.assertGreater(view.combo_days.geometry().x(), view.combo_level.geometry().x())

            # Zero horizontal overlap in Row 1 and Row 2
            self.assertGreaterEqual(view.txt_title.geometry().x(), view.combo_member_top.geometry().right())
            self.assertGreaterEqual(view.combo_templates.geometry().x(), view.combo_goal.geometry().right())
            self.assertGreaterEqual(view.combo_goal.geometry().x(), view.combo_days.geometry().right())
            self.assertGreaterEqual(view.combo_days.geometry().x(), view.combo_level.geometry().right())

            # 5) Bi-directional sync between combo_member_top and combo_member
            view.combo_member_top.setCurrentIndex(0)
            self.assertEqual(view.combo_member.currentData(), 1)
            view.combo_member.setCurrentIndex(1)
            self.assertEqual(view.combo_member_top.currentData(), 2)
            view.set_selected_member(1)
            self.assertEqual(view.combo_member_top.currentData(), 1)
            self.assertEqual(view.combo_member.currentData(), 1)

            # Manual typing in combo_member_top resolves cleanly in assign_plan()
            view.txt_title.setText("برنامه تخصصی افزایش حجم و قدرت بالاتنه")
            _, tbl = view.day_tables[0]
            view.add_exercise_row(tbl, [ex_item])
            tbl.cellWidget(0, 0).setCurrentIndex(0)
            view.combo_member.set_empty()
            view.combo_member_top.setEditText("محسن صمدی")

            with patch("nemov.views.workout_editor_view.WorkoutService.get_member_assignments", return_value=[]), \
                 patch("nemov.views.workout_editor_view.MemberService.get_health_record", return_value=None), \
                 patch("nemov.views.workout_editor_view.WorkoutService.create_workout_plan", return_value=SimpleNamespace(id=99, title="x")), \
                 patch("nemov.views.workout_editor_view.WorkoutService.assign_plan_to_member") as m_ap, \
                 patch("nemov.views.workout_editor_view.QMessageBox.information"), \
                 patch.object(view, "_handle_unregistered_exercises", return_value=True), \
                 patch("nemov.views.workout_editor_view.IncompletePlanWarningDialog") as m_dlg:
                from PyQt6.QtWidgets import QDialog
                m_dlg.return_value.exec.return_value = QDialog.DialogCode.Accepted
                view.assign_plan()
                m_ap.assert_called_once_with(2, 99)

            qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
            qa_dir.mkdir(parents=True, exist_ok=True)
            form_box.grab().save(str(qa_dir / "workout_header_dark_qa.png"))

            # Also verify light theme contrast & rendering ("olympic_white")
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            form_box.grab().save(str(qa_dir / "workout_header_light_qa.png"))
            view.close()

    def test_02_nutrition_editor_removed_subtitle_smaller_goal_larger_tdee_qa(self):
        from nemov.utils.theme_manager import ThemeManager, PALETTES
        from nemov.views.nutrition_editor_view import NutritionEditorView

        ThemeManager.apply_theme("crimson_fury", self.app)
        member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", status="expired",
            height_cm=180.0, initial_weight_kg=75.0, birth_date_shamsi="1380/01/01",
            gender="male", activity_level="moderately_active"
        )
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[member]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=member), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=[]):
            view = NutritionEditorView()
            view.resize(1280, 760)
            view.show()
            view.set_selected_member(1)
            self._pump()

            # 1) Removed subtitle text when expanded & collapse button anchored on form_box top border (y == 0)
            self.assertFalse(view.lbl_form_sub.isVisible())
            self.assertEqual(view.lbl_form_sub.text(), "")
            self.assertIs(view.btn_toggle_form.parentWidget(), view.form_box)
            self.assertEqual(view.btn_toggle_form.y(), 0)
            self.assertLessEqual(view.btn_toggle_form.x(), 24)
            # First row moves cleanly near the top of form_box with no blank row above it
            title_top_in_box = view.txt_title.mapTo(view.form_box, QPoint(0, 0)).y()
            self.assertLessEqual(title_top_in_box, 38)
            # No vertical overlap between border button (y=0..24) and row-1 widgets below
            btn_rect = QRect(view.btn_toggle_form.pos(), view.btn_toggle_form.size())
            tpl_rect = QRect(view.combo_templates.mapTo(view.form_box, QPoint(0, 0)), view.combo_templates.size())
            self.assertFalse(btn_rect.intersects(tpl_rect), f"btn_toggle_form {btn_rect} overlapped row1 {tpl_rect}")

            # 2) Compact Goal combobox (~156px) and enlarged TDEE field fitting full "2,740 کیلوکالری"
            self.assertLessEqual(view.combo_goal.width(), 168)
            self.assertGreaterEqual(view.txt_member_tdee.width(), 132)
            tdee_text = view.txt_member_tdee.text()
            self.assertIn("کیلوکالری", tdee_text)
            fm = QFontMetrics(view.txt_member_tdee.font())
            self.assertLess(fm.horizontalAdvance(tdee_text) + 12, view.txt_member_tdee.width())

            qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
            qa_dir.mkdir(parents=True, exist_ok=True)
            view.grab().save(str(qa_dir / "nutrition_header_tdee_dark_qa.png"))

            # Still shows compact summary on collapse, keeps button anchored on border without clipping, and hides again on expand
            view.toggle_form_collapse()
            self._pump()
            self.assertTrue(view.lbl_form_sub.isVisible())
            self.assertIn("ابوالفضل صمدی", view.lbl_form_sub.text())
            self.assertEqual(view.btn_toggle_form.y(), 0)
            fm_btn = QFontMetrics(view.btn_toggle_form.font())
            self.assertLess(fm_btn.horizontalAdvance(view.btn_toggle_form.text()) + 12, view.btn_toggle_form.width())
            sub_rect = QRect(view.lbl_form_sub.mapTo(view.form_box, QPoint(0, 0)), view.lbl_form_sub.size())
            collapsed_btn_rect = QRect(view.btn_toggle_form.pos(), view.btn_toggle_form.size())
            self.assertFalse(collapsed_btn_rect.intersects(sub_rect), "btn_toggle_form overlapped summary label when collapsed")
            view.grab().save(str(qa_dir / "nutrition_header_collapsed_qa.png"))

            view.toggle_form_collapse()
            self._pump()
            self.assertFalse(view.lbl_form_sub.isVisible())
            self.assertEqual(view.lbl_form_sub.text(), "")
            self.assertEqual(view.btn_toggle_form.y(), 0)

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            view.grab().save(str(qa_dir / "nutrition_header_light_qa.png"))
            view.close()

        # Verify distinct base vs input background contrast across ALL 17 dark & light themes
        for key, pal in PALETTES.items():
            self.assertNotEqual(pal.bg_base.lower(), pal.input_bg.lower(), f"Theme {key} lacks contrast between box base and input fields")

    def test_03_table_notes_and_delete_buttons_cell_fit_qa(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.workout_editor_view import WorkoutEditorView
        from nemov.views.nutrition_editor_view import NutritionEditorView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        # 1) Workout table: Notes ("📝 توضیحات" / "📝 توضیحات ✓") and Delete ("🗑️ حذف")
        ex_list = [SimpleNamespace(id=1, name_fa="اسکوات هالتر", primary_muscle="پا", description="")]
        with patch("nemov.views.workout_editor_view.MemberService.get_all_members", return_value=[]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_exercises", return_value=ex_list):
            w_view = WorkoutEditorView()
            w_view.resize(1280, 760)
            w_view.show()
            tbl = w_view.day_tables[0][1]
            w_view.add_exercise_row(tbl, ex_list)
            # Also add a row with custom trainer notes so checkmark state is verified
            tbl.insertRow(1)
            w_view._create_exercise_row_widgets(tbl, 1, ex_list, {"trainer_notes": "تست", "is_custom": True})
            self._pump()

            for row_idx in (0, 1):
                row_h = tbl.rowHeight(row_idx)
                row_top = tbl.rowViewportPosition(row_idx)
                btn_notes = tbl.cellWidget(row_idx, 6)
                btn_del = tbl.cellWidget(row_idx, 7)

                self.assertIn("توضیحات", btn_notes.text())
                self.assertGreaterEqual(btn_notes.geometry().y() - row_top, 4)
                self.assertLessEqual(btn_notes.geometry().bottom() - row_top, row_h - 4)
                self.assertLessEqual(btn_notes.width(), tbl.columnWidth(6) - 10)
                fm_n = QFontMetrics(btn_notes.font())
                self.assertLess(fm_n.horizontalAdvance(btn_notes.text()) + 12, btn_notes.width())

                self.assertIn("حذف", btn_del.text())
                self.assertIn("🗑", btn_del.text())
                self.assertGreaterEqual(btn_del.geometry().y() - row_top, 4)
                self.assertLessEqual(btn_del.geometry().bottom() - row_top, row_h - 4)
                self.assertLessEqual(btn_del.width(), tbl.columnWidth(7) - 10)
                fm_d = QFontMetrics(btn_del.font())
                self.assertLess(fm_d.horizontalAdvance("حذف") + 24, btn_del.width())

            tbl.grab().save(str(qa_dir / "workout_table_buttons_qa.png"))
            w_view.close()

        # 2) Nutrition table: Delete ("🗑️ حذف") inside food rows
        foods = [SimpleNamespace(id=1, name_fa="تخم مرغ", unit="عدد", calories=70, protein=6, carbs=1, fat=5)]
        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=foods):
            n_view = NutritionEditorView()
            n_view.resize(1280, 760)
            n_view.show()
            nt = n_view.meal_tables[0][1]
            n_view.add_food_row(nt, foods)
            self._pump()

            row_h = nt.rowHeight(0)
            n_del = nt.cellWidget(0, 4)
            self.assertIn("حذف", n_del.text())
            self.assertIn("🗑", n_del.text())
            self.assertGreaterEqual(n_del.geometry().y(), 4)
            self.assertLessEqual(n_del.geometry().bottom(), row_h - 4)
            self.assertLessEqual(n_del.width(), nt.columnWidth(4) - 10)
            fm_nd = QFontMetrics(n_del.font())
            self.assertLess(fm_nd.horizontalAdvance("حذف") + 24, n_del.width())

            nt.grab().save(str(qa_dir / "nutrition_table_buttons_qa.png"))
            n_view.close()

    def test_04_library_tables_select_and_row_columns_qa(self):
        from PyQt6.QtWidgets import QCheckBox
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.workout_library_view import WorkoutLibraryView
        from nemov.views.food_library_view import FoodLibraryView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        exercises = [
            SimpleNamespace(
                id=i + 1, name_fa=f"حرکت {i + 1}", primary_muscle="chest",
                equipment="barbell", contraindications="-", description="توضیح",
                is_corrective=False, video_cloud_url=None, media_path=None, media_type=None, video_url=None,
            )
            for i in range(12)
        ]
        with patch("nemov.views.workout_library_view.WorkoutService.get_all_exercises", return_value=exercises), \
             patch("nemov.services.cloud_sync_service.get_pending_sync_count", return_value=0):
            wl = WorkoutLibraryView()
            wl.resize(1280, 760)
            wl.show()
            self._pump()

            tbl = wl.table
            self.assertFalse(tbl.verticalHeader().isVisible())
            self.assertEqual(tbl.horizontalHeaderItem(0).text(), "انتخاب")
            self.assertEqual(tbl.horizontalHeaderItem(1).text(), "ردیف")
            self.assertEqual(tbl.horizontalHeaderItem(2).text(), "نام حرکت")
            # In RTL, col 0 (انتخاب) is rightmost -> x >= col 1 (ردیف)
            hdr = tbl.horizontalHeader()
            self.assertGreater(hdr.sectionViewportPosition(0), hdr.sectionViewportPosition(1))

            # Verify no header/number/checkbox clipping up to row 12 and Persian numerals
            fm_hdr = QFontMetrics(hdr.font())
            self.assertLess(fm_hdr.horizontalAdvance("انتخاب") + 12, hdr.sectionSize(0))
            self.assertLess(fm_hdr.horizontalAdvance("ردیف") + 12, hdr.sectionSize(1))
            self.assertEqual(tbl.item(0, 1).text(), "۱")
            self.assertEqual(tbl.item(11, 1).text(), "۱۲")
            self.assertEqual(tbl.item(0, 2).text(), "حرکت 1")
            fm_cell = QFontMetrics(tbl.font())
            self.assertLess(fm_cell.horizontalAdvance("۱۲") + 16, tbl.columnWidth(1))

            chk_w = tbl.cellWidget(0, 0)
            chk = chk_w.findChild(QCheckBox)
            self.assertIsNotNone(chk)
            self.assertLess(chk.width(), chk_w.width() + 2)
            chk.click()
            self.assertEqual(wl.get_selected_exercise_ids(), [1])

            tbl.grab().save(str(qa_dir / "workout_library_cols_qa.png"))
            wl.close()

        foods = [
            SimpleNamespace(
                id=i + 1, name_fa=f"ماده {i + 1}", category="meat",
                unit="100 گرم", calories=150, protein_g=20, carbs_g=2, fat_g=6,
            )
            for i in range(12)
        ]
        with patch("nemov.views.food_library_view.NutritionService.get_all_foods", return_value=foods):
            fl = FoodLibraryView()
            fl.resize(1280, 760)
            fl.show()
            self._pump()

            ftbl = fl.table
            self.assertFalse(ftbl.verticalHeader().isVisible())
            self.assertEqual(ftbl.horizontalHeaderItem(0).text(), "انتخاب")
            self.assertEqual(ftbl.horizontalHeaderItem(1).text(), "ردیف")
            self.assertEqual(ftbl.horizontalHeaderItem(2).text(), "نام ماده غذایی")
            fhdr = ftbl.horizontalHeader()
            self.assertGreater(fhdr.sectionViewportPosition(0), fhdr.sectionViewportPosition(1))

            fm_fhdr = QFontMetrics(fhdr.font())
            self.assertLess(fm_fhdr.horizontalAdvance("انتخاب") + 12, fhdr.sectionSize(0))
            self.assertLess(fm_fhdr.horizontalAdvance("ردیف") + 12, fhdr.sectionSize(1))
            self.assertEqual(ftbl.item(0, 1).text(), "۱")
            self.assertEqual(ftbl.item(11, 1).text(), "۱۲")
            self.assertEqual(ftbl.item(0, 2).text(), "ماده 1")
            fm_fcell = QFontMetrics(ftbl.font())
            self.assertLess(fm_fcell.horizontalAdvance("۱۲") + 16, ftbl.columnWidth(1))

            fchk_w = ftbl.cellWidget(0, 0)
            fchk = fchk_w.findChild(QCheckBox)
            self.assertIsNotNone(fchk)
            fchk.click()
            self.assertEqual(fl.get_selected_food_ids(), [1])

            ftbl.grab().save(str(qa_dir / "food_library_cols_qa.png"))
            fl.close()

    def test_05_member_list_select_col_matches_libraries_60px_qa(self):
        from PyQt6.QtWidgets import QCheckBox
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.member_list_view import MemberListView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        members = [
            SimpleNamespace(
                id=1, full_name="ابوالفضل صمدی", trainer_name="مربی", phone="09120000000",
                membership_type="12_sessions", membership_expire_shamsi="1405/12/29",
                status="active", photo_path=None,
            )
        ]
        with patch("nemov.views.member_list_view.MemberService.get_all_members", return_value=members):
            mv = MemberListView()
            mv.resize(1280, 760)
            mv.show()
            self._pump()

            mt = mv.table
            self.assertEqual(mt.horizontalHeaderItem(0).text(), "انتخاب")
            self.assertEqual(mt.columnWidth(0), 60)
            self.assertEqual(mt.horizontalHeader().sectionSize(0), 60)
            fm_hdr = QFontMetrics(mt.horizontalHeader().font())
            self.assertLess(fm_hdr.horizontalAdvance("انتخاب") + 12, mt.horizontalHeader().sectionSize(0))
            chk_w = mt.cellWidget(0, 0)
            self.assertIsNotNone(chk_w.findChild(QCheckBox))
            mt.grab().save(str(qa_dir / "member_list_select_col_qa.png"))
            mv.close()

    def test_06_all_select_columns_unified_60px_qa(self):
        from PyQt6.QtWidgets import QCheckBox
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.templates_manager_view import TemplatesManagerView
        from nemov.views.sms_view import SmsView
        from nemov.views.member_detail_view import MemberDetailView
        from nemov.views.backup_view import BackupView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        def assert_select_col_uniform(tbl, has_row_num: bool, expected_row_h: int = 52):
            self.assertFalse(tbl.verticalHeader().isVisible())
            self.assertEqual(tbl.verticalHeader().defaultSectionSize(), expected_row_h)
            self.assertEqual(tbl.horizontalHeaderItem(0).text(), "انتخاب")
            self.assertEqual(tbl.columnWidth(0), 60)
            self.assertEqual(tbl.horizontalHeader().sectionSize(0), 60)
            fm_hdr = QFontMetrics(tbl.horizontalHeader().font())
            self.assertLess(fm_hdr.horizontalAdvance("انتخاب") + 12, tbl.horizontalHeader().sectionSize(0))
            if has_row_num:
                self.assertEqual(tbl.horizontalHeaderItem(1).text(), "ردیف")
                self.assertEqual(tbl.columnWidth(1), 54)
                self.assertEqual(tbl.horizontalHeader().sectionSize(1), 54)
                self.assertLess(fm_hdr.horizontalAdvance("ردیف") + 12, tbl.horizontalHeader().sectionSize(1))

        # 1) TemplatesManagerView (workout & nutrition templates)
        w_tpl = SimpleNamespace(
            id=1, title="الگو تمرینی ۱", goal="hypertrophy", days_per_week=4,
            training_level="intermediate", days=[SimpleNamespace(workout_exercises=[SimpleNamespace(id=1)])],
            assignments=[],
        )
        n_tpl = SimpleNamespace(
            id=2, title="الگو غذایی ۱", goal="weight_loss", target_calories=2200,
            target_protein=160, target_carbs=220, target_fat=65,
            meals=[SimpleNamespace(id=1)], assignments=[],
        )
        with patch("nemov.services.workout_service.WorkoutService.get_all_plans", return_value=[w_tpl]), \
             patch("nemov.services.nutrition_service.NutritionService.get_all_plans", return_value=[n_tpl]):
            tm = TemplatesManagerView()
            tm.resize(1280, 760)
            tm.show()
            self._pump()
            assert_select_col_uniform(tm.table_workouts, has_row_num=True, expected_row_h=52)
            assert_select_col_uniform(tm.table_nutrition, has_row_num=True, expected_row_h=52)
            self.assertIsNotNone(tm.table_workouts.cellWidget(0, 0).findChild(QCheckBox))
            self.assertIsNotNone(tm.table_nutrition.cellWidget(0, 0).findChild(QCheckBox))
            tm.table_workouts.grab().save(str(qa_dir / "templates_manager_cols_qa.png"))
            tm.close()

        # 2) SmsView (recipients table)
        sms_member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", phone="09120000000",
            membership_expire_shamsi="1405/12/29", status="active",
        )
        with patch("nemov.services.member_service.MemberService.get_all_members", return_value=[sms_member]), \
             patch("nemov.services.sms_service.SmsService.get_balance", return_value=(True, 100, "")), \
             patch("nemov.services.sms_service.SmsService.get_history", return_value=[]), \
             patch("nemov.services.sms_service.SmsService.check_and_send_automated_birthdays", return_value=0), \
             patch("nemov.services.sms_service.SmsService.check_and_send_automated_tuitions", return_value=0), \
             patch("nemov.views.sms_view.SmsBalanceThread.start"), \
             patch("nemov.views.sms_view.SmsHistoryThread.start"):
            sv = SmsView()
            sv.resize(1280, 760)
            sv.show()
            self._pump()
            assert_select_col_uniform(sv.table_members, has_row_num=False, expected_row_h=52)
            self.assertIsNotNone(sv.table_members.cellWidget(0, 0).findChild(QCheckBox))
            sv.table_members.grab().save(str(qa_dir / "sms_members_cols_qa.png"))
            sv.close()

        # 3) MemberDetailView (workout & nutrition history tables)
        md_member = SimpleNamespace(
            id=1, full_name="ابوالفضل صمدی", trainer_name="مربی", phone="09120000000",
            gender="male", birth_date_shamsi="1380/01/01", height_cm=180, initial_weight_kg=75,
            membership_type="12_sessions", membership_expire_shamsi="1405/12/29",
            status="active", photo_path=None, notes="", activity_level="moderately_active",
        )
        with patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=md_member), \
             patch("nemov.services.workout_service.WorkoutService.get_member_assignments", return_value=[]), \
             patch("nemov.services.nutrition_service.NutritionService.get_member_assignments", return_value=[]):
            md = MemberDetailView(1)
            md.resize(1280, 760)
            md.show()
            self._pump()
            assert_select_col_uniform(md.table_workout, has_row_num=True, expected_row_h=52)
            assert_select_col_uniform(md.table_nutrition, has_row_num=True, expected_row_h=52)
            md.table_workout.grab().save(str(qa_dir / "member_detail_cols_qa.png"))
            md.close()

        # 4) BackupView (backup archives & notification history tables)
        with patch("nemov.services.backup_service.BackupService.get_all_backups", return_value=[]), \
             patch("nemov.services.notification_service.NotificationService.get_history", return_value=[]):
            bv = BackupView()
            bv.resize(1280, 760)
            bv.show()
            self._pump()
            assert_select_col_uniform(bv.table, has_row_num=True, expected_row_h=52)
            assert_select_col_uniform(bv.table_notif_history, has_row_num=True, expected_row_h=52)
            bv.table.grab().save(str(qa_dir / "backup_cols_qa.png"))
            bv.close()

    def test_07_sidebar_brand_title_and_subtitle_right_aligned_qa(self):
        from PyQt6.QtCore import QPoint
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.components.sidebar import Sidebar

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)

        ThemeManager.apply_theme("crimson_fury", self.app)
        with patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "", "club_logo_path": ""}):
            sb = Sidebar()
            sb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            sb.resize(230, 760)
            sb.show()
            self._pump()

            # Expanded header: Logo on far right -> Title "نِمو" sits ~15px left of logo -> Toggle button on far left
            logo_left = sb.logo_lbl.mapTo(sb, QPoint(0, 0)).x()
            logo_right = sb.logo_lbl.mapTo(sb, QPoint(sb.logo_lbl.width() - 1, 0)).x()
            title_left = sb.title_lbl.mapTo(sb, QPoint(0, 0)).x()
            title_right = sb.title_lbl.mapTo(sb, QPoint(sb.title_lbl.width() - 1, 0)).x()
            sub_left = sb.sub_lbl.mapTo(sb, QPoint(0, 0)).x()
            toggle_left = sb.btn_toggle_sidebar.mapTo(sb, QPoint(0, 0)).x()
            toggle_right = sb.btn_toggle_sidebar.mapTo(sb, QPoint(sb.btn_toggle_sidebar.width() - 1, 0)).x()

            self.assertGreaterEqual(logo_right, sb.width() - 24)
            logo_title_gap = logo_left - title_right
            self.assertGreaterEqual(logo_title_gap, 10)
            self.assertLessEqual(logo_title_gap, 22)
            self.assertGreaterEqual(title_left, sub_left - 2)
            self.assertLessEqual(toggle_left, 20)
            self.assertLess(toggle_right, title_left)
            self.assertTrue(bool(sb.sub_lbl.alignment() & Qt.AlignmentFlag.AlignRight))
            self.assertTrue(bool(sb.sub_lbl.alignment() & Qt.AlignmentFlag.AlignAbsolute))

            sb.grab().save(str(qa_dir / "sidebar_brand_dark_qa.png"))
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            sb.grab().save(str(qa_dir / "sidebar_brand_light_qa.png"))
            sb.close()

    def test_08_password_recovery_eye_buttons_no_clipping_qa(self):
        from PyQt6.QtWidgets import QLineEdit
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.password_recovery_dialog import PasswordRecoveryDialog

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        dlg = PasswordRecoveryDialog()
        dlg.step2_frame.setVisible(True)
        dlg.setFixedSize(540, 700)
        dlg.show()
        self._pump()

        for btn, field in (
            (dlg.btn_eye_rec, dlg.txt_recovery_code),
            (dlg.btn_eye_new, dlg.txt_new_password),
        ):
            self.assertEqual(btn.objectName(), "eye_button")
            self.assertIn("padding: 0px", btn.styleSheet())
            self.assertEqual(btn.size().width(), 44)
            self.assertEqual(btn.size().height(), 38)
            self.assertEqual(btn.text(), "👁️")
            fm = QFontMetrics(btn.font())
            self.assertLess(fm.horizontalAdvance("👁️"), btn.width() - 6)
            self.assertLess(fm.horizontalAdvance("🙈"), btn.width() - 6)

            btn.click()
            self._pump()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
            self.assertEqual(btn.text(), "🙈")

        dlg.step2_frame.grab().save(str(qa_dir / "recovery_eye_toggled_qa.png"))
        dlg.btn_eye_new.click()
        self._pump()
        self.assertEqual(dlg.btn_eye_new.text(), "👁️")
        dlg.step2_frame.grab().save(str(qa_dir / "recovery_eye_dark_qa.png"))
        dlg.close()

    def test_09_trainer_register_eye_buttons_no_clipping_qa(self):
        from PyQt6.QtWidgets import QLineEdit
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.trainer_register_dialog import TrainerRegisterDialog

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        dlg = TrainerRegisterDialog()
        dlg.show()
        self._pump()

        eye_pairs = (
            (dlg.btn_eye1, dlg.txt_password),
            (dlg.btn_eye2, dlg.txt_password_confirm),
            (dlg.btn_eye3, dlg.txt_recovery_code),
            (dlg.btn_eye4, dlg.txt_recovery_confirm),
        )
        for btn, field in eye_pairs:
            self.assertEqual(btn.objectName(), "eye_button")
            self.assertIn("padding: 0px", btn.styleSheet())
            self.assertEqual(btn.size().width(), 44)
            self.assertEqual(btn.size().height(), 38)
            self.assertEqual(btn.text(), "👁️")
            fm = QFontMetrics(btn.font())
            self.assertLess(fm.horizontalAdvance("👁️"), btn.width() - 6)
            self.assertLess(fm.horizontalAdvance("🙈"), btn.width() - 6)

            btn.click()
            self._pump()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
            self.assertEqual(btn.text(), "🙈")

            btn.click()
            self._pump()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
            self.assertEqual(btn.text(), "👁️")

        dlg.close()

    def test_10_scoped_container_stylesheets_preserve_button_backgrounds_qa(self):
        from PyQt6.QtWidgets import QFrame, QScrollArea
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.backup_view import BackupView
        from nemov.views.developer_view import DeveloperView
        from nemov.views.components.trainer_details_dialog import TrainerDetailsDialog

        for theme_id in ("crimson_fury", "olympic_white", "fresh_mint"):
            ThemeManager.apply_theme(theme_id, self.app)
            with patch("nemov.services.backup_service.BackupService.get_all_backups", return_value=[]), \
                 patch("nemov.services.notification_service.NotificationService.get_history", return_value=[]), \
                 patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={}):
                bv = BackupView()
                bv.tabs.setCurrentWidget(bv.tab_appearance)
                bv.show()
                self._pump()

                # Container inside QScrollArea must scope its transparent rule to its objectName
                app_container = bv.tab_appearance.widget()
                self.assertEqual(app_container.objectName(), "appearance_scroll_container")
                self.assertIn("QWidget#appearance_scroll_container", app_container.styleSheet())
                self.assertEqual(bv.btn_save_club_info.objectName(), "primary_button")

                prof_container = bv.tab_profile.widget()
                self.assertEqual(prof_container.objectName(), "profile_scroll_container")
                self.assertIn("QWidget#profile_scroll_container", prof_container.styleSheet())
                bv.close()

        with patch("nemov.auth.authentication.is_app_license_active", return_value=True):
            dv = DeveloperView()
            for tab_idx, obj_name in ((0, "dev_app_scroll_container"), (1, "dev_info_scroll_container")):
                sa = dv.tabs.widget(tab_idx).findChild(QScrollArea) or dv.tabs.widget(tab_idx)
                w = sa.widget() if hasattr(sa, "widget") else None
                if w is not None:
                    self.assertEqual(w.objectName(), obj_name)
                    self.assertIn(f"QWidget#{obj_name}", w.styleSheet())
            dv.close()

        td = TrainerDetailsDialog(None, {"display_name": "تست", "username": "t1", "password_plain": "123", "phone": "09120000000"})
        for obj_name in ("trainer_pass_row", "trainer_rec_row", "trainer_reset_pass_box", "trainer_pass_card"):
            child = td.findChild(QFrame, obj_name)
            self.assertIsNotNone(child, f"Missing scoped container {obj_name}")
            self.assertIn(f"QFrame#{obj_name}", child.styleSheet())
        td.close()

    def test_11_trainer_details_eyes_and_backup_prog_close_no_clipping_qa(self):
        from PyQt6.QtWidgets import QLineEdit
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.backup_view import BackupView
        from nemov.views.components.trainer_details_dialog import TrainerDetailsDialog

        ThemeManager.apply_theme("crimson_fury", self.app)

        td = TrainerDetailsDialog(None, {
            "id": 2, "display_name": "تست", "username": "t1",
            "password": "secret", "recovery_code": "rec99", "phone": "09120000000"
        })
        td.reset_pass_box.setVisible(True)
        td.show()
        self._pump()

        for btn, field, exp_h in (
            (td.btn_eye_pass, td.txt_display_pass, 34),
            (td.btn_eye_rec, td.txt_display_rec, 34),
            (td.btn_eye_new, td.txt_admin_new_pass, 36),
        ):
            self.assertEqual(btn.objectName(), "eye_button")
            self.assertIn("padding: 0px", btn.styleSheet())
            self.assertEqual(btn.width(), 44)
            self.assertEqual(btn.height(), exp_h)
            fm = QFontMetrics(btn.font())
            self.assertLess(fm.horizontalAdvance("👁️"), btn.width() - 6)
            self.assertLess(fm.horizontalAdvance("🙈"), btn.width() - 6)

            btn.click()
            self._pump()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
            self.assertEqual(btn.text(), "🙈")

            btn.click()
            self._pump()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
            self.assertEqual(btn.text(), "👁️")
        td.close()

        with patch("nemov.services.backup_service.BackupService.get_all_backups", return_value=[]), \
             patch("nemov.services.notification_service.NotificationService.get_history", return_value=[]), \
             patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={}):
            bv = BackupView()
            bv.progress_card.setVisible(True)
            bv.btn_prog_close.setVisible(True)
            bv.show()
            self._pump()
            self.assertIn("padding: 0px", bv.btn_prog_close.styleSheet())
            self.assertEqual(bv.btn_prog_close.width(), 26)
            self.assertEqual(bv.btn_prog_close.height(), 26)
            fm_c = QFontMetrics(bv.btn_prog_close.font())
            self.assertLess(fm_c.horizontalAdvance("✕"), bv.btn_prog_close.width() - 4)
            bv.close()

    def test_12_sms_dynamic_card_uniform_background_qa(self):
        from PyQt6.QtWidgets import QLineEdit
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.sms_view import SmsView

        ThemeManager.apply_theme("crimson_fury", self.app)
        with patch("nemov.views.sms_view.MemberService.get_all_members", return_value=[]):
            sv = SmsView()
            sv.resize(1200, 760)
            sv.show()
            self._pump()

            self.assertEqual(sv.dynamic_frame.objectName(), "sms_dynamic_card")
            self.assertIn("QFrame#sms_dynamic_card", sv.dynamic_frame.styleSheet())
            self.assertIn(ThemeManager.get_current_palette().bg_base, sv.dynamic_frame.styleSheet())
            self.assertEqual(sv.panel_holiday.objectName(), "sms_panel_holiday")
            self.assertIn("QWidget#sms_panel_holiday", sv.panel_holiday.styleSheet())
            self.assertIn("background: transparent", sv.panel_holiday.styleSheet())
            self.assertEqual(sv.panel_hours.objectName(), "sms_panel_hours")
            self.assertIn("QWidget#sms_panel_hours", sv.panel_hours.styleSheet())
            self.assertIn("background: transparent", sv.panel_hours.styleSheet())

            # Ensure inner inputs remain accessible and intact across both template panels
            self.assertGreater(sv.input_dyn_date.width(), 100)
            self.assertGreater(sv.input_dyn_reason.width(), 100)
            sv.combo_templates.setCurrentIndex(1)
            self._pump()
            self.assertTrue(sv.panel_hours.isVisible())
            sv.close()

    def test_13_password_recovery_and_dev_update_card_no_inset_contrast_qa(self):
        from PyQt6.QtWidgets import QFrame
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.developer_view import DeveloperView
        from nemov.views.password_recovery_dialog import PasswordRecoveryDialog

        ThemeManager.apply_theme("crimson_fury", self.app)

        dlg = PasswordRecoveryDialog()
        dlg.show()
        self._pump()
        self.assertEqual(dlg.stack.objectName(), "recovery_stack")
        self.assertIn("QStackedWidget#recovery_stack", dlg.stack.styleSheet())
        self.assertIn("background: transparent", dlg.stack.styleSheet())

        p0 = dlg.stack.widget(0)
        p1 = dlg.stack.widget(1)
        self.assertEqual(p0.objectName(), "recovery_page_sms")
        self.assertIn("QFrame#recovery_page_sms", p0.styleSheet())
        self.assertIn("background: transparent", p0.styleSheet())
        self.assertEqual(p1.objectName(), "recovery_page_secret")
        self.assertIn("QFrame#recovery_page_secret", p1.styleSheet())
        self.assertIn("background: transparent", p1.styleSheet())
        dlg.close()

        with patch("nemov.auth.authentication.is_app_license_active", return_value=True):
            dv = DeveloperView()
            dv.changelog_container.setVisible(True)
            dv.download_panel.setVisible(True)
            dv.show()
            self._pump()

            self.assertEqual(dv.update_status_card.objectName(), "dev_update_status_card")
            self.assertIn("QFrame#dev_update_status_card", dv.update_status_card.styleSheet())
            self.assertEqual(dv.changelog_container.objectName(), "dev_changelog_container")
            self.assertIn("QWidget#dev_changelog_container", dv.changelog_container.styleSheet())
            self.assertIn("background: transparent", dv.changelog_container.styleSheet())
            self.assertEqual(dv.download_panel.objectName(), "dev_download_panel")
            self.assertIn("QWidget#dev_download_panel", dv.download_panel.styleSheet())
            self.assertIn("background: transparent", dv.download_panel.styleSheet())
            dv.close()

    def test_14_dual_logo_routing_pdf_and_light_theme_qa(self):
        import numpy as np
        from PIL import Image
        from types import SimpleNamespace
        from nemov.utils.theme_manager import ThemeManager
        from nemov.services.branding_service import BrandingService
        from nemov.pdf.pdf_generator import PDFGenerator
        from nemov.views.login_view import LoginView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)

        # 1. Default branding: Dark theme -> white-text logo; Light theme & PDF -> dark-slate logo
        with patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "", "club_logo_path": ""}):
            ThemeManager.apply_theme("crimson_fury", self.app)
            dark_path = Path(BrandingService.get_active_logo_path())
            self.assertEqual(dark_path.name, "nemov_logo.png")
            self.assertTrue(dark_path.exists())

            # PDF ALWAYS selects dark-slate logo even when active theme is Dark
            pdf_path_in_dark = Path(BrandingService.get_pdf_logo_path())
            self.assertEqual(pdf_path_in_dark.name, "nemov_logo_light.png")
            self.assertTrue(pdf_path_in_dark.exists())

            # Light theme UI selects dark-slate logo automatically
            ThemeManager.apply_theme("olympic_white", self.app)
            light_path = Path(BrandingService.get_active_logo_path())
            self.assertEqual(light_path.name, "nemov_logo_light.png")

            # Verify NEMOV text pixels in nemov_logo_light.png are genuinely dark slate (high contrast on white)
            light_arr = np.array(Image.open(light_path).convert("RGBA"))
            text_region = light_arr[522:590, :, :]
            opaque_mask = text_region[:, :, 3] > 200
            self.assertTrue(opaque_mask.any())
            mean_rgb = text_region[opaque_mask][:, :3].mean()
            self.assertLess(mean_rgb, 90.0)

        # 2. Custom club logo ALWAYS takes precedence for both UI and PDF
        custom_img = PROJECT_ROOT / "resources" / "images" / "app_icon.png"
        if custom_img.exists():
            with patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "باشگاه تست", "club_logo_path": str(custom_img)}):
                ThemeManager.apply_theme("olympic_white", self.app)
                self.assertEqual(Path(BrandingService.get_active_logo_path()).resolve(), custom_img.resolve())
                self.assertEqual(Path(BrandingService.get_pdf_logo_path()).resolve(), custom_img.resolve())

        # 3. LoginView live logo swap & visual captures in both dark and light themes
        ThemeManager.apply_theme("crimson_fury", self.app)
        lv = LoginView()
        lv.show()
        self._pump()
        dark_pm_hash = lv.lbl_logo.pixmap().toImage().constBits().asstring(lv.lbl_logo.pixmap().toImage().sizeInBytes())
        lv.grab().save(str(qa_dir / "login_dark_logo_qa.png"))

        ThemeManager.apply_theme("olympic_white", self.app)
        self._pump()
        light_pm_hash = lv.lbl_logo.pixmap().toImage().constBits().asstring(lv.lbl_logo.pixmap().toImage().sizeInBytes())
        self.assertNotEqual(dark_pm_hash, light_pm_hash)
        lv.grab().save(str(qa_dir / "login_light_logo_qa.png"))
        lv.close()

        # 4. Real workout PDF generation uses get_pdf_logo_path and produces non-empty PDF
        out_pdf = qa_dir / "workout_pdf_dual_logo_qa.pdf"
        member = SimpleNamespace(
            id=1,
            full_name="محسن صمدی",
            age=28,
            height=178,
            weight=76,
            gender="آقا",
            phone="09120000000",
            coach_name="محراب حاجی‌پور",
            goal="تناسب اندام",
            trainer_id=1,
            membership_expire_shamsi="1405/12/01",
            trainer=SimpleNamespace(full_name="محراب حاجی‌پور", phone="09120000001"),
        )
        ex_item = SimpleNamespace(
            exercise=None,
            custom_exercise_name="پرس سینه هالتر",
            trainer_notes="",
            tempo="3-1-1",
            rest_seconds=60,
            weight_suggestion="60",
            reps="10",
            sets=4,
        )
        plan = SimpleNamespace(
            title="برنامه تستی",
            goal="hypertrophy",
            days_per_week=3,
            days_count=3,
            notes="تست لوگو",
            trainer_name="مربی",
            created_at=None,
            days=[SimpleNamespace(day_title="روز اول — سینه", workout_exercises=[ex_item])],
        )
        with patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "", "club_logo_path": ""}), \
             patch("nemov.services.branding_service.BrandingService.get_pdf_logo_path", wraps=BrandingService.get_pdf_logo_path) as spy_pdf_logo:
            ThemeManager.apply_theme("crimson_fury", self.app)
            ok = PDFGenerator.generate_workout_pdf(member, plan, str(out_pdf))
            self.assertTrue(ok)
            self.assertTrue(out_pdf.exists() and out_pdf.stat().st_size > 2000)
            spy_pdf_logo.assert_called()

            # Render Page 1 via PyQt6.QtPdf if available for direct visual inspection
            try:
                from PyQt6.QtPdf import QPdfDocument
                doc = QPdfDocument()
                if doc.load(str(out_pdf)) == QPdfDocument.Error.None_:
                    img = doc.render(0, doc.pagePointSize(0).toSize() * 2)
                    img.save(str(qa_dir / "workout_pdf_page1_qa.png"))
                doc.close()
            except Exception:
                pass

    def test_15_nutrition_templates_persian_goal_and_macro_column_qa(self):
        from types import SimpleNamespace
        from PyQt6.QtGui import QFontMetrics
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.templates_manager_view import TemplatesManagerView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        sample_plans = [
            SimpleNamespace(id=1, title="رژیم تست مواد اختصاصی", goal="muscle_gain", target_calories=2500, target_protein=160, target_carbs=280, target_fat=75, meals=[1], assignments=[1]),
            SimpleNamespace(id=2, title="رژیم چربی‌سوزی ویژه", goal="weight_loss", target_calories=1800, target_protein=145, target_carbs=150, target_fat=55, meals=[1, 2], assignments=[]),
            SimpleNamespace(id=3, title="رژیم افزایش وزن پیشرفته", goal="weight_gain", target_calories=3200, target_protein=210, target_carbs=420, target_fat=95, meals=[1, 2, 3], assignments=[1, 2]),
            SimpleNamespace(id=4, title="رژیم تثبیت", goal="maintenance", target_calories=2200, target_protein=130, target_carbs=250, target_fat=70, meals=[], assignments=[]),
            SimpleNamespace(id=5, title="", goal="", target_calories=0, target_protein=0, target_carbs=0, target_fat=0, meals=None, assignments=None),
        ]

        with patch("nemov.views.templates_manager_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.templates_manager_view.NutritionService.get_all_plans", return_value=sample_plans):
            tm = TemplatesManagerView()
            tm.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            tm.resize(1120, 620)
            tm.tabs.setCurrentWidget(tm.tab_nutrition)
            tm.load_all_templates()
            tm.show()
            self._pump()

            # 1. Zero English words in nutrition filter combo items while filter keys remain intact
            for idx in range(tm.combo_filter_nutrition_goal.count()):
                item_txt = tm.combo_filter_nutrition_goal.itemText(idx)
                for eng in ("Muscle Gain", "Weight Loss", "Weight Gain", "Maintenance", "(", ")"):
                    self.assertNotIn(eng, item_txt)

            # 2. Column widths transferred cleanly from goal (95px) to macros (210px)
            self.assertEqual(tm.table_nutrition.columnWidth(3), 95)
            self.assertGreaterEqual(tm.table_nutrition.columnWidth(5), 210)

            # 3. Every goal cell has Persian-only text & zero clipping; every macro cell fits cleanly in 210px with LRM
            fm = QFontMetrics(tm.table_nutrition.font())
            expected_goals = ["عضله‌سازی", "کاهش وزن", "افزایش وزن", "تثبیت وزن", "-"]
            for row in range(len(sample_plans)):
                g_txt = tm.table_nutrition.item(row, 3).text()
                self.assertEqual(g_txt, expected_goals[row])
                for eng in ("Muscle", "Weight", "Maintenance", "(", ")"):
                    self.assertNotIn(eng, g_txt)
                self.assertLessEqual(fm.horizontalAdvance(g_txt), tm.table_nutrition.columnWidth(3) - 10)

                m_txt = tm.table_nutrition.item(row, 5).text()
                self.assertTrue(m_txt.startswith("\u200EP: "))
                self.assertLessEqual(fm.horizontalAdvance(m_txt), tm.table_nutrition.columnWidth(5) - 10, f"Macro cell clipped: '{m_txt}' w={fm.horizontalAdvance(m_txt)} vs col={tm.table_nutrition.columnWidth(5)}")

            # Header title for macros fits inside column 5 width
            hdr_txt = tm.table_nutrition.horizontalHeaderItem(5).text()
            self.assertLessEqual(fm.horizontalAdvance(hdr_txt), tm.table_nutrition.columnWidth(5) - 6)

            tm.grab().save(str(qa_dir / "nutrition_templates_table_qa.png"))

            # 4. Filter dropdown still filters accurately by goal key
            idx_loss = tm.combo_filter_nutrition_goal.findData("weight_loss")
            tm.combo_filter_nutrition_goal.setCurrentIndex(idx_loss)
            self._pump()
            self.assertEqual(tm.table_nutrition.rowCount(), 1)
            self.assertEqual(tm.table_nutrition.item(0, 3).text(), "کاهش وزن")
            tm.close()


if __name__ == "__main__":
    unittest.main()
