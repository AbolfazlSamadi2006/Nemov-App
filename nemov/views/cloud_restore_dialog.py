from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from nemov.services.backup_service import download_and_restore_cloud_backup
from nemov.auth.authentication import CurrentUser, get_all_trainers


class CloudRestoreDialog(QDialog):
    restore_success = pyqtSignal()

    def __init__(self, parent=None, initial_phone: str = ""):
        super().__init__(parent)
        self.setWindowTitle("☁️ بازیابی اطلاعات از سرور - نرم‌افزار نِمُو (Nemov)")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(460, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.initial_phone = initial_phone
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("card")
        card_l = QVBoxLayout(card)
        card_l.setSpacing(12)

        title = QLabel("☁️ بازیابی خودکار اطلاعات از سرور")
        title.setObjectName("h2")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_l.addWidget(title)

        desc = QLabel(
            "اگر برنامه را در سیستم جدید نصب کرده‌اید یا قصد بازگردانی اطلاعات را دارید، "
            "شماره موبایل ثبت‌شده خود را وارد کنید تا آخرین نسخه پشتیبان از سرور دریافت و بارگذاری شود:"
        )
        desc.setObjectName("muted_text")
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
        self.btn_submit.setObjectName("primary_button")
        self.btn_submit.clicked.connect(self.do_restore)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(42)
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

        self.lbl_status.setText("⏳ در حال برقراری ارتباط با سرور و دریافت آخرین نسخه پشتیبان...")
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
                    from nemov.models.database_models import User
                    from nemov.database.connection import SessionLocal
                    with SessionLocal() as db:
                        u = db.query(User).filter(User.id == matching[0]["id"]).first()
                        if u:
                            CurrentUser.set(u)
                else:
                    from nemov.models.database_models import User
                    from nemov.database.connection import SessionLocal
                    with SessionLocal() as db:
                        u = db.query(User).first()
                        if u:
                            CurrentUser.set(u)
                            trainer_name = u.display_name

            QMessageBox.information(
                self,
                "بازیابی موفقیت‌آمیز",
                f"اطلاعات شما با موفقیت از سرور بازیابی شد!\nخوش آمدید {trainer_name} 🌸\nتمامی ورزشکاران، برنامه‌ها و پرونده‌ها در نرم‌افزار بارگذاری شدند."
            )
            self.restore_success.emit()
            self.accept()
        else:
            self.lbl_status.setText(f"❌ {msg}")
            QMessageBox.warning(self, "عدم موفقیت در بازیابی", msg)