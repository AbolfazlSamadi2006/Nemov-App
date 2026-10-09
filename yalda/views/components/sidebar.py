from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy, QProgressBar,
    QScrollArea, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QFontMetrics, QFont
import config

class SidebarNotifButton(QPushButton):
    """
    Notification item button that returns a compact minimum size hint
    to prevent horizontal overflow clipping inside RTL QScrollArea,
    forwards mouse wheel events to parent scroll area,
    and dynamically elides long text to maximize usable space up to the border.
    """
    def __init__(self, text: str = "", scroll_area=None, parent=None):
        super().__init__(parent)
        self._scroll_area = scroll_area
        self._raw_text = text
        f = QFont("Vazirmatn")
        f.setPixelSize(11)
        self.setFont(f)
        if text:
            self._update_elided_text()

    def set_scroll_area(self, scroll_area):
        self._scroll_area = scroll_area

    def wheelEvent(self, event):
        if self._scroll_area:
            self._scroll_area.wheelEvent(event)
        else:
            event.ignore()

    def set_full_text(self, raw_text: str, tooltip_text: str = ""):
        self._raw_text = raw_text
        if tooltip_text:
            self.setToolTip(tooltip_text)
        self._update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        if not self._raw_text:
            return
        # Allow text to fill available width with a clean buffer (12px) for scrollbar clearance
        avail_w = max(50, self.width() - 12) if self.width() > 50 else 170
        fm = QFontMetrics(self.font())
        if fm.horizontalAdvance(self._raw_text) <= avail_w:
            self.setText(self._raw_text)
        else:
            self.setText(fm.elidedText(self._raw_text, Qt.TextElideMode.ElideRight, avail_w))

    def minimumSizeHint(self):
        return QSize(50, 34)

    def sizeHint(self):
        return QSize(150, 34)


class NotifScrollArea(QScrollArea):
    """
    Custom scroll area for sidebar notifications providing
    smooth pixel-by-pixel scrolling like standard natural scrollbars.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalScrollBar().setSingleStep(12)
        self._target_value = 0
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setDuration(120)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

    def _on_scroll_value_changed(self, val):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._target_value = val

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            sb = self.verticalScrollBar()
            # Smooth pixel-by-pixel scrolling: gentle 16 pixels per wheel notch
            step = int((delta / 120.0) * 16)
            base = self._target_value if self._anim.state() == QPropertyAnimation.State.Running else sb.value()
            self._target_value = max(0, min(sb.maximum(), base - step))
            self._anim.stop()
            self._anim.setStartValue(sb.value())
            self._anim.setEndValue(self._target_value)
            self._anim.start()
            event.accept()
        else:
            super().wheelEvent(event)


class UnifiedNotifCard(QFrame):
    """
    Notification container card that forwards wheel events
    from anywhere on the card header/background to the inner scroll area.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_area = None

    def set_scroll_area(self, scroll_area):
        self._scroll_area = scroll_area

    def wheelEvent(self, event):
        if self._scroll_area:
            self._scroll_area.wheelEvent(event)
        else:
            super().wheelEvent(event)


