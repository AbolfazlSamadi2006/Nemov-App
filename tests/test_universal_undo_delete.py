import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestUniversalUndoDelete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pump(self):
        self.app.processEvents()

    # ------------------------------------------------------------------
    # 1. UndoDeleteBanner core behavior, 5s default & Visual Geometry QA
    # ------------------------------------------------------------------
    def test_01_undo_banner_default_5s_and_geometry_qa(self):
        from nemov.views.components.undo_delete_banner import UndoDeleteBanner

        host = QWidget()
        host.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        host.resize(820, 120)
        lay = QVBoxLayout(host)
        banner = UndoDeleteBanner(host)
        lay.addWidget(banner)

        self.assertEqual(banner.remaining_seconds, 5)
        self.assertEqual(banner.total_seconds, 5)
        self.assertIn("۵ ثانیه", banner.lbl_countdown.text())
        self.assertIn("۵ ثانیه‌ای", banner.btn_dismiss.toolTip())

        committed = []
        undone = []

        banner.start_countdown(
            item_count=2,
            pending_items=[101, 102],
            on_commit=lambda ids: committed.extend(ids),
            on_undo=lambda ids: undone.extend(ids),
            item_label="رکورد تستی",
        )
        host.show()
        self._pump()

        self.assertTrue(banner.isVisible())
        self.assertEqual(banner.remaining_seconds, 5)
        self.assertEqual(banner.total_seconds, 5)
        self.assertIn("۵ ثانیه", banner.lbl_countdown.text())
        self.assertIn("۲", banner.lbl_message.text())

        # Geometry & non-clipping QA checks
        b_rect = banner.rect()
        for child in (banner.lbl_message, banner.lbl_countdown, banner.btn_undo, banner.btn_dismiss):
            geom = child.geometry()
            self.assertGreater(geom.width(), 20)
            self.assertGreater(geom.height(), 16)
            self.assertTrue(b_rect.contains(geom), f"Clipped child {child.text()}: {geom} not inside {b_rect}")

        # Verify RTL horizontal ordering (message rightmost -> dismiss leftmost)
        self.assertGreater(banner.lbl_message.geometry().x(), banner.lbl_countdown.geometry().x())
        self.assertGreater(banner.btn_undo.geometry().x(), banner.btn_dismiss.geometry().x())

        # Capture visual QA screenshot
        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        host.grab().save(str(qa_dir / "undo_banner_5s_qa.png"))

        # Also verify non-clipped geometry of UndoDeleteBanner inside AccountingView
        from nemov.views.accounting_view import AccountingView
        with patch("nemov.views.accounting_view.AccountingService.get_all_trainers", return_value=[]), \
             patch("nemov.views.accounting_view.AccountingService.get_financial_summary", return_value={"total_income": 0, "total_expense": 0, "net_profit": 0, "total_transactions": 0}), \
             patch("nemov.views.accounting_view.AccountingService.get_transactions", return_value=[]):
            av = AccountingView()
            av.resize(1100, 720)
            av.show()
            av.undo_banner.start_countdown(1, [99], lambda _: None, lambda _: None, "تراکنش تستی")
            self._pump()
            self.assertTrue(av.undo_banner.isVisible())
            self.assertGreater(av.undo_banner.height(), 30)
            self.assertTrue(av.rect().contains(av.undo_banner.geometry()))
            av.undo_banner.timer.stop()
            av.close()

        # Test countdown ticks down 5 -> 4 -> ... -> 1 -> 0 (commit)
        banner._on_tick()
        self.assertEqual(banner.remaining_seconds, 4)
        self.assertIn("۴ ثانیه", banner.lbl_countdown.text())
        banner.trigger_undo()
        self.assertFalse(banner.isVisible())
        self.assertFalse(banner.timer.isActive())
        self.assertEqual(undone, [101, 102])
        self.assertEqual(committed, [])

        # Restart and let timer expire
        banner.start_countdown(1, [202], lambda ids: committed.extend(ids), lambda ids: undone.extend(ids), "آیتم")
        for _ in range(5):
            banner._on_tick()
        self.assertFalse(banner.isVisible())
        self.assertEqual(committed, [202])

        # Re-triggering while active commits prior pending item
        committed.clear()
        banner.start_countdown(1, [301], lambda ids: committed.extend(ids), lambda _: None)
        banner.start_countdown(1, [302], lambda ids: committed.extend(ids), lambda _: None)
        self.assertEqual(committed, [301])
        banner.timer.stop()
        host.close()

    # ------------------------------------------------------------------
    # 2. AccountingView: expense & tuition delete confirm + 5s undo
    # ------------------------------------------------------------------
    def test_02_accounting_view_delete_expense_and_tuition(self):
        from nemov.views.accounting_view import AccountingView

        with patch("nemov.views.accounting_view.AccountingService.get_all_trainers", return_value=[]), \
             patch("nemov.views.accounting_view.AccountingService.get_financial_summary", return_value={
                 "total_income": 500000, "total_expense": 100000, "net_profit": 400000, "total_transactions": 2
             }), \
             patch("nemov.views.accounting_view.AccountingService.get_transactions", return_value=[
                 {"id": 11, "type": "expense", "title": "خرید وزنه", "category": "تجهیزات", "date_shamsi": "1405/01/01", "amount": 100000, "trainer_name": "مربی", "description": ""},
                 {"id": 22, "type": "income", "title": "شهریه علی", "category": "شهریه", "date_shamsi": "1405/01/02", "amount": 500000, "trainer_name": "مربی", "description": ""},
             ]):
            view = AccountingView()
            view.load_data()
            self.assertEqual(view.table.rowCount(), 2)

            tx_exp = {"id": 11, "title": "خرید وزنه", "amount": 100000}
            tx_inc = {"id": 22, "title": "شهریه علی", "amount": 500000}

            # Cancel confirmation -> nothing deleted, row stays visible
            with patch("nemov.views.accounting_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.No) as m_warn, \
                 patch("nemov.views.accounting_view.AccountingService.delete_expense") as m_del_exp:
                view.delete_expense(tx_exp)
                m_warn.assert_called_once()
                self.assertIn("۵ ثانیه", m_warn.call_args[0][2])
                m_del_exp.assert_not_called()
                self.assertFalse(view.undo_banner.timer.isActive())
                self.assertFalse(view.table.isRowHidden(0))

            # Confirm expense -> row hidden, 5s banner active, undo cancels deletion
            with patch("nemov.views.accounting_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.accounting_view.AccountingService.delete_expense") as m_del_exp:
                view.delete_expense(tx_exp)
                self.assertEqual(view.undo_banner.remaining_seconds, 5)
                self.assertTrue(view.table.isRowHidden(0))
                view.undo_banner.trigger_undo()
                m_del_exp.assert_not_called()

            # Confirm tuition -> commit_now calls delete_tuition_payment
            with patch("nemov.views.accounting_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.accounting_view.AccountingService.delete_tuition_payment") as m_del_inc:
                view.delete_tuition_payment(tx_inc)
                self.assertEqual(view.undo_banner.remaining_seconds, 5)
                self.assertTrue(view.table.isRowHidden(1))
                view.undo_banner.commit_now()
                m_del_inc.assert_called_once_with(22)
            view.close()

    # ------------------------------------------------------------------
    # 3. AssessmentView: delete confirm + 5s undo
    # ------------------------------------------------------------------
    def test_03_assessment_view_delete_confirm_and_undo(self):
        from nemov.views.assessment_view import AssessmentView

        rec = SimpleNamespace(
            id=55, assessment_date_shamsi="1405/02/10", height_cm=175, weight_kg=72,
            body_fat_percentage=15, bmr=1700, tdee=2500, neck_circ=38, chest_circ=100,
            arm_circ=35, abdomen_circ=82, waist_circ=80, hip_circ=95, thigh_circ=56,
            before_photo_path=None, after_photo_path=None
        )
        with patch("nemov.views.assessment_view.AssessmentService.get_member_assessments", return_value=[rec]), \
             patch("nemov.services.member_service.MemberService.get_member_by_id", return_value=None):
            view = AssessmentView(member_id=1)

            with patch("nemov.views.assessment_view.QMessageBox.question", return_value=QMessageBox.StandardButton.No), \
                 patch("nemov.views.assessment_view.AssessmentService.delete_assessment") as m_del:
                view.delete_assessment_confirm(rec)
                m_del.assert_not_called()
                self.assertFalse(view.table.isRowHidden(0))

            with patch("nemov.views.assessment_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.assessment_view.AssessmentService.delete_assessment") as m_del:
                view.delete_assessment_confirm(rec)
                self.assertEqual(view.undo_banner.remaining_seconds, 5)
                self.assertTrue(view.table.isRowHidden(0))
                view.undo_banner.trigger_undo()
                m_del.assert_not_called()

            with patch("nemov.views.assessment_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.assessment_view.AssessmentService.delete_assessment") as m_del:
                view.delete_assessment_confirm(rec)
                view.undo_banner.commit_now()
                m_del.assert_called_once_with(55)
            view.close()

    # ------------------------------------------------------------------
    # 4. HealthRecordView & AddMedicalDocumentDialog: confirm + 5s undo
    # ------------------------------------------------------------------
    def test_04_health_record_and_doc_page_remove_confirm_and_undo(self):
        from nemov.views.health_record_view import HealthRecordView, AddMedicalDocumentDialog

        doc = SimpleNamespace(
            id=88, title="آزمایش خون", created_at_shamsi="1405/03/01",
            notes="عادی", file_paths_list=["page1.png", "page2.png"]
        )
        with patch("nemov.views.health_record_view.MemberService.get_health_record", return_value=None), \
             patch("nemov.views.health_record_view.MemberService.get_medical_documents", return_value=[doc]):
            view = HealthRecordView(member_id=1)

            with patch("nemov.views.health_record_view.QMessageBox.question", return_value=QMessageBox.StandardButton.No), \
                 patch("nemov.views.health_record_view.MemberService.delete_medical_document") as m_del:
                view.delete_document(88)
                m_del.assert_not_called()

            with patch("nemov.views.health_record_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.health_record_view.MemberService.delete_medical_document") as m_del:
                view.delete_document(88)
                self.assertEqual(view.undo_banner.remaining_seconds, 5)
                self.assertTrue(view.table_docs.isRowHidden(0))
                view.undo_banner.trigger_undo()
                m_del.assert_not_called()

            with patch("nemov.views.health_record_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.health_record_view.MemberService.delete_medical_document") as m_del:
                view.delete_document(88)
                view.undo_banner.commit_now()
                m_del.assert_called_once_with(88)
            view.close()

        # Test AddMedicalDocumentDialog.remove_file (previously lacked BOTH dialog and undo)
        dlg = AddMedicalDocumentDialog(member_id=1)
        dlg.selected_files = ["C:/docs/p1.jpg", "C:/docs/p2.jpg", "C:/docs/p3.jpg"]
        dlg.refresh_pages_table()

        with patch("nemov.views.health_record_view.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            dlg.remove_file("C:/docs/p2.jpg")
            self.assertEqual(len(dlg.selected_files), 3)

        with patch("nemov.views.health_record_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dlg.remove_file("C:/docs/p2.jpg")
            self.assertEqual(dlg.selected_files, ["C:/docs/p1.jpg", "C:/docs/p3.jpg"])
            self.assertEqual(dlg.undo_banner.remaining_seconds, 5)
            dlg.undo_banner.trigger_undo()
            self.assertEqual(dlg.selected_files, ["C:/docs/p1.jpg", "C:/docs/p2.jpg", "C:/docs/p3.jpg"])
        dlg.close()

    # ------------------------------------------------------------------
    # 5. WorkoutLibraryView & ExerciseFormDialog.remove_media
    # ------------------------------------------------------------------
    def test_05_exercise_form_dialog_remove_media_and_workout_library(self):
        from nemov.views.workout_library_view import ExerciseFormDialog, WorkoutLibraryView

        ex = SimpleNamespace(
            id=12, name_fa="پرس سینه", primary_muscle="chest", equipment="barbell",
            contraindications="", description="", is_corrective=False,
            media_path="images/bench.png", media_type="image", thumbnail_path="images/bench_thumb.png",
            video_url="", video_cloud_url="https://nemovapp.ir/media/bench.mp4"
        )
        with patch("nemov.views.workout_library_view.WorkoutService.get_all_exercises", return_value=[ex]):
            dlg = ExerciseFormDialog(exercise_data=ex)
            with patch("nemov.views.workout_library_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
                dlg.remove_media()
                self.assertIsNone(dlg.media_path)
                self.assertEqual(dlg.undo_banner.remaining_seconds, 5)
                dlg.undo_banner.trigger_undo()
                self.assertEqual(dlg.media_path, "images/bench.png")
                self.assertEqual(dlg.video_cloud_url, "https://nemovapp.ir/media/bench.mp4")
            dlg.close()

            wlib = WorkoutLibraryView()
            self.assertIn("۵ ثانیه", wlib.undo_banner.lbl_countdown.text())
            wlib.close()

    # ------------------------------------------------------------------
    # 6. WorkoutEditorView & NutritionEditorView: instant delete, unbounded Undo/Redo, & nav persistence
    # ------------------------------------------------------------------
    def test_06_editors_instant_delete_unbounded_undo_redo_and_nav_persistence(self):
        from PyQt6.QtWidgets import QStackedWidget
        from nemov.views.workout_editor_view import WorkoutEditorView
        from nemov.views.nutrition_editor_view import NutritionEditorView

        member_obj = SimpleNamespace(
            id=10, full_name="امیر حسینی", status="active",
            height_cm=180.0, initial_weight_kg=80.0, birth_date_shamsi="1375/01/01",
            gender="male", activity_level="moderately_active", membership_type="16_sessions"
        )
        ex_item = SimpleNamespace(id=1, name_fa="اسکات", primary_muscle="legs", description="تمرین پا")
        with patch("nemov.views.workout_editor_view.WorkoutService.get_all_exercises", return_value=[ex_item]), \
             patch("nemov.views.workout_editor_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.workout_editor_view.MemberService.get_all_members", return_value=[member_obj]), \
             patch("nemov.views.workout_editor_view.MemberService.get_member_by_id", return_value=member_obj):
            stack = QStackedWidget()
            w_view = WorkoutEditorView()
            other_page = QWidget()
            stack.addWidget(w_view)
            stack.addWidget(other_page)
            stack.show()

            # Must NOT have a 5-second expiring banner — uses full session Undo/Redo instead
            self.assertFalse(hasattr(w_view, "undo_banner"))

            w_view.txt_title.setText("برنامه نیمه‌کاره بدنسازی")
            w_view.set_selected_member(10)
            _, table = w_view.day_tables[0]
            w_view.add_exercise_row(table, [ex_item])
            w_view.add_exercise_row(table, [ex_item])
            table.cellWidget(0, 1).setText("5")
            table.cellWidget(1, 1).setText("8")
            self.assertEqual(table.rowCount(), 2)
            btn_rm = table.cellWidget(1, 7)

            # Deleting row happens INSTANTLY without QMessageBox and without saving to DB
            with patch("nemov.views.workout_editor_view.QMessageBox.question") as m_q, \
                 patch("nemov.views.workout_editor_view.WorkoutService.create_workout_plan") as m_cw, \
                 patch("nemov.views.workout_editor_view.WorkoutService.assign_plan_to_member") as m_aw:
                w_view.remove_exercise_row(table, btn_rm)
                m_q.assert_not_called()
                m_cw.assert_not_called()
                m_aw.assert_not_called()
                self.assertEqual(table.rowCount(), 1)

            # Navigate away to another page and return before undoing
            stack.setCurrentWidget(other_page)
            self._pump()
            w_view.refresh_editor()
            stack.setCurrentWidget(w_view)
            self._pump()

            # Plan fields persist across navigation, AND unbounded Undo still restores row with sets="8"
            self.assertEqual(w_view.txt_title.text(), "برنامه نیمه‌کاره بدنسازی")
            self.assertEqual(w_view.combo_member.currentData(), 10)
            w_view.undo()
            _, restored_table = w_view.day_tables[0]
            self.assertEqual(restored_table.rowCount(), 2)
            self.assertEqual(restored_table.cellWidget(0, 1).text(), "5")
            self.assertEqual(restored_table.cellWidget(1, 1).text(), "8")

            # Redo re-deletes instantly, Undo restores again
            w_view.redo()
            self.assertEqual(w_view.day_tables[0][1].rowCount(), 1)
            w_view.undo()
            self.assertEqual(w_view.day_tables[0][1].rowCount(), 2)
            stack.close()

        food_item = SimpleNamespace(
            id=2, name_fa="سینه مرغ", unit="۱۰۰ گرم", calories=165,
            protein=31, carbs=0, fat=3.6, protein_g=31, carbs_g=0, fat_g=3.6
        )
        with patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=[food_item]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=[member_obj]), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=member_obj):
            stack2 = QStackedWidget()
            n_view = NutritionEditorView()
            other_page2 = QWidget()
            stack2.addWidget(n_view)
            stack2.addWidget(other_page2)
            stack2.show()

            self.assertFalse(hasattr(n_view, "undo_banner"))

            n_view.txt_title.setText("رژیم در حال تنظیم")
            n_view.set_selected_member(10)
            n_view.txt_target_p.setText("210")
            n_view.txt_target_c.setText("310")
            n_view.txt_target_f.setText("75")
            _, n_table = n_view.meal_tables[0]
            n_view.add_food_row(n_table, [food_item])
            n_table.cellWidget(0, 1).setText("2.5")
            self.assertEqual(n_table.rowCount(), 1)
            n_btn_rm = n_table.cellWidget(0, 4)

            # Instant delete without confirmation dialog or DB save
            with patch("nemov.views.nutrition_editor_view.QMessageBox.question") as m_q, \
                 patch("nemov.views.nutrition_editor_view.NutritionService.create_nutrition_plan") as m_cn, \
                 patch("nemov.views.nutrition_editor_view.NutritionService.assign_nutrition_plan") as m_an:
                n_view.remove_food_row(n_table, n_btn_rm)
                m_q.assert_not_called()
                m_cn.assert_not_called()
                m_an.assert_not_called()
                self.assertEqual(n_table.rowCount(), 0)

            # Switch away and return -> custom macros, title, member persist, AND Undo restores the deleted row
            stack2.setCurrentWidget(other_page2)
            self._pump()
            n_view.refresh_editor()
            stack2.setCurrentWidget(n_view)
            self._pump()

            self.assertEqual(n_view.txt_title.text(), "رژیم در حال تنظیم")
            self.assertEqual(n_view.combo_member.currentData(), 10)
            self.assertEqual(n_view.txt_target_p.text(), "210")
            self.assertEqual(n_view.txt_target_c.text(), "310")
            self.assertEqual(n_view.txt_target_f.text(), "75")

            n_view.undo()
            _, restored_n_table = n_view.meal_tables[0]
            self.assertEqual(restored_n_table.rowCount(), 1)
            self.assertEqual(restored_n_table.cellWidget(0, 1).text(), "2.5")

            n_view.redo()
            self.assertEqual(n_view.meal_tables[0][1].rowCount(), 0)
            n_view.undo()
            self.assertEqual(n_view.meal_tables[0][1].rowCount(), 1)
            stack2.close()

    # ------------------------------------------------------------------
    # 7. BackupView: all 10 delete handlers (photo, logo, notifs, trainers, backups, account)
    # ------------------------------------------------------------------
    def test_07_backup_view_all_delete_handlers_confirm_and_5s_undo(self):
        from nemov.views.backup_view import BackupView

        fake_user = SimpleNamespace(
            id=9, username="coach_ali", role="trainer", display_name="مربی علی",
            first_name="علی", last_name="رضایی", phone="09120000000", email="",
            birth_date_shamsi="1370/01/01", recovery_code="1234", photo_path="photos/coach.png"
        )
        fake_notif = SimpleNamespace(id=301, title="سررسید شهریه", description="یادآور", date_shamsi="1405/01/01", is_read=False)
        fake_backup = SimpleNamespace(id=401, file_name="bk.zip", file_path="C:/bk/bk.zip", backup_date_shamsi="1405/01/01", backup_size_mb=1.2)
        fake_trainer = {"id": 77, "full_name": "مربی تست", "username": "t_test", "password": "123", "phone": "09121112233", "member_count": 3}

        with patch("nemov.views.backup_view.CurrentUser.get", return_value=fake_user), \
             patch("nemov.views.backup_view.BackupService.get_all_backups", return_value=[fake_backup]), \
             patch("nemov.views.backup_view.get_all_trainers", return_value=[fake_trainer]), \
             patch("nemov.services.notification_service.NotificationService.get_history", return_value=[fake_notif]), \
             patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "", "club_phone": "", "club_address": "", "club_logo_path": "logos/c.png", "selected_theme_id": "crimson_fury"}), \
             patch("nemov.services.branding_service.BrandingService.get_active_logo_path", return_value="logos/c.png"):
            bview = BackupView()

            # (a) remove_trainer_photo
            with patch("nemov.views.backup_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.update_trainer_profile") as m_upd:
                bview.selected_photo_path = "photos/coach.png"
                bview.remove_trainer_photo()
                self.assertEqual(bview.selected_photo_path, "")
                self.assertEqual(bview.undo_banner.remaining_seconds, 5)
                bview.undo_banner.trigger_undo()
                self.assertEqual(bview.selected_photo_path, "photos/coach.png")
                m_upd.assert_not_called()

            # (b) reset_to_default_logo_action
            with patch("nemov.views.backup_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.services.branding_service.BrandingService.reset_to_default_logo") as m_reset:
                bview.reset_to_default_logo_action()
                self.assertEqual(bview.undo_banner.remaining_seconds, 5)
                bview.undo_banner.trigger_undo()
                m_reset.assert_not_called()

            # (c) delete_single_notification (cancel -> skip; confirm -> undo vs commit)
            with patch("nemov.views.backup_view.QMessageBox.question", return_value=QMessageBox.StandardButton.No), \
                 patch("nemov.services.notification_service.NotificationService.delete_by_ids") as m_ndel:
                bview.delete_single_notification(301)
                m_ndel.assert_not_called()

            with patch("nemov.views.backup_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.services.notification_service.NotificationService.delete_by_ids") as m_ndel:
                bview.delete_single_notification(301)
                self.assertEqual(bview.undo_banner.remaining_seconds, 5)
                self.assertTrue(bview.table_notif_history.isRowHidden(0))
                bview.undo_banner.commit_now()
                m_ndel.assert_called_once_with([301])

            # (d) delete_selected_notifications & delete_all_notifications_history
            bview._notif_checkboxes[0].setChecked(True)
            with patch("nemov.views.backup_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.services.notification_service.NotificationService.delete_by_ids") as m_ndel:
                bview.delete_selected_notifications()
                bview.undo_banner.trigger_undo()
                m_ndel.assert_not_called()

            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.services.notification_service.NotificationService.delete_all_history") as m_nall:
                bview.delete_all_notifications_history()
                bview.undo_banner.commit_now()
                m_nall.assert_called_once()

            # (e) delete_backup_item, delete_selected_backups, delete_all_backups_history
            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.BackupService.delete_backup", return_value=True) as m_bdel:
                bview.delete_backup_item(401, "bk.zip")
                self.assertTrue(bview.table.isRowHidden(0))
                bview.undo_banner.trigger_undo()
                m_bdel.assert_not_called()

            bview._backup_checkboxes[0].setChecked(True)
            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.BackupService.delete_backup", return_value=True) as m_bdel:
                bview.delete_selected_backups()
                bview.undo_banner.commit_now()
                m_bdel.assert_called_once_with(401)

            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.BackupService.delete_backup", return_value=True) as m_bdel:
                bview.delete_all_backups_history()
                bview.undo_banner.commit_now()
                m_bdel.assert_called_once_with(401)

            # (f) admin_delete_trainer
            bview.load_trainers_for_admin()
            self.assertEqual(bview.table_trainers.rowCount(), 1)
            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.QMessageBox.critical", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.delete_trainer_account") as m_tdel:
                bview.admin_delete_trainer(77, "مربی تست", 3)
                self.assertEqual(bview.undo_banner.remaining_seconds, 5)
                self.assertTrue(bview.table_trainers.isRowHidden(0))
                bview.undo_banner.trigger_undo()
                m_tdel.assert_not_called()

            # (g) delete_current_trainer_account
            with patch("nemov.views.backup_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.QMessageBox.critical", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.backup_view.delete_trainer_account") as m_tdel, \
                 patch("nemov.views.backup_view.CurrentUser.logout"):
                bview.delete_current_trainer_account()
                self.assertFalse(bview.btn_del_account.isEnabled())
                bview.undo_banner.trigger_undo()
                self.assertTrue(bview.btn_del_account.isEnabled())
                m_tdel.assert_not_called()

                bview.delete_current_trainer_account()
                bview.undo_banner.commit_now()
                m_tdel.assert_called_once_with(9)

            bview.close()

    # ------------------------------------------------------------------
    # 8. LogViewerDialog.handle_clear_logs & Group A prompt/5s verification
    # ------------------------------------------------------------------
    def test_08_log_viewer_clear_logs_and_group_a_5s_prompts(self):
        from nemov.views.components.error_dialog import LogViewerDialog
        from nemov.views.member_list_view import MemberListView
        from nemov.views.food_library_view import FoodLibraryView
        from nemov.views.templates_manager_view import TemplatesManagerView

        with patch("nemov.views.components.error_dialog.get_parsed_log_entries", return_value=[]):
            lv = LogViewerDialog()
            with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("nemov.views.components.error_dialog.clear_logs") as m_cl:
                lv.handle_clear_logs()
                self.assertEqual(lv.undo_banner.remaining_seconds, 5)
                lv.undo_banner.trigger_undo()
                m_cl.assert_not_called()

                lv.handle_clear_logs()
                lv.undo_banner.commit_now()
                m_cl.assert_called_once()
            lv.close()

        # Verify Group A views use 5s default banner & 5s prompt wording
        with patch("nemov.views.member_list_view.MemberService.get_all_members", return_value=[]):
            mlv = MemberListView()
            member = SimpleNamespace(id=7, full_name="سارا محمدی")
            with patch("nemov.views.member_list_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes) as m_q, \
                 patch("nemov.views.member_list_view.MemberService.delete_member") as m_mdel:
                mlv.delete_member(member)
                self.assertIn("۵ ثانیه", m_q.call_args[0][2])
                self.assertEqual(mlv.undo_banner.remaining_seconds, 5)
                mlv.undo_banner.trigger_undo()
                m_mdel.assert_not_called()
            mlv.close()

        with patch("nemov.views.food_library_view.NutritionService.get_all_foods", return_value=[]):
            flv = FoodLibraryView()
            food = SimpleNamespace(id=8, name_fa="تخم مرغ")
            with patch("nemov.views.food_library_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes) as m_q, \
                 patch("nemov.views.food_library_view.NutritionService.delete_food") as m_fdel:
                flv.delete_food(food)
                self.assertIn("۵ ثانیه", m_q.call_args[0][2])
                self.assertEqual(flv.undo_banner.remaining_seconds, 5)
                flv.undo_banner.commit_now()
                m_fdel.assert_called_once_with(8)
            flv.close()

        with patch("nemov.views.templates_manager_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.templates_manager_view.NutritionService.get_all_plans", return_value=[]):
            tmv = TemplatesManagerView()
            with patch("nemov.views.templates_manager_view.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes) as m_w, \
                 patch("nemov.views.templates_manager_view.WorkoutService.delete_plan") as m_wdel:
                tmv.delete_workout_template(15, "برنامه سینه")
                self.assertIn("۵ ثانیه", m_w.call_args[0][2])
                self.assertEqual(tmv.undo_banner_w.remaining_seconds, 5)
                tmv.undo_banner_w.trigger_undo()
                m_wdel.assert_not_called()
            tmv.close()


if __name__ == "__main__":
    unittest.main()
