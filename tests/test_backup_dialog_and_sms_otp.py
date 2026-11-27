"""
Unit tests for:
1. Removing email-backup option from backup dialogs & BackupView.
2. Switching password recovery & OTP flows from EmailService to SmsService (SMS.ir template 585804).
3. PyQt6 visual geometry / RTL / clipping checks on modified dialogs.
"""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QMessageBox

_APP = QApplication.instance() or QApplication(sys.argv)

from nemov.services.sms_service import SmsService, DEFAULT_SMS_TEMPLATES
from nemov.views.components.backup_destination_dialog import BackupDestinationDialog
from nemov.views.components.exit_backup_dialog import ExitBackupDialog
from nemov.views.password_recovery_dialog import PasswordRecoveryDialog, SendOtpThread


class TestBackupDialogsEmailRemoval(unittest.TestCase):
    """Verifies backup dialogs no longer expose email backup or spam guide options."""

    def test_backup_destination_dialog_has_no_email_option(self):
        dlg = BackupDestinationDialog()
        self.assertFalse(hasattr(BackupDestinationDialog, "CHOICE_EMAIL"))
        self.assertFalse(hasattr(dlg, "_open_spam_guide"))

        buttons = dlg.findChildren(QPushButton)
        # Option buttons use inner QLabels for title + description
        all_texts = [btn.text() for btn in buttons] + [lbl.text() for lbl in dlg.findChildren(QLabel)]
        joined = " | ".join(all_texts)
        self.assertNotIn("ایمیل", joined)
        self.assertNotIn("هرزنامه", joined)
        self.assertNotIn("Spam", joined)

        # Remaining 3 backup choices + cancel button
        self.assertEqual(len(buttons), 4)
        self.assertIn("💻 ذخیره در سیستم", " ".join(lbl.text() for lbl in buttons[0].findChildren(QLabel)))
        self.assertIn("☁️ ذخیره در سرور (آنلاین)", " ".join(lbl.text() for lbl in buttons[1].findChildren(QLabel)))
        self.assertIn("📁 ذخیره در مسیر نصب برنامه", " ".join(lbl.text() for lbl in buttons[2].findChildren(QLabel)))
        self.assertEqual(buttons[3].text(), "انصراف و بستن")

    def test_backup_destination_dialog_choices_work(self):
        expected = [
            (0, BackupDestinationDialog.CHOICE_SYSTEM),
            (1, BackupDestinationDialog.CHOICE_SERVER),
            (2, BackupDestinationDialog.CHOICE_INSTALL_DIR),
        ]
        for idx, choice_const in expected:
            dlg = BackupDestinationDialog()
            buttons = dlg.findChildren(QPushButton)
            buttons[idx].click()
            self.assertEqual(dlg.selected_choice, choice_const)

    def test_exit_backup_dialog_has_no_email_option(self):
        dlg = ExitBackupDialog(is_logout=False)
        dlg_logout = ExitBackupDialog(is_logout=True)
        for d in (dlg, dlg_logout):
            texts = " | ".join(btn.text() for btn in d.findChildren(QPushButton))
            self.assertNotIn("ایمیل", texts)
            self.assertNotIn("هرزنامه", texts)
            self.assertEqual(len(d.findChildren(QPushButton)), 4)

    def test_backup_view_has_no_email_backup_handlers(self):
        from nemov.views import backup_view
        self.assertFalse(hasattr(backup_view, "EmailBackupThread"))
        self.assertFalse(hasattr(backup_view.BackupView, "_start_email_backup_async"))
        self.assertFalse(hasattr(backup_view.BackupView, "_on_email_backup_finished"))
        self.assertFalse(hasattr(backup_view.BackupView, "open_spam_guide_dialog"))