class Sidebar(QFrame):
    page_changed = pyqtSignal(str) # Emits view name, e.g. "dashboard", "members"
    logout_requested = pyqtSignal()
    member_birthday_clicked = pyqtSignal(int)
    member_expiration_clicked = pyqtSignal(int)
    notifications_marked_read = pyqtSignal()

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
        self._main_layout = layout
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        # Brand Header
        header = QHBoxLayout()
        self.logo_lbl = QLabel()
        icon_path = config.BASE_DIR / "resources" / "images" / "app_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_lbl.setPixmap(pix)
        else:
            self.logo_lbl.setText("🔥")
            self.logo_lbl.setStyleSheet("font-size: 24px;")
        
        self.title_lbl = QLabel(config.APP_NAME)
        self.title_lbl.setStyleSheet("color: #8B0000; font-size: 20px; font-weight: bold;")

        header.addWidget(self.logo_lbl)
        header.addWidget(self.title_lbl)
        header.addStretch()
        layout.addLayout(header)

        self.sub_lbl = QLabel("نرم‌افزار مدیریت باشگاه بدنسازی")
        self.sub_lbl.setStyleSheet("color: #666666; font-size: 11px; margin-bottom: 6px;")
        layout.addWidget(self.sub_lbl)

        # Scrollable Navigation Container (prevents bottom overlap on any screen height)
        self.nav_scroll_area = QScrollArea()
        self.nav_scroll_area.setObjectName("sidebarNavScroll")
        self.nav_scroll_area.setWidgetResizable(True)
        self.nav_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav_scroll_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.nav_scroll_area.setStyleSheet("""
            QScrollArea#sidebarNavScroll {
                background: transparent;
                border: none;
            }
            QScrollArea#sidebarNavScroll > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea#sidebarNavScroll QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0px;
            }
            QScrollArea#sidebarNavScroll QScrollBar::handle:vertical {
                background: #3F3F46;
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollArea#sidebarNavScroll QScrollBar::add-line:vertical,
            QScrollArea#sidebarNavScroll QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.nav_container = QWidget()
        self.nav_container.setObjectName("navContainer")
        self.nav_container.setStyleSheet("QWidget#navContainer { background: transparent; }")
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        self.nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Navigation Buttons
        menu_items = [
            ("dashboard", "📊  داشبورد"),
            ("members", "👥  اعضای باشگاه"),
            ("workouts", "🏋️  برنامه‌ریزی تمرینی"),
            ("nutrition", "🥗  برنامه‌ریزی تغذیه"),
            ("templates", "📋  مدیریت الگوها"),
            ("exercises", "🏃  بانک حرکات ورزشی"),
            ("foods", "🍎  بانک مواد غذایی"),
            ("accounting", "💰  امور مالی و حسابداری"),
            ("sms", "📱  سامانه پیامک و اطلاع‌رسانی"),
            ("backup", "💾  تنظیمات و پشتیبان‌گیری")
        ]

        self.nav_buttons_list = []
        for nav_id, title in menu_items:
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, nid=nav_id: self.navigate(nid))
            self.nav_layout.addWidget(btn)
            self.buttons[nav_id] = btn
            self.nav_buttons_list.append(btn)

        self.nav_layout.addStretch(1)
        self.nav_scroll_area.setWidget(self.nav_container)
        layout.addWidget(self.nav_scroll_area, 1)

        # Cloud Video Upload Progress Panel (Directly under Navigation)
        self.sync_progress_frame = QFrame()
        self.sync_progress_frame.setObjectName("syncProgressFrame")
        self.sync_progress_frame.setStyleSheet("""
            QFrame#syncProgressFrame {
                background-color: #12161F;
                border: 1px solid #1D4ED8;
                border-radius: 8px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
        """)
        sync_layout = QVBoxLayout(self.sync_progress_frame)
        sync_layout.setContentsMargins(10, 8, 10, 8)
        sync_layout.setSpacing(6)

        self.lbl_sync_title = QLabel("در حال آپلود ...")
        self.lbl_sync_title.setStyleSheet("color: #93C5FD; font-size: 11px; font-weight: bold;")
        self.lbl_sync_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        sync_layout.addWidget(self.lbl_sync_title)

        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setFixedHeight(5)
        self.sync_progress_bar.setTextVisible(False)
        self.sync_progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #26262B;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 2px;
            }
        """)
        self.sync_progress_bar.setRange(0, 100)
        self.sync_progress_bar.setValue(0)
        sync_layout.addWidget(self.sync_progress_bar)

        layout.addWidget(self.sync_progress_frame)
        self.sync_progress_frame.setVisible(False)

        # ========================================================
        # Unified Notifications Card ("🔔 یادآوری‌های روز")
        # ========================================================
        self.unified_notif_card = UnifiedNotifCard()
        self.unified_notif_card.setObjectName("unifiedNotifCard")
        self.unified_notif_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.unified_notif_card.setStyleSheet("""
            QFrame#unifiedNotifCard {
                background-color: #18181B;
                border: 1px solid #3F3F46;
                border-radius: 8px;
            }
        """)
        u_card_layout = QVBoxLayout(self.unified_notif_card)
        u_card_layout.setContentsMargins(8, 8, 8, 8)
        u_card_layout.setSpacing(6)

        # Header with Bell icon, Title, and Count Badge
        u_header = QHBoxLayout()
        u_header.setContentsMargins(0, 0, 0, 0)
        u_header.setSpacing(6)

        icon_bell = QLabel("🔔")
        icon_bell.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        
        self.lbl_unified_title = QLabel("یادآوری‌های روز")
        self.lbl_unified_title.setStyleSheet("color: #FAFAFA; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        
        self.lbl_notif_badge = QLabel("۰")
        self.lbl_notif_badge.setStyleSheet("""
            QLabel {
                background-color: #DC2626;
                color: #FFFFFF;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 6px;
                border: none;
            }
        """)

        self.btn_mark_all_read = QPushButton("✓✓")
        self.btn_mark_all_read.setFixedSize(26, 20)
        self.btn_mark_all_read.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mark_all_read.setToolTip("خواندن همه اعلانات (مخفی کردن از یادآوری‌های روز)")
        self.btn_mark_all_read.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #10B981;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #FFFFFF;
                border: 1px solid #10B981;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_mark_all_read.clicked.connect(self.on_mark_all_notifications_read)

        u_header.addWidget(icon_bell)
        u_header.addWidget(self.lbl_unified_title)
        u_header.addStretch()
        u_header.addWidget(self.btn_mark_all_read)
        u_header.addWidget(self.lbl_notif_badge)
        u_card_layout.addLayout(u_header)

        # Scroll Area for Notification Items
        self.notif_inner_scroll = NotifScrollArea()
        self.notif_inner_scroll.setObjectName("notifInnerScroll")
        self.notif_inner_scroll.setWidgetResizable(True)
        self.notif_inner_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notif_inner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.notif_inner_scroll.setStyleSheet("""
            QScrollArea#notifInnerScroll {
                background: transparent;
                border: none;
            }
            QScrollArea#notifInnerScroll > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea#notifInnerScroll QScrollBar:vertical {
                background: #1C1C20;
                width: 6px;
                margin: 0px 1px 0px 1px;
                border-radius: 3px;
            }
            QScrollArea#notifInnerScroll QScrollBar::handle:vertical {
                background: #52525B;
                min-height: 22px;
                border-radius: 3px;
            }
            QScrollArea#notifInnerScroll QScrollBar::handle:vertical:hover {
                background: #DC2626;
            }
            QScrollArea#notifInnerScroll QScrollBar::add-line:vertical,
            QScrollArea#notifInnerScroll QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.unified_notif_card.set_scroll_area(self.notif_inner_scroll)

        self.notif_items_container = QWidget()
        self.notif_items_container.setObjectName("notifItemsContainer")
        self.notif_items_container.setStyleSheet("background: transparent;")
        self.notif_items_layout = QVBoxLayout(self.notif_items_container)
        self.notif_items_layout.setContentsMargins(6, 2, 4, 2)
        self.notif_items_layout.setSpacing(4)
        self.notif_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.notif_inner_scroll.setWidget(self.notif_items_container)
        u_card_layout.addWidget(self.notif_inner_scroll)

        layout.addWidget(self.unified_notif_card)
        self.unified_notif_card.setVisible(False)

        # ========================================================
        # Bottom Action Bar: Horizontal Logout and Developer buttons
        # ========================================================
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(6)

        # Logout Button (Right side in RTL)
        btn_logout = QPushButton("🚪  خروج")
        btn_logout.setFixedHeight(36)
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setToolTip("خروج از حساب کاربری مربی")
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
                border: none;
                padding: 6px 4px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        btn_logout.clicked.connect(self.logout_requested.emit)

        # Developer Button (Left side in RTL)
        btn_dev = QPushButton("👨‍💻  درباره")
        btn_dev.setFixedHeight(36)
        btn_dev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dev.setToolTip("درباره برنامه‌نویس و اطلاعات توسعه‌دهنده")
        btn_dev.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #D4D4D8;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #3F3F46;
                padding: 6px 4px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #202024;
            }
            QPushButton[active="true"] {
                background-color: #8B0000;
                color: #FFFFFF;
                border: 1px solid #DC2626;
                font-weight: bold;
            }
        """)
        btn_dev.clicked.connect(lambda: self.navigate("developer"))
        self.buttons["developer"] = btn_dev

        self.btn_logout = btn_logout
        self.btn_dev = btn_dev
        bottom_row.addWidget(btn_logout, 1)
        bottom_row.addWidget(btn_dev, 1)
        layout.addLayout(bottom_row)

        # Set default active page
        self.set_active("dashboard")
        self._apply_responsive_metrics()

    def on_mark_all_notifications_read(self):
        try:
            from yalda.services.notification_service import NotificationService
            NotificationService.mark_all_as_read()
        except Exception:
            pass
        self.refresh_notifications()
        self.notifications_marked_read.emit()

    def refresh_notifications(self):
        while self.notif_items_layout.count() > 0:
            item = self.notif_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        upcoming_count = 0
        exp_count = 0

        try:
            from yalda.services.notification_service import NotificationService
            upcoming_members, upcoming_exp = NotificationService.sync_and_get_unread_sidebar_notifications()
            
            # --- 1. Birthday Notifications (Today & Tomorrow) ---
            if upcoming_members:
                upcoming_count = len(upcoming_members)
                for member, delta, _nid in upcoming_members:
                    if delta == 0:
                        raw_text = f"🎂 امروز تولد: {member.full_name}"
                        tooltip_text = f"🎂 امروز تولد {member.full_name} است\n(جهت مشاهده پرونده عضو کلیک کنید)"
                    else:
                        raw_text = f"🎉 تولد فردا: {member.full_name}"
                        tooltip_text = f"🎉 فردا تولد {member.full_name} است\n(جهت مشاهده پرونده عضو کلیک کنید)"

                    btn = SidebarNotifButton(scroll_area=self.notif_inner_scroll)
                    btn.setFixedHeight(34)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #241607;
                            color: #FEF3C7;
                            border: 1px solid #D97706;
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            text-align: right;
                        }
                        QPushButton:hover {
                            background-color: #3B240B;
                            border: 1px solid #F59E0B;
                            color: #FFFFFF;
                        }
                    """)
                    btn.set_full_text(raw_text, tooltip_text)
                    btn.clicked.connect(lambda _, m_id=member.id: self.member_birthday_clicked.emit(m_id))
                    self.notif_items_layout.addWidget(btn)

            # --- 2. Membership Expiration / Tuition Notifications ---
            if upcoming_exp:
                exp_count = len(upcoming_exp)
                for member, delta, _nid in upcoming_exp:
                    if delta == 0:
                        raw_text = f"🚨 موعد شهریه: {member.full_name}"
                        tooltip_text = f"🚨 امروز موعد شهریه {member.full_name} است\n(جهت مشاهده پرونده عضو کلیک کنید)"
                    else:
                        raw_text = f"⏳ سررسید فردا: {member.full_name}"
                        tooltip_text = f"⏳ فردا پایان شهریه {member.full_name} است\n(جهت مشاهده پرونده عضو کلیک کنید)"

                    btn = SidebarNotifButton(scroll_area=self.notif_inner_scroll)
                    btn.setFixedHeight(34)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #200C0C;
                            color: #FEE2E2;
                            border: 1px solid #DC2626;
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            text-align: right;
                        }
                        QPushButton:hover {
                            background-color: #3B1111;
                            border: 1px solid #EF4444;
                            color: #FFFFFF;
                        }
                    """)
                    btn.set_full_text(raw_text, tooltip_text)
                    btn.clicked.connect(lambda _, m_id=member.id: self.member_expiration_clicked.emit(m_id))
                    self.notif_items_layout.addWidget(btn)

        except Exception:
            pass

        total_notifs = upcoming_count + exp_count
        self._total_notifs = total_notifs

        fa_count = str(total_notifs).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_notif_badge.setText(f" {fa_count} ")

        if total_notifs == 0:
            self.unified_notif_card.setVisible(False)
        else:
            self.unified_notif_card.setVisible(True)

        self._update_notif_scroll_height()

    def _apply_responsive_metrics(self):
        """Dynamically adapts sidebar vertical padding and spacing to screen height (TV HDMI / Laptop / PC)."""
        h = self.height() if self.height() > 100 else 760
        if h < 680:
            tier = "compact"
            margins = (10, 8, 10, 8)
            main_spacing = 4
            nav_spacing = 2
            sub_style = "color: #666666; font-size: 10.5px; margin-bottom: 2px;"
            btn_pad = "6px 12px"
            btn_font = "12.5px"
            bot_h = 32
        elif h < 760:
            tier = "medium"
            margins = (11, 10, 11, 10)
            main_spacing = 5
            nav_spacing = 4
            sub_style = "color: #666666; font-size: 11px; margin-bottom: 4px;"
            btn_pad = "8px 14px"
            btn_font = "13px"
            bot_h = 34
        else:
            tier = "full"
            margins = (12, 14, 12, 14)
            main_spacing = 6
            nav_spacing = 6
            sub_style = "color: #666666; font-size: 11px; margin-bottom: 6px;"
            btn_pad = "11px 16px"
            btn_font = "14px"
            bot_h = 36

        if getattr(self, "_responsive_tier", None) == tier:
            return
        self._responsive_tier = tier

        self._main_layout.setContentsMargins(*margins)
        self._main_layout.setSpacing(main_spacing)
        self.nav_layout.setSpacing(nav_spacing)
        self.sub_lbl.setStyleSheet(sub_style)
        if hasattr(self, "btn_logout"):
            self.btn_logout.setFixedHeight(bot_h)
            self.btn_dev.setFixedHeight(bot_h)

        self.nav_container.setObjectName("navContainer")
        self.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: #161616;
                border-left: 1px solid #282828;
            }}
            QWidget#navContainer > QPushButton {{
                background-color: transparent;
                color: #B0B0B0;
                text-align: right;
                padding: {btn_pad};
                border: none;
                border-radius: 6px;
                font-size: {btn_font};
            }}
            QWidget#navContainer > QPushButton:hover {{
                background-color: #8B0000;
                color: #FFFFFF;
            }}
            QWidget#navContainer > QPushButton[active="true"] {{
                background-color: #8B0000;
                color: #FFFFFF;
                font-weight: bold;
            }}
        """)
        for btn in self.buttons.values():
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_notif_scroll_height(self):
        total = getattr(self, "_total_notifs", 0)
        if total == 0:
            self.unified_notif_card.setVisible(False)
            return

        self.unified_notif_card.setVisible(True)

        # Total height needed to show all items without any scrolling
        needed_all_h = (total * 34) + max(0, total - 1) * 4 + 4
        self.notif_items_container.setFixedHeight(needed_all_h)

        # Maximum items visible at once based on sidebar height:
        # - Compact / TV screens (height < 720): 1 full item visible (38px) with smooth wheel scrolling for others
        # - Standard screens (720 <= height < 880): up to 2 items visible (76px)
        # - Tall / maximized screens (height >= 880): up to 3 items visible (114px)
        h = self.height() if self.height() > 100 else 760
        if h < 720:
            max_visible_items = 1
        elif h >= 880 and total >= 3:
            max_visible_items = 3
        else:
            max_visible_items = 2

        if total <= max_visible_items:
            # All items fit cleanly without scrollbar
            scroll_h = needed_all_h
            self.notif_inner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            scroll_h = (max_visible_items * 34) + (max_visible_items - 1) * 4 + 4
            self.notif_inner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.notif_inner_scroll.setFixedHeight(scroll_h)
        # Card fixed height = scroll_h + header (~22px) + layout spacing (6px) + card padding (16px) = scroll_h + 44px
        self.unified_notif_card.setFixedHeight(scroll_h + 44)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_metrics()
        self._update_notif_scroll_height()

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

    def show_cloud_sync_progress(self, remaining: int, total: int):
        """Updates the sidebar cloud video sync progress panel."""
        self.sync_progress_frame.setVisible(True)
        fa_rem = str(remaining).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        fa_tot = str(total).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_sync_title.setStyleSheet("color: #93C5FD; font-size: 11px; font-weight: bold;")
        self.lbl_sync_title.setText(f"در حال آپلود ... ( {fa_rem} از {fa_tot} )")
        done = max(0, total - remaining)
        pct = int((done / total) * 100) if total > 0 else 0
        self.sync_progress_bar.setValue(pct)

    def finish_cloud_sync_progress(self, success_count: int, fail_count: int):
        """Displays completion status and smoothly auto-hides after a brief delay."""
        fa_suc = str(success_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        if fail_count == 0:
            self.lbl_sync_title.setText(f"✅ آپلود {fa_suc} ویدیو با موفقیت انجام شد")
            self.lbl_sync_title.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold;")
            self.sync_progress_bar.setValue(100)
        else:
            fa_fail = str(fail_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.lbl_sync_title.setText(f"⚠️ {fa_suc} آپلود شد، {fa_fail} خطا")
            self.lbl_sync_title.setStyleSheet("color: #F87171; font-size: 11px; font-weight: bold;")

        QTimer.singleShot(4000, self.hide_cloud_sync_progress)

    def hide_cloud_sync_progress(self):
        """Hides the cloud sync progress panel."""
        self.sync_progress_frame.setVisible(False)
        self.lbl_sync_title.setStyleSheet("color: #93C5FD; font-size: 11px; font-weight: bold;")


