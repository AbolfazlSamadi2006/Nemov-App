from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy, QProgressBar,
    QScrollArea, QWidget, QGridLayout
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import QPixmap, QFontMetrics, QFont, QPainter, QPen, QColor, QIcon
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
    EXPANDED_WIDTH = 230
    COLLAPSED_WIDTH = 74

    page_changed = pyqtSignal(str) # Emits view name, e.g. "dashboard", "members"
    logout_requested = pyqtSignal()
    member_birthday_clicked = pyqtSignal(int)
    member_expiration_clicked = pyqtSignal(int)
    draft_clicked = pyqtSignal(str)  # Emits unfinished draft_id
    notifications_marked_read = pyqtSignal()
    collapse_toggled = pyqtSignal(bool)  # True = collapsed, False = expanded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._is_collapsed = False
        self._visual_collapsed = False
        self._collapse_anim_group = None
        self._sync_active = False
        self._sync_short_text = "☁️"
        self._sync_full_text = "در حال آپلود ..."
        self._responsive_tier = None
        self._btn_pad = "11px 16px"
        self._btn_font = "14px"
        self._sub_font = "11px"
        self._sub_mb = "6px"

        self.buttons = {}
        self._nav_meta = {}
        self._current_nav_id: str = "dashboard"
        self._excluded_draft_ids: set[str] = set()
        self.init_ui()
        self.refresh_notifications()
        self.refresh_branding()
        try:
            from nemov.utils.theme_manager import ThemeManager
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        try:
            from nemov.services.draft_service import get_draft_notifier
            get_draft_notifier().drafts_changed.connect(self.refresh_notifications)
        except Exception:
            pass
        self._apply_theme_style()

    @staticmethod
    def _make_sidebar_toggle_icon(color_hex: str, collapsed: bool, size: int = 18) -> QIcon:
        """Draws a crisp @2x vector icon showing an RTL right-docked sidebar and chevron direction."""
        dpr = 2
        pm = QPixmap(size * dpr, size * dpr)
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(color_hex), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Outer rounded window frame
        painter.drawRoundedRect(2, 3, size - 4, size - 6, 2.5, 2.5)
        # Right sidebar split divider
        split_x = size - 6
        painter.drawLine(split_x, 3, split_x, size - 3)

        # Directional chevron inside the main pane
        cy = size / 2.0
        if collapsed:
            # Arrow pointing left (<) to indicate expanding leftward
            painter.drawLine(int(split_x - 3), int(cy - 3), int(split_x - 6), int(cy))
            painter.drawLine(int(split_x - 6), int(cy), int(split_x - 3), int(cy + 3))
        else:
            # Arrow pointing right (>) to indicate collapsing toward right wall
            painter.drawLine(int(split_x - 6), int(cy - 3), int(split_x - 3), int(cy))
            painter.drawLine(int(split_x - 3), int(cy), int(split_x - 6), int(cy + 3))

        painter.end()
        return QIcon(pm)

    def init_ui(self):
        layout = QVBoxLayout(self)
        self._main_layout = layout
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        # Brand Header (Expanded Mode: Logo far right -> Title "نِمو" close to logo (~half gap) -> Toggle button far left)
        self.expanded_header_widget = QWidget()
        self.expanded_header_widget.setObjectName("sidebarHeaderWidget")
        header = QHBoxLayout(self.expanded_header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.brand_cluster = QWidget()
        self.brand_cluster.setObjectName("sidebarBrandCluster")
        brand_vbox = QVBoxLayout(self.brand_cluster)
        brand_vbox.setContentsMargins(0, 0, 0, 0)
        brand_vbox.setSpacing(3)

        brand_top = QHBoxLayout()
        brand_top.setContentsMargins(0, 0, 0, 0)
        brand_top.setSpacing(15)

        self.logo_lbl = QLabel()
        self.logo_lbl.setObjectName("sidebarLogo")
        self.logo_lbl.setFixedSize(46, 46)
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = config.BASE_DIR / "resources" / "images" / "nemov_logo.png"
        if not icon_path.exists():
            icon_path = config.BASE_DIR / "resources" / "images" / "app_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_lbl.setPixmap(pix)
        else:
            self.logo_lbl.setText("🔥")
            self.logo_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        self.title_lbl = QLabel(config.APP_NAME)
        self.title_lbl.setObjectName("sidebarBrandTitle")
        self.title_lbl.setContentsMargins(0, 0, 0, 0)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter)

        # In RTL: logo on far right, fixed 15px gap -> title "نِمو" sits close to logo, stretch fills remaining left side
        brand_top.addWidget(self.logo_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_top.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_top.addStretch(1)
        brand_vbox.addLayout(brand_top)

        self.sub_lbl = QLabel("نرم‌افزار مدیریت ورزشی")
        self.sub_lbl.setContentsMargins(0, 0, 0, 0)
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter)
        brand_vbox.addWidget(self.sub_lbl)

        self.btn_toggle_sidebar = QPushButton()
        self.btn_toggle_sidebar.setObjectName("sidebarToggleBtn")
        self.btn_toggle_sidebar.setFixedSize(32, 32)
        self.btn_toggle_sidebar.setIconSize(QSize(18, 18))
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.setToolTip("جمع کردن سایدبار")
        self.btn_toggle_sidebar.setAccessibleName("جمع کردن سایدبار")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_collapsed)

        # In RTL visual flow: brand cluster on right, flexible space in middle, collapse button on far left
        toggle_slot = QWidget()
        toggle_slot.setObjectName("sidebarToggleSlot")
        toggle_slot_lay = QVBoxLayout(toggle_slot)
        toggle_slot_lay.setContentsMargins(0, 7, 0, 0)
        toggle_slot_lay.setSpacing(0)
        toggle_slot_lay.addWidget(self.btn_toggle_sidebar, 0, Qt.AlignmentFlag.AlignTop)

        header.addWidget(self.brand_cluster, 0, Qt.AlignmentFlag.AlignTop)
        header.addStretch(1)
        header.addWidget(toggle_slot, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.expanded_header_widget)

        # Collapsed Header Mode: small centered logo + expand button below it
        self.collapsed_header_widget = QWidget()
        self.collapsed_header_widget.setObjectName("sidebarCollapsedHeaderWidget")
        c_header = QVBoxLayout(self.collapsed_header_widget)
        c_header.setContentsMargins(0, 0, 0, 4)
        c_header.setSpacing(6)
        c_header.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.collapsed_logo_lbl = QLabel()
        self.collapsed_logo_lbl.setObjectName("sidebarLogo")
        self.collapsed_logo_lbl.setFixedSize(34, 34)
        self.collapsed_logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path.exists():
            cpix = QPixmap(str(icon_path)).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.collapsed_logo_lbl.setPixmap(cpix)
        else:
            self.collapsed_logo_lbl.setText("🔥")
            self.collapsed_logo_lbl.setStyleSheet("font-size: 22px;")

        self.btn_expand_sidebar = QPushButton()
        self.btn_expand_sidebar.setObjectName("sidebarToggleBtn")
        self.btn_expand_sidebar.setFixedSize(38, 30)
        self.btn_expand_sidebar.setIconSize(QSize(18, 18))
        self.btn_expand_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand_sidebar.setToolTip("باز کردن سایدبار")
        self.btn_expand_sidebar.setAccessibleName("باز کردن سایدبار")
        self.btn_expand_sidebar.clicked.connect(self.toggle_collapsed)

        c_header.addWidget(self.collapsed_logo_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        c_header.addWidget(self.btn_expand_sidebar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.collapsed_header_widget)
        self.collapsed_header_widget.setVisible(False)

        # Scrollable Navigation Container (prevents bottom overlap on any screen height)
        self.nav_scroll_area = QScrollArea()
        self.nav_scroll_area.setObjectName("sidebarNavScroll")
        self.nav_scroll_area.setWidgetResizable(True)
        self.nav_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav_scroll_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

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
            parts = title.split("  ", 1)
            icon_char = parts[0].strip()
            clean_label = parts[1].strip() if len(parts) > 1 else title
            self._nav_meta[nav_id] = (icon_char, title, clean_label)
            btn = QPushButton(title)
            btn.setProperty("navId", nav_id)
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
        sync_layout = QVBoxLayout(self.sync_progress_frame)
        sync_layout.setContentsMargins(10, 8, 10, 8)
        sync_layout.setSpacing(6)

        self.lbl_sync_title = QLabel("در حال آپلود ...")
        self.lbl_sync_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        sync_layout.addWidget(self.lbl_sync_title)

        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setFixedHeight(5)
        self.sync_progress_bar.setTextVisible(False)
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
        
        self.lbl_notif_badge = QLabel("۰")

        self.btn_mark_all_read = QPushButton("✓✓")
        self.btn_mark_all_read.setFixedSize(26, 20)
        self.btn_mark_all_read.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mark_all_read.setToolTip("خواندن همه اعلانات (مخفی کردن از یادآوری‌های روز)")
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

        self.unified_notif_card.set_scroll_area(self.notif_inner_scroll)

        self.notif_items_container = QWidget()
        self.notif_items_container.setObjectName("notifItemsContainer")
        self.notif_items_container.setStyleSheet("QWidget#notifItemsContainer { background: transparent; }")
        self.notif_items_layout = QVBoxLayout(self.notif_items_container)
        self.notif_items_layout.setContentsMargins(6, 2, 4, 2)
        self.notif_items_layout.setSpacing(4)
        self.notif_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.notif_inner_scroll.setWidget(self.notif_items_container)
        u_card_layout.addWidget(self.notif_inner_scroll)

        layout.addWidget(self.unified_notif_card)
        self.unified_notif_card.setVisible(False)

        # Compact notification pill shown only when sidebar is collapsed & notifications exist
        self.btn_collapsed_notif = QPushButton("🔔")
        self.btn_collapsed_notif.setObjectName("collapsedNotifBtn")
        self.btn_collapsed_notif.setFixedSize(48, 34)
        self.btn_collapsed_notif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapsed_notif.setVisible(False)
        self.btn_collapsed_notif.clicked.connect(lambda: self.set_collapsed(False, animate=True, user_initiated=True))
        layout.addWidget(self.btn_collapsed_notif, 0, Qt.AlignmentFlag.AlignHCenter)

        # ========================================================
        # Bottom Action Bar: Horizontal (expanded) / Vertical icons (collapsed)
        # ========================================================
        self.bottom_grid = QGridLayout()
        self.bottom_grid.setContentsMargins(0, 0, 0, 0)
        self.bottom_grid.setSpacing(6)

        # Logout Button (Right side in RTL)
        btn_logout = QPushButton("🚪  خروج")
        btn_logout.setFixedHeight(36)
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setToolTip("خروج از حساب کاربری مربی")
        btn_logout.clicked.connect(self.logout_requested.emit)

        # Developer Button (Left side in RTL)
        btn_dev = QPushButton("👨‍💻  درباره")
        btn_dev.setFixedHeight(36)
        btn_dev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dev.setToolTip("درباره برنامه‌نویس و اطلاعات توسعه‌دهنده")
        btn_dev.clicked.connect(lambda: self.navigate("developer"))
        self.buttons["developer"] = btn_dev

        self.btn_logout = btn_logout
        self.btn_dev = btn_dev
        self.bottom_grid.addWidget(btn_logout, 0, 0)
        self.bottom_grid.addWidget(btn_dev, 0, 1)
        self.bottom_grid.setColumnStretch(0, 1)
        self.bottom_grid.setColumnStretch(1, 1)
        layout.addLayout(self.bottom_grid)

        # Set default active page
        self.set_active("dashboard")
        self._apply_responsive_metrics()
        self._apply_theme_style()

    def on_mark_all_notifications_read(self):
        try:
            from nemov.services.notification_service import NotificationService
            NotificationService.mark_all_as_read()
        except Exception:
            pass
        self.refresh_notifications()
        self.notifications_marked_read.emit()

    def set_excluded_draft_ids(self, draft_ids: set):
        new_ids = set(draft_ids or ())
        if new_ids != getattr(self, "_excluded_draft_ids", set()):
            self._excluded_draft_ids = new_ids
            self.refresh_notifications()

    def refresh_notifications(self):
        while self.notif_items_layout.count() > 0:
            item = self.notif_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        draft_count = 0
        upcoming_count = 0
        exp_count = 0

        try:
            from nemov.services.notification_service import NotificationService
            from nemov.services.draft_service import DraftService
            from nemov.utils.theme_manager import ThemeManager
            try:
                palette = ThemeManager.get_current_palette()
            except Exception:
                palette = None

            # --- 0. Unfinished Draft Work Notifications ---
            try:
                drafts = DraftService.list_drafts(exclude_draft_ids=getattr(self, "_excluded_draft_ids", set()))
            except Exception:
                drafts = []

            if drafts:
                draft_count = len(drafts)
                if palette:
                    d_bg, d_text, d_border, d_hover = ThemeManager.get_tone_colors("blue", palette)
                    r_bg, r_fg, r_bd, r_hv = ThemeManager.get_tone_colors("rose", palette)
                else:
                    d_bg, d_text, d_border, d_hover = "#1E293B", "#BFDBFE", "#3B82F6", "#1D4ED8"
                    r_bg, r_fg, r_bd, r_hv = "#3B1111", "#FCA5A5", "#EF4444", "#DC2626"

                for draft in drafts:
                    did = draft.get("draft_id", "")
                    sec_title = draft.get("section_title", "بخش")
                    d_title = draft.get("title") or sec_title
                    d_summary = draft.get("summary") or ""
                    d_time = draft.get("updated_shamsi") or ""

                    row_w = QWidget()
                    row_w.setFixedHeight(34)
                    row_w.setStyleSheet("background: transparent; border: none;")
                    row_l = QHBoxLayout(row_w)
                    row_l.setContentsMargins(0, 0, 0, 0)
                    row_l.setSpacing(3)

                    raw_text = f"📝 {d_title}"
                    tooltip_parts = [f"📝 کار ناتمام ({sec_title})", d_title]
                    if d_summary:
                        tooltip_parts.append(d_summary)
                    if d_time:
                        tooltip_parts.append(f"🕒 ذخیره خودکار: {d_time}")
                    tooltip_parts.append("(برای ادامه کلیک کنید)")
                    tooltip_text = "\n".join(tooltip_parts)

                    btn = SidebarNotifButton(scroll_area=self.notif_inner_scroll)
                    btn.setFixedHeight(34)
                    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {d_bg};
                            color: {d_text};
                            border: 1px solid {d_border};
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: right;
                        }}
                        QPushButton:hover {{
                            background-color: {d_hover};
                            border: 1px solid {d_border};
                            color: #FFFFFF;
                        }}
                    """)
                    btn.set_full_text(raw_text, tooltip_text)
                    btn.clicked.connect(lambda _, target_id=did: self.draft_clicked.emit(target_id))

                    btn_del = QPushButton("✕")
                    btn_del.setFixedSize(22, 34)
                    btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_del.setToolTip("حذف و صرف‌نظر کردن از این پیش‌نویس ناتمام")
                    btn_del.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {r_bg};
                            color: {r_fg};
                            border: 1px solid {r_bd};
                            border-radius: 6px;
                            font-size: 10px;
                            font-weight: bold;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: {r_hv};
                            color: #FFFFFF;
                            border-color: {r_hv};
                        }}
                    """)
                    btn_del.clicked.connect(lambda _, target_id=did: DraftService.delete_draft(target_id))

                    row_l.addWidget(btn, 1)
                    row_l.addWidget(btn_del, 0)
                    self.notif_items_layout.addWidget(row_w)

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
                    if palette and not palette.is_dark:
                        bday_bg = "#FEF3C7"
                        bday_text = "#78350F"
                        bday_border = "#F59E0B"
                        bday_hover = "#FDE68A"
                        bday_hover_border = "#D97706"
                    else:
                        bday_bg = palette.bg_surface if palette else "#241607"
                        bday_text = palette.text_primary if palette else "#FEF3C7"
                        bday_border = "#D97706"
                        bday_hover = palette.bg_card if palette else "#3B240B"
                        bday_hover_border = "#F59E0B"

                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {bday_bg};
                            color: {bday_text};
                            border: 1px solid {bday_border};
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            text-align: right;
                        }}
                        QPushButton:hover {{
                            background-color: {bday_hover};
                            border: 1px solid {bday_hover_border};
                            color: {bday_text if (palette and not palette.is_dark) else "#FFFFFF"};
                        }}
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
                    if palette and not palette.is_dark:
                        exp_bg = palette.btn_sec_bg
                        exp_text = palette.text_primary
                        exp_border = palette.primary
                        exp_hover = palette.btn_sec_hover
                        exp_hover_border = palette.primary_hover
                    else:
                        exp_bg = palette.bg_surface if palette else "#200C0C"
                        exp_text = palette.text_primary if palette else "#FEE2E2"
                        exp_border = palette.primary if palette else "#DC2626"
                        exp_hover = palette.bg_card if palette else "#3B1111"
                        exp_hover_border = palette.primary_hover if palette else "#EF4444"

                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {exp_bg};
                            color: {exp_text};
                            border: 1px solid {exp_border};
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            text-align: right;
                        }}
                        QPushButton:hover {{
                            background-color: {exp_hover};
                            border: 1px solid {exp_hover_border};
                            color: {exp_text if (palette and not palette.is_dark) else "#FFFFFF"};
                        }}
                    """)
                    btn.set_full_text(raw_text, tooltip_text)
                    btn.clicked.connect(lambda _, m_id=member.id: self.member_expiration_clicked.emit(m_id))
                    self.notif_items_layout.addWidget(btn)

            # --- 3. Update Available Notification ---
            update_count = 0
            try:
                from nemov.services.update_service import UpdateService
                if UpdateService.is_notification_pending():
                    info = UpdateService.get_latest_info()
                    new_tag = info.get("tag_name", "جدید")
                    update_count = 1
                    raw_text = f"🚀 نسخه جدید نِمو \u200E({new_tag})\u200E"
                    tooltip_text = f"نسخه جدید {new_tag} منتشر شده است.\n(جهت مشاهده تغییرات و دریافت کلیک فرمایید)"

                    btn = SidebarNotifButton(scroll_area=self.notif_inner_scroll)
                    btn.setFixedHeight(34)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    if palette and not palette.is_dark:
                        up_bg = "#ECFDF5"
                        up_text = "#065F46"
                        up_border = "#10B981"
                        up_hover = "#D1FAE5"
                        up_hover_border = "#059669"
                    else:
                        up_bg = "#064E3B"
                        up_text = "#A7F3D0"
                        up_border = "#10B981"
                        up_hover = "#065F46"
                        up_hover_border = "#34D399"

                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {up_bg};
                            color: {up_text};
                            border: 1px solid {up_border};
                            border-radius: 6px;
                            padding: 4px 6px;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: right;
                        }}
                        QPushButton:hover {{
                            background-color: {up_hover};
                            border: 1px solid {up_hover_border};
                            color: #FFFFFF;
                        }}
                    """)
                    btn.set_full_text(raw_text, tooltip_text)
                    btn.clicked.connect(self._on_update_notif_clicked)
                    self.notif_items_layout.addWidget(btn)
            except Exception:
                pass

        except Exception:
            pass

        total_notifs = draft_count + upcoming_count + exp_count + update_count
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
        if getattr(self, "_visual_collapsed", False):
            self._main_layout.setContentsMargins(6, 10, 6, 8)
            self._main_layout.setSpacing(4 if h < 680 else 6)
            c_nav_h = 32 if h < 660 else (36 if h < 740 else 40)
            self.nav_layout.setSpacing(2 if h < 660 else 4)
            for btn in self.nav_buttons_list:
                btn.setFixedHeight(c_nav_h)
            return
        if h < 680:
            tier = "compact"
            margins = (10, 8, 10, 8)
            main_spacing = 4
            nav_spacing = 2
            sub_font = "10.5px"
            sub_mb = "2px"
            btn_pad = "6px 12px"
            btn_font = "12.5px"
            bot_h = 32
        elif h < 760:
            tier = "medium"
            margins = (11, 10, 11, 10)
            main_spacing = 5
            nav_spacing = 4
            sub_font = "11px"
            sub_mb = "4px"
            btn_pad = "8px 14px"
            btn_font = "13px"
            bot_h = 34
        else:
            tier = "full"
            margins = (12, 14, 12, 14)
            main_spacing = 6
            nav_spacing = 6
            sub_font = "11px"
            sub_mb = "6px"
            btn_pad = "11px 16px"
            btn_font = "14px"
            bot_h = 36

        self._responsive_tier = tier
        self._btn_pad = btn_pad
        self._btn_font = btn_font
        self._sub_font = sub_font
        self._sub_mb = sub_mb
        self._bot_h = bot_h

        self._main_layout.setContentsMargins(*margins)
        self._main_layout.setSpacing(main_spacing)
        self.nav_layout.setSpacing(nav_spacing)
        if hasattr(self, "btn_logout"):
            self.btn_logout.setFixedHeight(bot_h)
            self.btn_dev.setFixedHeight(bot_h)

        self.nav_container.setObjectName("navContainer")
        self._apply_theme_style()

    def is_collapsed(self) -> bool:
        return bool(getattr(self, "_is_collapsed", False))

    def toggle_collapsed(self):
        self.set_collapsed(not self.is_collapsed(), animate=True, user_initiated=True)

    def set_collapsed(self, collapsed: bool, animate: bool = True, user_initiated: bool = False):
        """Smoothly slides the sidebar between expanded (230px) and collapsed icon-only (74px) states."""
        collapsed = bool(collapsed)
        target_w = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH

        if self._is_collapsed == collapsed and self.width() == target_w and getattr(self, "_visual_collapsed", collapsed) == collapsed:
            if user_initiated:
                self.collapse_toggled.emit(collapsed)
            return

        self._is_collapsed = collapsed

        if self._collapse_anim_group is not None:
            try:
                self._collapse_anim_group.stop()
            except Exception:
                pass
            self._collapse_anim_group = None

        if not animate:
            self.setFixedWidth(target_w)
            self._apply_collapsed_content(collapsed)
        else:
            if collapsed:
                # Hide expanded labels immediately so text never wraps/clips while narrowing
                self._apply_collapsed_content(True)

            group = QParallelAnimationGroup(self)
            anim_min = QPropertyAnimation(self, b"minimumWidth")
            anim_min.setDuration(220)
            anim_min.setStartValue(self.width())
            anim_min.setEndValue(target_w)
            anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)

            anim_max = QPropertyAnimation(self, b"maximumWidth")
            anim_max.setDuration(220)
            anim_max.setStartValue(self.width())
            anim_max.setEndValue(target_w)
            anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)

            group.addAnimation(anim_min)
            group.addAnimation(anim_max)
            self._collapse_anim_group = group
            group.finished.connect(lambda c=collapsed: self._on_collapse_anim_finished(c))
            group.start()

        if user_initiated:
            self.collapse_toggled.emit(collapsed)

    def _on_collapse_anim_finished(self, target_collapsed: bool):
        if self._is_collapsed != target_collapsed:
            return
        self.setFixedWidth(self.COLLAPSED_WIDTH if target_collapsed else self.EXPANDED_WIDTH)
        self._apply_collapsed_content(target_collapsed)

    def _apply_collapsed_content(self, collapsed: bool):
        self._visual_collapsed = collapsed
        self.expanded_header_widget.setVisible(not collapsed)
        self.collapsed_header_widget.setVisible(collapsed)

        # Navigation buttons: icon + Persian label (expanded) vs crisp centered icon + tooltip (collapsed)
        for btn in self.nav_buttons_list:
            nav_id = btn.property("navId")
            icon_char, full_title, clean_label = self._nav_meta.get(nav_id, ("", btn.text(), btn.text()))
            if collapsed:
                btn.setText(icon_char)
                btn.setToolTip(clean_label)
                btn.setFixedHeight(40)
            else:
                btn.setText(full_title)
                btn.setToolTip("")
                btn.setMinimumHeight(0)
                btn.setMaximumHeight(16777215)

        # Bottom action buttons: 1x2 horizontal row (expanded) vs 2x1 stacked icons (collapsed)
        if hasattr(self, "bottom_grid"):
            self.bottom_grid.removeWidget(self.btn_logout)
            self.bottom_grid.removeWidget(self.btn_dev)
            if collapsed:
                self.bottom_grid.setColumnStretch(0, 0)
                self.bottom_grid.setColumnStretch(1, 0)
                self.btn_dev.setText("👨‍💻")
                self.btn_logout.setText("🚪")
                self.btn_dev.setFixedSize(48, 34)
                self.btn_logout.setFixedSize(48, 34)
                self.bottom_grid.addWidget(self.btn_dev, 0, 0, Qt.AlignmentFlag.AlignHCenter)
                self.bottom_grid.addWidget(self.btn_logout, 1, 0, Qt.AlignmentFlag.AlignHCenter)
            else:
                bot_h = getattr(self, "_bot_h", 36)
                self.btn_logout.setMinimumWidth(0)
                self.btn_logout.setMaximumWidth(16777215)
                self.btn_dev.setMinimumWidth(0)
                self.btn_dev.setMaximumWidth(16777215)
                self.btn_logout.setFixedHeight(bot_h)
                self.btn_dev.setFixedHeight(bot_h)
                self.btn_logout.setText("🚪  خروج")
                self.btn_dev.setText("👨‍💻  درباره")
                self.bottom_grid.addWidget(self.btn_logout, 0, 0)
                self.bottom_grid.addWidget(self.btn_dev, 0, 1)
                self.bottom_grid.setColumnStretch(0, 1)
                self.bottom_grid.setColumnStretch(1, 1)

        # Sync progress text adaptation
        if self._sync_active and hasattr(self, "lbl_sync_title"):
            self.lbl_sync_title.setAlignment(Qt.AlignmentFlag.AlignCenter if collapsed else Qt.AlignmentFlag.AlignRight)
            self.lbl_sync_title.setText(self._sync_short_text if collapsed else self._sync_full_text)

        self._apply_responsive_metrics()
        self._apply_theme_style()
        self._update_notif_scroll_height()

    def _update_notif_scroll_height(self):
        total = getattr(self, "_total_notifs", 0)
        if total == 0:
            self.unified_notif_card.setVisible(False)
            if hasattr(self, "btn_collapsed_notif"):
                self.btn_collapsed_notif.setVisible(False)
            return

        fa_count = str(total).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        if getattr(self, "_visual_collapsed", False):
            self.unified_notif_card.setVisible(False)
            if hasattr(self, "btn_collapsed_notif"):
                self.btn_collapsed_notif.setText(f"🔔 {fa_count}")
                self.btn_collapsed_notif.setToolTip(f"یادآوری‌های روز ({fa_count} مورد) — کلیک برای مشاهده")
                self.btn_collapsed_notif.setVisible(True)
            return

        if hasattr(self, "btn_collapsed_notif"):
            self.btn_collapsed_notif.setVisible(False)
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
            from nemov.auth.authentication import get_developer_info
            from PyQt6.QtGui import QPixmap
            import os

            info = get_developer_info()
            fname = info.get("first_name", "مهندس ابوالفضل")
            lname = info.get("last_name", "صمدی کوچکسرائی")
            phone = info.get("phone", "09336427711")
            email = info.get("email", "a.samadi2006@gmail.com")
            github = info.get("github", "github.com/AbolfazlSamadi2006")
            photo_path = info.get("photo_path")

            self.lbl_dev_name.setText(f"{fname} {lname}".strip() or "مهندس ابوالفضل صمدی کوچکسرائی")
            self.lbl_dev_full.setText(f"{fname} {lname}".strip())
            self.lbl_dev_phone.setText(f"📞 {phone}")
            self.lbl_dev_email.setText(f"✉️ {email}")
            self.lbl_dev_github.setText(f"🐙 {github}")

            if photo_path and os.path.exists(photo_path):
                pixmap = QPixmap(photo_path)
                self.lbl_dev_photo.setPixmap(pixmap.scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                self.lbl_dev_photo.setFixedSize(42, 42)
                try:
                    from nemov.utils.theme_manager import ThemeManager
                    dev_border_color = ThemeManager.get_current_palette().primary
                except Exception:
                    dev_border_color = ThemeManager.PALETTES['crimson_fury'].primary
                self.lbl_dev_photo.setStyleSheet(f"border-radius: 21px; border: 1px solid {dev_border_color};")
            else:
                self.lbl_dev_photo.setText("👨‍💻")
                self.lbl_dev_photo.setStyleSheet("font-size: 20px;")
        except Exception:
            pass

    def refresh_branding(self):
        """Dynamically reloads the logo and title when updated in Appearance Settings."""
        try:
            from nemov.services.branding_service import BrandingService
            from PyQt6.QtGui import QPixmap
            import os

            # 1. Update logo (46x46 expanded, 34x34 collapsed)
            active_logo = BrandingService.get_active_logo_path()
            if active_logo and os.path.exists(active_logo):
                pix = QPixmap(active_logo).scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                if not pix.isNull():
                    self.logo_lbl.setPixmap(pix)
                if hasattr(self, "collapsed_logo_lbl"):
                    cpix = QPixmap(active_logo).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    if not cpix.isNull():
                        self.collapsed_logo_lbl.setPixmap(cpix)
            else:
                self.logo_lbl.setText("🔥")
                self.logo_lbl.setStyleSheet("font-size: 32px;")
                if hasattr(self, "collapsed_logo_lbl"):
                    self.collapsed_logo_lbl.setText("🔥")
                    self.collapsed_logo_lbl.setStyleSheet("font-size: 22px;")

            # 2. Update title & subtitle
            club_info = BrandingService.get_club_info()
            custom_club = (club_info.get("club_name") or "").strip()
            if custom_club:
                self.title_lbl.setText(custom_club)
                self.sub_lbl.setText(f"مدیریت ورزشی • {config.APP_NAME}")
            else:
                self.title_lbl.setText(config.APP_NAME)
                self.sub_lbl.setText("نرم‌افزار مدیریت ورزشی")

            # 3. Synchronize theme color and font-size
            self._apply_theme_style()
        except Exception:
            pass

    def _apply_theme_style(self):
        """Updates brand title color, sidebar background, navigation buttons, and sub-components to match active theme."""
        try:
            from nemov.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        if not palette:
            return

        if palette.key == "crimson_fury":
            brand_color = "#B91C1C"  # Rich slightly brighter crimson
        else:
            brand_color = palette.primary_hover if palette.is_dark else palette.primary

        btn_pad = getattr(self, "_btn_pad", "11px 16px")
        btn_font = getattr(self, "_btn_font", "14px")
        sub_font = getattr(self, "_sub_font", "11px")
        sub_mb = getattr(self, "_sub_mb", "6px")
        is_c = getattr(self, "_visual_collapsed", False)
        sb_h = self.height() if self.height() > 100 else 760
        nav_align = "center" if is_c else "right"
        nav_pad = "4px 2px" if is_c else btn_pad
        nav_font = ("16px" if sb_h < 660 else "19px") if is_c else btn_font

        # 1. Main sidebar frame, collapse/expand buttons & navigation buttons
        self.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {palette.bg_sidebar};
                border-left: 1px solid {palette.border};
            }}
            QWidget#sidebarHeaderWidget,
            QWidget#sidebarCollapsedHeaderWidget,
            QWidget#sidebarBrandCluster,
            QWidget#sidebarToggleSlot,
            QLabel#sidebarLogo {{
                background: transparent;
                border: none;
            }}
            QPushButton#sidebarToggleBtn {{
                background-color: {palette.btn_sec_bg};
                border: 1px solid {palette.btn_sec_border};
                border-radius: 7px;
                padding: 0px;
            }}
            QPushButton#sidebarToggleBtn:hover {{
                background-color: {palette.btn_sec_hover};
                border: 1px solid {palette.primary};
            }}
            QPushButton#collapsedNotifBtn {{
                background-color: {palette.bg_card};
                color: {palette.text_primary};
                border: 1px solid {palette.primary};
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 4px;
            }}
            QPushButton#collapsedNotifBtn:hover {{
                background-color: {palette.primary};
                color: {palette.primary_text};
            }}
            QWidget#navContainer > QPushButton {{
                background-color: transparent;
                color: {palette.text_secondary};
                text-align: {nav_align};
                padding: {nav_pad};
                border: none;
                border-radius: 6px;
                font-size: {nav_font};
            }}
            QWidget#navContainer > QPushButton:hover {{
                background-color: {palette.primary};
                color: {palette.primary_text};
            }}
            QWidget#navContainer > QPushButton[active="true"] {{
                background-color: {palette.primary};
                color: {palette.primary_text};
                font-weight: bold;
            }}
        """)

        icon_color = palette.text_primary if palette.is_dark else palette.text_secondary
        if hasattr(self, "btn_toggle_sidebar"):
            self.btn_toggle_sidebar.setIcon(self._make_sidebar_toggle_icon(icon_color, collapsed=False))
        if hasattr(self, "btn_expand_sidebar"):
            self.btn_expand_sidebar.setIcon(self._make_sidebar_toggle_icon(icon_color, collapsed=True))

        # 2. Brand title & Subtitle
        if hasattr(self, "title_lbl"):
            from nemov.services.branding_service import BrandingService
            club_info = BrandingService.get_club_info()
            custom_club = (club_info.get("club_name") or "").strip()
            if custom_club:
                f_size = 18 if len(custom_club) > 12 else 22
                self.title_lbl.setStyleSheet(f"color: {brand_color}; font-size: {f_size}px; font-weight: bold; background: transparent;")
            else:
                self.title_lbl.setStyleSheet(f"color: {brand_color}; font-size: 24px; font-weight: bold; background: transparent;")

        if hasattr(self, "sub_lbl"):
            self.sub_lbl.setStyleSheet(f"color: {palette.text_muted}; font-size: {sub_font}; margin-bottom: {sub_mb}; background: transparent;")

        # 3. Navigation scroll area scrollbar
        if hasattr(self, "nav_scroll_area"):
            self.nav_scroll_area.setStyleSheet(f"""
                QScrollArea#sidebarNavScroll {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea#sidebarNavScroll > QWidget > QWidget {{
                    background: transparent;
                }}
                QScrollArea#sidebarNavScroll QScrollBar:vertical {{
                    background: transparent;
                    width: 4px;
                    margin: 0px;
                }}
                QScrollArea#sidebarNavScroll QScrollBar::handle:vertical {{
                    background: {palette.scrollbar_handle};
                    min-height: 20px;
                    border-radius: 2px;
                }}
                QScrollArea#sidebarNavScroll QScrollBar::handle:vertical:hover {{
                    background: {palette.scrollbar_handle_hover};
                }}
                QScrollArea#sidebarNavScroll QScrollBar::add-line:vertical,
                QScrollArea#sidebarNavScroll QScrollBar::sub-line:vertical {{
                    height: 0px;
                    background: none;
                }}
            """)

        # 4. Sync progress frame & bar
        if hasattr(self, "sync_progress_frame"):
            sync_bg = palette.bg_surface if palette.is_dark else palette.bg_card
            self.sync_progress_frame.setStyleSheet(f"""
                QFrame#syncProgressFrame {{
                    background-color: {sync_bg};
                    border: 1px solid {palette.border};
                    border-radius: 8px;
                    margin-top: 4px;
                    margin-bottom: 4px;
                }}
            """)
        if hasattr(self, "lbl_sync_title"):
            sync_title_color = palette.primary_hover if palette.is_dark else palette.primary
            self.lbl_sync_title.setStyleSheet(f"color: {sync_title_color}; font-size: 11px; font-weight: bold;")
        if hasattr(self, "sync_progress_bar"):
            track_bg = palette.bg_base if palette.is_dark else "#E2E8F0"
            self.sync_progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {track_bg};
                    border-radius: 2px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background-color: {palette.primary};
                    border-radius: 2px;
                }}
            """)

        # 5. Unified notification card and controls
        if hasattr(self, "unified_notif_card"):
            self.unified_notif_card.setStyleSheet(f"""
                QFrame#unifiedNotifCard {{
                    background-color: {palette.bg_card};
                    border: 1px solid {palette.border};
                    border-radius: 8px;
                }}
            """)
        if hasattr(self, "lbl_unified_title"):
            self.lbl_unified_title.setStyleSheet(f"color: {palette.text_primary}; font-size: 11px; font-weight: bold; border: none; background: transparent;")

        if hasattr(self, "lbl_notif_badge"):
            self.lbl_notif_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {palette.primary};
                    color: {palette.primary_text};
                    border-radius: 9px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 1px 6px;
                    border: none;
                }}
            """)

        if hasattr(self, "btn_mark_all_read"):
            mark_bg = palette.btn_sec_bg
            mark_border = palette.btn_sec_border
            mark_text = palette.primary_hover if palette.is_dark else palette.primary
            self.btn_mark_all_read.setStyleSheet(f"""
                QPushButton {{
                    background-color: {mark_bg};
                    color: {mark_text};
                    border: 1px solid {mark_border};
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {palette.btn_sec_hover};
                    border: 1px solid {palette.primary};
                }}
                QPushButton:pressed {{
                    background-color: {mark_bg};
                }}
            """)

        if hasattr(self, "notif_inner_scroll"):
            self.notif_inner_scroll.setStyleSheet(f"""
                QScrollArea#notifInnerScroll {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea#notifInnerScroll > QWidget > QWidget {{
                    background: transparent;
                }}
                QScrollArea#notifInnerScroll QScrollBar:vertical {{
                    background-color: {palette.scrollbar_bg};
                    width: 4px;
                    margin: 0px;
                    border-radius: 2px;
                }}
                QScrollArea#notifInnerScroll QScrollBar::handle:vertical {{
                    background-color: {palette.scrollbar_handle};
                    min-height: 16px;
                    border-radius: 2px;
                }}
                QScrollArea#notifInnerScroll QScrollBar::handle:vertical:hover {{
                    background-color: {palette.scrollbar_handle_hover};
                }}
                QScrollArea#notifInnerScroll QScrollBar::add-line:vertical,
                QScrollArea#notifInnerScroll QScrollBar::sub-line:vertical {{
                    height: 0px;
                    background: none;
                }}
            """)

        # 6. Bottom action buttons (Logout & Developer)
        sec_bg = palette.btn_sec_bg
        sec_text = palette.btn_sec_text
        sec_border = palette.btn_sec_border
        sec_hover = palette.btn_sec_hover

        if hasattr(self, "btn_logout"):
            logout_hover = palette.primary_hover if palette.is_dark else palette.primary
            logout_pressed = palette.primary_pressed
            self.btn_logout.setStyleSheet(f"""
                QPushButton {{
                    background-color: {sec_bg};
                    color: {sec_text};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    border: 1px solid {sec_border};
                    padding: 6px 4px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {logout_hover};
                    color: {palette.primary_text};
                    border: 1px solid {logout_hover};
                }}
                QPushButton:pressed {{
                    background-color: {logout_pressed};
                    color: {palette.primary_text};
                }}
            """)

        if hasattr(self, "btn_dev"):
            self.btn_dev.setStyleSheet(f"""
                QPushButton {{
                    background-color: {sec_bg};
                    color: {sec_text};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    border: 1px solid {sec_border};
                    padding: 6px 4px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {sec_hover};
                    color: {palette.text_primary};
                }}
                QPushButton:pressed {{
                    background-color: {sec_bg};
                }}
                QPushButton[active="true"] {{
                    background-color: {palette.primary};
                    color: {palette.primary_text};
                    border: 1px solid {palette.primary_hover};
                    font-weight: bold;
                }}
            """)

        # 7. Developer avatar border if loaded
        if hasattr(self, "lbl_dev_photo") and self.lbl_dev_photo.pixmap() and not self.lbl_dev_photo.pixmap().isNull():
            self.lbl_dev_photo.setStyleSheet(f"border-radius: 21px; border: 1px solid {palette.primary};")

        # 8. Unpolish and polish buttons to refresh property styling
        current_nav = getattr(self, "_current_nav_id", "dashboard")
        for key, btn in self.buttons.items():
            btn.setProperty("active", (key == current_nav))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_theme_changed(self, theme_key: str):
        """Immediately re-applies brand logo/title, sidebar styles, and notification cards when theme changes."""
        self.refresh_branding()
        self._apply_theme_style()
        self.refresh_notifications()

    def _on_update_notif_clicked(self):
        try:
            from nemov.services.update_service import UpdateService
            UpdateService.mark_notification_seen()
        except Exception:
            pass
        self.refresh_notifications()
        self.navigate("developer")

    def navigate(self, nav_id: str):
        if nav_id == "developer":
            try:
                from nemov.services.update_service import UpdateService
                UpdateService.mark_notification_seen()
                QTimer.singleShot(50, self.refresh_notifications)
            except Exception:
                pass

        self.set_active(nav_id)
        self.page_changed.emit(nav_id)

    def set_active(self, nav_id: str):
        self._current_nav_id = nav_id
        for key, btn in self.buttons.items():
            is_active = (key == nav_id)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_cloud_sync_progress(self, remaining: int, total: int):
        """Updates the sidebar cloud video sync progress panel."""
        self._sync_active = True
        self.sync_progress_frame.setVisible(True)
        fa_rem = str(remaining).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        fa_tot = str(total).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        try:
            from nemov.utils.theme_manager import ThemeManager
            pal = ThemeManager.get_current_palette()
            color = pal.primary_hover if pal.is_dark else pal.primary
        except Exception:
            color = "#93C5FD"
        self._sync_full_text = f"در حال آپلود ... ( {fa_rem} از {fa_tot} )"
        self._sync_short_text = f"☁️ {fa_rem}"
        is_c = getattr(self, "_visual_collapsed", False)
        self.lbl_sync_title.setAlignment(Qt.AlignmentFlag.AlignCenter if is_c else Qt.AlignmentFlag.AlignRight)
        self.lbl_sync_title.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        self.lbl_sync_title.setText(self._sync_short_text if is_c else self._sync_full_text)
        self.lbl_sync_title.setToolTip(self._sync_full_text)
        done = max(0, total - remaining)
        pct = int((done / total) * 100) if total > 0 else 0
        self.sync_progress_bar.setValue(pct)

    def finish_cloud_sync_progress(self, success_count: int, fail_count: int):
        """Displays completion status and smoothly auto-hides after a brief delay."""
        fa_suc = str(success_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        is_c = getattr(self, "_visual_collapsed", False)
        self.lbl_sync_title.setAlignment(Qt.AlignmentFlag.AlignCenter if is_c else Qt.AlignmentFlag.AlignRight)
        if fail_count == 0:
            self._sync_full_text = f"✅ آپلود {fa_suc} ویدیو با موفقیت انجام شد"
            self._sync_short_text = f"✅ {fa_suc}"
            self.lbl_sync_title.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold;")
            self.sync_progress_bar.setValue(100)
        else:
            fa_fail = str(fail_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self._sync_full_text = f"⚠️ {fa_suc} آپلود شد، {fa_fail} خطا"
            self._sync_short_text = f"⚠️ {fa_fail}"
            self.lbl_sync_title.setStyleSheet("color: #F87171; font-size: 11px; font-weight: bold;")
        self.lbl_sync_title.setText(self._sync_short_text if is_c else self._sync_full_text)
        self.lbl_sync_title.setToolTip(self._sync_full_text)

        QTimer.singleShot(4000, self.hide_cloud_sync_progress)

    def hide_cloud_sync_progress(self):
        """Hides the cloud sync progress panel."""
        self._sync_active = False
        self.sync_progress_frame.setVisible(False)
        self.lbl_sync_title.setStyleSheet("color: #93C5FD; font-size: 11px; font-weight: bold;")