class TestSmsOtpServiceAndAuth(unittest.TestCase):
    """Verifies shared SMS OTP sending (template 585804), verification, and auth behavior."""

    def setUp(self):
        SmsService._otp_cache.clear()

    def test_send_otp_sms_uses_login_template_and_normalizes_phone(self):
        with patch("nemov.auth.authentication.get_developer_info", return_value={"phone": "09336427711"}), \
             patch.object(SmsService, "send_single_sms", return_value=(True, "ok", 91)) as mock_send:
            ok, msg = SmsService.send_otp_sms(
                recipient_phone="+98۹۱۲۳۴۵۶۷۸۹",
                recipient_name="علی رضایی",
                otp_code="54321",
            )

        self.assertTrue(ok)
        self.assertIn("09123456789", msg)
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["recipient_phone"], "09123456789")
        self.assertEqual(kwargs["template_id"], DEFAULT_SMS_TEMPLATES["otp"]["template_id"])
        self.assertEqual(kwargs["template_id"], 585804)
        self.assertEqual(kwargs["message_type"], "otp")
        self.assertEqual(kwargs["member_name"], "علی رضایی")
        self.assertEqual(kwargs["trainer_phone"], "09336427711")
        self.assertEqual(
            kwargs["parameters"],
            [
                {"name": "OTP", "value": "54321"},
                {"name": "CODE", "value": "54321"},
                {"name": "Code", "value": "54321"},
                {"name": "Otp", "value": "54321"},
            ],
        )

    def test_send_otp_sms_fallbacks_to_trainer_phone_when_master_credit_depleted(self):
        with patch("nemov.auth.authentication.get_developer_info", return_value={"phone": "09336427711"}), \
             patch.object(
                 SmsService,
                 "send_single_sms",
                 side_effect=[
                     (False, "اعتبار بسته پیامک شما به پایان رسیده است.", 0),
                     (True, "ok", 10),
                 ],
             ) as mock_send:
            ok, _ = SmsService.send_otp_sms("09121112233", "مربی تست", otp_code="11223")

        self.assertTrue(ok)
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(mock_send.call_args_list[0].kwargs["trainer_phone"], "09336427711")
        self.assertEqual(mock_send.call_args_list[1].kwargs["trainer_phone"], "09121112233")

    def test_send_otp_sms_rejects_invalid_phone_without_gateway_call(self):
        with patch.object(SmsService, "send_single_sms") as mock_send:
            ok, msg = SmsService.send_otp_sms("12345", "تست")
        self.assertFalse(ok)
        self.assertIn("معتبر", msg)
        mock_send.assert_not_called()

    def test_developer_otp_delegates_to_shared_sms_otp_sender(self):
        with patch.object(SmsService, "send_single_sms", return_value=(True, "ok", 90)) as mock_send:
            ok, msg = SmsService.send_developer_activation_otp_sms(to_phone="09336427711", otp_code="98765")
        self.assertTrue(ok)
        self.assertIn("09336427711", msg)
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["template_id"], 585804)
        self.assertEqual(kwargs["recipient_phone"], "09336427711")
        self.assertEqual(kwargs["trainer_phone"], "09336427711")

    def test_otp_cache_verifies_persian_and_english_digits_and_expires(self):
        code = SmsService.generate_and_store_otp("09123456789")
        persian_code = code.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

        ok_wrong, _ = SmsService.verify_otp("09123456789", "00000")
        self.assertFalse(ok_wrong)

        ok_right, _ = SmsService.verify_otp("09123456789", persian_code)
        self.assertTrue(ok_right)

        # Consumed after verification
        ok_reuse, _ = SmsService.verify_otp("09123456789", code)
        self.assertFalse(ok_reuse)

    def test_otp_brute_force_lockout_and_varied_phone_formats(self):
        # Varied valid phone formats normalize identically
        for raw in ("09123456789", "۰۹۱۲۳۴۵۶۷۸۹", "+989123456789", "00989123456789", "9123456789", "0912-345 6789"):
            self.assertEqual(SmsService.normalize_phone_number(raw), "09123456789")

        # Invalid phones fail cleanly
        for bad in ("", "abc", "09123", "08123456789"):
            ok, _ = SmsService.send_otp_sms(bad, "تست")
            self.assertFalse(ok)

        # >5 failed attempts lock out OTP
        code = SmsService.generate_and_store_otp("09123456789")
        for _ in range(6):
            ok, _ = SmsService.verify_otp("09123456789", "99999")
            self.assertFalse(ok)
        ok_after_lock, _ = SmsService.verify_otp("09123456789", code)
        self.assertFalse(ok_after_lock)

    def test_authenticate_user_uses_sms_otp_not_email_otp(self):
        from nemov.auth.authentication import authenticate_user
        from nemov.services.email_service import EmailService

        EmailService.generate_and_store_otp("a.samadi2006@gmail.com")
        email_otp = EmailService._otp_cache["a.samadi2006@gmail.com"]["code"]

        with patch("nemov.auth.authentication.get_developer_info", return_value={"phone": "09336427711", "email": "a.samadi2006@gmail.com"}), \
             patch("nemov.auth.authentication.is_app_license_active", return_value=True):
            # Email OTP must NOT authenticate anymore
            user_via_email = authenticate_user("admin", email_otp)
            self.assertIsNone(user_via_email)


