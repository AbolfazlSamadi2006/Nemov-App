import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import config
from nemov.auth.authentication import register_trainer, CurrentUser
from nemov.views.components.jalali_calendar_widget import JalaliDatePicker
from nemov.views.components.field_validator import (
    MicroWarningLabel, validate_phone, validate_birthdate_age
)
from nemov.utils.image_utils import get_circular_pixmap
from nemov.utils.theme_manager import ThemeManager



class TrainerRegisterDialog(QDialog):
    registration_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ثبت‌نام مربی جدید - نرم‌افزار مدیریت ورزشی نِمُو (Nemov)")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 800
        self.setFixedSize(540, min(680, max(540, avail_h - 36)))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.selected_photo_path = None
        self.init_ui()

    def init_ui(self):
        palette = ThemeManager.get_current_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # Header Title
        title_lbl = QLabel("📝 ثبت‌نام مربی جدید در سیستم")
        title_lbl.setObjectName("h1")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        # Scroll Area for inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        form_layout = QVBoxLayout(scroll_widget)
        form_layout.setSpacing(8)

        # Row 1: First Name & Last Name
        row_name = QHBoxLayout()
        row_name.setSpacing(10)

        v1 = QVBoxLayout()
        v1.addWidget(QLabel("نام مربی:"))
        self.txt_first_name = QLineEdit()
        self.txt_first_name.setFixedHeight(38)
        self.txt_first_name.setPlaceholderText("نام")
        v1.addWidget(self.txt_first_name)

        v2 = QVBoxLayout()
        v2.addWidget(QLabel("نام خانوادگی:"))
        self.txt_last_name = QLineEdit()
        self.txt_last_name.setFixedHeight(38)
        self.txt_last_name.setPlaceholderText("نام خانوادگی")
        v2.addWidget(self.txt_last_name)

        row_name.addLayout(v1)
        row_name.addLayout(v2)
        form_layout.addLayout(row_name)

        # Row 2: Phone & Birthdate
        row_contact = QHBoxLayout()
        row_contact.setSpacing(10)

        v3 = QVBoxLayout()
        v3.addWidget(QLabel("شماره همراه:"))
        self.txt_phone = QLineEdit()
        self.txt_phone.setFixedHeight(38)
        self.txt_phone.setPlaceholderText("09123456789")
        self.txt_phone.setMaxLength(11)
        v3.addWidget(self.txt_phone)
        self.lbl_phone_warn = MicroWarningLabel()
        v3.addWidget(self.lbl_phone_warn)
        self.txt_phone.editingFinished.connect(self._validate_phone)

        v4 = QVBoxLayout()
        v4.addWidget(QLabel("تاریخ تولد (شمسی):"))
        self.picker_birth_date = JalaliDatePicker(default_today=False)
        self.picker_birth_date.setFixedHeight(38)
        v4.addWidget(self.picker_birth_date)
        self.lbl_birth_warn = MicroWarningLabel()
        v4.addWidget(self.lbl_birth_warn)
        self.picker_birth_date.date_changed.connect(self._validate_birth)


        row_contact.addLayout(v3)
        row_contact.addLayout(v4)
        form_layout.addLayout(row_contact)

        # Email Field (Optional / Recommended for recovery and backup)
        form_layout.addWidget(QLabel("آدرس ایمیل مربی (جهت بازیابی رمز و دریافت فایل پشتیبان):"))
        self.txt_email = QLineEdit()
        self.txt_email.setFixedHeight(38)
        self.txt_email.setPlaceholderText("مثال: coach@example.com (اختیاری اما توصیه‌شده)")
        form_layout.addWidget(self.txt_email)

        # Row 3: Photo Selection Preview
        photo_box = QHBoxLayout()
        photo_box.setSpacing(12)

        self.lbl_photo_preview = QLabel("📷 بدون عکس")
        self.lbl_photo_preview.setFixedSize(60, 60)
        self.lbl_photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo_preview.setStyleSheet(f"border: 1px dashed {palette.border}; border-radius: 30px; color: {palette.text_secondary}; font-size: 11px;")

        btn_select_photo = QPushButton("📷 انتخاب / ثبت عکس مربی (اختیاری)")
        btn_select_photo.setFixedHeight(38)
        btn_select_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_photo.setObjectName("secondary_button")
        btn_select_photo.clicked.connect(self.choose_photo)

        photo_box.addWidget(self.lbl_photo_preview)
        photo_box.addWidget(btn_select_photo)
        form_layout.addLayout(photo_box)

        # Row 4: Username
        form_layout.addWidget(QLabel("نام کاربری مربی (جهت ورود):"))
        self.txt_username = QLineEdit()
        self.txt_username.setFixedHeight(38)
        self.txt_username.setPlaceholderText("نام کاربری انگلیسی")
        form_layout.addWidget(self.txt_username)

        # Row 5: Password & Confirm Password
        form_layout.addWidget(QLabel("کلمه عبور:"))
        pass1_box = QHBoxLayout()
        pass1_box.setSpacing(6)
        self.txt_password = QLineEdit()
        self.txt_password.setFixedHeight(38)
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("کلمه عبور جدید")

        btn_eye1 = QPushButton("👁️")
        btn_eye1.setFixedSize(42, 38)
        btn_eye1.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye1.setObjectName("secondary_button")
        btn_eye1.clicked.connect(lambda: self.toggle_eye(self.txt_password, btn_eye1))

        pass1_box.addWidget(self.txt_password)
        pass1_box.addWidget(btn_eye1)
        form_layout.addLayout(pass1_box)

        form_layout.addWidget(QLabel("تکرار کلمه عبور:"))
        pass2_box = QHBoxLayout()
        pass2_box.setSpacing(6)
        self.txt_password_confirm = QLineEdit()
        self.txt_password_confirm.setFixedHeight(38)
        self.txt_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password_confirm.setPlaceholderText("تکرار کلمه عبور")

        btn_eye2 = QPushButton("👁️")
        btn_eye2.setFixedSize(42, 38)
        btn_eye2.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye2.setObjectName("secondary_button")
        btn_eye2.clicked.connect(lambda: self.toggle_eye(self.txt_password_confirm, btn_eye2))

        pass2_box.addWidget(self.txt_password_confirm)
        pass2_box.addWidget(btn_eye2)
        form_layout.addLayout(pass2_box)

        self.lbl_pass_confirm_error = QLabel()
        self.lbl_pass_confirm_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; background: transparent; padding: 2px;")
        self.lbl_pass_confirm_error.setVisible(False)
        self.txt_password_confirm.textChanged.connect(self.clear_pass_confirm_error)
        self.txt_password.textChanged.connect(self.clear_pass_confirm_error)
        form_layout.addWidget(self.lbl_pass_confirm_error)

        # Row 6: Recovery Code & Confirm Recovery Code
        form_layout.addWidget(QLabel("رمز ریکاوری مخفی (جهت فراموشی رمز):"))
        rec1_box = QHBoxLayout()
        rec1_box.setSpacing(6)
        self.txt_recovery_code = QLineEdit()
        self.txt_recovery_code.setFixedHeight(38)
        self.txt_recovery_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_recovery_code.setPlaceholderText("یک رمز مخفی یا PIN چند رقمی یادداشت کنید")

        btn_eye3 = QPushButton("👁️")
        btn_eye3.setFixedSize(42, 38)
        btn_eye3.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye3.setObjectName("secondary_button")
        btn_eye3.clicked.connect(lambda: self.toggle_eye(self.txt_recovery_code, btn_eye3))

        rec1_box.addWidget(self.txt_recovery_code)
        rec1_box.addWidget(btn_eye3)
        form_layout.addLayout(rec1_box)

        form_layout.addWidget(QLabel("تکرار رمز ریکاوری مخفی:"))
        rec2_box = QHBoxLayout()
        rec2_box.setSpacing(6)
        self.txt_recovery_confirm = QLineEdit()
        self.txt_recovery_confirm.setFixedHeight(38)
        self.txt_recovery_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_recovery_confirm.setPlaceholderText("تکرار رمز مخفی")

        btn_eye4 = QPushButton("👁️")
        btn_eye4.setFixedSize(42, 38)
        btn_eye4.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye4.setObjectName("secondary_button")
        btn_eye4.clicked.connect(lambda: self.toggle_eye(self.txt_recovery_confirm, btn_eye4))

        rec2_box.addWidget(self.txt_recovery_confirm)
        rec2_box.addWidget(btn_eye4)
        form_layout.addLayout(rec2_box)

        self.lbl_rec_confirm_error = QLabel()
        self.lbl_rec_confirm_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; background: transparent; padding: 2px;")
        self.lbl_rec_confirm_error.setVisible(False)
        self.txt_recovery_confirm.textChanged.connect(self.clear_rec_confirm_error)
        self.txt_recovery_code.textChanged.connect(self.clear_rec_confirm_error)
        form_layout.addWidget(self.lbl_rec_confirm_error)


        scroll.setWidget(scroll_widget)
        card_layout.addWidget(scroll)

        # Cloud Restore Helper Button
        btn_cloud_help = QPushButton("☁️ اگر در سیستم دیگری حساب دارید: بازیابی با شماره موبایل")
        btn_cloud_help.setFixedHeight(34)
        btn_cloud_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cloud_help.setObjectName("secondary_button")
        btn_cloud_help.clicked.connect(self.restore_from_cloud_dialog)
        card_layout.addWidget(btn_cloud_help)

        # Submit Register Button
        btn_submit = QPushButton("🚀 تکمیل و ثبت‌نام مربی")
        btn_submit.setFixedHeight(44)
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setObjectName("primary_button")
        btn_submit.clicked.connect(self.do_register)
        card_layout.addWidget(btn_submit)

        layout.addWidget(card)

    def restore_from_cloud_dialog(self):
        from nemov.views.cloud_restore_dialog import CloudRestoreDialog
        dlg = CloudRestoreDialog(self, initial_phone=self.txt_phone.text().strip())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.registration_success.emit()
            self.accept()

    def toggle_eye(self, field: QLineEdit, btn: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁️")

    def choose_photo(self):
        from nemov.utils.image_source_chooser import get_image_file_path
        temp_path = get_image_file_path(
            self,
            dialog_title="انتخاب یا ثبت تصویر مربی",
            file_filter="فایل‌های تصویری (*.png *.jpg *.jpeg *.bmp *.webp)",
            is_square_default=True
        )
        if temp_path and os.path.exists(temp_path):
            # Copy to profile-photos directory
            dest_dir = config.PROFILE_PHOTOS_DIR
            dest_dir.mkdir(parents=True, exist_ok=True)
            ext = Path(temp_path).suffix or ".jpg"
            import uuid
            filename = f"trainer_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = dest_dir / filename
            import shutil
            shutil.copy2(temp_path, dest_path)
            self.selected_photo_path = str(dest_path)

            pixmap = QPixmap(str(dest_path))
            circ_pixmap = get_circular_pixmap(pixmap, 60)
            self.lbl_photo_preview.setPixmap(circ_pixmap)
            self.lbl_photo_preview.setText("")
            self.lbl_photo_preview.setStyleSheet("border: none; background: transparent;")

    def clear_pass_confirm_error(self):
        self.txt_password_confirm.setStyleSheet("")
        self.lbl_pass_confirm_error.setText("")
        self.lbl_pass_confirm_error.setVisible(False)

    def clear_rec_confirm_error(self):
        self.txt_recovery_confirm.setStyleSheet("")
        self.lbl_rec_confirm_error.setText("")
        self.lbl_rec_confirm_error.setVisible(False)

    def _validate_phone(self):
        err = validate_phone(self.txt_phone.text())
        self.lbl_phone_warn.show_warning(err)
        return err is None

    def _validate_birth(self):
        err = validate_birthdate_age(self.picker_birth_date.text())
        self.lbl_birth_warn.show_warning(err)
        return err is None

    def do_register(self):
        self._validate_phone()
        self._validate_birth()
        try:
            self.clear_pass_confirm_error()
            self.clear_rec_confirm_error()

            first_name = self.txt_first_name.text().strip()
            last_name = self.txt_last_name.text().strip()
            phone = self.txt_phone.text().strip()
            birth_date = self.picker_birth_date.get_date()
            username = self.txt_username.text().strip()
            password = self.txt_password.text().strip()
            confirm_password = self.txt_password_confirm.text().strip()
            recovery_code = self.txt_recovery_code.text().strip()
            confirm_recovery = self.txt_recovery_confirm.text().strip()

            if not first_name or not last_name or not phone or not username or not password or not recovery_code:
                QMessageBox.warning(self, "خطا در فرم ثبت‌نام", "لطفاً تمامی فیلدهای نام، نام خانوادگی، شماره موبایل، نام کاربری، کلمه عبور و رمز ریکاوری را تکمیل کنید.")
                return

            phone_digits = "".join(filter(str.isdigit, phone.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))))
            if len(phone_digits) > 11:
                QMessageBox.warning(
                    self,
                    "خطا در شماره تلفن",
                    "شماره تماس نمی‌تواند بیشتر از ۱۱ رقم باشد."
                )
                self.txt_phone.setFocus()
                return

            ERROR_STYLE = """
                QLineEdit {
                    background-color: #2D1515;
                    color: #FFAAAA;
                    border: 1.5px solid #EF4444;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1.5px solid #FF4444;
                }
            """

            if password != confirm_password:
                self.txt_password_confirm.setStyleSheet(ERROR_STYLE)
                self.lbl_pass_confirm_error.setText("❌ رمزهای عبور با یکدیگر مغایرت دارند.")
                self.lbl_pass_confirm_error.setVisible(True)
                self.txt_password_confirm.setFocus()
                return

            if recovery_code != confirm_recovery:
                self.txt_recovery_confirm.setStyleSheet(ERROR_STYLE)
                self.lbl_rec_confirm_error.setText("❌ رمزهای ریکاوری با یکدیگر مغایرت دارند.")
                self.lbl_rec_confirm_error.setVisible(True)
                self.txt_recovery_confirm.setFocus()
                return

            email = self.txt_email.text().strip()

            user = register_trainer(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                birth_date_shamsi=birth_date,
                username=username,
                password=password,
                recovery_code=recovery_code,
                photo_path=self.selected_photo_path,
                email=email
            )
            CurrentUser.set(user)
            QMessageBox.information(self, "ثبت‌نام موفقیت‌آمیز", f"حساب کاربری مربی با موفقیت ایجاد شد! خوش آمدید {user.display_name} 🌸")
            self.registration_success.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا در ثبت‌نام", str(e))

