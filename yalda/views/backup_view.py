import os
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QGroupBox, QGridLayout, QFrame, QDialog, QScrollArea, QProgressBar, QInputDialog, QCheckBox, QAbstractItemView, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QPixmap, QColor, QBrush
import config
from yalda.services.backup_service import BackupService
from yalda.services.email_service import EmailService
from yalda.auth.authentication import (
    CurrentUser, update_trainer_profile, delete_trainer_account, get_all_trainers
)
from yalda.views.components.jalali_calendar_widget import JalaliDatePicker
from yalda.utils.image_utils import get_circular_pixmap, resolve_image_path


class CloudBackupThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, phone: str, trainer_name: str):
        super().__init__()
        self.phone = phone
        self.trainer_name = trainer_name

    def run(self):
        try:
            self.progress_signal.emit(15, "در حال آماده‌سازی و استخراج پایگاه‌داده...")
            time.sleep(0.3)
            self.progress_signal.emit(45, "در حال اتصال به سرور ابری یلدا...")
            time.sleep(0.3)
            self.progress_signal.emit(75, "در حال بارگذاری اطلاعات در سرور ابری...")
            from yalda.services.backup_service import upload_cloud_backup
            success, msg = upload_cloud_backup(trainer_phone=self.phone, trainer_name=self.trainer_name)
            if success:
                self.progress_signal.emit(100, "پشتیبان‌گیری ابری با موفقیت تکمیل شد.")
                self.finished_signal.emit(True, msg)
            else:
                self.finished_signal.emit(False, msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class EmailBackupThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str, str, float)  # ok, msg, filename, size_mb

    def __init__(self, email: str, trainer_name: str, trainer_id: int = None):
        super().__init__()
        self.email = email
        self.trainer_name = trainer_name
        self.trainer_id = trainer_id

    def run(self):
        try:
            self.progress_signal.emit(15, "در حال ایجاد نسخه پشتیبان دیتابیس (.db)...")
            from datetime import datetime
            from yalda.utils.jalali_date import gregorian_to_shamsi

            now = datetime.now()
            shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
            time_str = now.strftime("%H-%M-%S")
            shamsi_display = f"{gregorian_to_shamsi(now.date())} {now.strftime('%H:%M:%S')}"

            db_filename = f"yalda_backup_{shamsi_date}_{time_str}.db"
            db_target_path = config.BACKUPS_DIR / db_filename
            config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(config.DB_PATH, db_target_path)
            size_mb = round(os.path.getsize(db_target_path) / (1024 * 1024), 2)

            self.progress_signal.emit(45, "در حال اتصال امن به سرویس ایمیل (Gmail SSL/TLS)...")
            time.sleep(0.3)
            self.progress_signal.emit(75, f"در حال ارسال فایل دیتابیس ({size_mb} MB) به ایمیل مربی...")

            metadata = {
                "date": shamsi_display,
                "size": f"{size_mb} MB",
                "filename": db_filename,
                "members_count": "-"
            }
            try:
                from yalda.database.connection import SessionLocal
                from yalda.models.database_models import Member, User
                with SessionLocal() as db:
                    resolved_id = self.trainer_id

                    # 1. If trainer_id wasn't passed, resolve by email
                    if not resolved_id and self.email:
                        tr = db.query(User).filter(
                            User.email.ilike(self.email.strip()),
                            User.role != "admin"
                        ).first()
                        if tr:
                            resolved_id = tr.id
                            if not self.trainer_name or self.trainer_name == "مدیر باشگاه":
                                self.trainer_name = tr.display_name or tr.full_name

                    # 2. Resolve by trainer_name if still not resolved
                    if not resolved_id and self.trainer_name and self.trainer_name != "مدیر باشگاه":
                        tr = db.query(User).filter(
                            (User.full_name == self.trainer_name.strip()) |
                            ((User.first_name + " " + User.last_name) == self.trainer_name.strip()),
                            User.role != "admin"
                        ).first()
                        if tr:
                            resolved_id = tr.id

                    if resolved_id:
                        # Exactly count the students belonging to this specific trainer
                        count = db.query(Member).filter(Member.user_id == resolved_id).count()
                        metadata["members_count"] = str(count)
                    else:
                        metadata["members_count"] = str(db.query(Member).count())
            except Exception:
                pass

            success, msg = EmailService.send_backup_email(
                to_email=self.email,
                trainer_name=self.trainer_name,
                backup_filepath=str(db_target_path),
                metadata=metadata
            )

            if success:
                self.progress_signal.emit(100, "فایل پشتیبان با موفقیت به ایمیل مربی ارسال شد.")
                self.finished_signal.emit(True, msg, db_filename, size_mb)
            else:
                self.finished_signal.emit(False, msg, db_filename, size_mb)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "", 0.0)


