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
from yalda.utils.theme_manager import ThemeManager

STYLE_INPUT_NORMAL = ""
STYLE_INPUT_ERROR = ""

class LoginView(QWidget):
    login_success = pyqtSignal()

    @staticmethod
    def _get_input_style(palette, is_error=False) -> str:
        input_bg = getattr(palette, "bg_input", getattr(palette, "input_bg", palette.bg_card if palette.is_dark else "#FFFFFF"))
        input_border = getattr(palette, "input_border", palette.border_light)
        focus_border = getattr(palette, "input_focus_border", palette.primary)

        if is_error:
            err_bg = "#2D1515" if palette.is_dark else "#FEF2F2"
            err_text = "#FFAAAA" if palette.is_dark else "#991B1B"
            err_border = "#EF4444" if palette.is_dark else "#DC2626"
            return f"""
                QLineEdit {{
                    background-color: {err_bg};
                    color: {err_text};
                    border: 1.5px solid {err_border};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 14px;
                }}
                QLineEdit:focus {{
                    border: 1.5px solid #FF4444;
                }}
            """
        else:
            return f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {palette.text_primary};
                    border: 1px solid {input_border};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 14px;
                }}
                QLineEdit:focus {{
                    border: 1.5px solid {focus_border};
                }}
            """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("login_view")
        self.setWindowTitle(f"{config.APP_TITLE} - ورود به سیستم")

        # Explicitly set window icon to multi-resolution nemov.ico
        from yalda.utils.image_utils import get_app_icon, apply_windows_taskbar_icon
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        apply_windows_taskbar_icon(self)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._is_auto_filling = False
        self._user_has_error = False
        self._pass_has_error = False

        self.init_ui()

        try:
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

        self._apply_theme_style()

    def _on_theme_changed(self, theme_key: str):
        self._apply_theme_style()

    def showEvent(self, event):
        super().showEvent(event)
        from yalda.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self)
        self._apply_theme_style()
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
        self.card = QFrame()
        self.card.setFixedSize(480, 610)
        self.card.setObjectName("login_card")

        card_layout = QVBoxLayout(self.card)
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
        self.sub_lbl = QLabel(f"ورود به {config.APP_TITLE}")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.sub_lbl)

        # Username Input
        self.lbl_user = QLabel("نام کاربری:")
        
        self.txt_username = QLineEdit()
        self.txt_username.setFixedHeight(40)
        self.txt_username.setPlaceholderText("نام کاربری را وارد کنید")
        self.txt_username.textChanged.connect(self.on_username_text_changed)
        self.txt_username.returnPressed.connect(self.on_username_return_pressed)
        
        # Setup Auto-Complete Completer for Remembered Users
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setMaxVisibleItems(8)
        self.txt_username.setCompleter(self.completer)
        self.completer.activated[str].connect(self.on_account_selected)

        self.lbl_user_error = QLabel()
        self.lbl_user_error.setVisible(False)
        
        card_layout.addWidget(self.lbl_user)
        card_layout.addWidget(self.txt_username)
        card_layout.addWidget(self.lbl_user_error)

        # Password Input Layout with Eye Button
        self.lbl_pass = QLabel("کلمه عبور:")
        
        pass_box = QHBoxLayout()
        pass_box.setSpacing(6)

        self.txt_password = QLineEdit()
        self.txt_password.setFixedHeight(40)
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("کلمه عبور را وارد کنید")
        self.txt_password.returnPressed.connect(self.do_login)
        self.txt_password.textChanged.connect(self.clear_pass_error)

        self.btn_eye = QPushButton("👁️")
        self.btn_eye.setObjectName("eye_button")
        self.btn_eye.setFixedSize(44, 40)
        self.btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eye.setToolTip("نمایش / پنهان‌سازی کلمه عبور")
        self.btn_eye.clicked.connect(lambda: self.toggle_password(self.txt_password, self.btn_eye))

        pass_box.addWidget(self.txt_password)
        pass_box.addWidget(self.btn_eye)

        self.lbl_pass_error = QLabel()
        self.lbl_pass_error.setVisible(False)

        card_layout.addWidget(self.lbl_pass)
        card_layout.addLayout(pass_box)
        card_layout.addWidget(self.lbl_pass_error)

        # Remember Me Checkbox Row
        row_remember = QHBoxLayout()
        row_remember.setSpacing(8)
        self.chk_remember = QCheckBox("مرا به خاطر بسپار")
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.btn_cloud.clicked.connect(self.open_cloud_restore_dialog)
        card_layout.addWidget(self.btn_cloud)
        card_layout.addSpacing(6)

        # Submit Login Button
        self.btn_login = QPushButton("ورود به سیستم")
        self.btn_login.setFixedHeight(44)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setDefault(True)
        self.btn_login.setAutoDefault(True)
        self.btn_login.clicked.connect(self.do_login)
        card_layout.addWidget(self.btn_login)

        main_layout.addWidget(self.card)

    def _apply_theme_style(self):
        """Applies dynamic theme styling to login canvas, card, inputs, buttons, and popups."""
        try:
            palette = ThemeManager.get_current_palette()
        except Exception:
            return

        primary_text = getattr(palette, "text_on_primary", getattr(palette, "primary_text", "#FFFFFF"))

        # 1. Root canvas background (scoped strictly to QWidget#login_view to avoid cascade)
        self.setStyleSheet(f"QWidget#login_view {{ background-color: {palette.bg_base}; }}")

        # 2. Login card container
        if hasattr(self, "card"):
            self.card.setStyleSheet(f"""
                QFrame#login_card {{
                    background-color: {palette.bg_card};
                    border: 1px solid {palette.border};
                    border-radius: 12px;
                    padding: 20px 25px;
                }}
                QLabel {{
                    background-color: transparent;
                    background: transparent;
                }}
            """)

        # 3. Titles & Field labels
        if hasattr(self, "sub_lbl"):
            self.sub_lbl.setStyleSheet(f"color: {palette.text_secondary}; font-size: 14px; font-weight: bold; background: transparent; margin-top: 4px; margin-bottom: 6px;")
        if hasattr(self, "lbl_user"):
            self.lbl_user.setStyleSheet(f"color: {palette.text_primary}; font-weight: bold; background: transparent;")
        if hasattr(self, "lbl_pass"):
            self.lbl_pass.setStyleSheet(f"color: {palette.text_primary}; font-weight: bold; background: transparent;")

        # 4. Inputs
        if hasattr(self, "txt_username"):
            self.txt_username.setStyleSheet(self._get_input_style(palette, is_error=getattr(self, "_user_has_error", False)))
        if hasattr(self, "txt_password"):
            self.txt_password.setStyleSheet(self._get_input_style(palette, is_error=getattr(self, "_pass_has_error", False)))

        # 5. Error labels
        err_color = "#EF4444" if palette.is_dark else "#DC2626"
        if hasattr(self, "lbl_user_error"):
            self.lbl_user_error.setStyleSheet(f"color: {err_color}; font-size: 12px; font-weight: bold; background: transparent; padding: 2px;")
        if hasattr(self, "lbl_pass_error"):
            self.lbl_pass_error.setStyleSheet(f"color: {err_color}; font-size: 12px; font-weight: bold; background: transparent; padding: 2px;")

        # 6. Eye password toggle button
        if hasattr(self, "btn_eye"):
            self.btn_eye.setStyleSheet(f"""
                QPushButton#eye_button {{
                    background-color: {palette.primary};
                    color: {primary_text};
                    border: 1px solid {palette.primary_hover};
                    border-radius: 6px;
                    font-size: 16px;
                    font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton#eye_button:hover {{
                    background-color: {palette.primary_hover};
                }}
            """)

        # 7. Remember Checkbox
        if hasattr(self, "chk_remember"):
            check_icon_path = (config.BASE_DIR / "resources" / "images" / "check.svg").as_posix()
            self.chk_remember.setStyleSheet(f"""
                QCheckBox {{
                    color: {palette.text_secondary};
                    font-size: 13px;
                    font-weight: 500;
                    background: transparent;
                    spacing: 8px;
                }}
                QCheckBox:hover {{
                    color: {palette.text_primary};
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 1px solid {palette.indicator_border};
                    border-radius: 4px;
                    background-color: {palette.indicator_bg};
                }}
                QCheckBox::indicator:hover {{
                    border: 1px solid {palette.primary_hover};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {palette.primary};
                    border: 1px solid {palette.primary_hover};
                    image: url("{check_icon_path}");
                }}
            """)

        # 8. Forgot password button
        if hasattr(self, "btn_forgot"):
            self.btn_forgot.setStyleSheet(f"""
                QPushButton {{
                    background-color: {palette.btn_sec_bg};
                    color: {palette.btn_sec_text};
                    border: 1px solid {palette.btn_sec_border};
                    border-radius: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {palette.btn_sec_hover};
                    color: {palette.text_primary};
                }}
            """)

        # 9. Cloud Restore Button
        if hasattr(self, "btn_cloud"):
            cloud_bg = "#1E3A8A" if palette.is_dark else "#EFF6FF"
            cloud_text = "#93C5FD" if palette.is_dark else "#1D4ED8"
            cloud_border = "#2563EB" if palette.is_dark else "#BFDBFE"
            cloud_hover = "#2563EB" if palette.is_dark else "#DBEAFE"
            self.btn_cloud.setStyleSheet(f"""
                QPushButton {{
                    background-color: {cloud_bg};
                    color: {cloud_text};
                    border: 1px solid {cloud_border};
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {cloud_hover};
                    color: {"#FFFFFF" if palette.is_dark else "#1E40AF"};
                }}
            """)

        # 10. Login Submit Button
        if hasattr(self, "btn_login"):
            self.btn_login.setStyleSheet(f"""
                QPushButton {{
                    background-color: {palette.primary};
                    color: {primary_text};
                    font-size: 15px;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {palette.primary_hover};
                }}
                QPushButton:pressed {{
                    background-color: {palette.primary_pressed};
                }}
            """)

        # 11. Auto-complete popup dropdown
        if hasattr(self, "completer") and self.completer:
            popup = self.completer.popup()
            if popup:
                popup.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                popup_bg = palette.bg_surface if palette.is_dark else "#FFFFFF"
                popup_border = palette.border
                popup_hover = palette.table_item_selected if not palette.is_dark else palette.bg_card
                popup_sel = palette.primary
                popup_sel_txt = palette.primary_text
                popup.setStyleSheet(f"""
                    QListView {{
                        background-color: {popup_bg};
                        color: {palette.text_primary};
                        border: 1px solid {popup_border};
                        border-radius: 6px;
                        selection-background-color: {popup_sel};
                        selection-color: {popup_sel_txt};
                        padding: 4px;
                        font-size: 13px;
                        outline: none;
                    }}
                    QListView::item {{
                        padding: 8px 12px;
                        border-radius: 4px;
                    }}
                    QListView::item:hover {{
                        background-color: {popup_hover};
                        color: {palette.text_primary};
                    }}
                    QListView::item:selected {{
                        background-color: {popup_sel};
                        color: {popup_sel_txt};
                    }}
                """)

        # 12. Register button state styling
        self.refresh_activation_state()

    def clear_user_error(self):
        self._user_has_error = False
        try:
            palette = ThemeManager.get_current_palette()
            self.txt_username.setStyleSheet(self._get_input_style(palette, is_error=False))
        except Exception:
            pass
        self.lbl_user_error.setText("")
        self.lbl_user_error.setVisible(False)

    def clear_pass_error(self):
        self._pass_has_error = False
        try:
            palette = ThemeManager.get_current_palette()
            self.txt_password.setStyleSheet(self._get_input_style(palette, is_error=False))
        except Exception:
            pass
        self.lbl_pass_error.setText("")
        self.lbl_pass_error.setVisible(False)

    def refresh_activation_state(self):
        active = is_app_license_active()
        try:
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        if not hasattr(self, "btn_register"):
            return

        if active:
            self.btn_register.setEnabled(True)
            self.btn_register.setToolTip("ثبت‌نام مربی جدید در سیستم")
            if palette and not palette.is_dark:
                reg_bg = "#ECFDF5"
                reg_text = "#047857"
                reg_border = "#A7F3D0"
                reg_hover = "#D1FAE5"
            else:
                reg_bg = "#065F46"
                reg_text = "#A7F3D0"
                reg_border = "#059669"
                reg_hover = "#047857"

            self.btn_register.setStyleSheet(f"""
                QPushButton {{
                    background-color: {reg_bg};
                    color: {reg_text};
                    border: 1px solid {reg_border};
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {reg_hover};
                    color: {"#FFFFFF" if (not palette or palette.is_dark) else "#065F46"};
                }}
            """)
        else:
            self.btn_register.setEnabled(False)
            self.btn_register.setToolTip("⚠️ ثبت‌نام مربی جدید در حال حاضر غیرفعال است.\nجهت فعال‌سازی، ابتدا ادمین کل باید وضعیت برنامه را فعال کند.")
            dis_bg = palette.btn_sec_bg if palette else ("#F1F5F9" if not palette or not palette.is_dark else "#262626")
            dis_text = palette.text_muted if palette else ("#94A3B8" if not palette or not palette.is_dark else "#666666")
            dis_border = palette.border if palette else ("#CBD5E1" if not palette or not palette.is_dark else "#333333")

            self.btn_register.setStyleSheet(f"""
                QPushButton {{
                    background-color: {dis_bg};
                    color: {dis_text};
                    border: 1px solid {dis_border};
                    border-radius: 6px;
                    font-size: 12px;
                }}
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

        try:
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        if not username:
            self._user_has_error = True
            if palette:
                self.txt_username.setStyleSheet(self._get_input_style(palette, is_error=True))
            self.lbl_user_error.setText("❌ لطفاً نام کاربری را وارد کنید.")
            self.lbl_user_error.setVisible(True)
            self.txt_username.setFocus()
            return

        if not password:
            self._pass_has_error = True
            if palette:
                self.txt_password.setStyleSheet(self._get_input_style(palette, is_error=True))
            self.lbl_pass_error.setText("❌ لطفاً کلمه عبور را وارد کنید.")
            self.lbl_pass_error.setVisible(True)
            self.txt_password.setFocus()
            return

        target_user = username if check_username_exists(username) else (raw_username if check_username_exists(raw_username) else None)
        if not target_user:
            self._user_has_error = True
            if palette:
                self.txt_username.setStyleSheet(self._get_input_style(palette, is_error=True))
            self.lbl_user_error.setText("❌ چنین نام کاربری در سیستم وجود ندارد.")
            self.lbl_user_error.setVisible(True)
            self.txt_username.setFocus()
            return

        # Check Hardware License: if app is not active on this machine and user is NOT admin, block login!
        if target_user != "admin" and not is_app_license_active():
            self._user_has_error = True
            if palette:
                self.txt_username.setStyleSheet(self._get_input_style(palette, is_error=True))
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
            self._pass_has_error = True
            if palette:
                self.txt_password.setStyleSheet(self._get_input_style(palette, is_error=True))
            self.lbl_pass_error.setText("❌ رمز عبور اشتباه است.")
            self.lbl_pass_error.setVisible(True)
            self.txt_password.setFocus()
