from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame,
    QCheckBox, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QPixmap, QIcon
import config
from yalda.auth.authentication import authenticate_user, is_app_license_active, check_username_exists
from yalda.utils.security import normalize_digits
from yalda.utils.credential_manager import CredentialManager
from yalda.views.password_recovery_dialog import PasswordRecoveryDialog
from yalda.views.trainer_register_dialog import TrainerRegisterDialog
from yalda.views.cloud_restore_dialog import CloudRestoreDialog

STYLE_INPUT_NORMAL = """
    QLineEdit {
        background-color: #1E1E1E;
        color: #FFFFFF;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border: 1px solid #8B0000;
    }
"""

STYLE_INPUT_ERROR = """
    QLineEdit {
        background-color: #2D1515;
        color: #FFAAAA;
        border: 1.5px solid #EF4444;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border: 1.5px solid #FF4444;
    }
"""

class LoginView(QWidget):
    login_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{config.APP_TITLE} - ورود به سیستم")

        # Explicitly set window icon to multi-resolution nemov.ico
        ico_path = config.BASE_DIR / "resources" / "icons" / "nemov.ico"
        png_path = config.BASE_DIR / "resources" / "images" / "nemov_logo.png"
        legacy_ico = config.BASE_DIR / "resources" / "images" / "app_icon.ico"
        app_icon = QIcon()
        if ico_path.exists():
            app_icon.addFile(str(ico_path))
        elif legacy_ico.exists():
            app_icon.addFile(str(legacy_ico))
        if png_path.exists():
            app_icon.addFile(str(png_path))
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #121212;")
        self._is_auto_filling = False
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_activation_state()
        self.clear_user_error()
        self.clear_pass_error()
        self.load_remembered_credentials()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            u_norm = normalize_digits(self.txt_username.text().strip())
            p_text = self.txt_password.text().strip()
            if u_norm and p_text:
                self.do_login()
                event.accept()
                return
            elif u_norm and not p_text:
                if CredentialManager.has_credential(u_norm):
                    self.on_account_selected(u_norm)
                    if self.txt_password.text().strip():
                        self.do_login()
                        event.accept()
                        return
                self.txt_password.setFocus()
                event.accept()
                return
        super().keyPressEvent(event)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Login Card Container
        card = QFrame()
        card.setFixedSize(480, 610)
        card.setObjectName("login_card")
        card.setStyleSheet("""
            QFrame#login_card {
                background-color: #000000;
                border: 1px solid #222222;
                border-radius: 12px;
                padding: 20px 25px;
            }
            QLabel {
                background-color: transparent;
                background: transparent;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        # Logo Image (Enlarged)
        icon_path = config.BASE_DIR / "resources" / "images" / "nemov_logo.png"
        if not icon_path.exists():
            icon_path = config.BASE_DIR / "resources" / "images" / "app_icon.png"
        if icon_path.exists():
            lbl_logo = QLabel()
            pix = QPixmap(str(icon_path)).scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_logo)

        # Subtitle Text
        sub_lbl = QLabel(f"ورود به {config.APP_TITLE}")
        sub_lbl.setStyleSheet("color: #E2E8F0; font-size: 14px; font-weight: bold; background: transparent; margin-top: 4px; margin-bottom: 6px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(sub_lbl)

        # Username Input
        lbl_user = QLabel("نام کاربری:")
        lbl_user.setStyleSheet("color: #DDDDDD; font-weight: bold; background: transparent;")
        
        self.txt_username = QLineEdit()
        self.txt_username.setFixedHeight(40)
        self.txt_username.setPlaceholderText("نام کاربری را وارد کنید")
        self.txt_username.setStyleSheet(STYLE_INPUT_NORMAL)
        self.txt_username.textChanged.connect(self.on_username_text_changed)
        self.txt_username.returnPressed.connect(self.on_username_return_pressed)
        
        # Setup Auto-Complete Completer for Remembered Users
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setMaxVisibleItems(8)
        popup = self.completer.popup()
        if popup:
            popup.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            popup.setStyleSheet("""
                QListView {
                    background-color: #1A1A1A;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    selection-background-color: #8B0000;
                    selection-color: #FFFFFF;
                    padding: 4px;
                    font-size: 13px;
                    outline: none;
                }
                QListView::item {
                    padding: 8px 12px;
                    border-radius: 4px;
                }
                QListView::item:hover {
                    background-color: #2D1515;
                    color: #FFFFFF;
                }
                QListView::item:selected {
                    background-color: #8B0000;
                    color: #FFFFFF;
                }
            """)
        self.txt_username.setCompleter(self.completer)
        self.completer.activated[str].connect(self.on_account_selected)

        self.lbl_user_error = QLabel()
        self.lbl_user_error.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold; background: transparent; padding: 2px;")
        self.lbl_user_error.setVisible(False)
        
        card_layout.addWidget(lbl_user)
        card_layout.addWidget(self.txt_username)
        card_layout.addWidget(self.lbl_user_error)

        # Password Input Layout with Eye Button
        lbl_pass = QLabel("کلمه عبور:")
        lbl_pass.setStyleSheet("color: #DDDDDD; font-weight: bold; background: transparent;")
        
        pass_box = QHBoxLayout()
        pass_box.setSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setFixedHeight(40)
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("کلمه عبور را وارد کنید")
        self.txt_password.returnPressed.connect(self.do_login)
        self.txt_password.setStyleSheet(STYLE_INPUT_NORMAL)
        self.txt_password.textChanged.connect(self.clear_pass_error)

        btn_eye = QPushButton("👁️")
        btn_eye.setObjectName("eye_button")
        btn_eye.setFixedSize(44, 40)
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setToolTip("نمایش / پنهان‌سازی کلمه عبور")
        btn_eye.setStyleSheet("""
            QPushButton#eye_button {
                background-color: #8B0000;
                color: #FFFFFF;
                border: 1px solid #A00000;
                border-radius: 6px;
                font-size: 16px;
                font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#eye_button:hover {
                background-color: #A00000;
            }
        """)

        btn_eye.clicked.connect(lambda: self.toggle_password(self.txt_password, btn_eye))

        pass_box.addWidget(self.txt_password)
        pass_box.addWidget(btn_eye)

        self.lbl_pass_error = QLabel()
        self.lbl_pass_error.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold; background: transparent; padding: 2px;")
        self.lbl_pass_error.setVisible(False)

        card_layout.addWidget(lbl_pass)
        card_layout.addLayout(pass_box)
        card_layout.addWidget(self.lbl_pass_error)

        # Remember Me Checkbox Row
        check_icon_path = str(config.BASE_DIR / "resources" / "images" / "check.svg").replace("\\", "/")
        row_remember = QHBoxLayout()
        row_remember.setSpacing(8)
        self.chk_remember = QCheckBox("مرا به خاطر بسپار")
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_remember.setStyleSheet(f"""
            QCheckBox {{
                color: #CCCCCC;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox:hover {{
                color: #FFFFFF;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #1E1E1E;
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid #8B0000;
            }}
            QCheckBox::indicator:checked {{
                background-color: #8B0000;
                border: 1px solid #A00000;
                image: url("{check_icon_path}");
            }}
        """)
        self.chk_remember.toggled.connect(self.on_remember_toggled)
        row_remember.addWidget(self.chk_remember)
        row_remember.addStretch()
        card_layout.addLayout(row_remember)
        card_layout.addSpacing(4)

        # Actions Row: Forgot Password & Register New Trainer
        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)

        self.btn_forgot = QPushButton("🔑 فراموشی کلمه عبور")
        self.btn_forgot.setFixedHeight(36)
        self.btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forgot.setStyleSheet("""
            QPushButton {
                background-color: #1F2937;
                color: #9CA3AF;
                border: 1px solid #374151;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #FFFFFF;
            }
        """)
        self.btn_forgot.clicked.connect(self.open_forgot_dialog)

        self.btn_register = QPushButton("📝 ثبت‌نام مربی جدید")
        self.btn_register.setFixedHeight(36)
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.clicked.connect(self.open_register_dialog)

        row_actions.addWidget(self.btn_forgot)
        row_actions.addWidget(self.btn_register)
        card_layout.addLayout(row_actions)

        # Cloud Restore Button (for new computer or fresh install)
        self.btn_cloud = QPushButton("☁️ بازیابی اطلاعات از سرور ابری (سیستم جدید)")
        self.btn_cloud.setFixedHeight(36)
        self.btn_cloud.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cloud.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #93C5FD;
                border: 1px solid #2563EB;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        self.btn_cloud.clicked.connect(self.open_cloud_restore_dialog)
        card_layout.addWidget(self.btn_cloud)
        card_layout.addSpacing(6)

        # Submit Login Button
        self.btn_login = QPushButton("ورود به سیستم")
        self.btn_login.setFixedHeight(44)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setDefault(True)
        self.btn_login.setAutoDefault(True)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #A00000;
            }
        """)
        self.btn_login.clicked.connect(self.do_login)
        card_layout.addWidget(self.btn_login)

        main_layout.addWidget(card)
        self.refresh_activation_state()

    def clear_user_error(self):
        self.txt_username.setStyleSheet(STYLE_INPUT_NORMAL)
        self.lbl_user_error.setText("")
        self.lbl_user_error.setVisible(False)

    def clear_pass_error(self):
        self.txt_password.setStyleSheet(STYLE_INPUT_NORMAL)
        self.lbl_pass_error.setText("")
        self.lbl_pass_error.setVisible(False)

    def refresh_activation_state(self):
        active = is_app_license_active()
        if active:
            self.btn_register.setEnabled(True)
            self.btn_register.setToolTip("ثبت‌نام مربی جدید در سیستم")
            self.btn_register.setStyleSheet("""
                QPushButton {
                    background-color: #065F46;
                    color: #A7F3D0;
                    border: 1px solid #059669;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #047857;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_register.setEnabled(False)
            self.btn_register.setToolTip("⚠️ ثبت‌نام مربی جدید در حال حاضر غیرفعال است.\nجهت فعال‌سازی، ابتدا ادمین کل باید وضعیت برنامه را فعال کند.")
            self.btn_register.setStyleSheet("""
                QPushButton {
                    background-color: #262626;
                    color: #666666;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    font-size: 12px;
                }
            """)

    def toggle_password(self, field: QLineEdit, button: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("👁️")

    def open_forgot_dialog(self):
        dlg = PasswordRecoveryDialog(self)
        dlg.recovery_success.connect(self.login_success.emit)
        dlg.exec()

    def open_register_dialog(self):
        if not is_app_license_active():
            QMessageBox.warning(self, "برنامه غیرفعال است", "ثبت‌نام مربی جدید غیرفعال می‌باشد. ادمین باید وضعیت برنامه را به فعال تغییر دهد.")
            return
        dlg = TrainerRegisterDialog(self)
        dlg.registration_success.connect(self.login_success.emit)
        dlg.exec()

    def open_cloud_restore_dialog(self):
        dlg = CloudRestoreDialog(self)
        dlg.restore_success.connect(self.login_success.emit)
        dlg.exec()

    def refresh_completer(self):
        saved_users = CredentialManager.get_all_saved_usernames()
        model = QStringListModel(saved_users, self.completer)
        self.completer.setModel(model)

    def load_remembered_credentials(self):
        self._is_auto_filling = True
        try:
            self.refresh_completer()
            self.txt_username.clear()
            self.txt_password.clear()
            self.chk_remember.setChecked(False)
            self.txt_username.setFocus()
        finally:
            self._is_auto_filling = False

    def on_account_selected(self, text_or_index):
        if not text_or_index:
            return
        if isinstance(text_or_index, str):
            username = text_or_index
        else:
            try:
                username = text_or_index.data()
            except Exception:
                username = str(text_or_index)
        u_norm = normalize_digits(username.strip())
        self._is_auto_filling = True
        try:
            self.txt_username.setText(u_norm)
            saved_pwd = CredentialManager.get_password(u_norm)
            if saved_pwd:
                self.txt_password.setText(saved_pwd)
                self.chk_remember.setChecked(True)
                self.btn_login.setFocus()
            else:
                self.txt_password.clear()
                self.chk_remember.setChecked(False)
                self.txt_password.setFocus()
        finally:
            self._is_auto_filling = False

    def on_username_text_changed(self, text: str):
        self.clear_user_error()
        if self._is_auto_filling:
            return
        # When typing, do not auto-fill password until chosen from suggestions.
        # Clear password if it was previously auto-filled to prevent mismatched credentials.
        if self.txt_password.text():
            self._is_auto_filling = True
            try:
                self.txt_password.clear()
                self.chk_remember.setChecked(False)
            finally:
                self._is_auto_filling = False

    def on_username_return_pressed(self):
        u_norm = normalize_digits(self.txt_username.text().strip())
        if u_norm and CredentialManager.has_credential(u_norm) and not self.txt_password.text().strip():
            self.on_account_selected(u_norm)

        if u_norm and self.txt_password.text().strip():
            self.do_login()
        else:
            self.txt_password.setFocus()

    def on_remember_toggled(self, checked: bool):
        if not checked and not self._is_auto_filling:
            raw_u = self.txt_username.text().strip()
            u_norm = normalize_digits(raw_u)
            if u_norm and CredentialManager.has_credential(u_norm):
                CredentialManager.remove_credential(u_norm)
                self.refresh_completer()

    def do_login(self):
        self.clear_user_error()
        self.clear_pass_error()

        raw_username = self.txt_username.text().strip()
        username = normalize_digits(raw_username)
        password = self.txt_password.text().strip()

        if not username:
            self.txt_username.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_user_error.setText("❌ لطفاً نام کاربری را وارد کنید.")
            self.lbl_user_error.setVisible(True)
            self.txt_username.setFocus()
            return

        if not password:
            self.txt_password.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_pass_error.setText("❌ لطفاً کلمه عبور را وارد کنید.")
            self.lbl_pass_error.setVisible(True)
            self.txt_password.setFocus()
            return

        target_user = username if check_username_exists(username) else (raw_username if check_username_exists(raw_username) else None)
        if not target_user:
            self.txt_username.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_user_error.setText("❌ چنین نام کاربری در سیستم وجود ندارد.")
            self.lbl_user_error.setVisible(True)
            self.txt_username.setFocus()
            return

        # Check Hardware License: if app is not active on this machine and user is NOT admin, block login!
        if target_user != "admin" and not is_app_license_active():
            self.txt_username.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_user_error.setText("⛔ این نسخه برای سخت‌افزار این رایانه فعال نشده است.\nجهت فعال‌سازی با مدیر سیستم تماس بگیرید.")
            self.lbl_user_error.setVisible(True)
            return

        user = authenticate_user(target_user, password)
        if user:
            if self.chk_remember.isChecked():
                CredentialManager.save_credential(target_user, password)
            else:
                CredentialManager.remove_credential(target_user)
            self.login_success.emit()
        else:
            self.txt_password.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_pass_error.setText("❌ رمز عبور اشتباه است.")
            self.lbl_pass_error.setVisible(True)
            self.txt_password.setFocus()
