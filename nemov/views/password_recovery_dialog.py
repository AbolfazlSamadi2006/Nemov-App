from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QScrollArea, QStackedWidget, QSizePolicy, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QStringListModel
from nemov.auth.authentication import (
    verify_recovery_credentials, update_trainer_profile, CurrentUser, find_user_by_email_or_phone
)
from nemov.services.sms_service import SmsService
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

    def __init__(self, phone: str, trainer_name: str, otp_code: str):
        super().__init__()
        self.phone = phone
        self.trainer_name = trainer_name
        self.otp_code = otp_code

    def run(self):
        try:
            success, msg = SmsService.send_otp_sms(
                recipient_phone=self.phone,
                recipient_name=self.trainer_name,
                otp_code=self.otp_code,
            )
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class PasswordRecoveryDialog(QDialog):
    recovery_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بازیابی نام کاربری و کلمه عبور مربی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(540, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.matched_user = None
        self.pending_user = None
        self.pending_phone = ""
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

        self.btn_tab_sms = QPushButton("📱 ارسال کد به موبایل (آنلاین)")
        self.btn_tab_sms.setFixedHeight(38)
        self.btn_tab_sms.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_secret = QPushButton("🔑 رمز ریکاوری مخفی (آفلاین)")
        self.btn_tab_secret.setFixedHeight(38)
        self.btn_tab_secret.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_sms.clicked.connect(lambda: self.switch_mode(0))
        self.btn_tab_secret.clicked.connect(lambda: self.switch_mode(1))

        tab_box.addWidget(self.btn_tab_sms)
        tab_box.addWidget(self.btn_tab_secret)
        card_layout.addLayout(tab_box)

        # Stacked Container for the 2 Modes
        self.stack = AutoResizingStackedWidget()
        self.stack.setObjectName("recovery_stack")
        self.stack.setStyleSheet("QStackedWidget#recovery_stack { background: transparent; border: none; }")
        self.stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        # ========================================================
        # PAGE 0: SMS OTP Mode (Online via SMS.ir)
        # ========================================================
        page_sms = QFrame()
        page_sms.setObjectName("recovery_page_sms")
        page_sms.setStyleSheet("QFrame#recovery_page_sms { background: transparent; border: none; }")
        page_sms_layout = QVBoxLayout(page_sms)
        page_sms_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        page_sms_layout.setContentsMargins(0, 4, 0, 0)
        page_sms_layout.setSpacing(6)

        desc_sms = QLabel("با وارد کردن شماره همراه یا نام کاربری، کد تایید ۵ رقمی به موبایل شما پیامک می‌شود:")
        desc_sms.setObjectName("muted_text")
        desc_sms.setWordWrap(True)
        page_sms_layout.addWidget(desc_sms)

        page_sms_layout.addWidget(QLabel("شماره همراه یا نام کاربری مربی:"))
        self.txt_sms_identity = QLineEdit()
        self.txt_sms_identity.setFixedHeight(38)
        self.txt_sms_identity.setPlaceholderText("مثال: 09123456789 یا نام کاربری")
        page_sms_layout.addWidget(self.txt_sms_identity)
        self._setup_identity_completer()

        # Send Code Button
        self.btn_send_otp = QPushButton("📱 دریافت کد تایید پیامکی")
        self.btn_send_otp.setFixedHeight(40)
        self.btn_send_otp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_otp.setObjectName("primary_button")
        self.btn_send_otp.clicked.connect(self.do_send_sms_otp)
        page_sms_layout.addWidget(self.btn_send_otp)

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

        otp_box_layout.addWidget(QLabel("کد تایید ۵ رقمی پیامک‌شده:"))
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
        self.btn_confirm_otp.clicked.connect(self.do_verify_sms_otp)
        otp_box_layout.addWidget(self.btn_confirm_otp)

        page_sms_layout.addWidget(self.otp_verify_box)
        self.otp_verify_box.setVisible(False)

        self.stack.addWidget(page_sms)

        # ========================================================
        # PAGE 1: Secret Recovery Code Mode (Offline)
        # ========================================================
        page_secret = QFrame()
        page_secret.setObjectName("recovery_page_secret")
        page_secret.setStyleSheet("QFrame#recovery_page_secret { background: transparent; border: none; }")
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

        self.btn_eye_rec = self._create_eye_button(self.txt_recovery_code, palette)
        btn_eye_rec = self.btn_eye_rec

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

        self.btn_eye_new = self._create_eye_button(self.txt_new_password, palette)
        btn_eye_new = self.btn_eye_new

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
            self.btn_tab_sms, self.btn_tab_secret, self.btn_send_otp,
            self.btn_confirm_otp, btn_eye_rec,
            self.btn_verify_secret, btn_eye_new, self.btn_reset_and_login
        ):
            btn.setAutoDefault(False)
            btn.setDefault(False)

        self.txt_phone.returnPressed.connect(self.do_verify_secret)
        self.txt_recovery_code.returnPressed.connect(self.do_verify_secret)
        self.txt_sms_identity.returnPressed.connect(self._on_identity_return_pressed)
        self.txt_entered_otp.returnPressed.connect(self.do_verify_sms_otp)
        self.txt_new_password.returnPressed.connect(self.do_reset_and_login)

        # Default to SMS OTP Mode
        self.switch_mode(0)

    def _get_registered_identities(self) -> list[str]:
        try:
            from nemov.database.connection import get_session
            from nemov.models.database_models import User
            session = get_session()
            try:
                results = session.query(User.phone).filter(
                    User.phone.isnot(None),
                    User.phone != ""
                ).distinct().all()
                phones = [r[0].strip() for r in results if r[0] and r[0].strip()]
                return sorted(list(set(phones)))
            finally:
                session.close()
        except Exception:
            return []

    def _setup_identity_completer(self):
        identities = self._get_registered_identities()
        self.identity_completer = QCompleter(identities, self.txt_sms_identity)
        self.identity_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.identity_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.identity_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.identity_completer.activated[str].connect(self._on_identity_selected)

        palette = ThemeManager.get_current_palette()
        popup = self.identity_completer.popup()
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
        self.txt_sms_identity.setCompleter(self.identity_completer)
        self.txt_sms_identity.textChanged.connect(self._on_identity_text_changed)

    def _on_identity_selected(self, value: str):
        self.txt_sms_identity.setText(value)
        self.txt_sms_identity.setCursorPosition(len(value))

    def _on_identity_text_changed(self, text: str):
        if hasattr(self, "identity_completer") and self.identity_completer.popup():
            if not text.strip() or self.identity_completer.completionModel().rowCount() == 0:
                self.identity_completer.popup().hide()

    def _on_identity_return_pressed(self):
        if (
            hasattr(self, "identity_completer")
            and self.identity_completer.popup()
            and self.identity_completer.popup().isVisible()
            and self.identity_completer.completionModel().rowCount() > 0
        ):
            popup = self.identity_completer.popup()
            idx = popup.currentIndex()
            if idx.isValid():
                self._on_identity_selected(idx.data())
            else:
                first_idx = self.identity_completer.completionModel().index(0, 0)
                if first_idx.isValid():
                    self._on_identity_selected(first_idx.data())
            popup.hide()
            return
        self.do_send_sms_otp()

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
                    hasattr(self, "identity_completer")
                    and self.identity_completer.popup()
                    and self.identity_completer.popup().isVisible()
                    and self.identity_completer.completionModel().rowCount() > 0
                ):
                    popup = self.identity_completer.popup()
                    idx = popup.currentIndex()
                    if idx.isValid():
                        self._on_identity_selected(idx.data())
                    else:
                        first_idx = self.identity_completer.completionModel().index(0, 0)
                        if first_idx.isValid():
                            self._on_identity_selected(first_idx.data())
                    popup.hide()
                    event.accept()
                    return
                if self.otp_verify_box.isVisible():
                    self.do_verify_sms_otp()
                else:
                    self.do_send_sms_otp()
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
                    self.setFixedSize(540, 640)
                else:
                    self.setFixedSize(540, 580)
        else:
            if index == 1:
                self.setFixedSize(540, 640)
            else:
                self.setFixedSize(540, 700)

        palette = ThemeManager.get_current_palette()
        if index == 0:
            if hasattr(self, "identity_completer") and self.identity_completer.model():
                identities = self._get_registered_identities()
                self.identity_completer.model().setStringList(identities)
            self.btn_tab_sms.setStyleSheet(f"background-color: {palette.primary}; color: {palette.text_primary}; font-weight: bold; border-radius: 6px; border: none;")
            self.btn_tab_secret.setStyleSheet(f"background-color: {palette.bg_surface}; color: {palette.text_secondary}; border: 1px solid {palette.border}; border-radius: 6px;")
        else:
            self.btn_tab_sms.setStyleSheet(f"background-color: {palette.bg_surface}; color: {palette.text_secondary}; border: 1px solid {palette.border}; border-radius: 6px;")
            self.btn_tab_secret.setStyleSheet(f"background-color: {palette.primary}; color: {palette.text_primary}; font-weight: bold; border-radius: 6px; border: none;")

    def _create_eye_button(self, field: QLineEdit, palette) -> QPushButton:
        """Creates a compact eye toggle button without #secondary_button padding clipping."""
        btn = QPushButton("👁️")
        btn.setObjectName("eye_button")
        btn.setFixedSize(44, 38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("نمایش / پنهان‌سازی کلمه عبور")
        btn.setStyleSheet(f"""
            QPushButton#eye_button {{
                background-color: {palette.bg_input};
                color: {palette.text_primary};
                border: 1px solid {palette.border};
                border-radius: 6px;
                font-size: 16px;
                font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton#eye_button:hover {{
                background-color: {palette.bg_surface};
                border: 1px solid {palette.primary};
            }}
        """)
        btn.clicked.connect(lambda: self.toggle_eye(field, btn))
        return btn

    def toggle_eye(self, field: QLineEdit, btn: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁️")

    def _mask_phone(self, phone: str) -> str:
        clean = SmsService.normalize_phone_number(phone)
        if len(clean) >= 8:
            return f"{clean[:4]}***{clean[-4:]}"
        return clean

    def do_send_sms_otp(self):
        identity = self.txt_sms_identity.text().strip()
        if not identity:
            QMessageBox.warning(self, "خطا", "لطفاً شماره همراه یا نام کاربری خود را وارد کنید.")
            return

        user = find_user_by_email_or_phone(identity)
        if not user:
            norm_ident = SmsService.normalize_phone_number(identity)
            if norm_ident and norm_ident != identity:
                user = find_user_by_email_or_phone(norm_ident)
        if not user:
            QMessageBox.critical(self, "یافت نشد", "هیچ حسابی با این مشخصات یافت نشد.")
            return

        clean_phone = SmsService.normalize_phone_number(getattr(user, "phone", "") or "")
        if not clean_phone or not clean_phone.startswith("09") or len(clean_phone) != 11:
            QMessageBox.warning(
                self,
                "عدم وجود شماره موبایل معتبر",
                "برای این حساب کاربری شماره موبایل معتبری ثبت نشده است.\nلطفاً از تب «رمز ریکاوری مخفی (آفلاین)» استفاده کنید."
            )
            return

        self.pending_user = user
        self.pending_phone = clean_phone
        otp = SmsService.generate_and_store_otp(clean_phone)

        self.btn_send_otp.setEnabled(False)
        self.btn_send_otp.setText("در حال ارسال پیامک...")

        self.otp_thread = SendOtpThread(clean_phone, user.display_name, otp)
        self.otp_thread.finished_signal.connect(self._on_otp_sent)
        self.otp_thread.start()

    def _on_otp_sent(self, success: bool, msg: str):
        if success:
            masked = self._mask_phone(self.pending_phone)
            self.lbl_otp_sent_info.setText(
                f"✅ کد تایید ۵ رقمی به شماره موبایل «\u202A{masked}\u202C» پیامک شد."
            )
            self.otp_verify_box.setVisible(True)
            self.stack.updateGeometry()
            self.setFixedSize(540, 640)

            # Start 60 second countdown timer
            self.countdown_seconds = 60
            self.btn_send_otp.setEnabled(False)
            self.btn_send_otp.setText(f"ارسال مجدد ({self.countdown_seconds} ثانیه)")
            self.resend_timer.start()
        else:
            self.btn_send_otp.setEnabled(True)
            self.btn_send_otp.setText("📱 دریافت کد تایید پیامکی")
            QMessageBox.critical(self, "خطا در ارسال پیامک", msg)

    def _update_resend_countdown(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            self.resend_timer.stop()
            self.btn_send_otp.setEnabled(True)
            self.btn_send_otp.setText("📱 ارسال مجدد کد تایید پیامکی")
        else:
            self.btn_send_otp.setText(f"ارسال مجدد ({self.countdown_seconds} ثانیه)")

    def do_verify_sms_otp(self):
        if not getattr(self, "pending_user", None) or not getattr(self, "pending_phone", ""):
            return

        code = self.txt_entered_otp.text().strip()
        if not code:
            QMessageBox.warning(self, "خطا", "لطفاً کد ۵ رقمی پیامک‌شده را وارد کنید.")
            return

        success, msg = SmsService.verify_otp(self.pending_phone, code)
        if success:
            self.resend_timer.stop()
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
        self.resend_timer.stop()
        self.lbl_matched_username.setText(f"✅ مربی تایید شد: {user.display_name} (نام کاربری: {user.username})")

        # Disable step 1 controls
        self.btn_tab_sms.setEnabled(False)
        self.btn_tab_secret.setEnabled(False)
        self.txt_sms_identity.setEnabled(False)
        self.btn_send_otp.setEnabled(False)
        self.txt_entered_otp.setEnabled(False)
        self.btn_confirm_otp.setEnabled(False)
        self.txt_phone.setEnabled(False)
        self.txt_recovery_code.setEnabled(False)
        self.btn_verify_secret.setEnabled(False)

        self.step2_frame.setVisible(True)
        if self.stack.currentIndex() == 0:
            self.setFixedSize(540, 700)
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
