from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import config
from yalda.auth.authentication import authenticate_user, is_app_license_active, check_username_exists
from yalda.utils.security import normalize_digits
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
        self.setWindowTitle(f"{config.APP_NAME} - ورود به سیستم")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #121212;")
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_activation_state()
        self.clear_user_error()
        self.clear_pass_error()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Login Card Container
        card = QFrame()
        card.setFixedSize(480, 590)
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
        icon_path = config.BASE_DIR / "resources" / "images" / "app_icon.png"
        if icon_path.exists():
            lbl_logo = QLabel()
            pix = QPixmap(str(icon_path)).scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_logo)

        # Subtitle Text
        sub_lbl = QLabel("ورود به نرم‌افزار مدیریت باشگاه بدنسازی یلدا")
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
        self.txt_username.textChanged.connect(self.clear_user_error)
        self.txt_username.returnPressed.connect(lambda: self.txt_password.setFocus())
        
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
        btn_login = QPushButton("ورود به سیستم")
        btn_login.setFixedHeight(44)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet("""
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
        btn_login.clicked.connect(self.do_login)
        card_layout.addWidget(btn_login)

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

        user = authenticate_user(target_user, password)
        if user:
            self.login_success.emit()
        else:
            self.txt_password.setStyleSheet(STYLE_INPUT_ERROR)
            self.lbl_pass_error.setText("❌ رمز عبور اشتباه است.")
            self.lbl_pass_error.setVisible(True)
            self.txt_password.setFocus()
