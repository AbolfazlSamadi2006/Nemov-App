import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QGroupBox, QGridLayout, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import config
from yalda.auth.authentication import (
    CurrentUser, get_developer_info, set_developer_info, is_app_license_active, set_app_license_active
)
from yalda.utils.image_utils import get_circular_pixmap



class DeveloperView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.selected_dev_photo_path = None
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title and Back Button
        header = QHBoxLayout()
        btn_back = QPushButton("⬅️ بازگشت به صفحه قبل")
        btn_back.setObjectName("back_button")
        btn_back.clicked.connect(self.back_requested.emit)

        title = QLabel("👨‍💻 درباره برنامه‌نویس و وضعیت مجوز نرم‌افزار")
        title.setObjectName("h1")

        header.addWidget(btn_back)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ----------------------------------------------------
        # BOX 1: Developer Display Card (For All Users)
        # ----------------------------------------------------
        card_box = QGroupBox("📋 اطلاعات توسعه دهنده")

        layout_card = QHBoxLayout(card_box)
        layout_card.setContentsMargins(20, 20, 20, 20)
        layout_card.setSpacing(20)

        self.lbl_dev_photo = QLabel()
        self.lbl_dev_photo.setFixedSize(110, 110)
        self.lbl_dev_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v_info = QVBoxLayout()
        SELECTABLE_FLAGS = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse

        self.lbl_dev_full_name = QLabel("ابوالفضل صمدی کوچکسرائی")
        self.lbl_dev_full_name.setTextInteractionFlags(SELECTABLE_FLAGS)
        self.lbl_dev_full_name.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")

        self.lbl_dev_role = QLabel("طراح، پیاده‌ساز و توسعه‌دهنده نرم‌افزار مدیریت باشگاه یلدا")
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
        # BOX 2: App License Status Control
        # ----------------------------------------------------
        license_box = QGroupBox("🟢 وضعیت فعال‌سازی و مجوز برنامه (App License Status)")
        layout_lic = QHBoxLayout(license_box)
        layout_lic.setContentsMargins(15, 15, 15, 15)
        layout_lic.setSpacing(12)

        lbl_lic_status = QLabel("وضعیت فعلی سیستم:")
        lbl_lic_status.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.combo_license = QComboBox()
        self.combo_license.setFixedHeight(38)
        self.combo_license.addItem("🔴 غیرفعال", "false")
        self.combo_license.addItem("🟢 فعال", "true")


        self.btn_save_license = QPushButton("💾 ثبت وضعیت برنامه")
        self.btn_save_license.setFixedHeight(38)
        self.btn_save_license.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_license.clicked.connect(self.save_license_status)

        layout_lic.addWidget(lbl_lic_status)
        layout_lic.addWidget(self.combo_license)
        layout_lic.addWidget(self.btn_save_license)
        layout_lic.addStretch()

        layout.addWidget(license_box)


        # ----------------------------------------------------
        # BOX 3: Developer Info Edit Box (Admin Only)
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
        from yalda.utils.image_source_chooser import get_image_file_path

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
            status_str = "فعال 🟢" if val else "غیرفعال 🔴"
            QMessageBox.information(self, "موفقیت", f"وضعیت سیستم با موفقیت به '{status_str}' تغییر یافت.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت وضعیت برنامه: {str(e)}")

    def load_data(self):
        # 1. Dev Info
        info = get_developer_info()
        fname = info.get("first_name", "ابوالفضل")
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

        # 2. License Status
        active = is_app_license_active()
        self.combo_license.setCurrentIndex(1 if active else 0)

        # 3. Admin permissions
        is_admin = CurrentUser.is_admin()
        self.combo_license.setEnabled(is_admin)
        self.btn_save_license.setEnabled(is_admin)
        self.dev_edit_box.setVisible(is_admin)

        if is_admin:
            self.combo_license.setStyleSheet("""
                QComboBox {
                    background-color: #1E1E1E; color: #FFFFFF; border: 1px solid #333333; border-radius: 6px; padding: 4px 8px;
                }
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
            # Dimmed/disabled styling for non-admin trainers
            self.combo_license.setStyleSheet("""
                QComboBox {
                    background-color: #181818; color: #555555; border: 1px solid #282828; border-radius: 6px; padding: 4px 8px;
                }
            """)
            self.btn_save_license.setStyleSheet("""
                QPushButton {
                    background-color: #222222; color: #555555; border-radius: 6px; font-weight: bold; padding: 0 15px; font-size: 13px; border: 1px solid #2A2A2A;
                }
            """)


