from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QScrollArea, QStackedWidget, QSizePolicy, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QStringListModel
from nemov.auth.authentication import (
    verify_recovery_credentials, update_trainer_profile, CurrentUser, find_user_by_email_or_phone
)
from nemov.services.email_service import EmailService
from nemov.utils.theme_manager import ThemeManager


class AutoResizingStackedWidget(QStackedWidget):
    def sizeHint(self):
        current = self.currentWidget()
        if current:
            return current.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        if current:
            return current.minimumSizeHint()
        return super().minimumSizeHint()


class SendOtpThread(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, email: str, trainer_name: str, otp_code: str):
        super().__init__()
        self.email = email
        self.trainer_name = trainer_name
        self.otp_code = otp_code

    def run(self):
        success, msg = EmailService.send_otp_email(self.email, self.trainer_name, self.otp_code)
        self.finished_signal.emit(success, msg)


class PasswordRecoveryDialog(QDialog):
    recovery_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بازیابی نام کاربری و کلمه عبور مربی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(540, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.matched_user = None
        self.resend_timer = QTimer(self)
        self.resend_timer.setInterval(1000)
        self.resend_timer.timeout.connect(self._update_resend_countdown)
        self.countdown_seconds = 0
        self.otp_thread = None

        self.init_ui()

    def init_ui(self):
        palette = ThemeManager.get_current_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header Title
        title_lbl = QLabel("🔑 بازیابی حساب کاربری مربی")
        title_lbl.setObjectName("h1")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        # Tab Switching Buttons (Dual Mode)
        tab_box = QHBoxLayout()
        tab_box.setSpacing(8)

        self.btn_tab_email = QPushButton("📧 ارسال کد به ایمیل (آنلاین)")
        self.btn_tab_email.setFixedHeight(38)
        self.btn_tab_email.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_secret = QPushButton("🔑 رمز ریکاوری مخفی (آفلاین)")
        self.btn_tab_secret.setFixedHeight(38)
        self.btn_tab_secret.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_email.clicked.connect(lambda: self.switch_mode(0))
        self.btn_tab_secret.clicked.connect(lambda: self.switch_mode(1))

        tab_box.addWidget(self.btn_tab_email)
        tab_box.addWidget(self.btn_tab_secret)
        card_layout.addLayout(tab_box)

        # Stacked Container for the 2 Modes
        self.stack = AutoResizingStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        # ========================================================
        # PAGE 0: Email OTP Mode (Online)
        # ========================================================
        page_email = QFrame()
        page_email_layout = QVBoxLayout(page_email)
        page_email_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_email_layout.setContentsMargins(0, 4, 0, 0)
        page_email_layout.setSpacing(6)

        desc_email = QLabel("با وارد کردن ایمیل، شماره تماس یا نام کاربری، کد تایید ۵ رقمی به ایمیل شما فرستاده می‌شود:")
        desc_email.setObjectName("muted_text")
        desc_email.setWordWrap(True)
        page_email_layout.addWidget(desc_email)

        page_email_layout.addWidget(QLabel("ایمیل، شماره همراه یا نام کاربری مربی:"))
        self.txt_email_identity = QLineEdit()
        self.txt_email_identity.setFixedHeight(38)
        self.txt_email_identity.setPlaceholderText("مثال: coach@example.com یا 09123456789")
        page_email_layout.addWidget(self.txt_email_identity)
        self._setup_email_completer()

        # Send Code Button
        self.btn_send_otp = QPushButton("📩 دریافت کد تایید در ایمیل")
        self.btn_send_otp.setFixedHeight(40)
        self.btn_send_otp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_otp.setObjectName("primary_button")
        self.btn_send_otp.clicked.connect(self.do_send_email_otp)
        page_email_layout.addWidget(self.btn_send_otp)

        # OTP Verification Container (Hidden initially)
        self.otp_verify_box = QFrame()
        self.otp_verify_box.setObjectName("otp_verify_box")
        self.otp_verify_box.setStyleSheet(f"QFrame#otp_verify_box {{ background-color: {palette.bg_surface}; border: 1px dashed {palette.primary}; border-radius: 8px; padding: 8px; }}")
        otp_box_layout = QVBoxLayout(self.otp_verify_box)
        otp_box_layout.setSpacing(6)

        self.lbl_otp_sent_info = QLabel()
        self.lbl_otp_sent_info.setStyleSheet(f"color: {palette.primary}; font-size: 12px; font-weight: bold;")
        self.lbl_otp_sent_info.setWordWrap(True)
        otp_box_layout.addWidget(self.lbl_otp_sent_info)

        otp_box_layout.addWidget(QLabel("کد تایید ۵ رقمی دریافتی:"))
        self.txt_entered_otp = QLineEdit()
        self.txt_entered_otp.setFixedHeight(42)
        self.txt_entered_otp.setMaxLength(5)
        self.txt_entered_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_entered_otp.setPlaceholderText("— — — — —")
        self.txt_entered_otp.setStyleSheet(f"""
            QLineEdit {{
                font-size: 20px; font-weight: bold; letter-spacing: 8px; color: {palette.primary}; background-color: {palette.bg_input}; border: 1px solid {palette.border}; border-radius: 6px; padding: 4px;
            }}
        """)
        otp_box_layout.addWidget(self.txt_entered_otp)

        self.btn_confirm_otp = QPushButton("✅ تایید کد و ادامه")
        self.btn_confirm_otp.setFixedHeight(38)
        self.btn_confirm_otp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm_otp.setObjectName("primary_button")
        self.btn_confirm_otp.clicked.connect(self.do_verify_email_otp)
        otp_box_layout.addWidget(self.btn_confirm_otp)

        self.btn_otp_spam_help = QPushButton("❓ کد تایید نیامد؟ راهنمای پوشه Spam (هرزنامه)")
        self.btn_otp_spam_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_otp_spam_help.setObjectName("secondary_button")
        self.btn_otp_spam_help.clicked.connect(self._open_spam_guide)
        otp_box_layout.addWidget(self.btn_otp_spam_help, alignment=Qt.AlignmentFlag.AlignCenter)

        page_email_layout.addWidget(self.otp_verify_box)
        self.otp_verify_box.setVisible(False)

        self.stack.addWidget(page_email)

        # ========================================================
        # PAGE 1: Secret Recovery Code Mode (Offline)
        # ========================================================
        page_secret = QFrame()
        page_secret_layout = QVBoxLayout(page_secret)
        page_secret_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_secret_layout.setContentsMargins(0, 4, 0, 0)
        page_secret_layout.setSpacing(6)

        desc_secret = QLabel("شماره تلفن همراه و رمز ریکاوری مخفی ثبت‌شده خود را وارد کنید:")
        desc_secret.setObjectName("muted_text")
        desc_secret.setWordWrap(True)
        page_secret_layout.addWidget(desc_secret)

        page_secret_layout.addWidget(QLabel("شماره همراه مربی:"))
        self.txt_phone = QLineEdit()
        self.txt_phone.setFixedHeight(38)
        self.txt_phone.setPlaceholderText("مثال: 09123456789")
        self.txt_phone.setMaxLength(11)
        page_secret_layout.addWidget(self.txt_phone)

        page_secret_layout.addWidget(QLabel("رمز ریکاوری مخفی:"))
        pass_rec_box = QHBoxLayout()
        pass_rec_box.setSpacing(6)

        self.txt_recovery_code = QLineEdit()
        self.txt_recovery_code.setFixedHeight(38)
        self.txt_recovery_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_recovery_code.setPlaceholderText("رمز ریکاوری مخفی خود را وارد کنید")

        btn_eye_rec = QPushButton("👁️")
        btn_eye_rec.setFixedSize(42, 38)
        btn_eye_rec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_rec.setObjectName("secondary_button")
        btn_eye_rec.clicked.connect(lambda: self.toggle_eye(self.txt_recovery_code, btn_eye_rec))

        pass_rec_box.addWidget(self.txt_recovery_code)
        pass_rec_box.addWidget(btn_eye_rec)
        page_secret_layout.addLayout(pass_rec_box)

        self.btn_verify_secret = QPushButton("🔍 بررسی و تایید اطلاعات")
        self.btn_verify_secret.setFixedHeight(40)
        self.btn_verify_secret.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_verify_secret.setObjectName("primary_button")
        self.btn_verify_secret.clicked.connect(self.do_verify_secret)
        page_secret_layout.addWidget(self.btn_verify_secret)

        self.stack.addWidget(page_secret)
        card_layout.addWidget(self.stack)

        # ========================================================
        # STEP 2: Set New Password (Revealed when verified)
        # ========================================================
        self.step2_frame = QFrame()
        self.step2_frame.setObjectName("step2_frame")
        self.step2_frame.setStyleSheet(f"""
            QFrame#step2_frame {{
                background-color: {palette.bg_surface};
                border: 1px solid {palette.primary};
                border-radius: 8px;
            }}
        """)
        step2_layout = QVBoxLayout(self.step2_frame)
        step2_layout.setContentsMargins(12, 12, 12, 12)
        step2_layout.setSpacing(8)

        self.lbl_matched_username = QLabel("نام کاربری شما:")
        self.lbl_matched_username.setStyleSheet(f"color: {palette.primary}; font-size: 14px; font-weight: bold;")
        step2_layout.addWidget(self.lbl_matched_username)

        step2_layout.addWidget(QLabel("کلمه عبور جدید:"))
        pass_new_box = QHBoxLayout()
        pass_new_box.setSpacing(6)

        self.txt_new_password = QLineEdit()
        self.txt_new_password.setFixedHeight(38)
        self.txt_new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_password.setPlaceholderText("کلمه عبور جدید را وارد کنید")

        btn_eye_new = QPushButton("👁️")
        btn_eye_new.setFixedSize(42, 38)
        btn_eye_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_new.setObjectName("secondary_button")
        btn_eye_new.clicked.connect(lambda: self.toggle_eye(self.txt_new_password, btn_eye_new))

        pass_new_box.addWidget(self.txt_new_password)
        pass_new_box.addWidget(btn_eye_new)
        step2_layout.addLayout(pass_new_box)

        self.btn_reset_and_login = QPushButton("🔐 ذخیره کلمه عبور جدید و ورود")
        self.btn_reset_and_login.setFixedHeight(40)
        self.btn_reset_and_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_and_login.setObjectName("primary_button")
        self.btn_reset_and_login.clicked.connect(self.do_reset_and_login)
        step2_layout.addWidget(self.btn_reset_and_login)

        card_layout.addWidget(self.step2_frame)
        self.step2_frame.setVisible(False)

        scroll.setWidget(card)
        layout.addWidget(scroll)

        # Ensure buttons do not steal Enter key, and line edits trigger verification
        for btn in (
            self.btn_tab_email, self.btn_tab_secret, self.btn_send_otp,
            self.btn_confirm_otp, self.btn_otp_spam_help, btn_eye_rec,
            self.btn_verify_secret, btn_eye_new, self.btn_reset_and_login
        ):
            btn.setAutoDefault(False)
            btn.setDefault(False)

        self.txt_phone.returnPressed.connect(self.do_verify_secret)
        self.txt_recovery_code.returnPressed.connect(self.do_verify_secret)
        self.txt_email_identity.returnPressed.connect(self._on_email_return_pressed)
        self.txt_entered_otp.returnPressed.connect(self.do_verify_email_otp)
        self.txt_new_password.returnPressed.connect(self.do_reset_and_login)

        # Default to Email Mode
        self.switch_mode(0)

    def _get_registered_emails(self) -> list[str]:
        try:
            from nemov.database.connection import get_session
            from nemov.models.database_models import User
            session = get_session()
            try:
                results = session.query(User.email).filter(
                    User.email.isnot(None),
                    User.email != ""
                ).distinct().all()
                emails = [r[0].strip() for r in results if r[0] and r[0].strip()]
                return sorted(list(set(emails)))
            finally:
                session.close()
        except Exception:
            return []

    def _setup_email_completer(self):
        emails = self._get_registered_emails()
        self.email_completer = QCompleter(emails, self.txt_email_identity)
        self.email_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.email_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.email_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.email_completer.activated[str].connect(self._on_email_selected)

        palette = ThemeManager.get_current_palette()
        popup = self.email_completer.popup()
        popup.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        popup.setStyleSheet(f"""
            QListView {{
                background-color: {palette.bg_card};
                color: {palette.text_primary};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 4px;
                font-family: 'Vazirmatn', 'Segoe UI', sans-serif;
                font-size: 13px;
                outline: none;
            }}
            QListView::item {{
                padding: 8px 12px;
                border-radius: 6px;
                min-height: 24px;
            }}
            QListView::item:hover {{
                background-color: {palette.bg_surface};
                color: {palette.text_primary};
            }}
            QListView::item:selected {{
                background-color: {palette.primary};
                color: {palette.text_primary};
            }}
        """)
        self.txt_email_identity.setCompleter(self.email_completer)
        self.txt_email_identity.textChanged.connect(self._on_email_text_changed)

    def _on_email_selected(self, email: str):
        self.txt_email_identity.setText(email)
        self.txt_email_identity.setCursorPosition(len(email))

    def _on_email_text_changed(self, text: str):
        if hasattr(self, "email_completer") and self.email_completer.popup():
            if not text.strip() or self.email_completer.completionModel().rowCount() == 0:
                self.email_completer.popup().hide()

    def _on_email_return_pressed(self):
        if (
            hasattr(self, "email_completer")
            and self.email_completer.popup()
            and self.email_completer.popup().isVisible()
            and self.email_completer.completionModel().rowCount() > 0
        ):
            popup = self.email_completer.popup()
            idx = popup.currentIndex()
            if idx.isValid():
                self._on_email_selected(idx.data())
            else:
                first_idx = self.email_completer.completionModel().index(0, 0)
                if first_idx.isValid():
                    self._on_email_selected(first_idx.data())
            popup.hide()
            return
        self.do_send_email_otp()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.step2_frame.isVisible():
                self.do_reset_and_login()
                event.accept()
                return
            elif self.stack.currentIndex() == 1:
                self.do_verify_secret()
                event.accept()
                return
            elif self.stack.currentIndex() == 0:
                if (
                    hasattr(self, "email_completer")
                    and self.email_completer.popup()
                    and self.email_completer.popup().isVisible()
                    and self.email_completer.completionModel().rowCount() > 0
                ):
                    popup = self.email_completer.popup()
                    idx = popup.currentIndex()
                    if idx.isValid():
                        self._on_email_selected(idx.data())
                    else:
                        first_idx = self.email_completer.completionModel().index(0, 0)
                        if first_idx.isValid():
                            self._on_email_selected(first_idx.data())
                    popup.hide()
                    event.accept()
                    return
                if self.otp_verify_box.isVisible():
                    self.do_verify_email_otp()
                else:
                    self.do_send_email_otp()
                event.accept()
                return
            super().keyPressEvent(event)

    def switch_mode(self, index: int):
        self.stack.setCurrentIndex(index)
        self.stack.updateGeometry()
        if not self.step2_frame.isVisible():
            if index == 1:
                self.setFixedSize(540, 580)
            else:
                if self.otp_verify_box.isVisible():
                    self.setFixedSize(540, 680)
                else:
                    self.setFixedSize(540, 580)
        else:
            if index == 1:
                self.setFixedSize(540, 640)
            else:
                self.setFixedSize(540, 730)

        palette = ThemeManager.get_current_palette()
        if index == 0:
            if hasattr(self, "email_completer") and self.email_completer.model():
                emails = self._get_registered_emails()
                self.email_completer.model().setStringList(emails)
            self.btn_tab_email.setStyleSheet(f"background-color: {palette.primary}; color: {palette.text_primary}; font-weight: bold; border-radius: 6px; border: none;")
            self.btn_tab_secret.setStyleSheet(f"background-color: {palette.bg_surface}; color: {palette.text_secondary}; border: 1px solid {palette.border}; border-radius: 6px;")
        else:
            self.btn_tab_email.setStyleSheet(f"background-color: {palette.bg_surface}; color: {palette.text_secondary}; border: 1px solid {palette.border}; border-radius: 6px;")
            self.btn_tab_secret.setStyleSheet(f"background-color: {palette.primary}; color: {palette.text_primary}; font-weight: bold; border-radius: 6px; border: none;")

    def toggle_eye(self, field: QLineEdit, btn: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁️")

    def _mask_email(self, email: str) -> str:
        if "@" not in email:
            return email
        name, domain = email.split("@", 1)
        if len(name) <= 2:
            masked_name = name[0] + "*"
        else:
            masked_name = name[0] + ("*" * (len(name) - 2)) + name[-1]
        return f"{masked_name}@{domain}"

    def do_send_email_otp(self):
        identity = self.txt_email_identity.text().strip()
        if not identity:
            QMessageBox.warning(self, "خطا", "لطفاً ایمیل، شماره همراه یا نام کاربری خود را وارد کنید.")
            return

        user = find_user_by_email_or_phone(identity)
        if not user:
            if "@" in identity:
                QMessageBox.critical(self, "یافت نشد", "حسابی با این ایمیل وجود ندارد.")
            else:
                QMessageBox.critical(self, "یافت نشد", "هیچ حسابی با این مشخصات یافت نشد.")
            return

        if not user.email:
            QMessageBox.warning(
                self,
                "عدم وجود ایمیل ثبت‌شده",
                "برای این حساب کاربری هیچ ایمیلی ثبت نشده است.\nلطفاً از تب «رمز ریکاوری مخفی (آفلاین)» استفاده کنید."
            )
            return

        self.pending_user = user
        otp = EmailService.generate_and_store_otp(user.email)

        self.btn_send_otp.setEnabled(False)
        self.btn_send_otp.setText("در حال ارسال ایمیل...")

        self.otp_thread = SendOtpThread(user.email, user.display_name, otp)
        self.otp_thread.finished_signal.connect(self._on_otp_sent)
        self.otp_thread.start()

    def _on_otp_sent(self, success: bool, msg: str):
        if success:
            masked = self._mask_email(self.pending_user.email)
            self.lbl_otp_sent_info.setText(
                f"✅ کد تایید ۵ رقمی به ایمیل «{masked}» فرستاده شد.\n"
                "💡 در صورت عدم مشاهده در Inbox، حتماً پوشه Spam (هرزنامه) را بررسی نمایید."
            )
            self.otp_verify_box.setVisible(True)
            self.stack.updateGeometry()
            self.setFixedSize(540, 680)

            # Start 60 second countdown timer
            self.countdown_seconds = 60
            self.btn_send_otp.setEnabled(False)
            self.btn_send_otp.setText(f"ارسال مجدد ({self.countdown_seconds} ثانیه)")
            self.resend_timer.start()
        else:
            self.btn_send_otp.setEnabled(True)
            self.btn_send_otp.setText("📩 دریافت کد تایید در ایمیل")
            QMessageBox.critical(self, "خطا در ارسال ایمیل", msg)

    def _open_spam_guide(self):
        from nemov.views.components.email_spam_guide_dialog import EmailSpamGuideDialog
        EmailSpamGuideDialog(self).exec()

    def _update_resend_countdown(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            self.resend_timer.stop()
            self.btn_send_otp.setEnabled(True)
            self.btn_send_otp.setText("📩 ارسال مجدد کد تایید")
        else:
            self.btn_send_otp.setText(f"ارسال مجدد ({self.countdown_seconds} ثانیه)")

    def do_verify_email_otp(self):
        if not hasattr(self, "pending_user") or not self.pending_user:
            return

        code = self.txt_entered_otp.text().strip()
        if not code:
            QMessageBox.warning(self, "خطا", "لطفاً کد ۵ رقمی دریافتی در ایمیل را وارد کنید.")
            return

        success, msg = EmailService.verify_otp(self.pending_user.email, code)
        if success:
            self._activate_step2(self.pending_user)
        else:
            QMessageBox.critical(self, "خطا در تایید کد", msg)

    def do_verify_secret(self):
        phone = self.txt_phone.text().strip()
        code = self.txt_recovery_code.text().strip()

        if not phone or not code:
            QMessageBox.warning(self, "خطا", "لطفاً هم شماره همراه و هم رمز ریکاوری مخفی را وارد کنید.")
            return

        user = verify_recovery_credentials(phone, code)
        if user:
            self._activate_step2(user)
        else:
            QMessageBox.critical(self, "اطلاعات نادرست", "هیچ حسابی با این شماره همراه و رمز ریکاوری یافت نشد.")

    def _activate_step2(self, user):
        self.matched_user = user
        self.lbl_matched_username.setText(f"✅ مربی تایید شد: {user.display_name} (نام کاربری: {user.username})")

        # Disable step 1 controls
        self.btn_tab_email.setEnabled(False)
        self.btn_tab_secret.setEnabled(False)
        self.txt_email_identity.setEnabled(False)
        self.btn_send_otp.setEnabled(False)
        self.txt_entered_otp.setEnabled(False)
        self.btn_confirm_otp.setEnabled(False)
        self.txt_phone.setEnabled(False)
        self.txt_recovery_code.setEnabled(False)
        self.btn_verify_secret.setEnabled(False)

        self.step2_frame.setVisible(True)
        if self.stack.currentIndex() == 0:
            self.setFixedSize(540, 730)
        else:
            self.setFixedSize(540, 640)
        self.txt_new_password.setFocus()

    def do_reset_and_login(self):
        if not self.matched_user:
            return

        new_pass = self.txt_new_password.text().strip()
        if not new_pass:
            QMessageBox.warning(self, "خطا", "لطفاً کلمه عبور جدید را وارد کنید.")
            return

        try:
            update_trainer_profile(
                user_id=self.matched_user.id,
                first_name=self.matched_user.first_name,
                last_name=self.matched_user.last_name,
                phone=self.matched_user.phone,
                email=self.matched_user.email,
                birth_date_shamsi=self.matched_user.birth_date_shamsi,
                photo_path=self.matched_user.photo_path,
                username=self.matched_user.username,
                password=new_pass,
                recovery_code=self.matched_user.recovery_code
            )
            CurrentUser.set(self.matched_user)
            QMessageBox.information(
                self,
                "موفقیت",
                f"کلمه عبور جدید با موفقیت ذخیره شد. خوش آمدید {self.matched_user.display_name}! 🌸"
            )
            self.recovery_success.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تغییر کلمه عبور: {str(e)}")