class BackupView(QWidget):
    account_deleted_signal = pyqtSignal()
    back_requested = pyqtSignal()
    notifications_changed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.selected_photo_path = None
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_all_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # Header Title and Actions
        header_frame = QFrame()
        header_frame.setObjectName("backupHeaderCard")
        header_frame.setStyleSheet("""
            QFrame#backupHeaderCard {
                background-color: #1A1A1A;
                border: 1px solid #282828;
                border-radius: 12px;
                padding: 10px 16px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(14)

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.setFixedHeight(36)
        btn_back.clicked.connect(self.back_requested.emit)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("⚙️ اطلاعات شخص مربی و پشتیبان‌گیری دیتابیس")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")
        subtitle = QLabel("مدیریت مشخصات و امنیت مربی، مرکز آرشیو و بازگردانی پشتیبان، تاریخچه اعلانات و لاگ‌های خطا")
        subtitle.setStyleSheet("font-size: 11px; color: #888888;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addWidget(btn_back)
        header_layout.addLayout(title_box, 1)
        header_layout.addStretch()
        main_layout.addWidget(header_frame)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #1A1A1A;
                border: 1px solid #282828;
                border-radius: 10px;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #141414;
                color: #A0A0A0;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-left: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border-bottom: 2px solid #8B0000;
            }
            QTabBar::tab:hover:!selected {
                background-color: #222222;
                color: #E0E0E0;
            }
        """)

        self.tab_profile = self._create_profile_tab()
        self.tab_backup = self._create_backup_tab()
        self.tab_logs_notifs = self._create_logs_notifs_tab()

        self.tabs.addTab(self.tab_profile, "👤  مشخصات مربی و امنیت حساب")
        self.tabs.addTab(self.tab_backup, "💾  مرکز پشتیبان‌گیری و بازگردانی دیتابیس")
        self.tabs.addTab(self.tab_logs_notifs, "🔔  تاریخچه اعلانات و لاگ‌های سیستم")

        main_layout.addWidget(self.tabs, 1)

        self.load_all_data()

    def _create_profile_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # BOX 1: Trainer Profile & Credentials Settings
        profile_box = QGroupBox("👤 اطلاعات شخص مربی و تنظیمات ورود")
        layout_prof = QVBoxLayout(profile_box)
        layout_prof.setSpacing(12)

        grid_prof = QGridLayout()
        grid_prof.setHorizontalSpacing(15)
        grid_prof.setVerticalSpacing(10)

        # Row 0: Photo & Names
        self.lbl_trainer_photo = QLabel("📷 بدون عکس")
        self.lbl_trainer_photo.setFixedSize(65, 65)
        self.lbl_trainer_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_trainer_photo.setStyleSheet("border: 1px dashed #666; border-radius: 32px; color: #888;")

        btn_change_photo = QPushButton("📷 تغییر عکس مربی")
        btn_change_photo.setFixedHeight(36)
        btn_change_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_photo.clicked.connect(self.choose_trainer_photo)

        self.btn_remove_photo = QPushButton("🗑️ حذف عکس")
        self.btn_remove_photo.setFixedHeight(28)
        self.btn_remove_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove_photo.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #7F1D1D;
                border-radius: 4px;
                font-size: 11px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.btn_remove_photo.clicked.connect(self.remove_trainer_photo)
        self.btn_remove_photo.setVisible(False)

        photo_layout = QVBoxLayout()
        photo_layout.addWidget(self.lbl_trainer_photo, alignment=Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(btn_change_photo)
        photo_layout.addWidget(self.btn_remove_photo)

        grid_prof.addLayout(photo_layout, 0, 0, 2, 1)

        # Name fields
        self.txt_first_name = QLineEdit()
        self.txt_first_name.setFixedHeight(36)
        self.txt_first_name.setPlaceholderText("نام")

        self.txt_last_name = QLineEdit()
        self.txt_last_name.setFixedHeight(36)
        self.txt_last_name.setPlaceholderText("نام خانوادگی")

        grid_prof.addWidget(QLabel("نام مربی:"), 0, 1)
        grid_prof.addWidget(self.txt_first_name, 0, 2)
        grid_prof.addWidget(QLabel("نام خانوادگی:"), 0, 3)
        grid_prof.addWidget(self.txt_last_name, 0, 4)

        # Phone & Birthdate
        self.txt_phone = QLineEdit()
        self.txt_phone.setFixedHeight(36)
        self.txt_phone.setPlaceholderText("شماره همراه مربی")
        self.txt_phone.setMaxLength(11)

        self.picker_birth_date = JalaliDatePicker(default_today=False)
        self.picker_birth_date.setFixedHeight(36)

        grid_prof.addWidget(QLabel("شماره همراه:"), 1, 1)
        grid_prof.addWidget(self.txt_phone, 1, 2)
        grid_prof.addWidget(QLabel("تاریخ تولد:"), 1, 3)
        grid_prof.addWidget(self.picker_birth_date, 1, 4)

        # Username, Passwords & Secret Recovery Code
        self.txt_username = QLineEdit()
        self.txt_username.setFixedHeight(36)
        self.txt_username.setPlaceholderText("نام کاربری مربی")

        self.txt_password = QLineEdit()
        self.txt_password.setFixedHeight(36)
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("کلمه عبور جدید (اختیاری)")

        EYE_STYLE = """
            QPushButton {
                background-color: #8B0000;
                color: #FFFFFF;
                border: 1px solid #A91D22;
                border-radius: 6px;
                font-size: 16px;
                font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #A91D22;
            }
        """

        btn_eye_pass = QPushButton("👁️")
        btn_eye_pass.setFixedSize(42, 36)
        btn_eye_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_pass.setStyleSheet(EYE_STYLE)
        btn_eye_pass.clicked.connect(lambda: self.toggle_eye(self.txt_password, btn_eye_pass))
        pass_box = QHBoxLayout()
        pass_box.setSpacing(4)
        pass_box.addWidget(self.txt_password)
        pass_box.addWidget(btn_eye_pass)

        self.txt_recovery_code = QLineEdit()
        self.txt_recovery_code.setFixedHeight(36)
        self.txt_recovery_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_recovery_code.setPlaceholderText("رمز ریکاوری مخفی مربی")

        btn_eye_rec = QPushButton("👁️")
        btn_eye_rec.setFixedSize(42, 36)
        btn_eye_rec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye_rec.setStyleSheet(EYE_STYLE)
        btn_eye_rec.clicked.connect(lambda: self.toggle_eye(self.txt_recovery_code, btn_eye_rec))

        rec_box = QHBoxLayout()
        rec_box.setSpacing(4)
        rec_box.addWidget(self.txt_recovery_code)
        rec_box.addWidget(btn_eye_rec)

        grid_prof.addWidget(QLabel("نام کاربری:"), 2, 1)
        grid_prof.addWidget(self.txt_username, 2, 2)
        grid_prof.addWidget(QLabel("کلمه عبور جدید:"), 2, 3)
        grid_prof.addLayout(pass_box, 2, 4)

        grid_prof.addWidget(QLabel("رمز ریکاوری مخفی:"), 3, 1)
        grid_prof.addLayout(rec_box, 3, 2, 1, 3)

        # Row 4: Email Address
        self.txt_email = QLineEdit()
        self.txt_email.setFixedHeight(36)
        self.txt_email.setPlaceholderText("ایمیل مربی (جهت بازیابی رمز و دریافت نسخه پشتیبان)")

        btn_spam_guide = QPushButton("🛡️ راهنمای پوشه هرزنامه")
        btn_spam_guide.setFixedHeight(36)
        btn_spam_guide.setFixedWidth(155)
        btn_spam_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_spam_guide.setToolTip("راهنمای گام‌به‌گام خروج ایمیل‌های ارسالی برنامه از پوشه هرزنامه (Spam) جیمیل")
        btn_spam_guide.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        btn_spam_guide.clicked.connect(self.open_spam_guide_dialog)

        email_row_box = QHBoxLayout()
        email_row_box.setSpacing(8)
        email_row_box.addWidget(self.txt_email, 1)
        email_row_box.addWidget(btn_spam_guide)

        grid_prof.addWidget(QLabel("ایمیل مربی:"), 4, 1)
        grid_prof.addLayout(email_row_box, 4, 2, 1, 3)

        layout_prof.addLayout(grid_prof)

        # Action Buttons for Profile
        row_prof_actions = QHBoxLayout()
        row_prof_actions.setSpacing(12)

        self.btn_save_prof = QPushButton("💾 ذخیره مشخصات مربی")
        self.btn_save_prof.setFixedHeight(40)
        self.btn_save_prof.setFixedWidth(200)
        self.btn_save_prof.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_prof.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: #FFFFFF;
                border: 1px solid #A91D22;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #A00000;
            }
            QPushButton:disabled {
                background-color: #2D2D2D;
                color: #777777;
                border: 1px solid #444444;
            }
        """)
        self.btn_save_prof.setEnabled(False)
        self.btn_save_prof.clicked.connect(self.save_trainer_profile)
        row_prof_actions.addWidget(self.btn_save_prof)

        self.btn_reset_prof = QPushButton("🔄 بازنشانی / لغو تغییرات")
        self.btn_reset_prof.setFixedHeight(40)
        self.btn_reset_prof.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_prof.setObjectName("secondary_button")
        self.btn_reset_prof.setEnabled(False)
        self.btn_reset_prof.clicked.connect(self.revert_profile_changes)
        row_prof_actions.addWidget(self.btn_reset_prof)

        # Connect listeners to detect profile changes
        self.txt_first_name.textChanged.connect(self.check_profile_dirty)
        self.txt_last_name.textChanged.connect(self.check_profile_dirty)
        self.txt_phone.textChanged.connect(self.check_profile_dirty)
        self.picker_birth_date.line_edit.textChanged.connect(self.check_profile_dirty)
        self.txt_username.textChanged.connect(self.check_profile_dirty)
        self.txt_password.textChanged.connect(self.check_profile_dirty)
        self.txt_recovery_code.textChanged.connect(self.check_profile_dirty)
        self.txt_email.textChanged.connect(self.check_profile_dirty)

        btn_del_account = QPushButton("🗑️ حذف حساب مربی و کلیه شاگردان")
        btn_del_account.setFixedHeight(40)
        btn_del_account.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_account.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        btn_del_account.clicked.connect(self.delete_current_trainer_account)
        row_prof_actions.addWidget(btn_del_account)
        row_prof_actions.addStretch()

        layout_prof.addLayout(row_prof_actions)
        layout.addWidget(profile_box)

        # BOX 2: Admin Trainers Management & Account Deletion (Admin Only)
        self.box_admin_trainers = QGroupBox("👥 مدیریت مربیان و حذف حساب‌ها (مخصوص مدیر ارشد سیستم)")
        layout_adm = QVBoxLayout(self.box_admin_trainers)
        layout_adm.setSpacing(10)

        lbl_adm_desc = QLabel("به عنوان مدیر ارشد سیستم، می‌توانید حساب هر مربی را به همراه کلیه شاگردان، سوابق و برنامه‌هایش به صورت یکجا حذف کنید.")
        lbl_adm_desc.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout_adm.addWidget(lbl_adm_desc)

        self.table_trainers = QTableWidget()
        self.table_trainers.setColumnCount(7)
        self.table_trainers.setHorizontalHeaderLabels(["ردیف", "نام و نام خانوادگی مربی", "نام کاربری", "رمز عبور", "شماره تماس", "تعداد شاگردان", "عملیات"])
        header_tr = self.table_trainers.horizontalHeader()
        header_tr.setMinimumSectionSize(44)
        header_tr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_trainers.setColumnWidth(0, 44)
        header_tr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_trainers.setColumnWidth(2, 110)
        self.table_trainers.setColumnWidth(3, 105)
        self.table_trainers.setColumnWidth(4, 110)
        self.table_trainers.setColumnWidth(5, 90)
        self.table_trainers.setColumnWidth(6, 245)
        self.table_trainers.verticalHeader().setVisible(False)
        self.table_trainers.verticalHeader().setDefaultSectionSize(62)
        self.table_trainers.setStyleSheet("QTableWidget::item { padding: 0px 8px; }")
        self.table_trainers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_trainers.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_trainers.setMinimumHeight(200)
        layout_adm.addWidget(self.table_trainers)

        layout.addWidget(self.box_admin_trainers)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_backup_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Top Control Card / Backup & Restore Actions
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #202024;
                border: 1px solid #2E2E32;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(10)

        btn_create = QPushButton("⚡ ایجاد فایل پشتیبان جدید")
        btn_create.setFixedHeight(36)
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setToolTip("ایجاد نسخه پشتیبان جدید از پایگاه داده و تصاویر")
        btn_create.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: #FFFFFF;
                border: 1px solid #A91D22;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #A00000;
                border: 1px solid #DC2626;
            }
            QPushButton:pressed {
                background-color: #700000;
            }
        """)
        btn_create.clicked.connect(self.create_backup)
        toolbar_layout.addWidget(btn_create)

        btn_restore_cloud = QPushButton("☁️ بازگردانی از سرور ابری")
        btn_restore_cloud.setFixedHeight(36)
        btn_restore_cloud.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore_cloud.setToolTip("بازگردانی آخرین نسخه پشتیبان از سرور ابری کلودفلر")
        btn_restore_cloud.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #93C5FD;
                border: 1px solid #2563EB;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        btn_restore_cloud.clicked.connect(self.open_cloud_restore_dialog)
        toolbar_layout.addWidget(btn_restore_cloud)

        btn_restore_file = QPushButton("📁 بازگردانی از فایل خارجی")
        btn_restore_file.setFixedHeight(36)
        btn_restore_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore_file.setToolTip("بازگردانی نسخه پشتیبان از فایل خارجی در سیستم")
        btn_restore_file.setStyleSheet("""
            QPushButton {
                background-color: #262626;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 0 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #71717A;
            }
        """)
        btn_restore_file.clicked.connect(self.restore_from_file)
        toolbar_layout.addWidget(btn_restore_file)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        # Non-blocking Backup Progress Card
        self.progress_card = QFrame()
        self.progress_card.setObjectName("progressCard")
        self.progress_card.setStyleSheet("""
            QFrame#progressCard {
                background-color: #18181B;
                border: 1.5px solid #DC2626;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        prog_layout = QVBoxLayout(self.progress_card)
        prog_layout.setContentsMargins(12, 10, 12, 10)
        prog_layout.setSpacing(6)

        header_prog = QHBoxLayout()
        self.lbl_prog_title = QLabel("⏳ در حال پردازش نسخه پشتیبان...")
        self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #F87171; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
        header_prog.addWidget(self.lbl_prog_title)
        header_prog.addStretch()

        self.btn_prog_spam_guide = QPushButton("🛡️ راهنمای پوشه اسپم")
        self.btn_prog_spam_guide.setFixedHeight(24)
        self.btn_prog_spam_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prog_spam_guide.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        self.btn_prog_spam_guide.clicked.connect(self.open_spam_guide_dialog)
        self.btn_prog_spam_guide.setVisible(False)
        header_prog.addWidget(self.btn_prog_spam_guide)

        self.btn_prog_close = QPushButton("✕")
        self.btn_prog_close.setFixedSize(24, 24)
        self.btn_prog_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prog_close.setStyleSheet("background: transparent; color: #9CA3AF; border: none; font-size: 13px; font-weight: bold;")
        self.btn_prog_close.clicked.connect(lambda: self.progress_card.setVisible(False))
        self.btn_prog_close.setVisible(False)
        header_prog.addWidget(self.btn_prog_close)
        prog_layout.addLayout(header_prog)

        self.lbl_prog_detail = QLabel("در حال شروع فرآیند...")
        self.lbl_prog_detail.setStyleSheet("color: #D1D5DB; font-size: 11px;")
        prog_layout.addWidget(self.lbl_prog_detail)

        self.backup_progress_bar = QProgressBar()
        self.backup_progress_bar.setFixedHeight(18)
        self.backup_progress_bar.setTextVisible(True)
        self.backup_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 6px;
                background-color: #111111;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #991B1B, stop:0.5 #DC2626, stop:1 #EF4444);
                border-radius: 5px;
            }
        """)
        prog_layout.addWidget(self.backup_progress_bar)

        lbl_notice = QLabel("💡 این عملیات در پس‌زمینه انجام می‌شود و مانع کار با سایر بخش‌های برنامه نخواهد بود.")
        lbl_notice.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        prog_layout.addWidget(lbl_notice)

        layout.addWidget(self.progress_card)
        self.progress_card.setVisible(False)

        # Archive List Header Frame (Title on Right, Selection/Deletion Buttons on Left - matching Notification History)
        table_header_frame = QFrame()
        table_header_frame.setStyleSheet("""
            QFrame {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        th_layout = QHBoxLayout(table_header_frame)
        th_layout.setContentsMargins(12, 6, 12, 6)
        th_layout.setSpacing(10)

        lbl_table_title = QLabel("📋 لیست آرشیوهای پشتیبان موجود")
        lbl_table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #E4E4E7;")
        th_layout.addWidget(lbl_table_title)
        th_layout.addStretch()

        self.btn_select_all_backups = QPushButton("☑️ انتخاب همه")
        self.btn_select_all_backups.setFixedHeight(34)
        self.btn_select_all_backups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all_backups.setToolTip("انتخاب یا لغو انتخاب تمام ردیف‌های جدول")
        self.btn_select_all_backups.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #E4E4E7;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
            }
        """)
        self.btn_select_all_backups.clicked.connect(self.toggle_select_all_backups)
        th_layout.addWidget(self.btn_select_all_backups)

        self.btn_delete_selected_backups = QPushButton("🗑️ حذف انتخاب‌شده")
        self.btn_delete_selected_backups.setFixedHeight(34)
        self.btn_delete_selected_backups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_selected_backups.setToolTip("حذف موارد انتخاب‌شده در جدول")
        self.btn_delete_selected_backups.setStyleSheet("""
            QPushButton {
                background-color: #7F1D1D;
                color: #FECACA;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.btn_delete_selected_backups.clicked.connect(self.delete_selected_backups)
        th_layout.addWidget(self.btn_delete_selected_backups)

        self.btn_delete_all_backups = QPushButton("🧹 حذف همگانی")
        self.btn_delete_all_backups.setFixedHeight(34)
        self.btn_delete_all_backups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_all_backups.setToolTip("حذف کلیه نسخه‌های پشتیبان موجود در آرشیو")
        self.btn_delete_all_backups.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.btn_delete_all_backups.clicked.connect(self.delete_all_backups_history)
        th_layout.addWidget(self.btn_delete_all_backups)

        layout.addWidget(table_header_frame)

        # Backups Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "نام فایل پشتیبان", "مسیر ذخیره‌سازی فایل", "تاریخ و زمان ثبت (شمسی)", "حجم فایل", "عملیات"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 48)
        self.table.setColumnWidth(2, 250)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 82)
        self.table.setColumnWidth(6, 230)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setStyleSheet("QTableWidget::item { padding: 0px 8px; }")
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table, 1)

        return widget

    def _create_logs_notifs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Top Card: System Error Logs & Diagnostics
        logs_card = QFrame()
        logs_card.setStyleSheet("""
            QFrame {
                background-color: #202024;
                border: 1px solid #2E2E32;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        logs_layout = QHBoxLayout(logs_card)
        logs_layout.setContentsMargins(12, 8, 12, 8)
        logs_layout.setSpacing(12)

        desc_box = QVBoxLayout()
        desc_box.setSpacing(2)
        lbl_logs_title = QLabel("🛠️ گزارش وقایع و لاگ‌های تشخیصی سیستم")
        lbl_logs_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #E4E4E7;")
        lbl_logs_desc = QLabel("کلیه وقایع و خطاهای احتمالی ثبت می‌شوند. در صورت نیاز می‌توانید گزارش لاگ را مشاهده یا ارسال فرمایید.")
        lbl_logs_desc.setStyleSheet("color: #888888; font-size: 11px;")
        desc_box.addWidget(lbl_logs_title)
        desc_box.addWidget(lbl_logs_desc)
        logs_layout.addLayout(desc_box, 1)

        btn_view_logs = QPushButton("👁️ مشاهده لاگ‌ها")
        btn_view_logs.setFixedHeight(36)
        btn_view_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_logs.setToolTip("مشاهده کامل گزارش وقایع و خطاهای سیستم")
        btn_view_logs.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_view_logs.clicked.connect(self.open_log_viewer_dialog)
        logs_layout.addWidget(btn_view_logs)

        btn_open_logs_folder = QPushButton("📁 پوشه لاگ‌ها")
        btn_open_logs_folder.setFixedHeight(36)
        btn_open_logs_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_logs_folder.setToolTip("باز کردن پوشه حاوی فایل‌های لاگ در ویندوز")
        btn_open_logs_folder.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #F3F4F6;
                border: 1px solid #4B5563;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        btn_open_logs_folder.clicked.connect(self.open_logs_folder_action)
        logs_layout.addWidget(btn_open_logs_folder)

        self.btn_copy_last_err = QPushButton("📋 کپی آخرین خطا")
        self.btn_copy_last_err.setFixedHeight(36)
        self.btn_copy_last_err.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_last_err.setToolTip("کپی متن آخرین خطای رخ‌داده در کلیپ‌بورد")
        self.btn_copy_last_err.setStyleSheet("""
            QPushButton {
                background-color: #1F2937;
                color: #D1D5DB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #FFFFFF;
            }
        """)
        self.btn_copy_last_err.clicked.connect(self.copy_last_error_action)
        logs_layout.addWidget(self.btn_copy_last_err)

        layout.addWidget(logs_card)

        # Bottom Section: Notification History
        notif_header_frame = QFrame()
        notif_header_frame.setStyleSheet("""
            QFrame {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        notif_top_layout = QHBoxLayout(notif_header_frame)
        notif_top_layout.setContentsMargins(12, 6, 12, 6)
        notif_top_layout.setSpacing(10)

        lbl_notif_title = QLabel("🔔 تاریخچه اعلانات و یادآوری‌ها")
        lbl_notif_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #E4E4E7;")
        notif_top_layout.addWidget(lbl_notif_title)
        notif_top_layout.addStretch()

        self.btn_select_all_notifs = QPushButton("☑️ انتخاب همه")
        self.btn_select_all_notifs.setFixedHeight(34)
        self.btn_select_all_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all_notifs.setToolTip("انتخاب یا لغو انتخاب تمام ردیف‌های جدول")
        self.btn_select_all_notifs.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #E4E4E7;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
            }
        """)
        self.btn_select_all_notifs.clicked.connect(self.toggle_select_all_notifications)
        notif_top_layout.addWidget(self.btn_select_all_notifs)

        self.btn_delete_selected_notifs = QPushButton("🗑️ حذف انتخاب‌شده")
        self.btn_delete_selected_notifs.setFixedHeight(34)
        self.btn_delete_selected_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_selected_notifs.setToolTip("حذف موارد انتخاب‌شده در جدول")
        self.btn_delete_selected_notifs.setStyleSheet("""
            QPushButton {
                background-color: #7F1D1D;
                color: #FECACA;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.btn_delete_selected_notifs.clicked.connect(self.delete_selected_notifications)
        notif_top_layout.addWidget(self.btn_delete_selected_notifs)

        self.btn_delete_all_notifs = QPushButton("🧹 حذف همگانی")
        self.btn_delete_all_notifs.setFixedHeight(34)
        self.btn_delete_all_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_all_notifs.setToolTip("حذف کلیه اعلانات موجود در تاریخچه")
        self.btn_delete_all_notifs.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #DC2626;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.btn_delete_all_notifs.clicked.connect(self.delete_all_notifications_history)
        notif_top_layout.addWidget(self.btn_delete_all_notifs)

        layout.addWidget(notif_header_frame)

        self.table_notif_history = QTableWidget()
        self.table_notif_history.setColumnCount(7)
        self.table_notif_history.setHorizontalHeaderLabels([
            "انتخاب", "ردیف", "عنوان اعلان", "شرح کامل اعلان", "تاریخ ثبت", "وضعیت", "عملیات"
        ])
        nh_header = self.table_notif_history.horizontalHeader()
        nh_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_notif_history.setColumnWidth(0, 65)
        self.table_notif_history.setColumnWidth(1, 55)
        self.table_notif_history.setColumnWidth(2, 210)
        nh_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_notif_history.setColumnWidth(4, 145)
        self.table_notif_history.setColumnWidth(5, 130)
        self.table_notif_history.setColumnWidth(6, 105)
        self.table_notif_history.verticalHeader().setVisible(False)
        self.table_notif_history.verticalHeader().setDefaultSectionSize(46)
        self.table_notif_history.setStyleSheet("QTableWidget::item { padding: 0px 8px; }")
        self.table_notif_history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_notif_history.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_notif_history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_notif_history, 1)

        return widget

    def open_log_viewer_dialog(self):
        from yalda.views.components.error_dialog import LogViewerDialog
        dlg = LogViewerDialog(parent=self.window())
        dlg.exec()

    def open_logs_folder_action(self):
        from yalda.utils.logger import open_logs_folder
        open_logs_folder()

    def copy_last_error_action(self):
        from yalda.utils.logger import get_last_error_snippet
        from PyQt6.QtWidgets import QApplication
        err_snippet = get_last_error_snippet()
        QApplication.clipboard().setText(err_snippet)
        self.btn_copy_last_err.setText("کپی شد! ✓")
        QTimer.singleShot(2500, lambda: self.btn_copy_last_err.setText("📋 کپی آخرین گزارش خطا"))

    def toggle_eye(self, field: QLineEdit, button: QPushButton):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("👁️")

    def choose_trainer_photo(self):
        from yalda.utils.image_source_chooser import get_image_file_path
        temp_path = get_image_file_path(
            self,
            dialog_title="انتخاب یا ثبت تصویر مربی",
            file_filter="فایل‌های تصویری (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if temp_path and os.path.exists(temp_path):
            dest_dir = config.PROFILE_PHOTOS_DIR
            dest_dir.mkdir(parents=True, exist_ok=True)
            ext = Path(temp_path).suffix or ".jpg"
            import uuid
            filename = f"trainer_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = dest_dir / filename
            import shutil
            shutil.copy2(temp_path, dest_path)

            # Mirror to APPDATA_DATA_DIR as well for persistent multi-install safety
            try:
                appdata_dest = config.APPDATA_DATA_DIR / "uploads" / "profile-photos" / filename
                appdata_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(temp_path, appdata_dest)
            except Exception:
                pass

            # Store the relative filename for universal portability
            self.selected_photo_path = filename
            self.display_photo(filename)

            # Auto-save immediately to database so user never loses it
            u = CurrentUser.get()
            if u:
                try:
                    update_trainer_profile(
                        user_id=u.id,
                        first_name=u.first_name,
                        last_name=u.last_name,
                        phone=u.phone,
                        email=u.email,
                        birth_date_shamsi=u.birth_date_shamsi,
                        photo_path=filename,
                        username=u.username
                    )
                    u.photo_path = filename
                    if hasattr(self, "_baseline_profile"):
                        self._baseline_profile["photo_path"] = filename
                    QMessageBox.information(self, "موفقیت", "تصویر مربی با موفقیت انتخاب و در سیستم ذخیره شد.")
                except Exception as ex:
                    print(f"Auto-save trainer photo error: {ex}")

            self.check_profile_dirty()

    def remove_trainer_photo(self):
        reply = QMessageBox.question(
            self,
            "حذف عکس مربی",
            "آیا از حذف عکس پروفایل مربی اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        u = CurrentUser.get()
        if u:
            try:
                update_trainer_profile(
                    user_id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    phone=u.phone,
                    email=u.email,
                    birth_date_shamsi=u.birth_date_shamsi,
                    photo_path="",
                    username=u.username
                )
                u.photo_path = ""
                self.selected_photo_path = ""
                if hasattr(self, "_baseline_profile"):
                    self._baseline_profile["photo_path"] = ""
                self.display_photo("")
                self.check_profile_dirty()
                QMessageBox.information(self, "موفقیت", "عکس پروفایل مربی حذف گردید.")
            except Exception as ex:
                QMessageBox.critical(self, "خطا", f"خطا در حذف عکس: {str(ex)}")

    def display_photo(self, photo_path: str):
        resolved = resolve_image_path(photo_path)
        if resolved:
            pixmap = QPixmap(resolved)
            circ = get_circular_pixmap(pixmap, 65)
            self.lbl_trainer_photo.setPixmap(circ)
            self.lbl_trainer_photo.setText("")
            self.lbl_trainer_photo.setStyleSheet("border: none; background: transparent;")
            if hasattr(self, "btn_remove_photo"):
                self.btn_remove_photo.setVisible(True)
        else:
            self.lbl_trainer_photo.setPixmap(QPixmap())
            self.lbl_trainer_photo.setText("📷 بدون عکس")
            self.lbl_trainer_photo.setStyleSheet("border: 1px dashed #666; border-radius: 32px; color: #888;")
            if hasattr(self, "btn_remove_photo"):
                self.btn_remove_photo.setVisible(False)

    def check_profile_dirty(self):
        if getattr(self, "_loading_profile", False):
            return

        current = {
            "first_name": self.txt_first_name.text().strip(),
            "last_name": self.txt_last_name.text().strip(),
            "phone": self.txt_phone.text().strip(),
            "email": self.txt_email.text().strip(),
            "birth_date": self.picker_birth_date.get_date().strip(),
            "username": self.txt_username.text().strip(),
            "recovery_code": self.txt_recovery_code.text().strip(),
            "photo_path": self.selected_photo_path or ""
        }
        new_pass = self.txt_password.text().strip()
        is_dirty = bool(new_pass) or (current != getattr(self, "_baseline_profile", {}))
        self.btn_save_prof.setEnabled(is_dirty)
        if hasattr(self, "btn_reset_prof"):
            self.btn_reset_prof.setEnabled(is_dirty)

    def revert_profile_changes(self):
        base = getattr(self, "_baseline_profile", {})
        if not base:
            return
        self._loading_profile = True
        self.txt_first_name.setText(base.get("first_name", ""))
        self.txt_last_name.setText(base.get("last_name", ""))
        self.txt_phone.setText(base.get("phone", ""))
        self.txt_email.setText(base.get("email", ""))
        self.picker_birth_date.set_date(base.get("birth_date", ""))
        self.txt_username.setText(base.get("username", ""))
        self.txt_password.clear()
        self.txt_recovery_code.setText(base.get("recovery_code", ""))
        self.selected_photo_path = base.get("photo_path", "")
        self.display_photo(self.selected_photo_path)
        self._loading_profile = False
        self.btn_save_prof.setEnabled(False)
        if hasattr(self, "btn_reset_prof"):
            self.btn_reset_prof.setEnabled(False)

    def load_all_data(self):
        # 1. Current trainer profile
        u = CurrentUser.get()
        if u:
            self._loading_profile = True
            self.txt_first_name.setText(u.first_name or "")
            self.txt_last_name.setText(u.last_name or "")
            self.txt_phone.setText(u.phone or "")
            email_val = (u.email or "").strip()
            if email_val.lower() == getattr(config, "SUPPORT_EMAIL_ADDRESS", "").lower():
                email_val = ""
            self.txt_email.setText(email_val)
            self.picker_birth_date.set_date(u.birth_date_shamsi or "")
            self.txt_username.setText(u.username or "")
            self.txt_password.clear()
            self.txt_recovery_code.setText(u.recovery_code or "")
            self.selected_photo_path = u.photo_path
            self.display_photo(u.photo_path)

            self._baseline_profile = {
                "first_name": (u.first_name or "").strip(),
                "last_name": (u.last_name or "").strip(),
                "phone": (u.phone or "").strip(),
                "email": email_val,
                "birth_date": (u.birth_date_shamsi or "").strip(),
                "username": (u.username or "").strip(),
                "recovery_code": (u.recovery_code or "").strip(),
                "photo_path": u.photo_path or ""
            }
            self._loading_profile = False
            self.btn_save_prof.setEnabled(False)
            if hasattr(self, "btn_reset_prof"):
                self.btn_reset_prof.setEnabled(False)

        # 2. Admin Trainers Box visibility
        if CurrentUser.is_admin():
            self.box_admin_trainers.setVisible(True)
            self.load_trainers_for_admin()
        else:
            self.box_admin_trainers.setVisible(False)

        # 3. Backups
        self.load_backups()

        # 4. Notification History
        self.load_notification_history()

    def load_notification_history(self):
        if not hasattr(self, "table_notif_history"):
            return
        from yalda.services.notification_service import NotificationService
        records = NotificationService.get_history()
        self.table_notif_history.setRowCount(0)
        self._notif_checkboxes = []

        if not records:
            self.table_notif_history.setRowCount(1)
            empty_item = QTableWidgetItem("هیچ اعلانی در تاریخچه ثبت نشده است.")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(QBrush(QColor("#888888")))
            self.table_notif_history.setSpan(0, 0, 1, 7)
            self.table_notif_history.setItem(0, 0, empty_item)
            return

        self.table_notif_history.clearSpans()
        self.table_notif_history.setRowCount(len(records))

        for row, rec in enumerate(records):
            # 0: Checkbox for multi-select
            chk_container = QWidget()
            chk_container.setStyleSheet("background: transparent;")
            chk_layout = QHBoxLayout(chk_container)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setProperty("notif_id", rec.id)
            chk_layout.addWidget(chk)
            self.table_notif_history.setCellWidget(row, 0, chk_container)
            self._notif_checkboxes.append(chk)

            # 1: Row Index (Persian digits)
            fa_idx = str(row + 1).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            it_idx = QTableWidgetItem(fa_idx)
            it_idx.setData(Qt.ItemDataRole.UserRole, rec.id)
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_notif_history.setItem(row, 1, it_idx)

            # 2: Title
            it_title = QTableWidgetItem(rec.title or "-")
            it_title.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "موعد" in (rec.title or "") or "سررسید" in (rec.title or ""):
                it_title.setForeground(QBrush(QColor("#FCA5A5")))
            else:
                it_title.setForeground(QBrush(QColor("#FDE68A")))
            self.table_notif_history.setItem(row, 2, it_title)

            # 3: Description
            fa_desc = str(rec.description or rec.title or "-").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            it_desc = QTableWidgetItem(fa_desc)
            it_desc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_notif_history.setItem(row, 3, it_desc)

            # 4: Date
            fa_date = str(rec.date_shamsi or "-").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            it_date = QTableWidgetItem(fa_date)
            it_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_notif_history.setItem(row, 4, it_date)

            # 5: Read Status
            is_read = bool(rec.is_read)
            status_str = "🟢 خوانده شده" if is_read else "🔴 خوانده نشده"
            it_status = QTableWidgetItem(status_str)
            it_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_status.setForeground(QBrush(QColor("#10B981" if is_read else "#F87171")))
            self.table_notif_history.setItem(row, 5, it_status)

            # 6: Single Delete Action Button (centered vertically & horizontally)
            act_widget = QWidget()
            act_widget.setStyleSheet("background: transparent;")
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 0, 4, 0)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_del_one = QPushButton("🗑️ حذف")
            btn_del_one.setFixedSize(76, 30)
            btn_del_one.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del_one.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11.5px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
            """)
            btn_del_one.clicked.connect(lambda _, nid=rec.id: self.delete_single_notification(nid))
            act_layout.addWidget(btn_del_one)
            self.table_notif_history.setCellWidget(row, 6, act_widget)

    def _get_selected_notification_ids(self) -> list:
        selected_ids = set()
        for chk in getattr(self, "_notif_checkboxes", []):
            if chk.isChecked():
                nid = chk.property("notif_id")
                if nid is not None:
                    selected_ids.add(int(nid))
        for idx in self.table_notif_history.selectionModel().selectedRows():
            row = idx.row()
            it = self.table_notif_history.item(row, 1)
            if it:
                nid = it.data(Qt.ItemDataRole.UserRole)
                if nid is not None:
                    selected_ids.add(int(nid))
        return list(selected_ids)

    def toggle_select_all_notifications(self):
        checkboxes = getattr(self, "_notif_checkboxes", [])
        if not checkboxes:
            return
        any_unchecked = any(not c.isChecked() for c in checkboxes)
        for c in checkboxes:
            c.setChecked(any_unchecked)
        if any_unchecked:
            self.table_notif_history.selectAll()
        else:
            self.table_notif_history.clearSelection()

    def delete_single_notification(self, notif_id: int):
        from yalda.services.notification_service import NotificationService
        NotificationService.delete_by_ids([notif_id])
        self.load_notification_history()
        self.notifications_changed_signal.emit()

    def delete_selected_notifications(self):
        ids = self._get_selected_notification_ids()
        if not ids:
            QMessageBox.information(self, "انتخاب موارد", "لطفاً ابتدا یک یا چند اعلان را از لیست انتخاب (تیک) نمایید.")
            return
        fa_cnt = str(len(ids)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        reply = QMessageBox.question(
            self,
            "حذف اعلانات انتخاب‌شده",
            f"آیا از حذف {fa_cnt} اعلان انتخاب‌شده از تاریخچه اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from yalda.services.notification_service import NotificationService
            NotificationService.delete_by_ids(ids)
            self.load_notification_history()
            self.notifications_changed_signal.emit()

    def delete_all_notifications_history(self):
        checkboxes = getattr(self, "_notif_checkboxes", [])
        if not checkboxes:
            QMessageBox.information(self, "تاریخچه خالی", "هیچ اعلانی در تاریخچه برای حذف وجود ندارد.")
            return
        reply = QMessageBox.warning(
            self,
            "حذف همگانی تاریخچه اعلانات",
            "آیا از پاک کردن تمامی اعلانات موجود در تاریخچه اطمینان دارید؟\nاین عمل قابل بازگشت نیست.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from yalda.services.notification_service import NotificationService
            NotificationService.delete_all_history()
            self.load_notification_history()
            self.notifications_changed_signal.emit()

    def load_trainers_for_admin(self):
        trainers = get_all_trainers()
        self.table_trainers.setRowCount(len(trainers))

        for row, t in enumerate(trainers):
            self.table_trainers.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table_trainers.setItem(row, 1, QTableWidgetItem(t["full_name"]))
            self.table_trainers.setItem(row, 2, QTableWidgetItem(t["username"]))
            
            pass_val = t.get("password") or "-"
            item_pass = QTableWidgetItem(pass_val)
            if pass_val != "-":
                item_pass.setToolTip("رمز عبور مربی (جهت ورود به سیستم)")
            else:
                item_pass.setToolTip("رمز این مربی در نسخه‌های قبل ثبت شده است. برای مشاهده، از دکمه 'مشخصات مربی' یک رمز جدید برای او ثبت کنید.")
            self.table_trainers.setItem(row, 3, item_pass)

            self.table_trainers.setItem(row, 4, QTableWidgetItem(t["phone"]))
            self.table_trainers.setItem(row, 5, QTableWidgetItem(f"{t['member_count']} نفر"))

            for c in (0, 2, 3, 4, 5):
                item = self.table_trainers.item(row, c)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 0, 4, 0)
            action_l.setSpacing(6)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_details = QPushButton("👁️ مشخصات مربی")
            btn_details.setToolTip("مشاهده مشخصات کامل، رمز ریکاوری و تغییر رمز این مربی")
            btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_details.setFixedHeight(34)
            btn_details.setStyleSheet("""
                QPushButton {
                    background-color: #1E3A8A;
                    color: #93C5FD;
                    border: 1px solid #2563EB;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 2px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                    color: #FFFFFF;
                }
            """)
            btn_details.clicked.connect(lambda _, tr=t: self.open_trainer_details(tr))

            btn_del = QPushButton("🗑️ حذف مربی")
            btn_del.setToolTip("حذف کامل حساب مربی به همراه تمام شاگردان، سوابق و برنامه‌ها")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setFixedHeight(34)
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #EF4444;
                    border: 1px solid #DC2626;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 2px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                    color: #FFFFFF;
                }
            """)
            btn_del.clicked.connect(lambda _, t_id=t["id"], t_name=t["full_name"], m_cnt=t["member_count"]: self.admin_delete_trainer(t_id, t_name, m_cnt))
            action_l.addWidget(btn_details)
            action_l.addWidget(btn_del)
            self.table_trainers.setRowHeight(row, 62)
            self.table_trainers.setCellWidget(row, 6, action_w)

    def open_trainer_details(self, trainer_data: dict):
        from yalda.views.components.trainer_details_dialog import TrainerDetailsDialog
        dlg = TrainerDetailsDialog(self, trainer_data=trainer_data)
        dlg.exec()
        self.load_trainers_for_admin()

    def admin_delete_trainer(self, trainer_id: int, trainer_name: str, member_count: int):
        reply1 = QMessageBox.warning(
            self,
            "⚠️ تایید حذف مربی توسط مدیر ارشد",
            f"آیا مطمئن هستید که می‌خواهید مربی «{trainer_name}» را به همراه کلیه {member_count} شاگرد، سوابق و برنامه‌های ایشان حذف کنید؟\n\nاین عملیات غیرقابل بازگشت است!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply1 != QMessageBox.StandardButton.Yes:
            return

        reply2 = QMessageBox.critical(
            self,
            "🔴 تایید نهایی حذف",
            f"تمامی اطلاعات مربی «{trainer_name}» از دیتابیس و فضای ابری پاک خواهد شد. آیا تایید می‌کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply2 == QMessageBox.StandardButton.Yes:
            try:
                delete_trainer_account(trainer_id)
                QMessageBox.information(self, "موفقیت", f"حساب مربی «{trainer_name}» و کلیه شاگردان ایشان با موفقیت حذف شدند.")
                self.load_all_data()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف مربی: {str(e)}")

    def save_trainer_profile(self):
        u = CurrentUser.get()
        if not u:
            return

        username = self.txt_username.text().strip()
        first_name = self.txt_first_name.text().strip()
        last_name = self.txt_last_name.text().strip()
        phone = self.txt_phone.text().strip()
        email = self.txt_email.text().strip()
        birth_date = self.picker_birth_date.get_date()
        password = self.txt_password.text().strip()
        recovery_code = self.txt_recovery_code.text().strip()

        if not username:
            QMessageBox.warning(self, "خطا", "لطفاً نام کاربری را وارد کنید.")
            return

        if email:
            if "@" not in email or "." not in email:
                QMessageBox.warning(
                    self,
                    "خطا در آدرس ایمیل",
                    "لطفاً آدرس ایمیل را در قالب صحیح وارد کنید (مثال: coach@example.com)."
                )
                self.txt_email.setFocus()
                return

        if phone:
            phone_digits = "".join(filter(str.isdigit, phone.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))))
            if len(phone_digits) > 11:
                QMessageBox.warning(
                    self,
                    "خطا در شماره تلفن",
                    "شماره تماس نمی‌تواند بیشتر از ۱۱ رقم باشد."
                )
                self.txt_phone.setFocus()
                return

        photo_to_save = self.selected_photo_path if self.selected_photo_path is not None else u.photo_path
        try:
            update_trainer_profile(
                user_id=u.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                birth_date_shamsi=birth_date,
                photo_path=photo_to_save,
                username=username,
                password=password if password else None,
                recovery_code=recovery_code if recovery_code else None
            )
            QMessageBox.information(self, "موفقیت", "اطلاعات مربی با موفقیت به‌روزرسانی شد.")
            self.load_all_data()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ویرایش اطلاعات مربی: {str(e)}")


    def load_backups(self):
        backups = BackupService.get_all_backups()
        self.table.setRowCount(0)
        self._backup_checkboxes = []

        if not backups:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem("هیچ نسخه پشتیبانی در آرشیو ثبت نشده است.")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(QBrush(QColor("#888888")))
            self.table.setSpan(0, 0, 1, 7)
            self.table.setItem(0, 0, empty_item)
            return

        self.table.clearSpans()
        self.table.setRowCount(len(backups))

        for row, b in enumerate(backups):
            # 0: Checkbox for multi-select
            chk_container = QWidget()
            chk_container.setStyleSheet("background: transparent;")
            chk_layout = QHBoxLayout(chk_container)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setProperty("backup_id", b.id)
            chk_layout.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_container)
            self._backup_checkboxes.append(chk)

            # 1: Row number
            fa_idx = str(row + 1).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            it_idx = QTableWidgetItem(fa_idx)
            it_idx.setData(Qt.ItemDataRole.UserRole, b.id)
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, it_idx)

            # 2: File name
            item_name = QTableWidgetItem(b.file_name)
            item_name.setToolTip(b.file_name)
            self.table.setItem(row, 2, item_name)

            # 3: File Path / Location
            item_path = QTableWidgetItem(b.file_path or "-")
            item_path.setToolTip(b.file_path or "-")
            self.table.setItem(row, 3, item_path)

            # 4: Shamsi Date & Time
            self.table.setItem(row, 4, QTableWidgetItem(b.backup_date_shamsi))

            # 5: File Size
            self.table.setItem(row, 5, QTableWidgetItem(f"{b.backup_size_mb} MB"))

            for c in (1, 4, 5):
                item = self.table.item(row, c)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 0, 4, 0)
            action_l.setSpacing(6)
            action_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_restore = QPushButton("🔄 بازگردانی")
            btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_restore.setFixedHeight(29)
            btn_restore.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 4px; min-height: 29px; max-height: 29px; padding: 0px 8px; font-size: 11px;")
            btn_restore.clicked.connect(lambda _, fp=b.file_path: self.restore_backup(fp))

            btn_delete = QPushButton("🗑️ حذف")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setFixedHeight(29)
            btn_delete.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 4px; min-height: 29px; max-height: 29px; padding: 0px 8px; font-size: 11px;")
            btn_delete.clicked.connect(lambda _, b_id=b.id, fn=b.file_name: self.delete_backup_item(b_id, fn))

            action_l.addWidget(btn_restore)

            # If local file exists, add Open Folder button
            if b.file_path and not b.file_path.startswith("☁️") and not b.file_path.startswith("📧"):
                btn_open_folder = QPushButton("📂 پوشه")
                btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_open_folder.setFixedHeight(29)
                btn_open_folder.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 4px; min-height: 29px; max-height: 29px; padding: 0px 8px; font-size: 11px;")
                btn_open_folder.clicked.connect(lambda _, fp=b.file_path: self.open_backup_folder(fp))
                action_l.addWidget(btn_open_folder)

            action_l.addWidget(btn_delete)
            self.table.setRowHeight(row, 46)
            self.table.setCellWidget(row, 6, action_w)

    def _get_selected_backup_ids(self) -> list:
        selected_ids = set()
        for chk in getattr(self, "_backup_checkboxes", []):
            if chk.isChecked():
                bid = chk.property("backup_id")
                if bid is not None:
                    selected_ids.add(int(bid))
        for idx in self.table.selectionModel().selectedRows():
            row = idx.row()
            it = self.table.item(row, 1)
            if it:
                bid = it.data(Qt.ItemDataRole.UserRole)
                if bid is not None:
                    selected_ids.add(int(bid))
        return list(selected_ids)

    def toggle_select_all_backups(self):
        checkboxes = getattr(self, "_backup_checkboxes", [])
        if not checkboxes:
            return
        any_unchecked = any(not c.isChecked() for c in checkboxes)
        for c in checkboxes:
            c.setChecked(any_unchecked)
        if any_unchecked:
            self.table.selectAll()
        else:
            self.table.clearSelection()

    def delete_selected_backups(self):
        ids = self._get_selected_backup_ids()
        if not ids:
            QMessageBox.information(self, "انتخاب موارد", "لطفاً ابتدا یک یا چند فایل پشتیبان را از لیست انتخاب (تیک) نمایید.")
            return
        fa_cnt = str(len(ids)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        reply = QMessageBox.warning(
            self,
            "⚠️ حذف نسخه‌های پشتیبان انتخاب‌شده",
            f"آیا از حذف {fa_cnt} نسخه پشتیبان انتخاب‌شده اطمینان دارید؟\nفایل‌های انتخاب‌شده به طور کامل از روی حافظه سیستم پاک خواهند شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_cnt = 0
                for bid in ids:
                    if BackupService.delete_backup(bid):
                        deleted_cnt += 1
                self.load_backups()
                fa_del = str(deleted_cnt).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                QMessageBox.information(self, "موفقیت", f"{fa_del} نسخه پشتیبان با موفقیت حذف گردید.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف نسخه‌های پشتیبان: {str(e)}")

    def delete_all_backups_history(self):
        checkboxes = getattr(self, "_backup_checkboxes", [])
        if not checkboxes:
            QMessageBox.information(self, "آرشیو خالی", "هیچ نسخه پشتیبانی در آرشیو برای حذف وجود ندارد.")
            return
        reply = QMessageBox.warning(
            self,
            "⚠️ حذف همگانی آرشیو پشتیبان",
            "آیا از پاک کردن تمامی نسخه‌های پشتیبان موجود در آرشیو اطمینان دارید؟\nاین عمل فایل‌ها را از روی حافظه سیستم پاک کرده و قابل بازگشت نیست.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                backups = BackupService.get_all_backups()
                deleted_cnt = 0
                for b in backups:
                    if BackupService.delete_backup(b.id):
                        deleted_cnt += 1
                self.load_backups()
                fa_del = str(deleted_cnt).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                QMessageBox.information(self, "موفقیت", f"تمامی {fa_del} نسخه پشتیبان آرشیو با موفقیت حذف گردید.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف همگانی نسخه‌های پشتیبان: {str(e)}")

    def open_backup_folder(self, filepath: str):
        if not filepath or filepath.startswith("☁️") or filepath.startswith("📧"):
            return
        p = Path(filepath)
        folder = p.parent if p.suffix else p
        if not folder.exists():
            QMessageBox.warning(self, "خطا", f"پوشه مورد نظر در حافظه سیستم یافت نشد:\n{folder}")
            return
        try:
            import subprocess
            if p.exists() and p.is_file():
                subprocess.Popen(f'explorer /select,"{os.path.normpath(str(p))}"')
            else:
                os.startfile(os.path.normpath(str(folder)))
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در باز کردن پوشه: {e}")

    def delete_backup_item(self, backup_id: int, file_name: str):
        reply = QMessageBox.warning(
            self,
            "⚠️ تایید حذف نسخه پشتیبان",
            f"آیا مطمئن هستید که می‌خواهید فایل پشتیبان «{file_name}» را حذف کنید؟\nاین فایل به طور کامل از روی حافظه سیستم پاک خواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if BackupService.delete_backup(backup_id):
                    QMessageBox.information(self, "موفقیت", f"نسخه پشتیبان «{file_name}» با موفقیت حذف گردید.")
                    self.load_backups()
                else:
                    QMessageBox.warning(self, "خطا", "یافتن یا حذف فایل پشتیبان با خطا مواجه شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف فایل پشتیبان: {str(e)}")

    def create_backup(self):
        from yalda.views.components.backup_destination_dialog import BackupDestinationDialog
        from datetime import datetime
        from yalda.utils.jalali_date import gregorian_to_shamsi

        dlg = BackupDestinationDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selected_choice:
            return

        choice = dlg.selected_choice

        if choice == BackupDestinationDialog.CHOICE_SYSTEM:
            now = datetime.now()
            shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
            time_str = now.strftime("%H-%M-%S")
            default_filename = f"yalda_backup_{shamsi_date}_{time_str}.zip"

            from yalda.utils.export_utils import resolve_gym_export_path
            chosen_file, gym_folder_name = resolve_gym_export_path(
                default_filename,
                self,
                "انتخاب محل ذخیره نسخه پشتیبان در سیستم",
                "فایل فشرده پشتیبان (*.zip)"
            )
            if not chosen_file:
                return

            try:
                filepath = BackupService.create_backup(target_filepath=chosen_file)
                self.load_backups()
                from yalda.utils.logger import log_info
                log_info(f"Local backup created: {filepath}")
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"✅ نسخه پشتیبان با موفقیت در پوشه اختصاصی «{gym_folder_name}» ذخیره گردید:\n\n{filepath}"
                )
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                from yalda.utils.logger import log_error
                from yalda.views.components.error_dialog import show_error_dialog
                log_error(f"Error creating local backup: {e}\n{tb}")
                show_error_dialog(
                    parent=self.window(),
                    message="متاسفانه در ایجاد نسخه پشتیبان خطایی رخ داد.",
                    technical_details=tb,
                    title="خطا در پشتیبان‌گیری"
                )

        elif choice == BackupDestinationDialog.CHOICE_SERVER:
            u = CurrentUser.get()
            phone = u.phone if (u and u.phone) else "09336427711"
            trainer_name = u.full_name if u else "مدیر باشگاه"
            self._start_cloud_backup_async(phone, trainer_name)

        elif choice == BackupDestinationDialog.CHOICE_EMAIL:
            u = CurrentUser.get()
            # 1. First priority: whatever is currently entered in the email field on screen
            input_email = self.txt_email.text().strip()
            if input_email.lower() == getattr(config, "SUPPORT_EMAIL_ADDRESS", "").lower():
                input_email = ""

            # 2. Second priority: email stored in trainer user record (excluding support email)
            db_email = (u.email or "").strip() if u else ""
            if db_email.lower() == getattr(config, "SUPPORT_EMAIL_ADDRESS", "").lower():
                db_email = ""

            target_email = input_email or db_email

            if not target_email:
                email_input, ok = QInputDialog.getText(
                    self,
                    "ثبت ایمیل مربی",
                    "آدرس ایمیل مربی جهت دریافت نسخه پشتیبان ثبت نشده است.\nلطفاً آدرس ایمیل خود را وارد نمایید:",
                    QLineEdit.EchoMode.Normal,
                    ""
                )
                if not ok or not email_input.strip():
                    return
                target_email = email_input.strip()

            # Validate basic email structure
            if "@" not in target_email or "." not in target_email:
                QMessageBox.warning(
                    self,
                    "خطا در آدرس ایمیل",
                    "لطفاً یک آدرس ایمیل معتبر (مانند user@example.com) وارد نمایید."
                )
                self.txt_email.setFocus()
                return

            self.txt_email.setText(target_email)

            # 3. Always save & sync this email to the coach profile in database so it is recognized permanently
            if u and (target_email != db_email):
                try:
                    update_trainer_profile(
                        user_id=u.id,
                        first_name=u.first_name,
                        last_name=u.last_name,
                        phone=u.phone,
                        email=target_email,
                        birth_date_shamsi=u.birth_date_shamsi,
                        photo_path=u.photo_path,
                        username=u.username
                    )
                    self.load_all_data()
                except Exception as ex:
                    print(f"Auto-sync email error: {ex}")

            # Determine trainer identity and ID
            trainer_id = None
            if u and getattr(u, "role", "") != "admin":
                trainer_id = u.id
                trainer_name = u.display_name or u.full_name
            else:
                trainer_name = u.display_name if u else "مدیر باشگاه"
                try:
                    from yalda.database.connection import SessionLocal
                    from yalda.models.database_models import User
                    with SessionLocal() as db:
                        tr = db.query(User).filter(
                            User.email.ilike(target_email.strip()),
                            User.role != "admin"
                        ).first()
                        if tr:
                            trainer_id = tr.id
                            trainer_name = tr.display_name or tr.full_name
                except Exception:
                    pass

            self._start_email_backup_async(target_email, trainer_name, trainer_id=trainer_id)

        elif choice == BackupDestinationDialog.CHOICE_INSTALL_DIR:
            try:
                filepath = BackupService.create_backup()
                self.load_backups()
                from yalda.utils.logger import log_info
                log_info(f"Local install dir backup created: {filepath}")
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"✅ نسخه پشتیبان با موفقیت در پوشه پیش‌فرض نصب نرم‌افزار ایجاد گردید:\n\n{filepath}"
                )
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                from yalda.utils.logger import log_error
                from yalda.views.components.error_dialog import show_error_dialog
                log_error(f"Error creating install dir backup: {e}\n{tb}")
                show_error_dialog(
                    parent=self.window(),
                    message="متاسفانه در ایجاد نسخه پشتیبان در پوشه پیش‌فرض نصب خطایی رخ داد.",
                    technical_details=tb,
                    title="خطا در پشتیبان‌گیری"
                )

    def _start_cloud_backup_async(self, phone: str, trainer_name: str):
        self.progress_card.setVisible(True)
        self.btn_prog_close.setVisible(False)
        if hasattr(self, "btn_prog_spam_guide"):
            self.btn_prog_spam_guide.setVisible(False)
        self.lbl_prog_title.setText("☁️ در حال ارسال نسخه پشتیبان به سرور ابری...")
        self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #F87171; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
        self.lbl_prog_detail.setText("در حال برقراری ارتباط با سرور ابری یلدا...")
        self.backup_progress_bar.setValue(10)
        self.backup_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444; border-radius: 6px; background-color: #18181B; text-align: center; color: #FFFFFF; font-weight: bold; font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #991B1B, stop:0.5 #DC2626, stop:1 #EF4444);
                border-radius: 5px;
            }
        """)

        self.cloud_worker = CloudBackupThread(phone, trainer_name)
        self.cloud_worker.progress_signal.connect(self._on_backup_progress)
        self.cloud_worker.finished_signal.connect(lambda ok, msg: self._on_cloud_backup_finished(ok, msg, phone))
        self.cloud_worker.start()

    def _start_email_backup_async(self, email: str, trainer_name: str, trainer_id: int = None):
        self.progress_card.setVisible(True)
        self.btn_prog_close.setVisible(False)
        if hasattr(self, "btn_prog_spam_guide"):
            self.btn_prog_spam_guide.setVisible(False)
        self.lbl_prog_title.setText("📧 در حال آماده‌سازی و ارسال نسخه پشتیبان به ایمیل مربی...")
        self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #F87171; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
        self.lbl_prog_detail.setText(f"در حال ایجاد بسته و ارسال به نشانی {email}...")
        self.backup_progress_bar.setValue(10)
        self.backup_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444; border-radius: 6px; background-color: #18181B; text-align: center; color: #FFFFFF; font-weight: bold; font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #991B1B, stop:0.5 #DC2626, stop:1 #EF4444);
                border-radius: 5px;
            }
        """)

        self.email_worker = EmailBackupThread(email, trainer_name, trainer_id=trainer_id)
        self.email_worker.progress_signal.connect(self._on_backup_progress)
        self.email_worker.finished_signal.connect(lambda ok, msg, fn, sz: self._on_email_backup_finished(ok, msg, email, fn, sz))
        self.email_worker.start()

    def _on_backup_progress(self, percent: int, detail_msg: str):
        self.backup_progress_bar.setValue(percent)
        self.lbl_prog_detail.setText(detail_msg)

    def _on_cloud_backup_finished(self, success: bool, msg: str, phone: str):
        self.btn_prog_close.setVisible(True)
        if success:
            BackupService.record_cloud_backup(phone)
            self.load_backups()
            self.lbl_prog_title.setText("✅ پشتیبان‌گیری در سرور ابری با موفقیت تکمیل شد!")
            self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #10B981; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
            self.lbl_prog_detail.setText(msg)
            self.backup_progress_bar.setValue(100)
            self.backup_progress_bar.setStyleSheet("""
                QProgressBar { border: 1px solid #059669; border-radius: 6px; background-color: #18181B; text-align: center; color: #FFFFFF; font-weight: bold; font-size: 11px; }
                QProgressBar::chunk { background-color: #10B981; border-radius: 5px; }
            """)
            QTimer.singleShot(6000, lambda: self.progress_card.setVisible(False))
        else:
            self.lbl_prog_title.setText("❌ خطا در پشتیبان‌گیری ابری")
            self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #EF4444; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
            self.lbl_prog_detail.setText(f"خطا: {msg}")

    def _on_email_backup_finished(self, success: bool, msg: str, email: str, filename: str, size_mb: float):
        self.btn_prog_close.setVisible(True)
        if success:
            BackupService.record_email_backup(email, filename, size_mb)
            self.load_backups()
            self.lbl_prog_title.setText("✅ نسخه پشتیبان با موفقیت به ایمیل مربی ارسال شد!")
            self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #10B981; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
            self.lbl_prog_detail.setText(f"فایل {filename} ({size_mb} MB) به نشانی {email} فرستاده شد. (در صورت عدم مشاهده در اینباکس، پوشه Spam را بررسی فرمایید)")
            self.backup_progress_bar.setValue(100)
            self.backup_progress_bar.setStyleSheet("""
                QProgressBar { border: 1px solid #059669; border-radius: 6px; background-color: #18181B; text-align: center; color: #FFFFFF; font-weight: bold; font-size: 11px; }
                QProgressBar::chunk { background-color: #10B981; border-radius: 5px; }
            """)
            if hasattr(self, "btn_prog_spam_guide"):
                self.btn_prog_spam_guide.setVisible(True)
            QTimer.singleShot(15000, lambda: self.progress_card.setVisible(False))
        else:
            self.lbl_prog_title.setText("❌ خطا در ارسال ایمیل پشتیبان")
            self.lbl_prog_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #EF4444; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
            self.lbl_prog_detail.setText(f"خطا: {msg}")

    def open_spam_guide_dialog(self):
        from yalda.views.components.email_spam_guide_dialog import EmailSpamGuideDialog
        dialog = EmailSpamGuideDialog(self)
        dialog.exec()

    def open_cloud_restore_dialog(self):
        from yalda.views.cloud_restore_dialog import CloudRestoreDialog
        u = CurrentUser.get()
        init_phone = u.phone if u else ""
        dlg = CloudRestoreDialog(self, initial_phone=init_phone)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_all_data()

    def restore_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل پشتیبان",
            "",
            "فایل‌های پشتیبان (*.db *.zip *.yalda_bak);;پایگاه‌داده SQLite (*.db);;فایل فشرده (*.zip)"
        )
        if filepath:
            self.restore_backup(filepath)

    def restore_backup(self, filepath: str):
        if not filepath:
            return
        if filepath.startswith("☁️"):
            self.open_cloud_restore_dialog()
            return
        if filepath.startswith("📧"):
            QMessageBox.information(
                self,
                "نسخه ارسالی به ایمیل",
                "این نسخه پشتیبان به ایمیل مربی ارسال شده است.\nجهت بازگردانی، فایل پیوست ارسال‌شده به ایمیلتان را دانلود نموده و از طریق دکمه «📁 بازگردانی از فایل خارجی...» آن را انتخاب کنید."
            )
            return

        reply = QMessageBox.warning(
            self,
            "تایید بازگردانی اطلاعات",
            "⚠️ آیا مطمئن هستید؟ با بازگردانی اطلاعات، تمام داده‌های فعلی جایگزین خواهند شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                BackupService.restore_backup(filepath)
                QMessageBox.information(self, "موفقیت", "اطلاعات دیتابیس و تصاویر با موفقیت بازگردانی شد. لطفا برنامه را یکبار باز و بست کنید.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در بازگردانی: {str(e)}")

    def delete_current_trainer_account(self):
        u = CurrentUser.get()
        if not u:
            return

        if u.username == "admin" or u.role == "admin":
            QMessageBox.warning(self, "خطا", "حساب کاربری مدیر ارشد سیستم قابل حذف نمی‌باشد.")
            return

        reply1 = QMessageBox.warning(
            self,
            "⚠️ هشدار حذف کامل حساب کاربری مربی",
            f"آیا مطمئن هستید که می‌خواهید حساب کاربری «{u.display_name}» را به همراه کلیه شاگردان، سوابق و برنامه‌ها حذف کنید؟\n\nاین عملیات غیرقابل بازگشت است!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply1 != QMessageBox.StandardButton.Yes:
            return

        reply2 = QMessageBox.critical(
            self,
            "🔴 تایید نهایی حذف",
            "کلیه اطلاعات این مربی از حافظه سیستم و سرور ابری پاک خواهد شد. آیا تایید نهایی را صادر می‌کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply2 == QMessageBox.StandardButton.Yes:
            try:
                delete_trainer_account(u.id)
                QMessageBox.information(self, "موفقیت", "حساب کاربری مربی و تمامی اطلاعات شاگردان با موفقیت حذف گردید.")
                CurrentUser.logout()
                self.account_deleted_signal.emit()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف حساب کاربری: {str(e)}")

