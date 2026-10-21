import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from nemov.services.member_service import MemberService
from nemov.utils.jalali_date import days_until_expire, get_today_shamsi
from nemov.utils.image_utils import get_circular_pixmap, resolve_image_path
from nemov.views.components.circular_image_preview_dialog import CircularImagePreviewDialog

class DashboardView(QWidget):
    navigate_to = pyqtSignal(str) # Emits target page name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        try:
            from nemov.utils.theme_manager import ThemeManager
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def init_ui(self):
        try:
            from nemov.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Title & Date
        header_layout = QHBoxLayout()
        from nemov.services.branding_service import BrandingService
        club_name = BrandingService.get_active_club_name()
        title = QLabel(f"داشبورد مدیریتی | {club_name}")
        title.setObjectName("h1")
        
        date_color = palette.primary if palette else "#DC2626"
        self.date_lbl = QLabel(f"تاریخ امروز: {get_today_shamsi()}")
        self.date_lbl.setStyleSheet(f"color: {date_color}; font-weight: bold; font-size: 14px;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.date_lbl)
        layout.addLayout(header_layout)

        # Quick Actions Bar
        from PyQt6.QtWidgets import QSizePolicy
        actions_frame = QFrame()
        actions_frame.setObjectName("card")
        actions_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(12, 12, 12, 12)

        quick_color = palette.text_primary if palette else "#FFFFFF"
        self.lbl_quick = QLabel("دسترسی سریع:")
        self.lbl_quick.setStyleSheet(f"font-weight: bold; color: {quick_color}; background: transparent;")

        btn_add_member = QPushButton("➕ ثبت عضو جدید")
        btn_add_member.setObjectName("primary_button")
        btn_add_member.setFixedHeight(36)
        btn_add_member.clicked.connect(lambda: self.navigate_to.emit("add_member"))

        btn_quick_tuition = QPushButton("💰 ثبت شهریه")
        btn_quick_tuition.setFixedHeight(36)
        btn_quick_tuition.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quick_tuition.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        btn_quick_tuition.clicked.connect(lambda: self.navigate_to.emit("pay_tuition"))

        btn_new_workout = QPushButton("🏋️ ساخت برنامه تمرینی")
        btn_new_workout.setObjectName("secondary_button")
        btn_new_workout.setFixedHeight(36)
        btn_new_workout.clicked.connect(lambda: self.navigate_to.emit("new_workout"))

        btn_new_nutrition = QPushButton("🥗 ساخت برنامه غذایی")
        btn_new_nutrition.setObjectName("secondary_button")
        btn_new_nutrition.setFixedHeight(36)
        btn_new_nutrition.clicked.connect(lambda: self.navigate_to.emit("new_nutrition"))

        actions_layout.addWidget(self.lbl_quick)
        actions_layout.addWidget(btn_add_member)
        actions_layout.addWidget(btn_quick_tuition)
        actions_layout.addWidget(btn_new_workout)
        actions_layout.addWidget(btn_new_nutrition)
        actions_layout.addStretch()

        layout.addWidget(actions_frame)

        # All Members Table
        table_title = QLabel("📋 لیست کلیه ورزشکاران و وضعیت انقضای عضویت")
        table_title.setObjectName("h2")
        layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ورزشکار", "مربی مربوطه", "شماره تماس", "نوع عضویت", "تاریخ انقضا (شمسی)", "وضعیت"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table, 1)
        
        # Initial Data Refresh
        self.refresh_dashboard()

    def open_avatar_preview(self, photo_path: str, member_name: str):
        """Opens a circular animated popup zoom of athlete's photo."""
        resolved = resolve_image_path(photo_path)
        if resolved:
            dlg = CircularImagePreviewDialog(resolved, title=member_name, parent=self)
            dlg.exec()

    def refresh_dashboard(self):
        try:
            from nemov.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        border_col = palette.primary if palette else "#DC2626"
        name_col = palette.text_primary if palette else "#FFFFFF"

        members = MemberService.get_all_members(status_filter="all")
        
        # Populate All Members Table
        self.table.setRowCount(len(members))

        MEMBERSHIP_TYPE_MAP = {
            "12_sessions": "۱۲ جلسه در ماه",
            "8_sessions": "۸ جلسه در ماه",
            "16_sessions": "۱۶ جلسه در ماه",
            "20_sessions": "۲۰ جلسه در ماه",
            "daily_access": "همه روزه"
        }

        for row, m in enumerate(members):
            # Custom Column 0: Circular Avatar + Name
            cell_w = QWidget()
            cell_w.setStyleSheet("background: transparent;")
            cell_l = QHBoxLayout(cell_w)
            cell_l.setContentsMargins(8, 3, 8, 3)
            cell_l.setSpacing(10)
            cell_l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            lbl_avatar = QLabel()
            lbl_avatar.setFixedSize(36, 36)
            lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

            has_valid_photo = False
            resolved_photo = resolve_image_path(m.photo_path)
            if resolved_photo:
                pix = QPixmap(resolved_photo)
                if not pix.isNull():
                    circ_pix = get_circular_pixmap(pix, 36, border_color=border_col, border_width=2)
                    lbl_avatar.setPixmap(circ_pix)
                    lbl_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
                    lbl_avatar.setToolTip(f"برای مشاهده تصویر بزرگ‌تر «{m.full_name}» کلیک کنید")
                    lbl_avatar.mousePressEvent = lambda e, p=resolved_photo, n=m.full_name: self.open_avatar_preview(p, n)
                    has_valid_photo = True

            if not has_valid_photo:
                lbl_avatar.setText("👤")
                if palette:
                    lbl_avatar.setStyleSheet(f"""
                        QLabel {{
                            background-color: {palette.btn_sec_bg};
                            border: 1px solid {palette.border};
                            border-radius: 18px;
                            color: {palette.text_muted};
                            font-size: 16px;
                        }}
                    """)
                else:
                    lbl_avatar.setStyleSheet("""
                        QLabel {
                            background-color: #242424;
                            border: 1px solid #444444;
                            border-radius: 18px;
                            color: #777777;
                            font-size: 16px;
                        }
                    """)

            lbl_name = QLabel(m.full_name)
            lbl_name.setStyleSheet(f"color: {name_col}; font-size: 13px; font-weight: bold; background: transparent;")

            cell_l.addWidget(lbl_avatar)
            cell_l.addWidget(lbl_name)
            cell_l.addStretch()

            self.table.setCellWidget(row, 0, cell_w)

            # Column 1: Trainer
            item_trainer = QTableWidgetItem(m.trainer_name or "-")
            item_trainer.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, item_trainer)

            # Column 2: Phone
            item_phone = QTableWidgetItem(m.phone or "-")
            item_phone.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, item_phone)

            # Column 3: Membership Type
            m_type_fa = MEMBERSHIP_TYPE_MAP.get(m.membership_type, m.membership_type or "-")
            item_type = QTableWidgetItem(m_type_fa)
            item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, item_type)

            # Column 4: Expire Date
            item_exp = QTableWidgetItem(m.membership_expire_shamsi or "-")
            item_exp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, item_exp)
            
            # Column 5: Status
            days_left = days_until_expire(m.membership_expire_shamsi)
            if m.status == "archived":
                status_text = "آرشیو شده ⚪"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.gray)
            elif days_left < 0 or m.status == "expired":
                status_text = "انقضا یافته 🔴"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.red)
            elif 0 <= days_left <= 5:
                status_text = f"در آستانه انقضا ({days_left} روز) 🟡"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.yellow)
            else:
                status_text = f"فعال ({days_left} روز باقی‌مانده) 🟢"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.green)

            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, status_item)

    def _on_theme_changed(self, theme_key: str):
        self._apply_theme_style()
        self.refresh_dashboard()

    def _apply_theme_style(self):
        try:
            from nemov.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            return
        if hasattr(self, "date_lbl") and self.date_lbl:
            self.date_lbl.setStyleSheet(f"color: {palette.primary}; font-weight: bold; font-size: 14px;")
        if hasattr(self, "lbl_quick") and self.lbl_quick:
            self.lbl_quick.setStyleSheet(f"font-weight: bold; color: {palette.text_primary}; background: transparent;")

