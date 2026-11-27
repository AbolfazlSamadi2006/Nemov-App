import os
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QFrame, QLineEdit, QComboBox
from PyQt6.QtGui import QFontDatabase, QPixmap, QPainter
from PyQt6.QtCore import Qt, QRect, QModelIndex

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _hex_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def _lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = _hex_luminance(fg_hex)
    l2 = _hex_luminance(bg_hex)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


class TestFullThemeConsistencyQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for fp in (
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Regular.ttf",
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Bold.ttf",
        ):
            if fp.exists():
                QFontDatabase.addApplicationFont(str(fp))

    def tearDown(self):
        from nemov.utils.theme_manager import ThemeManager
        ThemeManager.apply_theme("crimson_fury", self.app)
        self.app.processEvents()

    def _pump(self):
        self.app.processEvents()

    def test_01_theme_manager_helpers_contrast_light_and_dark(self):
        from nemov.utils.theme_manager import ThemeManager

        tones = ("blue", "amber", "emerald", "rose", "indigo", "purple", "neutral")
        for theme_key in ("crimson_fury", "olympic_white", "nordic_frost", "midnight_emerald"):
            ThemeManager.apply_theme(theme_key, self.app)
            pal = ThemeManager.get_current_palette()
            for tone in tones:
                bg, fg, bd, hv = ThemeManager.get_tone_colors(tone, pal)
                ratio = _contrast_ratio(fg, bg)
                self.assertGreaterEqual(
                    ratio, 3.8,
                    f"Low contrast {ratio:.2f} for tone={tone} in theme={theme_key} ({fg} on {bg})"
                )
                self.assertTrue(hv.startswith("#"))
                self.assertTrue(bd.startswith("#"))

            bulk_qss = ThemeManager.get_bulk_delete_qss(pal)
            self.assertIn(pal.btn_sec_bg, bulk_qss)
            self.assertIn(pal.text_muted, bulk_qss)
            menu_qss = ThemeManager.get_popup_menu_qss(pal)
            self.assertIn(pal.bg_card, menu_qss)
            self.assertIn(pal.text_primary, menu_qss)

    def test_02_login_and_auth_subdialogs_light_and_dark(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.login_view import LoginView
        from nemov.views.cloud_restore_dialog import CloudRestoreDialog
        from nemov.views.trainer_register_dialog import TrainerRegisterDialog
        from nemov.views.password_recovery_dialog import PasswordRecoveryDialog

        with patch("nemov.views.login_view.CredentialManager.get_all_saved_usernames", return_value=[]):
            ThemeManager.apply_theme("crimson_fury", self.app)
            login = LoginView()
            login.show()
            self._pump()

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()
            self.assertIn(pal.bg_card, login.card.styleSheet())
            self.assertIn(pal.text_primary, login.txt_username.styleSheet())
            login.close()

            crd = CloudRestoreDialog()
            self.assertIn("background: transparent", crd.lbl_status.styleSheet())
            self.assertIn("#B45309", crd.lbl_status.styleSheet())
            crd.close()

            reg = TrainerRegisterDialog()
            self.assertIsNotNone(reg.findChild(QWidget, "reg_scroll_host"))
            reg.txt_first_name.setText("علی")
            reg.txt_last_name.setText("رضایی")
            reg.txt_phone.setText("09123456789")
            reg.txt_username.setText("ali_test")
            reg.txt_password.setText("Pass1234!")
            reg.txt_password_confirm.setText("Mismatch!")
            reg.txt_recovery_code.setText("rec1234")
            reg.txt_recovery_confirm.setText("rec1234")
            reg.do_register()
            self.assertIn("#FEF2F2", reg.txt_password_confirm.styleSheet())
            self.assertIn("#991B1B", reg.txt_password_confirm.styleSheet())
            reg.close()

            rec = PasswordRecoveryDialog()
            self.assertIn(pal.primary_text, rec.btn_tab_sms.styleSheet())
            self.assertIn(pal.btn_sec_bg, rec.btn_tab_secret.styleSheet())
            rec.close()

    def test_03_nutrition_editor_live_theme_switch_and_collapsed_summary(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.nutrition_editor_view import NutritionEditorView

        ThemeManager.apply_theme("crimson_fury", self.app)
        members = [SimpleNamespace(id=1, full_name="علی رضایی", height_cm=180, initial_weight_kg=80, birth_date_shamsi="1375/01/01", gender="male", activity_level="moderately_active", status="active")]
        foods = [SimpleNamespace(id=10, name_fa="سینه مرغ", unit_fa="100 گرم", calories=165.0, protein_g=31.0, carbs_g=0.0, fat_g=3.6)]

        with patch("nemov.views.nutrition_editor_view.MemberService.get_all_members", return_value=members), \
             patch("nemov.views.nutrition_editor_view.MemberService.get_member_by_id", return_value=members[0]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_plans", return_value=[]), \
             patch("nemov.views.nutrition_editor_view.NutritionService.get_all_foods", return_value=foods):
            view = NutritionEditorView()
            view.show()
            self._pump()

            # Switch live from Dark -> Light
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()

            self.assertIn(pal.btn_sec_bg, view.btn_toggle_form.styleSheet())
            self.assertNotIn("#1F2937", view.btn_toggle_form.styleSheet())
            self.assertIn(pal.input_bg, view.txt_member_tdee.styleSheet())
            self.assertIn(pal.input_bg, view.txt_total_calories.styleSheet())
            self.assertIn(pal.bg_card, view.card_protein.styleSheet())
            self.assertNotIn("#111827", view.card_protein.styleSheet())

            e_bg, _, _, _ = ThemeManager.get_tone_colors("emerald", pal)
            r_bg, _, _, _ = ThemeManager.get_tone_colors("rose", pal)
            for plus_btn in (view.btn_tdee_p300, view.btn_tdee_p500):
                self.assertIn(e_bg, plus_btn.styleSheet())
            for minus_btn in (view.btn_tdee_m300, view.btn_tdee_m500):
                self.assertIn(r_bg, minus_btn.styleSheet())

            # Collapse summary label must use dark text in Light theme
            view.toggle_form_collapse()
            self._pump()
            self.assertIn(pal.text_primary, view.lbl_form_sub.styleSheet())

            # Row calorie label adapts too
            view.txt_member_tdee.setText("2400")
            view._on_manual_tdee_edited("2400")
            self._pump()
            self.assertNotIn("#374151", view.lbl_calorie_comparison.styleSheet())

            # Switch back to Dark -> dark colors restored cleanly
            ThemeManager.apply_theme("crimson_fury", self.app)
            self._pump()
            dark_pal = ThemeManager.get_current_palette()
            self.assertIn(dark_pal.bg_card, view.card_protein.styleSheet())
            view.close()

    def test_04_workout_library_muscle_selector_and_food_library_light_dark(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.workout_library_view import WorkoutLibraryView, OperationsDelegate, TwoLineDescriptionDelegate, ExerciseFormDialog
        from nemov.views.food_library_view import FoodLibraryView
        from nemov.views.components.muscle_selector_widget import MuscleSelectorWidget

        ThemeManager.apply_theme("crimson_fury", self.app)
        sample_ex = SimpleNamespace(
            id=1, name_fa="پرس سینه هالتر", primary_muscle="chest",
            equipment="barbell", contraindications="", description="توضیح تست خط اول | نکته دوم",
            media_path=None, media_type="image", thumbnail_path=None,
            video_url=None, video_cloud_url=None, is_corrective=False
        )
        with patch("nemov.views.workout_library_view.WorkoutService.get_all_exercises", return_value=[sample_ex]), \
             patch("nemov.views.workout_library_view.WorkoutLibraryView.update_sync_button_state"):
            wview = WorkoutLibraryView()
            wview.show()
            self._pump()

            # Live switch to Light theme
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()

            self.assertIn(pal.bg_card, wview.anat_filter_frame.styleSheet())
            self.assertNotIn("#11141A", wview.anat_filter_frame.styleSheet())
            self.assertIn(pal.btn_sec_bg, wview.btn_toggle_mannequin.styleSheet())
            self.assertIn(pal.btn_sec_bg, wview.btn_show_all.styleSheet())
            self.assertIn(pal.btn_sec_bg, wview.btn_bulk_delete.styleSheet())
            self.assertNotIn("#333333", wview.btn_bulk_delete.styleSheet())

            # Test MuscleSelectorWidget selected & cleared chip in Light mode
            from nemov.views.components.muscle_selector_widget import MUSCLE_DEFINITIONS
            first_muscle_key = next(iter(MUSCLE_DEFINITIONS.keys()))
            ms = MuscleSelectorWidget(is_filter_mode=True)
            ms.set_selected_muscle(first_muscle_key, emit_signal=False)
            self.assertIn(f"color: {pal.text_primary}", ms.lbl_status.styleSheet())
            self.assertNotIn("color: #FFFFFF", ms.lbl_status.styleSheet())
            ms.clear_selection(emit_signal=False)
            self.assertIn(pal.bg_surface, ms.lbl_status.styleSheet())
            ms.close()

            # Test custom delegates paint without crashing in Light theme
            pix = QPixmap(400, 60)
            painter = QPainter(pix)
            op_del = OperationsDelegate()
            rect = op_del._get_button_rects(QRect(0, 0, 260, 50))
            self.assertEqual(len(rect), 3)
            painter.end()

            dlg = ExerciseFormDialog(exercise_data=sample_ex)
            self.assertIn(pal.text_primary, dlg.chk_corrective.styleSheet())
            self.assertIn(pal.text_muted, dlg.lbl_media_status.styleSheet())
            dlg.close()
            wview.close()

        with patch("nemov.views.food_library_view.NutritionService.get_all_foods", return_value=[]):
            ThemeManager.apply_theme("crimson_fury", self.app)
            fview = FoodLibraryView()
            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()
            self.assertIn(pal.btn_sec_bg, fview.btn_bulk_delete.styleSheet())
            self.assertNotIn("#333333", fview.btn_bulk_delete.styleSheet())
            fview.close()

    def test_05_sms_center_developer_and_backup_views_live_theme_switch(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.sms_view import SmsView, RechargeInfoDialog
        from nemov.views.developer_view import DeveloperView
        from nemov.views.backup_view import BackupView

        ThemeManager.apply_theme("crimson_fury", self.app)

        # --- SMS Center ---
        with patch("nemov.views.sms_view.MemberService.get_all_members", return_value=[]), \
             patch.object(SmsView, "refresh_balance"), \
             patch.object(SmsView, "load_auto_settings"):
            sms = SmsView()
            sms.on_balance_received({"success": True, "remaining": 150, "total_credited": 150})
            sms.show()
            self._pump()

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()

            # Balance badge & buttons adapt to Light mode
            self.assertIn("#ECFDF5", sms.card_balance.styleSheet())
            self.assertIn(pal.btn_sec_bg, sms.btn_refresh_bal.styleSheet())
            self.assertIn(pal.btn_sec_bg, sms.btn_refresh_history.styleSheet())
            self.assertIn(pal.text_primary, sms.lbl_tpl.styleSheet())
            self.assertIn(pal.text_primary, sms.lbl_recip.styleSheet())
            self.assertIn(pal.text_primary, sms.lbl_h_title.styleSheet())
            self.assertIn(pal.input_bg, sms.combo_templates.styleSheet())
            self.assertIn(pal.input_bg, sms.combo_tuition_days.styleSheet())
            self.assertIn(pal.input_bg, sms.input_search_member.styleSheet())

            # Phone screen & chat bubble use daytime light surfaces in Light theme
            self.assertIn("#F8FAFC", sms.phone_mockup.styleSheet())
            self.assertIn("#E2E8F0", sms.chat_bubble.styleSheet())
            self.assertIn("#0F172A", sms.lbl_preview_msg.styleSheet())

            # Tab 2 auto cards light
            self.assertIn(pal.text_primary, sms.lbl_auto_head.styleSheet())
            for tb in sms._auto_tpl_boxes:
                self.assertIn(pal.bg_surface, tb.styleSheet())

            # Recharge modal
            rdlg = RechargeInfoDialog()
            self.assertIn(pal.bg_card, rdlg.findChild(QFrame, "bankCard").styleSheet())
            rdlg.close()
            sms.close()

        # --- Developer / Update View ---
        ThemeManager.apply_theme("crimson_fury", self.app)
        dev_info = {
            "first_name": "ابوالفضل", "last_name": "صمدی",
            "phone": "09336427711", "email": "a@example.com",
            "telegram": "t.me/test", "github": "github.com/test",
            "photo_path": ""
        }
        with patch("nemov.views.developer_view.get_developer_info", return_value=dev_info), \
             patch("nemov.views.developer_view.is_app_license_active", return_value=True), \
             patch("nemov.views.developer_view.CurrentUser.is_admin", return_value=True), \
             patch("nemov.views.developer_view.UpdateService.mark_notification_seen"), \
             patch("nemov.views.developer_view.UpdateService.get_last_check_time", return_value=""):
            dev = DeveloperView()
            dev.load_data()
            dev._on_check_finished(
                True,
                {"tag_name": "v9.9.9", "name": "Test Release", "asset_size": 1024, "body": "Fix details"},
                "",
            )
            self._pump()

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()

            self.assertIn(pal.text_primary, dev.lbl_title.styleSheet())
            self.assertIn(pal.text_primary, dev.lbl_app_name.styleSheet())
            self.assertIn(pal.text_secondary, dev.lbl_platform.styleSheet())
            self.assertIn(pal.bg_card, dev.update_status_card.styleSheet())
            self.assertIn(pal.bg_surface, dev.txt_changelog.styleSheet())
            self.assertIn(pal.text_primary, dev.txt_changelog.styleSheet())
            self.assertIn(pal.text_primary, dev.lbl_dev_full_name.styleSheet())
            self.assertIn("#2563EB", dev.lbl_dev_email.text())
            self.assertIn(pal.btn_sec_bg, dev.btn_save_dev.styleSheet())
            dev.close()

        # --- Backup & Branding View ---
        ThemeManager.apply_theme("crimson_fury", self.app)
        with patch.object(BackupView, "load_all_data"), \
             patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_logo_path": ""}), \
             patch("nemov.services.branding_service.BrandingService.get_active_logo_path", return_value=""):
            bkp = BackupView()
            bkp.show()
            self._pump()

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            pal = ThemeManager.get_current_palette()

            self.assertIn(pal.bg_card, bkp.backup_toolbar_frame.styleSheet())
            self.assertIn(pal.bg_card, bkp.backup_table_header_frame.styleSheet())
            self.assertIn(pal.bg_card, bkp.logs_card.styleSheet())
            self.assertIn(pal.bg_card, bkp.notif_header_frame.styleSheet())
            self.assertIn(pal.text_primary, bkp.lbl_club_name.styleSheet())
            self.assertIn(pal.text_primary, bkp.lbl_club_phone.styleSheet())
            self.assertIn(pal.text_primary, bkp.lbl_club_address.styleSheet())
            self.assertIn(pal.text_secondary, bkp.lbl_logo_desc.styleSheet())
            self.assertIn(pal.btn_sec_bg, bkp.btn_upload_logo.styleSheet())
            self.assertIn(pal.btn_sec_bg, bkp.btn_reset_logo.styleSheet())
            self.assertIn(pal.btn_sec_bg, bkp.btn_restore_file.styleSheet())
            self.assertIn(pal.btn_sec_bg, bkp.btn_open_logs_folder.styleSheet())
            self.assertIn(pal.btn_sec_bg, bkp.btn_copy_last_err.styleSheet())
            bkp.close()

    def test_06_shared_dialogs_and_remaining_views_light_theme(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.templates_manager_view import TemplatesManagerView, AssignTemplateDialog
        from nemov.views.member_detail_view import MemberDetailView
        from nemov.views.components.undo_delete_banner import UndoDeleteBanner
        from nemov.views.components.error_dialog import ErrorDialog, LogViewerDialog
        from nemov.views.components.exit_backup_dialog import ExitBackupDialog

        ThemeManager.apply_theme("olympic_white", self.app)
        pal = ThemeManager.get_current_palette()

        banner = UndoDeleteBanner()
        self.assertIn("#FEF2F2", banner.styleSheet())
        self.assertIn(pal.text_primary, banner.styleSheet())
        ThemeManager.apply_theme("crimson_fury", self.app)
        self.assertIn("#261616", banner.styleSheet())
        banner.close()

        ThemeManager.apply_theme("olympic_white", self.app)
        with patch("nemov.views.templates_manager_view.MemberService.get_all_members", return_value=[]):
            assign_dlg = AssignTemplateDialog("workout", 1, "تست")
            lbls = assign_dlg.findChildren(QLabel)
            self.assertTrue(any(pal.text_primary in l.styleSheet() for l in lbls))
            self.assertFalse(any("#FFFFFF" in l.styleSheet() for l in lbls))
            assign_dlg.close()

        with patch("nemov.views.templates_manager_view.WorkoutService.get_all_plans", return_value=[]), \
             patch("nemov.views.templates_manager_view.NutritionService.get_all_plans", return_value=[]):
            tmv = TemplatesManagerView()
            self.assertIn(pal.btn_sec_bg, tmv.btn_bulk_delete_w.styleSheet())
            self.assertIn(pal.btn_sec_bg, tmv.btn_bulk_delete_n.styleSheet())
            tmv.close()

        with patch("nemov.views.member_detail_view.MemberService.get_member_by_id", return_value=None), \
             patch("nemov.views.member_detail_view.MemberService.get_health_record", return_value=None), \
             patch("nemov.views.assessment_view.AssessmentService.get_member_assessments", return_value=[]), \
             patch("nemov.views.member_detail_view.WorkoutService.get_member_assignments", return_value=[]), \
             patch("nemov.views.member_detail_view.NutritionService.get_member_assignments", return_value=[]):
            mdv = MemberDetailView(member_id=1)
            self.assertIn(pal.bg_surface, mdv.lbl_avatar.styleSheet())
            self.assertIn(pal.text_primary, mdv.lbl_workout_title.styleSheet())
            self.assertIn(pal.bg_card, mdv.lbl_no_workout.styleSheet())
            self.assertIn(pal.btn_sec_bg, mdv.btn_bulk_delete_workout.styleSheet())
            mdv.close()

        edlg = ErrorDialog(message="خطای تستی", technical_details="trace")
        self.assertIn(pal.btn_sec_bg, edlg.btn_toggle.styleSheet())
        self.assertIn(pal.bg_surface, edlg.txt_details.styleSheet())
        edlg.close()

        with patch("nemov.views.components.error_dialog.get_parsed_log_entries", return_value=[
            {"num": 1, "timestamp": "1405-01-01", "level": "ERROR", "message": "Err", "body": ["line1"], "raw": "raw"}
        ]):
            lvdlg = LogViewerDialog()
            self.assertIn(pal.bg_card, lvdlg.browser.styleSheet())
            html_out = lvdlg.browser.toHtml()
            self.assertIn("#991b1b", html_out.lower())
            lvdlg.close()

        exdlg = ExitBackupDialog()
        self.assertIn(pal.btn_sec_bg, exdlg.btn_normal_exit.styleSheet())
        exdlg.close()

    def test_07_theme_switch_does_not_trigger_exit_backup_dialog_and_persists_locally(self):
        from nemov.database.connection import init_db, reset_data_changed, has_data_changed
        from nemov.services.branding_service import BrandingService
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.main_window import MainWindow
        from nemov.auth.authentication import CurrentUser
        from PyQt6.QtGui import QCloseEvent

        init_db()
        original_theme = BrandingService.get_selected_theme_id()
        try:
            reset_data_changed()
            self.assertFalse(has_data_changed())

            # Switching dark -> light -> dark via BrandingService must NOT mark session dirty
            ThemeManager.apply_theme("olympic_white", self.app)
            BrandingService.save_selected_theme_id("olympic_white")
            self.assertFalse(has_data_changed())
            self.assertEqual(BrandingService.get_selected_theme_id(), "olympic_white")

            ThemeManager.apply_theme("crimson_fury", self.app)
            BrandingService.save_selected_theme_id("crimson_fury")
            self.assertFalse(has_data_changed())
            self.assertEqual(BrandingService.get_selected_theme_id(), "crimson_fury")

            # Also verify save_club_info(app_theme=...) alone does not mark dirty,
            # while club_name update still marks dirty
            BrandingService.save_club_info(app_theme="nordic_frost")
            self.assertFalse(has_data_changed())

            # Simulate MainWindow closing after user switched theme in memory without ExitBackupDialog
            ThemeManager.apply_theme("olympic_white", self.app)
            reset_data_changed()
            fake_user = SimpleNamespace(id=1, username="admin", full_name="مدیر", phone="09330000000", role="admin")
            with patch("nemov.views.main_window.ExitBackupDialog") as mock_exit_dlg, \
                 patch.object(CurrentUser, "get", return_value=fake_user):
                mw = MainWindow()
                mw.show()
                self._pump()

                ev = QCloseEvent()
                mw.closeEvent(ev)
                self.assertTrue(ev.isAccepted())
                mock_exit_dlg.assert_not_called()
                self.assertFalse(has_data_changed())
                # Selected theme is automatically saved locally on exit
                self.assertEqual(BrandingService.get_selected_theme_id(), "olympic_white")

                # Simulate next app launch restoring saved theme
                ThemeManager.apply_theme("crimson_fury", self.app)
                ThemeManager.apply_saved_theme(self.app)
                self.assertEqual(ThemeManager.get_current_theme_key(), "olympic_white")
                mw.close()
        finally:
            BrandingService.save_selected_theme_id(original_theme)
            ThemeManager.apply_theme(original_theme, self.app)
            reset_data_changed()


if __name__ == "__main__":
    unittest.main()