class TestPasswordRecoveryDialogSmsFlow(unittest.TestCase):
    """Verifies PasswordRecoveryDialog uses SMS OTP end-to-end with no email OTP leftovers."""

    def setUp(self):
        SmsService._otp_cache.clear()
        self.fake_user = SimpleNamespace(
            id=42,
            username="ali_coach",
            first_name="علی",
            last_name="رضایی",
            display_name="علی رضایی",
            phone="09123456789",
            email="ali@example.com",
            birth_date_shamsi="1370/01/01",
            photo_path="",
            recovery_code="1234",
        )

    def test_dialog_ui_replaced_email_with_sms(self):
        with patch.object(PasswordRecoveryDialog, "_get_registered_identities", return_value=["09123456789"]):
            dlg = PasswordRecoveryDialog()

        self.assertFalse(hasattr(dlg, "btn_tab_email"))
        self.assertFalse(hasattr(dlg, "btn_otp_spam_help"))
        self.assertFalse(hasattr(dlg, "_open_spam_guide"))
        self.assertIn("موبایل", dlg.btn_tab_sms.text())
        self.assertIn("پیامک", dlg.btn_send_otp.text())

        all_btn_text = " | ".join(b.text() for b in dlg.findChildren(QPushButton))
        self.assertNotIn("ایمیل", all_btn_text)
        self.assertNotIn("هرزنامه", all_btn_text)
        self.assertNotIn("Spam", all_btn_text)

    def test_send_and_verify_sms_otp_and_reset_password_flow(self):
        class SyncThread:
            def __init__(self, phone, trainer_name, otp_code):
                self.phone = phone
                self.trainer_name = trainer_name
                self.otp_code = otp_code
                self.callbacks = []
                self.finished_signal = MagicMock()
                self.finished_signal.connect = lambda cb: self.callbacks.append(cb)

            def start(self):
                ok, msg = SmsService.send_otp_sms(
                    recipient_phone=self.phone,
                    recipient_name=self.trainer_name,
                    otp_code=self.otp_code,
                )
                for cb in self.callbacks:
                    cb(ok, msg)

        with patch.object(PasswordRecoveryDialog, "_get_registered_identities", return_value=["09123456789"]):
            dlg = PasswordRecoveryDialog()
            dlg.show()

        dlg.txt_sms_identity.setText("ali_coach")

        with patch("nemov.views.password_recovery_dialog.find_user_by_email_or_phone", return_value=self.fake_user), \
             patch("nemov.views.password_recovery_dialog.SendOtpThread", SyncThread), \
             patch.object(SmsService, "send_single_sms", return_value=(True, "sent", 50)) as mock_send:
            dlg.do_send_sms_otp()

        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.kwargs["recipient_phone"], "09123456789")
        self.assertEqual(mock_send.call_args.kwargs["template_id"], 585804)
        self.assertTrue(dlg.otp_verify_box.isVisible())
        self.assertIn("0912***6789", dlg.lbl_otp_sent_info.text())

        # Verify stored OTP unlocks Step 2
        stored_otp = SmsService._otp_cache["09123456789"]["code"]
        dlg.txt_entered_otp.setText(stored_otp)
        dlg.do_verify_sms_otp()

        self.assertTrue(dlg.step2_frame.isVisible())
        self.assertEqual(dlg.matched_user, self.fake_user)

        # Reset password
        dlg.txt_new_password.setText("NewPass123!")
        emitted = []
        dlg.recovery_success.connect(lambda: emitted.append(True))

        with patch("nemov.views.password_recovery_dialog.update_trainer_profile", return_value=True) as mock_update, \
             patch("nemov.views.password_recovery_dialog.CurrentUser.set") as mock_set_user, \
             patch.object(QMessageBox, "information"):
            dlg.do_reset_and_login()

        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args.kwargs["password"], "NewPass123!")
        self.assertEqual(mock_update.call_args.kwargs["user_id"], 42)
        mock_set_user.assert_called_once_with(self.fake_user)
        self.assertEqual(emitted, [True])
        dlg.close()

    def test_send_sms_otp_warns_when_user_has_no_valid_phone(self):
        no_phone_user = SimpleNamespace(
            id=99,
            username="no_phone",
            display_name="بدون شماره",
            phone="",
            email="x@y.com",
        )
        with patch.object(PasswordRecoveryDialog, "_get_registered_identities", return_value=[]):
            dlg = PasswordRecoveryDialog()
        dlg.txt_sms_identity.setText("no_phone")

        with patch("nemov.views.password_recovery_dialog.find_user_by_email_or_phone", return_value=no_phone_user), \
             patch.object(QMessageBox, "warning") as mock_warn, \
             patch.object(SmsService, "send_single_sms") as mock_send:
            dlg.do_send_sms_otp()

        mock_warn.assert_called_once()
        mock_send.assert_not_called()

    def test_send_otp_thread_calls_sms_service(self):
        t = SendOtpThread("09123456789", "مربی", "12345")
        results = []
        t.finished_signal.connect(lambda ok, msg: results.append((ok, msg)))
        with patch.object(SmsService, "send_otp_sms", return_value=(True, "sent_ok")) as mock_otp:
            t.run()
        mock_otp.assert_called_once_with(recipient_phone="09123456789", recipient_name="مربی", otp_code="12345")
        self.assertEqual(results, [(True, "sent_ok")])


