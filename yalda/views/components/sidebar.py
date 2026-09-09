from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
import config

class Sidebar(QFrame):
    page_changed = pyqtSignal(str) # Emits view name, e.g. "dashboard", "members"
    logout_requested = pyqtSignal()
    member_birthday_clicked = pyqtSignal(int)
    member_expiration_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        self.setStyleSheet("""
            QFrame#sidebar {
                background-color: #161616;
                border-left: 1px solid #282828;
            }
            QPushButton {
                background-color: transparent;
                color: #B0B0B0;
                text-align: right;
                padding: 12px 16px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8B0000;
                color: #FFFFFF;
            }
            QPushButton[active="true"] {
                background-color: #8B0000;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)

        self.buttons = {}
        self.init_ui()
        self.refresh_notifications()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)

        # Brand Header
        header = QHBoxLayout()
        logo_lbl = QLabel()
        icon_path = config.BASE_DIR / "resources" / "images" / "app_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("🔥")
            logo_lbl.setStyleSheet("font-size: 24px;")
        
        title_lbl = QLabel(config.APP_NAME)
        title_lbl.setStyleSheet("color: #8B0000; font-size: 20px; font-weight: bold;")

        header.addWidget(logo_lbl)
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        sub_lbl = QLabel("نرم‌افزار مدیریت باشگاه بدنسازی")
        sub_lbl.setStyleSheet("color: #666666; font-size: 11px; margin-bottom: 15px;")
        layout.addWidget(sub_lbl)

        # Navigation Buttons
        menu_items = [
            ("dashboard", "📊  داشبورد"),
            ("members", "👥  اعضای باشگاه"),
            ("workouts", "🏋️  برنامه‌ریزی تمرینی"),
            ("nutrition", "🥗  برنامه‌ریزی تغذیه"),
            ("templates", "📋  مدیریت الگوها"),
            ("exercises", "🏃  بانک حرکات ورزشی"),
            ("foods", "🍎  بانک مواد غذایی"),
            ("backup", "💾  تنظیمات و پشتیبان‌گیری")
        ]

        for nav_id, title in menu_items:
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, nid=nav_id: self.navigate(nid))
            layout.addWidget(btn)
            self.buttons[nav_id] = btn

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Birthday Notification Panel (Bottom Right Corner)
        self.notification_frame = QFrame()
        self.notification_frame.setObjectName("birthdayNotificationFrame")
        self.notification_frame.setStyleSheet("""
            QFrame#birthdayNotificationFrame {
                background-color: #241607;
                border: 1px solid #D97706;
                border-radius: 8px;
            }
        """)
        self.notification_layout = QVBoxLayout(self.notification_frame)
        self.notification_layout.setContentsMargins(8, 8, 8, 8)
        self.notification_layout.setSpacing(6)

        notif_header = QHBoxLayout()
        icon_lbl = QLabel("🎂")
        icon_lbl.setStyleSheet("font-size: 15px;")
        title_lbl = QLabel("یادآوری تولد (۱ روز مانده)")
        title_lbl.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: bold;")
        notif_header.addWidget(icon_lbl)
        notif_header.addWidget(title_lbl)
        notif_header.addStretch()
        self.notification_layout.addLayout(notif_header)

        self.notif_list_layout = QVBoxLayout()
        self.notif_list_layout.setSpacing(4)
        self.notification_layout.addLayout(self.notif_list_layout)

        layout.addWidget(self.notification_frame)
        self.notification_frame.setVisible(False)

        # Expiration / Tuition Deadline Notification Panel
        self.expiration_frame = QFrame()
        self.expiration_frame.setObjectName("expirationNotificationFrame")
        self.expiration_frame.setStyleSheet("""
            QFrame#expirationNotificationFrame {
                background-color: #200C0C;
                border: 1px solid #DC2626;
                border-radius: 8px;
            }
        """)
        self.expiration_layout = QVBoxLayout(self.expiration_frame)
        self.expiration_layout.setContentsMargins(8, 8, 8, 8)
        self.expiration_layout.setSpacing(6)

        exp_header = QHBoxLayout()
        icon_exp = QLabel("⏳")
        icon_exp.setStyleSheet("font-size: 15px;")
        title_exp = QLabel("سررسید شهریه (۱ روز مانده)")
        title_exp.setStyleSheet("color: #FCA5A5; font-size: 11px; font-weight: bold;")
        exp_header.addWidget(icon_exp)
        exp_header.addWidget(title_exp)
        exp_header.addStretch()
        self.expiration_layout.addLayout(exp_header)

        self.exp_list_layout = QVBoxLayout()
        self.exp_list_layout.setSpacing(4)
        self.expiration_layout.addLayout(self.exp_list_layout)

        layout.addWidget(self.expiration_frame)
        self.expiration_frame.setVisible(False)

        # About Developer Button (Placed above logout button)
        btn_dev = QPushButton("👨‍💻  درباره برنامه‌نویس")
        btn_dev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dev.clicked.connect(lambda: self.navigate("developer"))
        layout.addWidget(btn_dev)
        self.buttons["developer"] = btn_dev

        # Logout Button
        btn_logout = QPushButton("🚪  خروج از حساب")

        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                text-align: right;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #B91C1C;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(btn_logout)

        # Set default active page
        self.set_active("dashboard")

    def refresh_notifications(self):
        while self.notif_list_layout.count() > 0:
            item = self.notif_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        while self.exp_list_layout.count() > 0:
            item = self.exp_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            from yalda.services.member_service import MemberService
            
            # --- 1. Birthday Notifications ---
            upcoming_members = MemberService.get_upcoming_birthday_members(days_ahead=1)
            if upcoming_members:
                for member in upcoming_members:
                    btn = QPushButton(f"🎉 فردا تولد {member.full_name} است")
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3B240B;
                            color: #FEF3C7;
                            border: 1px solid #92400E;
                            border-radius: 5px;
                            padding: 6px 8px;
                            font-size: 11px;
                            text-align: right;
                        }
                        QPushButton:hover {
                            background-color: #78350F;
                            color: #FFFFFF;
                        }
                    """)
                    btn.clicked.connect(lambda _, m_id=member.id: self.member_birthday_clicked.emit(m_id))
                    self.notif_list_layout.addWidget(btn)
                self.notification_frame.setVisible(True)
            else:
                self.notification_frame.setVisible(False)

            # --- 2. Membership Expiration / Tuition Notifications ---
            upcoming_exp = MemberService.get_upcoming_expiration_members(days_ahead=1)
            if upcoming_exp:
                for member, delta in upcoming_exp:
                    if delta == 0:
                        btn_text = f"🚨 امروز موعد شهریه {member.full_name} است"
                    else:
                        btn_text = f"⏳ فردا پایان شهریه {member.full_name} است"

                    btn = QPushButton(btn_text)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3B1111;
                            color: #FEE2E2;
                            border: 1px solid #991B1B;
                            border-radius: 5px;
                            padding: 6px 8px;
                            font-size: 11px;
                            text-align: right;
                        }
                        QPushButton:hover {
                            background-color: #7F1D1D;
                            color: #FFFFFF;
                        }
                    """)
                    btn.clicked.connect(lambda _, m_id=member.id: self.member_expiration_clicked.emit(m_id))
                    self.exp_list_layout.addWidget(btn)
                self.expiration_frame.setVisible(True)
            else:
                self.expiration_frame.setVisible(False)

        except Exception:
            self.notification_frame.setVisible(False)
            self.expiration_frame.setVisible(False)

    def refresh_developer_info(self):
        try:
            from yalda.auth.authentication import get_developer_info
            from PyQt6.QtGui import QPixmap
            import os

            info = get_developer_info()
            fname = info.get("first_name", "ابوالفضل")
            lname = info.get("last_name", "صمدی کوچکسرائی")
            phone = info.get("phone", "09336427711")
            email = info.get("email", "a.samadi2006@gmail.com")
            github = info.get("github", "github.com/AbolfazlSamadi2006")
            photo_path = info.get("photo_path")

            self.lbl_dev_name.setText(f"{fname} {lname}".strip() or "ابوالفضل صمدی")
            self.lbl_dev_full.setText(f"{fname} {lname}".strip())
            self.lbl_dev_phone.setText(f"📞 {phone}")
            self.lbl_dev_email.setText(f"✉️ {email}")
            self.lbl_dev_github.setText(f"🐙 {github}")

            if photo_path and os.path.exists(photo_path):
                pixmap = QPixmap(photo_path)
                self.lbl_dev_photo.setPixmap(pixmap.scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                self.lbl_dev_photo.setFixedSize(42, 42)
                self.lbl_dev_photo.setStyleSheet("border-radius: 21px; border: 1px solid #8B0000;")
            else:
                self.lbl_dev_photo.setText("👨‍💻")
                self.lbl_dev_photo.setStyleSheet("font-size: 20px;")
        except Exception:
            pass

    def navigate(self, nav_id: str):

        self.set_active(nav_id)
        self.page_changed.emit(nav_id)

    def set_active(self, nav_id: str):
        for key, btn in self.buttons.items():
            is_active = (key == nav_id)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

