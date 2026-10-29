import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QGroupBox, QGridLayout, QComboBox, QScrollArea, QFrame, QTabWidget, QTextBrowser,
    QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices
import config
from nemov.auth.authentication import (
    CurrentUser, get_developer_info, set_developer_info, is_app_license_active, set_app_license_active
)
from nemov.utils.image_utils import get_circular_pixmap
from nemov.services.update_service import (
    UpdateService, UpdateCheckWorker, UpdateDownloadWorker, format_bytes
)


class DeveloperView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.selected_dev_photo_path = None
        self._check_worker = None
        self._download_worker = None
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()
        # Mark update notification as seen so it won't repeat in the sidebar
        UpdateService.mark_notification_seen()

    def init_ui(self):
        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(16, 12, 16, 12)
        main_vbox.setSpacing(10)

        # Header Title and Back Button
        header_frame = QFrame()
        header_frame.setObjectName("devHeaderCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(14)

        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)

        title = QLabel("ℹ️ درباره نرم‌افزار نِمو و اطلاعات برنامه‌نویس")
        title.setObjectName("h1")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")

        header_layout.addWidget(btn_back)
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_vbox.addWidget(header_frame)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tab_app_info = self._create_app_info_tab()
        self.tab_dev_info = self._create_dev_info_tab()

        self.tabs.addTab(self.tab_app_info, "ℹ️  اطلاعات برنامه")
        self.tabs.addTab(self.tab_dev_info, "👨‍💻  اطلاعات برنامه‌نویس")

        main_vbox.addWidget(self.tabs, 1)

    # =========================================================================
    # TAB 1: اطلاعات و به‌روزرسانی برنامه
    # =========================================================================
    def _create_app_info_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 12, 14, 16)
        layout.setSpacing(16)

        # ----------------------------------------------------
        # BOX 1: شناسنامه و مشخصات نرم‌افزار
        # ----------------------------------------------------
        app_box = QGroupBox("📋 مشخصات و شناسنامه نرم‌افزار")
        layout_app = QVBoxLayout(app_box)
        layout_app.setContentsMargins(18, 16, 18, 16)
        layout_app.setSpacing(14)

        # Row 1: Logo & Titles
        row_id = QHBoxLayout()
        row_id.setSpacing(16)

        self.lbl_app_logo = QLabel()
        self.lbl_app_logo.setFixedSize(60, 60)
        self.lbl_app_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_app_logo()

        v_app_text = QVBoxLayout()
        v_app_text.setSpacing(4)
        lbl_app_name = QLabel(config.APP_TITLE)
        lbl_app_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")

        row_meta = QHBoxLayout()
        row_meta.setSpacing(10)
        
        lbl_cur_ver = QLabel(f"🏷️ نسخه فعلی: {config.APP_VERSION}")
        lbl_cur_ver.setStyleSheet("font-size: 12px; color: #60A5FA; font-weight: bold;")

        lbl_platform = QLabel("💻 پلتفرم: ویندوز (نسخه ۶۴ بیتی)")
        lbl_platform.setStyleSheet("font-size: 12px; color: #A0AEC0;")

        row_meta.addWidget(lbl_cur_ver)
        row_meta.addWidget(QLabel("•"))
        row_meta.addWidget(lbl_platform)
        row_meta.addStretch()

        v_app_text.addWidget(lbl_app_name)
        v_app_text.addLayout(row_meta)

        row_id.addWidget(self.lbl_app_logo)
        row_id.addLayout(v_app_text)
        row_id.addStretch()
        layout_app.addLayout(row_id)

        # Row 2: License Control
        layout_lic = QHBoxLayout()
        layout_lic.setContentsMargins(0, 8, 0, 0)
        layout_lic.setSpacing(12)

        lbl_lic_status = QLabel("وضعیت لایسنس برنامه:")
        lbl_lic_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #E2E8F0;")

        self.combo_license = QComboBox()
        self.combo_license.setFixedHeight(36)
        self.combo_license.setMinimumWidth(320)
        self.combo_license.addItem("🔴 غیرفعال (غیرقابل استفاده در سیستم‌های جدید)", "false")
        self.combo_license.addItem("🟢 فعال و قفل‌شده برای این رایانه", "true")

        self.btn_save_license = QPushButton("💾 ثبت وضعیت برنامه")
        self.btn_save_license.setFixedHeight(36)
        self.btn_save_license.setMinimumWidth(170)
        self.btn_save_license.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_license.clicked.connect(self.save_license_status)

        layout_lic.addWidget(lbl_lic_status)
        layout_lic.addWidget(self.combo_license)
        layout_lic.addWidget(self.btn_save_license)
        layout_lic.addStretch()
        layout_app.addLayout(layout_lic)

        layout.addWidget(app_box)

        # ----------------------------------------------------
        # BOX 2: مرکز به‌روزرسانی و بررسی نسخه جدید نِمو
        # ----------------------------------------------------
        update_box = QGroupBox("🚀 مرکز به‌روزرسانی و دریافت نسخه جدید")
        layout_update = QVBoxLayout(update_box)
        layout_update.setContentsMargins(18, 16, 18, 16)
        layout_update.setSpacing(14)

        # Header row of update box: Button & Last check timestamp
        row_up_header = QHBoxLayout()
        row_up_header.setSpacing(14)

        self.btn_check_update = QPushButton("🔍 بررسی نسخه جدید")
        self.btn_check_update.setFixedHeight(38)
        self.btn_check_update.setMinimumWidth(180)
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 0 16px;
                border: 1px solid #1D4ED8;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #9CA3AF;
                border: 1px solid #4B5563;
            }
        """)
        self.btn_check_update.clicked.connect(self.check_for_updates_manual)

        self.lbl_last_check = QLabel("آخرین بررسی: هنوز انجام نشده")
        self.lbl_last_check.setStyleSheet("color: #9CA3AF; font-size: 12px;")

        row_up_header.addWidget(self.btn_check_update)
        row_up_header.addWidget(self.lbl_last_check)
        row_up_header.addStretch()
        layout_update.addLayout(row_up_header)

        # Dynamic Status Container
        self.update_status_card = QFrame()
        self.update_status_card.setStyleSheet("""
            QFrame {
                background-color: #1A202C;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout_status = QVBoxLayout(self.update_status_card)
        layout_status.setContentsMargins(14, 12, 14, 12)
        layout_status.setSpacing(10)

        # 1. Info / Initial State Label
        self.lbl_update_headline = QLabel("جهت بررسی وجود نسخه جدید در گیت‌هاب، روی دکمه «بررسی نسخه جدید» کلیک فرمایید.")
        self.lbl_update_headline.setStyleSheet("color: #E2E8F0; font-size: 13px; line-height: 1.5;")
        self.lbl_update_headline.setWordWrap(True)
        layout_status.addWidget(self.lbl_update_headline)

        # 2. Changelog Section (Visible when update is found)
        self.changelog_container = QWidget()
        v_cl = QVBoxLayout(self.changelog_container)
        v_cl.setContentsMargins(0, 4, 0, 4)
        v_cl.setSpacing(6)

        lbl_cl_title = QLabel("📋 قابلیت‌ها و تغییرات نسخه جدید:")
        lbl_cl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F59E0B;")
        v_cl.addWidget(lbl_cl_title)

        self.txt_changelog = QTextBrowser()
        self.txt_changelog.setFixedHeight(160)
        self.txt_changelog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.txt_changelog.setOpenExternalLinks(True)
        self.txt_changelog.setStyleSheet("""
            QTextBrowser {
                background-color: #111827;
                color: #E5E7EB;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Vazirmatn', sans-serif;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        v_cl.addWidget(self.txt_changelog)
        layout_status.addWidget(self.changelog_container)
        self.changelog_container.setVisible(False)

        # 3. Download Progress Panel
        self.download_panel = QWidget()
        v_dl = QVBoxLayout(self.download_panel)
        v_dl.setContentsMargins(0, 4, 0, 4)
        v_dl.setSpacing(6)

        self.lbl_download_progress = QLabel("در حال دریافت نسخه جدید...")
        self.lbl_download_progress.setStyleSheet("font-size: 12px; color: #60A5FA; font-weight: bold;")
        v_dl.addWidget(self.lbl_download_progress)

        self.bar_download = QProgressBar()
        self.bar_download.setFixedHeight(8)
        self.bar_download.setTextVisible(False)
        self.bar_download.setRange(0, 100)
        self.bar_download.setValue(0)
        self.bar_download.setStyleSheet("""
            QProgressBar {
                background-color: #374151;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 4px;
            }
        """)
        v_dl.addWidget(self.bar_download)
        layout_status.addWidget(self.download_panel)
        self.download_panel.setVisible(False)

        # 4. Action Buttons (Download, Apply, Cancel, Browser)
        self.row_up_actions = QHBoxLayout()
        self.row_up_actions.setSpacing(10)

        # In-App Download Button
        self.btn_download = QPushButton("📥 دانلود و دریافت نسخه جدید")
        self.btn_download.setFixedHeight(38)
        self.btn_download.setMinimumWidth(210)
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 0 18px;
                border: 1px solid #047857;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_download.clicked.connect(self.start_download)
        self.row_up_actions.addWidget(self.btn_download)

        # Cancel Download Button
        self.btn_cancel_dl = QPushButton("✖️ لغو دانلود")
        self.btn_cancel_dl.setFixedHeight(38)
        self.btn_cancel_dl.setMinimumWidth(110)
        self.btn_cancel_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_dl.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
                padding: 0 14px;
                border: 1px solid #B91C1C;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_cancel_dl.clicked.connect(self.cancel_download)
        self.row_up_actions.addWidget(self.btn_cancel_dl)
        self.btn_cancel_dl.setVisible(False)

        # Apply Update Button (Runs installer and exits app)
        self.btn_apply_update = QPushButton("🚀 اعمال به‌روزرسانی و نصب نسخه جدید")
        self.btn_apply_update.setFixedHeight(40)
        self.btn_apply_update.setMinimumWidth(260)
        self.btn_apply_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_update.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 0 20px;
                border: 1px solid #059669;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_apply_update.clicked.connect(self.apply_update_now)
        self.row_up_actions.addWidget(self.btn_apply_update)
        self.btn_apply_update.setVisible(False)

        # Fallback Browser Download Button
        self.btn_browser_download = QPushButton("🌐 دانلود دستی با مرورگر")
        self.btn_browser_download.setFixedHeight(38)
        self.btn_browser_download.setMinimumWidth(170)
        self.btn_browser_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browser_download.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
                padding: 0 14px;
                border: 1px solid #4B5563;
            }
            QPushButton:hover {
                background-color: #4B5563;
                color: #FFFFFF;
            }
        """)
        self.btn_browser_download.clicked.connect(self.open_browser_download)
        self.row_up_actions.addWidget(self.btn_browser_download)

        self.row_up_actions.addStretch()
        layout_status.addLayout(self.row_up_actions)

        # By default, action buttons are hidden until an update check runs
        self.btn_download.setVisible(False)
        self.btn_browser_download.setVisible(False)

        layout_update.addWidget(self.update_status_card)
        layout.addWidget(update_box)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _load_app_logo(self):
        try:
            from nemov.utils.image_utils import get_app_icon
            pix = get_app_icon().pixmap(54, 54)
            if not pix.isNull():
                self.lbl_app_logo.setPixmap(pix)
            else:
                self.lbl_app_logo.setText("🏆")
                self.lbl_app_logo.setStyleSheet("font-size: 38px;")
        except Exception:
            self.lbl_app_logo.setText("🏆")
            self.lbl_app_logo.setStyleSheet("font-size: 38px;")

    # =========================================================================
    # TAB 2: اطلاعات و مشخصات برنامه‌نویس
    # =========================================================================
    def _create_dev_info_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 12, 14, 16)
        layout.setSpacing(16)

        # ----------------------------------------------------
        # BOX 1: معرفی برنامه‌نویس
        # ----------------------------------------------------
        card_box = QGroupBox("📋 اطلاعات توسعه‌دهنده")
        layout_card = QHBoxLayout(card_box)
        layout_card.setContentsMargins(20, 20, 20, 20)
        layout_card.setSpacing(20)

        self.lbl_dev_photo = QLabel()
        self.lbl_dev_photo.setFixedSize(110, 110)
        self.lbl_dev_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v_info = QVBoxLayout()
        SELECTABLE_FLAGS = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse

        self.lbl_dev_full_name = QLabel("مهندس ابوالفضل صمدی کوچکسرائی")
        self.lbl_dev_full_name.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_full_name.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")

        # Fixed spelling to نِمو and removed "، پیاده‌ساز" and "(Nemov)" as requested
        self.lbl_dev_role = QLabel("طراح و توسعه‌دهنده نرم‌افزار مدیریت ورزشی نِمو")
        self.lbl_dev_role.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_role.setStyleSheet("font-size: 13px; color: #E53E3E; font-weight: bold;")

        v_info.addWidget(self.lbl_dev_full_name)
        v_info.addWidget(self.lbl_dev_role)
        v_info.addSpacing(6)

        icons_dir = config.BASE_DIR / "resources" / "images" / "icons"

        # Row 1: Phone
        row_phone = QHBoxLayout()
        row_phone.setSpacing(10)
        self.ico_phone = QLabel()
        self.ico_phone.setFixedSize(22, 22)
        phone_pix = QPixmap(str(icons_dir / "hd_icon_phone.png"))
        if not phone_pix.isNull():
            self.ico_phone.setPixmap(phone_pix.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_dev_phone = QLabel()
        self.lbl_dev_phone.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_phone.setStyleSheet("font-size: 14px; color: #DDDDDD;")
        row_phone.addWidget(self.ico_phone)
        row_phone.addWidget(self.lbl_dev_phone)
        row_phone.addStretch()

        # Row 2: Email (Gmail)
        row_email = QHBoxLayout()
        row_email.setSpacing(10)
        self.ico_email = QLabel()
        self.ico_email.setFixedSize(22, 22)
        email_pix = QPixmap(str(icons_dir / "hd_icon_gmail.png"))
        if not email_pix.isNull():
            self.ico_email.setPixmap(email_pix.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_dev_email = QLabel()
        self.lbl_dev_email.setOpenExternalLinks(True)
        self.lbl_dev_email.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_email.setStyleSheet("font-size: 14px; color: #DDDDDD;")
        row_email.addWidget(self.ico_email)
        row_email.addWidget(self.lbl_dev_email)
        row_email.addStretch()

        # Row 3: Telegram
        row_telegram = QHBoxLayout()
        row_telegram.setSpacing(10)
        self.ico_telegram = QLabel()
        self.ico_telegram.setFixedSize(22, 22)
        tg_pix = QPixmap(str(icons_dir / "hd_icon_telegram.png"))
        if not tg_pix.isNull():
            self.ico_telegram.setPixmap(tg_pix.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_dev_telegram = QLabel()
        self.lbl_dev_telegram.setOpenExternalLinks(True)
        self.lbl_dev_telegram.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_telegram.setStyleSheet("font-size: 14px; color: #DDDDDD;")
        row_telegram.addWidget(self.ico_telegram)
        row_telegram.addWidget(self.lbl_dev_telegram)
        row_telegram.addStretch()

        # Row 4: GitHub
        row_github = QHBoxLayout()
        row_github.setSpacing(10)
        self.ico_github = QLabel()
        self.ico_github.setFixedSize(22, 22)
        gh_pix = QPixmap(str(icons_dir / "hd_icon_github.png"))
        if not gh_pix.isNull():
            self.ico_github.setPixmap(gh_pix.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_dev_github = QLabel()
        self.lbl_dev_github.setOpenExternalLinks(True)
        self.lbl_dev_github.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_github.setStyleSheet("font-size: 14px; color: #DDDDDD;")
        row_github.addWidget(self.ico_github)
        row_github.addWidget(self.lbl_dev_github)
        row_github.addStretch()

        v_info.addLayout(row_phone)
        v_info.addLayout(row_email)
        v_info.addLayout(row_telegram)
        v_info.addLayout(row_github)

        layout_card.addWidget(self.lbl_dev_photo)
        layout_card.addLayout(v_info)
        layout_card.addStretch()
        layout.addWidget(card_box)

        # ----------------------------------------------------
        # BOX 2: ویرایش مشخصات توسط ادمین کل
        # ----------------------------------------------------
        self.dev_edit_box = QGroupBox("⚙️ ویرایش اطلاعات شناسنامه‌ای برنامه‌نویس (مخصوص ادمین کل)")
        layout_dev_edit = QVBoxLayout(self.dev_edit_box)
        layout_dev_edit.setSpacing(12)
        layout_dev_edit.setContentsMargins(15, 15, 15, 15)

        grid_dev = QGridLayout()
        grid_dev.setHorizontalSpacing(15)
        grid_dev.setVerticalSpacing(10)

        # Photo Picker
        self.lbl_dev_photo_edit = QLabel("📷 عکس")
        self.lbl_dev_photo_edit.setFixedSize(60, 60)
        self.lbl_dev_photo_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_dev_photo_edit.setStyleSheet("border: 1px dashed #666; border-radius: 30px; color: #888;")

        btn_dev_photo = QPushButton("📷 تغییر عکس برنامه‌نویس")
        btn_dev_photo.setFixedHeight(36)
        btn_dev_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dev_photo.clicked.connect(self.choose_dev_photo)

        v_dev_pic = QVBoxLayout()
        v_dev_pic.addWidget(self.lbl_dev_photo_edit, alignment=Qt.AlignmentFlag.AlignCenter)
        v_dev_pic.addWidget(btn_dev_photo)
        grid_dev.addLayout(v_dev_pic, 0, 0, 2, 1)

        self.txt_dev_fname = QLineEdit()
        self.txt_dev_fname.setFixedHeight(36)
        self.txt_dev_lname = QLineEdit()
        self.txt_dev_lname.setFixedHeight(36)

        grid_dev.addWidget(QLabel("نام:"), 0, 1)
        grid_dev.addWidget(self.txt_dev_fname, 0, 2)
        grid_dev.addWidget(QLabel("نام خانوادگی:"), 0, 3)
        grid_dev.addWidget(self.txt_dev_lname, 0, 4)

        self.txt_dev_phone = QLineEdit()
        self.txt_dev_phone.setFixedHeight(36)
        self.txt_dev_phone.setMaxLength(11)
        self.txt_dev_email = QLineEdit()
        self.txt_dev_email.setFixedHeight(36)

        grid_dev.addWidget(QLabel("شماره همراه:"), 1, 1)
        grid_dev.addWidget(self.txt_dev_phone, 1, 2)
        grid_dev.addWidget(QLabel("ایمیل:"), 1, 3)
        grid_dev.addWidget(self.txt_dev_email, 1, 4)

        self.txt_dev_telegram = QLineEdit()
        self.txt_dev_telegram.setFixedHeight(36)
        self.txt_dev_github = QLineEdit()
        self.txt_dev_github.setFixedHeight(36)

        grid_dev.addWidget(QLabel("آیدی تلگرام:"), 2, 1)
        grid_dev.addWidget(self.txt_dev_telegram, 2, 2)
        grid_dev.addWidget(QLabel("آدرس گیت‌هاب:"), 2, 3)
        grid_dev.addWidget(self.txt_dev_github, 2, 4)

        layout_dev_edit.addLayout(grid_dev)

        row_dev_actions = QHBoxLayout()
        row_dev_actions.setSpacing(12)

        self.btn_save_dev = QPushButton("💾 ذخیره تغییرات اطلاعات برنامه‌نویس")
        self.btn_save_dev.setFixedHeight(38)
        self.btn_save_dev.setFixedWidth(240)
        self.btn_save_dev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_dev.setStyleSheet("""
            QPushButton { background-color: #065F46; color: white; border-radius: 6px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #047857; }
            QPushButton:disabled { background-color: #2D2D2D; color: #777777; border: 1px solid #444444; }
        """)
        self.btn_save_dev.setEnabled(False)
        self.btn_save_dev.clicked.connect(self.save_dev_info)
        row_dev_actions.addWidget(self.btn_save_dev)

        self.btn_reset_dev = QPushButton("🔄 بازنشانی / لغو تغییرات")
        self.btn_reset_dev.setFixedHeight(38)
        self.btn_reset_dev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_dev.setObjectName("secondary_button")
        self.btn_reset_dev.setEnabled(False)
        self.btn_reset_dev.clicked.connect(self.revert_dev_changes)
        row_dev_actions.addWidget(self.btn_reset_dev)
        row_dev_actions.addStretch()

        layout_dev_edit.addLayout(row_dev_actions)

        # Connect listeners to detect dev info changes
        self.txt_dev_fname.textChanged.connect(self.check_dev_dirty)
        self.txt_dev_lname.textChanged.connect(self.check_dev_dirty)
        self.txt_dev_phone.textChanged.connect(self.check_dev_dirty)
        self.txt_dev_email.textChanged.connect(self.check_dev_dirty)
        self.txt_dev_telegram.textChanged.connect(self.check_dev_dirty)
        self.txt_dev_github.textChanged.connect(self.check_dev_dirty)

        layout.addWidget(self.dev_edit_box)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    # =========================================================================
    # UPDATE SYSTEM LOGIC
    # =========================================================================
    def check_for_updates_manual(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("⏳ در حال بررسی...")
        self.lbl_update_headline.setText("در حال ارتباط با مخزن گیت‌هاب و بررسی وضعیت آخرین نسخه...")
        self.lbl_update_headline.setStyleSheet("color: #60A5FA; font-size: 13px;")

        self._check_worker = UpdateCheckWorker(current_version=config.APP_VERSION)
        self._check_worker.finished_signal.connect(self._on_check_finished)
        self._check_worker.start()

    def _on_check_finished(self, has_update: bool, info: dict, error_msg: str):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔍 بررسی مجدد نسخه جدید")

        if error_msg:
            self.lbl_update_headline.setText(f"⚠️ {error_msg}")
            self.lbl_update_headline.setStyleSheet("color: #F87171; font-size: 13px;")
            self.changelog_container.setVisible(False)
            self.btn_download.setVisible(False)
            self.btn_browser_download.setVisible(False)
            return

        UpdateService.set_check_result(has_update, info)
        self.lbl_last_check.setText(f"آخرین بررسی: {UpdateService.get_last_check_time()}")

        if not has_update:
            tag = info.get("tag_name", config.APP_VERSION)
            self.lbl_update_headline.setText(
                f"✅ نرم‌افزار نِمو کاملاً به‌روز است!\n"
                f"شما در حال حاضر از جدیدترین و پایدارترین نسخه موجود ({tag}) استفاده می‌فرمایید."
            )
            self.lbl_update_headline.setStyleSheet("color: #34D399; font-size: 13px; line-height: 1.6;")
            self.changelog_container.setVisible(False)
            self.btn_download.setVisible(False)
            self.btn_browser_download.setVisible(False)
            self.btn_apply_update.setVisible(False)
        else:
            tag = info.get("tag_name", "")
            title = info.get("name", tag)
            size_str = format_bytes(info.get("asset_size", 0))

            self.lbl_update_headline.setText(
                f"🎉 نسخه جدید ({tag}) منتشر شد!\n"
                f"عنوان انتشار: {title}\n"
                f"حجم فایل: {size_str}"
            )
            self.lbl_update_headline.setStyleSheet("color: #FBBF24; font-size: 13px; line-height: 1.6; font-weight: bold;")

            body_text = info.get("body", "").strip() or "تغییرات و بهینه‌سازی‌های نرم‌افزار نِمو اعمال شده است."
            self.txt_changelog.setMarkdown(body_text)
            self.changelog_container.setVisible(True)

            # Check if installer is already downloaded
            downloaded = UpdateService.get_downloaded_installer()
            if downloaded and Path(downloaded).name == info.get("asset_name"):
                self.btn_apply_update.setVisible(True)
                self.btn_download.setVisible(False)
            else:
                self.btn_apply_update.setVisible(False)
                self.btn_download.setVisible(True)

            self.btn_browser_download.setVisible(True)

    def start_download(self):
        info = UpdateService.get_latest_info()
        download_url = info.get("download_url")
        asset_name = info.get("asset_name")

        if not download_url:
            QMessageBox.warning(self, "خطا در لینک دانلود", "لینک دانلود مستقیمی برای این نسخه یافت نشد.")
            return

        self.btn_download.setVisible(False)
        self.btn_cancel_dl.setVisible(True)
        self.download_panel.setVisible(True)
        self.bar_download.setValue(0)
        self.lbl_download_progress.setText("در حال آماده‌سازی و اتصال به سرور دانلود...")

        self._download_worker = UpdateDownloadWorker(download_url=download_url, asset_name=asset_name)
        self._download_worker.progress_signal.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_progress(self, percent: int, downloaded: int, total: int):
        self.bar_download.setValue(percent)
        fa_pct = str(percent).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        dl_str = format_bytes(downloaded)
        tot_str = format_bytes(total)
        self.lbl_download_progress.setText(f"در حال دریافت نسخه جدید... {fa_pct}٪ ({dl_str} از {tot_str})")

    def _on_download_finished(self, success: bool, file_path: str, error_msg: str):
        self.btn_cancel_dl.setVisible(False)

        if not success:
            self.download_panel.setVisible(False)
            self.btn_download.setVisible(True)
            if error_msg != "دانلود توسط کاربر لغو شد.":
                QMessageBox.critical(self, "خطا در دانلود", error_msg)
            return

        # Success!
        UpdateService.set_downloaded_installer(file_path)
        self.bar_download.setValue(100)
        self.lbl_download_progress.setText("✅ دانلود نسخه جدید با موفقیت تکمیل شد!")
        self.lbl_download_progress.setStyleSheet("font-size: 12px; color: #34D399; font-weight: bold;")
        self.btn_apply_update.setVisible(True)

    def cancel_download(self):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
        self.btn_cancel_dl.setVisible(False)
        self.download_panel.setVisible(False)
        self.btn_download.setVisible(True)

    def apply_update_now(self):
        installer_path = UpdateService.get_downloaded_installer()
        if not installer_path or not os.path.exists(installer_path):
            QMessageBox.warning(self, "فایل به‌روزرسانی یافت نشد", "فایل به‌روزرسانی یافت نشد. لطفاً مجدداً دانلود نمایید.")
            self.btn_apply_update.setVisible(False)
            self.btn_download.setVisible(True)
            return

        reply = QMessageBox.question(
            self,
            "اعمال به‌روزرسانی نِمو",
            "جهت نصب نسخه جدید، نرم‌افزار نِمو بسته شده و فرایند نصب آغاز خواهد شد.\n\nآیا مایل به خروج و اعمال به‌روزرسانی هستید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            UpdateService.apply_update_and_exit(installer_path)

    def open_browser_download(self):
        info = UpdateService.get_latest_info()
        url = info.get("download_url") or info.get("html_url") or f"https://github.com/{config.APP_ENGLISH_NAME}"
        QDesktopServices.openUrl(QUrl(url))

    # =========================================================================
    # DEVELOPER & LICENSE MANAGEMENT
    # =========================================================================
    def check_dev_dirty(self):
        if getattr(self, "_loading_dev", False):
            return
        current = {
            "first_name": self.txt_dev_fname.text().strip(),
            "last_name": self.txt_dev_lname.text().strip(),
            "phone": self.txt_dev_phone.text().strip(),
            "email": self.txt_dev_email.text().strip(),
            "telegram": self.txt_dev_telegram.text().strip(),
            "github": self.txt_dev_github.text().strip(),
            "photo_path": self.selected_dev_photo_path or ""
        }
        is_dirty = (current != getattr(self, "_baseline_dev", {}))
        self.btn_save_dev.setEnabled(is_dirty)
        if hasattr(self, "btn_reset_dev"):
            self.btn_reset_dev.setEnabled(is_dirty)

    def revert_dev_changes(self):
        base = getattr(self, "_baseline_dev", {})
        if not base:
            return
        self._loading_dev = True
        self.txt_dev_fname.setText(base.get("first_name", ""))
        self.txt_dev_lname.setText(base.get("last_name", ""))
        self.txt_dev_phone.setText(base.get("phone", ""))
        self.txt_dev_email.setText(base.get("email", ""))
        self.txt_dev_telegram.setText(base.get("telegram", ""))
        self.txt_dev_github.setText(base.get("github", ""))
        self.selected_dev_photo_path = base.get("photo_path")
        if self.selected_dev_photo_path and os.path.exists(self.selected_dev_photo_path):
            pixmap = QPixmap(self.selected_dev_photo_path)
            circ_edit = get_circular_pixmap(pixmap, 60)
            self.lbl_dev_photo_edit.setPixmap(circ_edit)
            self.lbl_dev_photo_edit.setText("")
            self.lbl_dev_photo_edit.setStyleSheet("border: none; background: transparent;")
        else:
            self.lbl_dev_photo_edit.setPixmap(QPixmap())
            self.lbl_dev_photo_edit.setText("📷")
            self.lbl_dev_photo_edit.setStyleSheet("border: 1px dashed #666; border-radius: 30px; color: #888;")
        self._loading_dev = False
        self.btn_save_dev.setEnabled(False)
        if hasattr(self, "btn_reset_dev"):
            self.btn_reset_dev.setEnabled(False)

    def choose_dev_photo(self):
        from nemov.utils.image_source_chooser import get_image_file_path

        temp_path = get_image_file_path(
            self,
            dialog_title="انتخاب یا ثبت تصویر برنامه‌نویس",
            file_filter="فایل‌های تصویری (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if temp_path and os.path.exists(temp_path):
            dest_dir = config.PROFILE_PHOTOS_DIR
            dest_dir.mkdir(parents=True, exist_ok=True)
            ext = Path(temp_path).suffix or ".jpg"
            filename = f"developer_photo{ext}"
            dest_path = dest_dir / filename
            import shutil
            shutil.copy2(temp_path, dest_path)
            self.selected_dev_photo_path = str(dest_path)
            pixmap = QPixmap(str(dest_path))
            circ = get_circular_pixmap(pixmap, 60)
            self.lbl_dev_photo_edit.setPixmap(circ)
            self.lbl_dev_photo_edit.setText("")
            self.lbl_dev_photo_edit.setStyleSheet("border: none; background: transparent;")
            self.check_dev_dirty()

    def save_dev_info(self):
        if not CurrentUser.is_admin():
            QMessageBox.warning(self, "عدم دسترسی", "ویرایش اطلاعات برنامه‌نویس فقط توسط ادمین کل (admin) امکان‌پذیر است.")
            return

        data = {
            "first_name": self.txt_dev_fname.text().strip(),
            "last_name": self.txt_dev_lname.text().strip(),
            "phone": self.txt_dev_phone.text().strip(),
            "email": self.txt_dev_email.text().strip(),
            "telegram": self.txt_dev_telegram.text().strip(),
            "github": self.txt_dev_github.text().strip(),
        }
        if self.selected_dev_photo_path:
            data["photo_path"] = self.selected_dev_photo_path

        if data["phone"]:
            phone_digits = "".join(filter(str.isdigit, data["phone"].translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))))
            if len(phone_digits) > 11:
                QMessageBox.warning(
                    self,
                    "خطا در شماره تلفن",
                    "شماره تماس نمی‌تواند بیشتر از ۱۱ رقم باشد."
                )
                self.txt_dev_phone.setFocus()
                return

        try:
            set_developer_info(data)
            self.load_data()
            QMessageBox.information(self, "موفقیت", "اطلاعات برنامه‌نویس با موفقیت به‌روزرسانی شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت اطلاعات برنامه‌نویس: {str(e)}")

    def save_license_status(self):
        if not CurrentUser.is_admin():
            QMessageBox.warning(self, "عدم دسترسی", "تغییر وضعیت فعال‌سازی برنامه فقط توسط ادمین کل (admin) امکان‌پذیر است.")
            return

        val = self.combo_license.currentData() == "true"
        try:
            set_app_license_active(val)
            self.load_data()
            status_str = "فعال و قفل‌شده روی این رایانه 🟢" if val else "غیرفعال 🔴"
            QMessageBox.information(self, "موفقیت", f"وضعیت لایسنس سخت‌افزاری با موفقیت به '{status_str}' به‌روزرسانی شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت وضعیت برنامه: {str(e)}")

    def load_data(self):
        # 1. Dev Info
        info = get_developer_info()
        fname = info.get("first_name", "مهندس ابوالفضل")
        lname = info.get("last_name", "صمدی کوچکسرائی")
        phone = info.get("phone", "09336427711")
        email = info.get("email", "a.samadi2006@gmail.com")
        telegram = info.get("telegram", "t.me/AqaSamadi")
        github = info.get("github", "github.com/AbolfazlSamadi2006")
        photo_path = info.get("photo_path")

        self.lbl_dev_full_name.setText(f"{fname} {lname}".strip())
        self.lbl_dev_phone.setText(f"شماره همراه: {phone}")

        self.lbl_dev_email.setText(f'پست الکترونیک (جیمیل): <a href="mailto:{email}" style="color: #60A5FA; text-decoration: underline;">{email}</a>')

        tg_clean = telegram.replace("https://", "").replace("http://", "").replace("t.me/", "").replace("@", "").strip()
        tg_url = f"https://t.me/{tg_clean}" if tg_clean else "https://t.me/AqaSamadi"
        tg_display = f"t.me/{tg_clean}" if tg_clean else "t.me/AqaSamadi"
        self.lbl_dev_telegram.setText(f'تلگرام: <a href="{tg_url}" style="color: #60A5FA; text-decoration: underline;">{tg_display}</a>')

        github_url = github if github.startswith("http") else f"https://{github}"
        self.lbl_dev_github.setText(f'گیت‌هاب: <a href="{github_url}" style="color: #60A5FA; text-decoration: underline;">{github}</a>')

        if photo_path and os.path.exists(photo_path):
            pixmap = QPixmap(photo_path)
            circ = get_circular_pixmap(pixmap, 110)
            self.lbl_dev_photo.setPixmap(circ)
            self.lbl_dev_photo.setStyleSheet("border: none; background: transparent;")
        else:
            self.lbl_dev_photo.setText("👨‍💻")
            self.lbl_dev_photo.setStyleSheet("font-size: 50px;")

        # 2. License Status & Hardware Binding
        active = is_app_license_active()
        self.combo_license.setCurrentIndex(1 if active else 0)

        # 3. Admin permissions
        is_admin = CurrentUser.is_admin()
        self.combo_license.setEnabled(is_admin)
        self.btn_save_license.setEnabled(is_admin)
        self.dev_edit_box.setVisible(is_admin)

        from nemov.utils.theme_manager import ThemeManager
        palette = ThemeManager.get_current_palette()

        if is_admin:
            self.combo_license.setStyleSheet(f"""
                QComboBox {{
                    background-color: {palette.input_bg}; color: {palette.text_primary}; border: 1px solid {palette.input_border}; border-radius: 6px; padding: 4px 8px;
                }}
            """)
            self.btn_save_license.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB; color: white; border-radius: 6px; font-weight: bold; padding: 0 15px; font-size: 13px;
                }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
            self._loading_dev = True
            self.txt_dev_fname.setText(fname)
            self.txt_dev_lname.setText(lname)
            self.txt_dev_phone.setText(phone)
            self.txt_dev_email.setText(email)
            self.txt_dev_telegram.setText(telegram)
            self.txt_dev_github.setText(github)
            self.selected_dev_photo_path = photo_path
            if photo_path and os.path.exists(photo_path):
                pixmap = QPixmap(photo_path)
                circ_edit = get_circular_pixmap(pixmap, 60)
                self.lbl_dev_photo_edit.setPixmap(circ_edit)
                self.lbl_dev_photo_edit.setText("")
                self.lbl_dev_photo_edit.setStyleSheet("border: none; background: transparent;")

            self._baseline_dev = {
                "first_name": (fname or "").strip(),
                "last_name": (lname or "").strip(),
                "phone": (phone or "").strip(),
                "email": (email or "").strip(),
                "telegram": (telegram or "").strip(),
                "github": (github or "").strip(),
                "photo_path": photo_path or ""
            }
            self._loading_dev = False
            self.btn_save_dev.setEnabled(False)
            if hasattr(self, "btn_reset_dev"):
                self.btn_reset_dev.setEnabled(False)
        else:
            self.combo_license.setStyleSheet(f"""
                QComboBox {{
                    background-color: {palette.bg_surface}; color: {palette.text_muted}; border: 1px solid {palette.border}; border-radius: 6px; padding: 4px 8px;
                }}
            """)
            self.btn_save_license.setStyleSheet(f"""
                QPushButton {{
                    background-color: {palette.btn_sec_bg}; color: {palette.text_muted}; border-radius: 6px; font-weight: bold; padding: 0 15px; font-size: 13px; border: 1px solid {palette.btn_sec_border};
                }}
            """)

        # If an update check result already exists in the session, reflect it
        last_check = UpdateService.get_last_check_time()
        if last_check:
            self.lbl_last_check.setText(f"آخرین بررسی: {last_check}")
            info = UpdateService.get_latest_info()
            has_update = UpdateService.has_update_available()
            if has_update:
                self._on_check_finished(True, info, "")
            elif info:
                self._on_check_finished(False, info, "")