class TestModifiedDialogsVisualGeometryQA(unittest.TestCase):
    """Performs layout geometry, RTL direction, and non-clipping QA checks on modified dialogs."""

    def _assert_buttons_fit_inside(self, widget):
        widget.ensurePolished()
        widget.adjustSize()
        _APP.processEvents()
        w_rect = widget.rect()
        for btn in widget.findChildren(QPushButton):
            if not btn.isVisibleTo(widget):
                continue
            top_left = btn.mapTo(widget, btn.rect().topLeft())
            bot_right = btn.mapTo(widget, btn.rect().bottomRight())
            self.assertGreaterEqual(top_left.x(), 0, f"Button clipped left: {btn.text()}")
            self.assertGreaterEqual(top_left.y(), 0, f"Button clipped top: {btn.text()}")
            self.assertLessEqual(bot_right.x(), w_rect.width() + 1, f"Button clipped right: {btn.text()}")
            self.assertLessEqual(bot_right.y(), w_rect.height() + 1, f"Button clipped bottom: {btn.text()}")

    def test_backup_destination_dialog_geometry_and_rtl(self):
        dlg = BackupDestinationDialog()
        dlg.show()
        self.assertEqual(dlg.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self._assert_buttons_fit_inside(dlg)
        dlg.close()

    def test_password_recovery_dialog_all_states_geometry_and_rtl(self):
        with patch.object(PasswordRecoveryDialog, "_get_registered_identities", return_value=["09123456789"]):
            dlg = PasswordRecoveryDialog()
        dlg.show()
        self.assertEqual(dlg.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self._assert_buttons_fit_inside(dlg)

        # Reveal OTP box
        dlg.pending_phone = "09123456789"
        dlg._on_otp_sent(True, "ok")
        dlg.resend_timer.stop()
        self._assert_buttons_fit_inside(dlg)

        # Reveal Step 2
        dlg._activate_step2(SimpleNamespace(display_name="مربی", username="coach"))
        self._assert_buttons_fit_inside(dlg)
        dlg.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
