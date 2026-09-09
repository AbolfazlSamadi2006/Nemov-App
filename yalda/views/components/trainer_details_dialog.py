import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit, QMessageBox, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

import config
from yalda.utils.image_utils import get_circular_pixmap
from yalda.auth.authentication import update_trainer_profile


class TrainerDetailsDialog(QDialog):
    """Dialog to display full trainer profile details and allow Admin to reset trainer password."""

    def __init__(self, parent=None, trainer_data: dict = None):
        super().__init__(parent)
        self.trainer_data = trainer_data or {}
        self.setWindowTitle(f"مشخصات کامل مربی - {self.trainer_data.get('full_name', '')}")
        self.setFixedWidth(560)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #FFFFFF;
                font-family: 'Vazirmatn', 'Segoe UI', sans-serif;
            }
            QFrame#cardFrame {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 12px;
                padding: 18px;
            }
            QLabel {
                color: #E5E7EB;
                background: transparent;
            }
            QLineEdit {
                background-color: #27272A;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #DC2626;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        # ----------------------------------------------------
        # 1. Header: Avatar + Name + Role Badge
        # ----------------------------------------------------
        header_box = QHBoxLayout()
        header_box.setSpacing(14)

        lbl_avatar = QLabel()
        lbl_avatar.setFixedSize(70, 70)
        lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        photo_path = self.trainer_data.get("photo_path", "")
        if photo_path and os.path.exists(photo_path):
            pix = QPixmap(photo_path)
            circ = get_circular_pixmap(pix, 70)
            lbl_avatar.setPixmap(circ)
            lbl_avatar.setStyleSheet("border: none; background: transparent;")
        else:
            lbl_avatar.setText("👤")
            lbl_avatar.setStyleSheet("""
                background-color: #27272A;
                border: 2px solid #3F3F46;
                border-radius: 35px;
                font-size: 32px;
                color: #9CA3AF;
            """)
        header_box.addWidget(lbl_avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        lbl_name = QLabel(self.trainer_data.get("full_name", "-"))
        lbl_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        name_box.addWidget(lbl_name)

        lbl_role = QLabel("🏋️ مربی رسمی باشگاه ورزشی یلدا")
        lbl_role.setStyleSheet("font-size: 12px; color: #10B981; font-weight: bold;")
        name_box.addWidget(lbl_role)

        header_box.addLayout(name_box)
        header_box.addStretch()
        card_layout.addLayout(header_box)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background-color: #27272A; max-height: 1px;")
        card_layout.addWidget(sep1)

        # ----------------------------------------------------
        # 2. Details Grid
        # ----------------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        LABEL_STYLE = "color: #9CA3AF; font-size: 13px; font-weight: bold;"
        VALUE_STYLE = "color: #F3F4F6; font-size: 13px;"

        def add_row(r: int, title: str, val_widget):
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet(LABEL_STYLE)
            lbl_t.setFixedWidth(130)
            grid.addWidget(lbl_t, r, 0)
            if isinstance(val_widget, str):
                w = QLabel(val_widget)
                w.setStyleSheet(VALUE_STYLE)
                grid.addWidget(w, r, 1)
            else:
                grid.addWidget(val_widget, r, 1)

        # Row 0: Username
        add_row(0, "نام کاربری (ورود):", self.trainer_data.get("username", "-"))

        # Row 1: Password with Eye Button
        pass_code = self.trainer_data.get("password") or "-"
        pass_box = QHBoxLayout()
        pass_box.setSpacing(6)

        self.txt_display_pass = QLineEdit(pass_code)
        self.txt_display_pass.setReadOnly(True)
        self.txt_display_pass.setFixedHeight(34)

        if pass_code != "-":
            self.txt_display_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_display_pass.setStyleSheet("""
                QLineEdit {
                    background-color: #202023; border: 1px solid #3F3F46; border-radius: 6px; padding: 4px 10px; font-weight: bold; color: #10B981;
                }
            """)
            btn_eye_pass = QPushButton("👁️")
            btn_eye_pass.setFixedSize(38, 34)
            btn_eye_pass.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eye_pass.setStyleSheet("""
                QPushButton {
                    background-color: #27272A; color: white; border: 1px solid #3F3F46; border-radius: 6px; font-size: 15px;
                }
                QPushButton:hover { background-color: #3F3F46; }
            """)
            btn_eye_pass.clicked.connect(lambda: self._toggle_eye(self.txt_display_pass, btn_eye_pass))
            pass_box.addWidget(self.txt_display_pass)
            pass_box.addWidget(btn_eye_pass)
        else:
            self.txt_display_pass.setStyleSheet("background-color: #202023; border: 1px solid #3F3F46; border-radius: 6px; padding: 4px 10px; color: #9CA3AF;")
            pass_box.addWidget(self.txt_display_pass)

        pass_widget = QFrame()
        pass_widget.setLayout(pass_box)
        pass_widget.setStyleSheet("background: transparent; border: none;")
        add_row(1, "رمز عبور (ورود):", pass_widget)

        # Row 2: Phone
        add_row(2, "شماره تماس همراه:", self.trainer_data.get("phone", "-"))

        # Row 3: Email
        email_val = self.trainer_data.get("email", "-")
        lbl_email = QLabel(email_val)
        lbl_email.setStyleSheet(VALUE_STYLE if email_val != "-" else "color: #6B7280; font-size: 13px;")
        add_row(3, "آدرس ایمیل مربی:", lbl_email)

        # Row 4: Birth Date
        add_row(4, "تاریخ تولد (شمسی):", self.trainer_data.get("birth_date_shamsi", "-"))

        # Row 5: Member Count
        member_cnt = self.trainer_data.get("member_count", 0)
        lbl_mem = QLabel(f"{member_cnt} نفر ورزشکار تحت پوشش")
        lbl_mem.setStyleSheet("color: #60A5FA; font-weight: bold; font-size: 13px;")
        add_row(5, "تعداد شاگردان:", lbl_mem)

        # Row 6: Secret Recovery Code with Eye Button
        rec_code = self.trainer_data.get("recovery_code", "-")
        rec_box = QHBoxLayout()
        rec_box.setSpacing(6)

        self.txt_display_rec = QLineEdit(rec_code)
        self.txt_display_rec.setReadOnly(True)
        self.txt_display_rec.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_display_rec.setFixedHeight(34)
        self.txt_display_rec.setStyleSheet("""
            QLineEdit {
                background-color: #202023; border: 1px solid #3F3F46; border-radius: 6px; padding: 4px 10px; font-weight: bold; color: #F59E0B;
            }
        """)

        btn_eye_rec = QPushButton("👁️")
        btn_eye_rec.setFixedSize(38, 34)
        btn_eye_rec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_rec.setStyleSheet("""
            QPushButton {
                background-color: #27272A; color: white; border: 1px solid #3F3F46; border-radius: 6px; font-size: 15px;
            }
            QPushButton:hover { background-color: #3F3F46; }
        """)
        btn_eye_rec.clicked.connect(lambda: self._toggle_eye(self.txt_display_rec, btn_eye_rec))

        rec_box.addWidget(self.txt_display_rec)
        rec_box.addWidget(btn_eye_rec)
        rec_widget = QFrame()
        rec_widget.setLayout(rec_box)
        rec_widget.setStyleSheet("background: transparent; border: none;")
        add_row(6, "رمز ریکاوری مخفی:", rec_widget)

        card_layout.addLayout(grid)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background-color: #27272A; max-height: 1px;")
        card_layout.addWidget(sep2)

        # ----------------------------------------------------
        # 3. Password Security & Admin Password Reset
        # ----------------------------------------------------
        pass_card = QFrame()
        pass_card.setStyleSheet("background-color: #202023; border: 1px solid #27272A; border-radius: 8px; padding: 10px;")
        pass_layout = QVBoxLayout(pass_card)
        pass_layout.setSpacing(8)

        lbl_pass_info = QLabel("🔐 وضعیت کلمه عبور: رمزنگاری‌شده با هش یک‌طرفه امن SHA-256 (غیرقابل دسترسی مستقیم جهت امنیت)")
        lbl_pass_info.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        lbl_pass_info.setWordWrap(True)
        pass_layout.addWidget(lbl_pass_info)

        self.btn_toggle_reset_pass = QPushButton("🔑 تعیین / تغییر کلمه عبور این مربی توسط مدیر")
        self.btn_toggle_reset_pass.setFixedHeight(36)
        self.btn_toggle_reset_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_reset_pass.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB; border-radius: 6px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563EB; color: #FFFFFF;
            }
        """)
        self.btn_toggle_reset_pass.clicked.connect(self._toggle_reset_password_box)
        pass_layout.addWidget(self.btn_toggle_reset_pass)

        # Expandable Reset Password Box
        self.reset_pass_box = QFrame()
        self.reset_pass_box.setStyleSheet("background: transparent; border: none;")
        reset_layout = QVBoxLayout(self.reset_pass_box)
        reset_layout.setContentsMargins(0, 4, 0, 0)
        reset_layout.setSpacing(8)

        reset_layout.addWidget(QLabel("کلمه عبور جدید برای این مربی:"))
        row_new_pass = QHBoxLayout()
        row_new_pass.setSpacing(6)

        self.txt_admin_new_pass = QLineEdit()
        self.txt_admin_new_pass.setFixedHeight(36)
        self.txt_admin_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_admin_new_pass.setPlaceholderText("کلمه عبور جدید را وارد کنید...")

        btn_eye_new = QPushButton("👁️")
        btn_eye_new.setFixedSize(38, 36)
        btn_eye_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_new.setStyleSheet("""
            QPushButton {
                background-color: #27272A; color: white; border: 1px solid #3F3F46; border-radius: 6px; font-size: 15px;
            }
            QPushButton:hover { background-color: #3F3F46; }
        """)
        btn_eye_new.clicked.connect(lambda: self._toggle_eye(self.txt_admin_new_pass, btn_eye_new))

        row_new_pass.addWidget(self.txt_admin_new_pass)
        row_new_pass.addWidget(btn_eye_new)
        reset_layout.addLayout(row_new_pass)

        self.btn_save_new_pass = QPushButton("💾 ذخیره کلمه عبور جدید")
        self.btn_save_new_pass.setFixedHeight(36)
        self.btn_save_new_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_new_pass.setStyleSheet("""
            QPushButton {
                background-color: #059669; color: white; border-radius: 6px; font-weight: bold; font-size: 12px; border: none;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.btn_save_new_pass.clicked.connect(self._save_new_password)
        reset_layout.addWidget(self.btn_save_new_pass)

        pass_layout.addWidget(self.reset_pass_box)
        self.reset_pass_box.setVisible(False)

        card_layout.addWidget(pass_card)
        layout.addWidget(card)

        # ----------------------------------------------------
        # Close Button
        # ----------------------------------------------------
        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #27272A; color: #D1D5DB; border: 1px solid #3F3F46; border-radius: 6px; font-size: 13px; padding: 4px 20px;
            }
            QPushButton:hover {
                background-color: #3F3F46; color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def _toggle_eye(self, field: QLineEdit, btn: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁️")

    def _toggle_reset_password_box(self):
        visible = not self.reset_pass_box.isVisible()
        self.reset_pass_box.setVisible(visible)
        if visible:
            self.txt_admin_new_pass.setFocus()
            self.adjustSize()

    def _save_new_password(self):
        new_pass = self.txt_admin_new_pass.text().strip()
        if not new_pass:
            QMessageBox.warning(self, "خطا", "لطفاً کلمه عبور جدید را وارد کنید.")
            return

        trainer_id = self.trainer_data.get("id")
        if not trainer_id:
            QMessageBox.critical(self, "خطا", "شناسه مربی یافت نشد.")
            return

        try:
            update_trainer_profile(
                user_id=trainer_id,
                first_name=self.trainer_data.get("first_name"),
                last_name=self.trainer_data.get("last_name"),
                phone=self.trainer_data.get("phone"),
                email=self.trainer_data.get("email"),
                birth_date_shamsi=self.trainer_data.get("birth_date_shamsi"),
                photo_path=self.trainer_data.get("photo_path"),
                username=self.trainer_data.get("username"),
                password=new_pass
            )
            QMessageBox.information(
                self,
                "موفقیت",
                f"کلمه عبور جدید برای مربی «{self.trainer_data.get('full_name')}» با موفقیت تنظیم و ذخیره شد."
            )
            self.trainer_data["password"] = new_pass
            self.txt_display_pass.setText(new_pass)
            self.txt_display_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.txt_display_pass.setStyleSheet("""
                QLineEdit {
                    background-color: #202023; border: 1px solid #3F3F46; border-radius: 6px; padding: 4px 10px; font-weight: bold; color: #10B981;
                }
            """)
            self.txt_admin_new_pass.clear()
            self.reset_pass_box.setVisible(False)
            self.adjustSize()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت کلمه عبور جدید: {str(e)}")
