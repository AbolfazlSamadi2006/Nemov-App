from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from yalda.services.backup_service import download_and_restore_cloud_backup
from yalda.auth.authentication import CurrentUser, get_all_trainers


class CloudRestoreDialog(QDialog):
    restore_success = pyqtSignal()

    def __init__(self, parent=None, initial_phone: str = ""):
        super().__init__(parent)
        self.setWindowTitle("☁️ بازیابی اطلاعات از سرور ابری - باشگاه یلدا")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(460, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.initial_phone = initial_phone
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #FFFFFF;
                font-family: 'Vazirmatn', 'Segoe UI', sans-serif;
            }
            QFrame#cardFrame {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 15px;
            }
            QLabel {
                color: #E5E7EB;
                background: transparent;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2563EB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("cardFrame")
        card_l = QVBoxLayout(card)
        card_l.setSpacing(12)

        title = QLabel("☁️ بازیابی خودکار اطلاعات از سرور ابری")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #3B82F6;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_l.addWidget(title)

        desc = QLabel(
            "اگر برنامه را در سیستم جدید نصب کرده‌اید یا قصد بازگردانی اطلاعات را دارید، "
            "شماره موبایل ثبت‌شده خود را وارد کنید تا آخرین نسخه پشتیبان از سرور ابری دریافت و بارگذاری شود:"
        )
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px; line-height: 1.5;")
        desc.setWordWrap(True)
        card_l.addWidget(desc)

        card_l.addWidget(QLabel("شماره همراه مربی:"))
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("09123456789")
        self.txt_phone.setMaxLength(11)
        self.txt_phone.setText(self.initial_phone)
        self.txt_phone.setFixedHeight(40)
        self.txt_phone.returnPressed.connect(self.do_restore)
        card_l.addWidget(self.txt_phone)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #F59E0B;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_l.addWidget(self.lbl_status)

        # Action buttons
        btn_box = QHBoxLayout()
        self.btn_submit = QPushButton("📥 دریافت و بارگذاری از سرور")
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.btn_submit.clicked.connect(self.do_restore)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #D1D5DB;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(self.btn_submit)
        btn_box.addWidget(btn_cancel)
        card_l.addLayout(btn_box)

        layout.addWidget(card)

    def do_restore(self):
        phone = self.txt_phone.text().strip()
        if not phone:
            QMessageBox.warning(self, "خطا", "لطفاً شماره موبایل مربی را وارد کنید.")
            return

        self.lbl_status.setText("⏳ در حال برقراری ارتباط با سرور ابری و دریافت آخرین نسخه پشتیبان...")
        self.btn_submit.setEnabled(False)
        self.repaint()

        success, msg = download_and_restore_cloud_backup(phone)
        self.btn_submit.setEnabled(True)

        if success:
            self.lbl_status.setText("✅ بازیابی با موفقیت انجام شد.")
            
            # Check if a trainer user is present in the restored DB
            trainers = get_all_trainers()
            trainer_name = "مربی گرامی"
            if trainers:
                # Set the first trainer matching phone or first trainer
                matching = [t for t in trainers if "".join(filter(str.isdigit, t.get("phone", ""))) == "".join(filter(str.isdigit, phone))]
                if matching:
                    trainer_name = matching[0].get("full_name", trainer_name)
                    from yalda.models.database_models import User
                    from yalda.database.connection import SessionLocal
                    with SessionLocal() as db:
                        u = db.query(User).filter(User.id == matching[0]["id"]).first()
                        if u:
                            CurrentUser.set(u)
                else:
                    from yalda.models.database_models import User
                    from yalda.database.connection import SessionLocal
                    with SessionLocal() as db:
                        u = db.query(User).first()
                        if u:
                            CurrentUser.set(u)
                            trainer_name = u.display_name

            QMessageBox.information(
                self,
                "بازیابی موفقیت‌آمیز",
                f"اطلاعات شما با موفقیت از سرور ابری بازیابی شد!\nخوش آمدید {trainer_name} 🌸\nتمامی ورزشکاران، برنامه‌ها و پرونده‌ها در نرم‌افزار بارگذاری شدند."
            )
            self.restore_success.emit()
            self.accept()
        else:
            self.lbl_status.setText(f"❌ {msg}")
            QMessageBox.warning(self, "عدم موفقیت در بازیابی", msg)