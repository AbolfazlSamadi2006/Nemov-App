from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from yalda.auth.authentication import CurrentUser
from yalda.services.backup_service import (
    create_local_backup, export_offline_backup, upload_cloud_backup, is_internet_connected
)
from yalda.utils.jalali_date import gregorian_to_shamsi


class ExitBackupDialog(QDialog):
    def __init__(self, parent=None, is_logout: bool = False):
        super().__init__(parent)
        self.is_logout = is_logout
        self.setWindowTitle("پشتیبان‌گیری و خروج از حساب" if self.is_logout else "پشتیبان‌گیری و خروج از برنامه")
        self.setFixedWidth(520)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header Title
        lbl_title = QLabel("💾 پشتیبان‌گیری و خروج از حساب" if self.is_logout else "💾 پشتیبان‌گیری و خروج از نرم‌افزار")
        lbl_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
        """)
        layout.addWidget(lbl_title)

        # Question prompt
        msg_text = "آیا مایل به تهیه نسخه پشتیبان از اطلاعات باشگاه پیش از خروج از حساب کاربری هستید؟" if self.is_logout else "آیا مایل به تهیه نسخه پشتیبان از اطلاعات باشگاه پیش از خروج هستید؟"
        lbl_msg = QLabel(msg_text)
        lbl_msg.setStyleSheet("color: #E0E0E0; font-size: 14px;")
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg)

        layout.addSpacing(4)

        # ----------------------------------------------------
        # Action Buttons
        # ----------------------------------------------------
        # 1. Cloud Online Backup
        self.btn_cloud = QPushButton("☁️ ذخیره در سرور ابری (آنلاین)")
        self.btn_cloud.setFixedHeight(46)
        self.btn_cloud.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cloud.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                text-align: center;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.btn_cloud.clicked.connect(self.handle_cloud_backup)
        layout.addWidget(self.btn_cloud)

        # 2. Offline Custom Path Backup
        self.btn_offline = QPushButton("💻 ذخیره در کامپیوتر (آفلاین)")
        self.btn_offline.setFixedHeight(46)
        self.btn_offline.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_offline.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                text-align: center;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_offline.clicked.connect(self.handle_offline_backup)
        layout.addWidget(self.btn_offline)

        # 3. Regular Exit (Only Local Save)
        self.btn_normal_exit = QPushButton("🚪 خیر")
        self.btn_normal_exit.setFixedHeight(42)
        self.btn_normal_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_normal_exit.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #F3F4F6;
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                border: 1px solid #4B5563;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.btn_normal_exit.clicked.connect(self.handle_normal_exit)
        layout.addWidget(self.btn_normal_exit)

        # 4. Cancel (Return to App)
        self.btn_cancel = QPushButton("بازگشت و انصراف")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9CA3AF;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                color: #E5E7EB;
                text-decoration: underline;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

    def handle_cloud_backup(self):
        # 1. Check Internet
        if not is_internet_connected():
            QMessageBox.warning(
                self,
                "قطع اتصال اینترنت",
                "⚠️ سیستم شما به اینترنت متصل نیست!\n\nلطفاً ابتدا سیستم خود را به اینترنت متصل نمایید و سپس دکمه «ذخیره در سرور ابری» را فشار دهید."
            )
            return

        u = CurrentUser.get()
        phone = u.phone if (u and u.phone) else "09336427711"
        trainer_name = u.full_name if u else "مدیر باشگاه"

        self.btn_cloud.setEnabled(False)
        self.btn_cloud.setText("⏳ در حال ارسال به سرور ابری...")

        success, msg = upload_cloud_backup(trainer_phone=phone, trainer_name=trainer_name)
        self.btn_cloud.setEnabled(True)
        self.btn_cloud.setText("☁️ ذخیره در سرور ابری (آنلاین)")

        if success:
            QMessageBox.information(self, "موفقیت", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "خطا در پشتیبان‌گیری ابری", f"{msg}\n\nاطلاعات شما همچنان در حافظه لوکال سیستم ذخیره شده است.")

    def handle_offline_backup(self):
        now = datetime.now()
        shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
        time_str = now.strftime("%H-%M-%S")
        suggested_name = f"Yalda_Backup_{shamsi_date}_{time_str}.db"

        target_file, _ = QFileDialog.getSaveFileName(
            self,
            "انتخاب مسیر ذخیره نسخه پشتیبان",
            suggested_name,
            "SQLite Database (*.db);;All Files (*.*)"
        )

        if not target_file:
            return

        if export_offline_backup(target_file):
            QMessageBox.information(self, "موفقیت", f"نسخه پشتیبان با موفقیت در مسیر زیر ذخیره شد:\n{target_file}")
            self.accept()
        else:
            QMessageBox.critical(self, "خطا", "خطا در استخراج فایل پشتیبان.")

    def handle_normal_exit(self):
        create_local_backup()
        self.accept()