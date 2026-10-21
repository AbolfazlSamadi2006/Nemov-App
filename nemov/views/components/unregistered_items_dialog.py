from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt
from nemov.utils.theme_manager import ThemeManager


class UnregisteredItemsDialog(QDialog):
    """
    Dialog displayed when a trainer writes exercises or food items that do not exist
    in the respective database bank.

    Allows the trainer to:
    1. Register the unlisted items into the bank and assign/save the plan.
    2. Assign/save the plan without registering the items in the bank (items persist in plan & PDF).
    3. Cancel and return to editing.
    """
    ACTION_REGISTER = "register"
    ACTION_UNLISTED = "unlisted"
    ACTION_CANCEL = "cancel"

    def __init__(self, item_type: str = "exercise", unregistered_items: list = None, mode: str = "assign", parent=None):
        super().__init__(parent)
        self.item_type = item_type  # "exercise" or "food"
        self.unregistered_items = unregistered_items or []
        self.mode = mode  # "assign" or "save"
        self.action_result = self.ACTION_CANCEL

        is_ex = (self.item_type == "exercise")
        self.unit_title = "حرکت ورزشی" if is_ex else "ماده غذایی"
        self.unit_plural = "حرکات ورزشی" if is_ex else "مواد غذایی"

        title_action = "تخصیص برنامه" if mode == "assign" else "ذخیره الگو"
        self.setWindowTitle(f"⚠️ بررسی {self.unit_plural} ثبت‌نشده در بانک")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(520)

        self.init_ui()

    def init_ui(self):
        palette = ThemeManager.get_current_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header with warning badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        lbl_icon = QLabel("!")
        lbl_icon.setFixedSize(38, 38)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"""
            background-color: rgba(245, 158, 11, 0.15);
            color: {palette.primary};
            font-size: 22px;
            font-weight: 900;
            font-family: Arial, Tahoma, sans-serif;
            border: 2px solid {palette.primary};
            border-radius: 19px;
        """)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        lbl_header_title = QLabel(f"ثبت‌نشده بودن {len(self.unregistered_items)} {self.unit_title} در بانک")
        lbl_header_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {palette.primary};")

        lbl_header_desc = QLabel(
            f"تعداد <b>{len(self.unregistered_items)} مورد</b> از {self.unit_plural} وارد شده در جدول، در بانک اطلاعاتی موجود نیستند."
        )
        lbl_header_desc.setWordWrap(True)
        lbl_header_desc.setObjectName("muted_text")

        header_text_layout.addWidget(lbl_header_title)
        header_text_layout.addWidget(lbl_header_desc)

        header_layout.addWidget(lbl_icon)
        header_layout.addLayout(header_text_layout, 1)
        layout.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"background-color: {palette.border}; max-height: 1px;")
        layout.addWidget(sep)

        # Collapsible button for list of unregistered items
        self.btn_toggle_list = QPushButton(f"لیست موارد ثبت‌نشده ({len(self.unregistered_items)} مورد)  [نمایش]")
        self.btn_toggle_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_list.setFixedHeight(34)
        self.btn_toggle_list.setObjectName("secondary_button")
        self.btn_toggle_list.clicked.connect(self._toggle_items_list)
        layout.addWidget(self.btn_toggle_list)

        # Scrollable container for unregistered items (initially hidden)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(120)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {palette.bg_surface};
                border: 1px solid {palette.border};
                border-radius: 6px;
            }}
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 8, 10, 8)
        scroll_layout.setSpacing(6)

        for idx, item_name in enumerate(self.unregistered_items, start=1):
            lbl_item = QLabel(f"<b>{idx}.</b> {item_name}")
            lbl_item.setStyleSheet(f"""
                background-color: {palette.bg_card};
                border: 1px solid {palette.border};
                border-radius: 4px;
                padding: 5px 10px;
                color: {palette.text_primary};
                font-size: 12px;
            """)
            scroll_layout.addWidget(lbl_item)

        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_widget)
        self.scroll_area.setVisible(False)
        layout.addWidget(self.scroll_area)

        # Explanatory description
        lbl_hint = QLabel(
            "لطفاً نحوه ذخیره‌سازی و ادامه عملیات را انتخاب نمایید:<br>"
            "• <b>ثبت در بانک:</b> این موارد به بانک دائمی اضافه شده و در آینده در لیست کشویی در دسترس خواهند بود.<br>"
            "• <b>بدون ثبت در بانک:</b> بانک تغییر نمی‌کند؛ ولی نام موارد در برنامه این ورزشکار و فایل PDF محفوظ می‌ماند."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted_text")
        layout.addWidget(lbl_hint)

        # Action Buttons
        btn_action_text = "تخصیص" if self.mode == "assign" else "ذخیره"

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_register = QPushButton(f"{btn_action_text} و ثبت در بانک")
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.setFixedHeight(40)
        self.btn_register.setObjectName("primary_button")
        self.btn_register.clicked.connect(self._on_register_clicked)

        self.btn_unlisted = QPushButton(f"{btn_action_text} بدون ثبت در بانک")
        self.btn_unlisted.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unlisted.setFixedHeight(40)
        self.btn_unlisted.setObjectName("secondary_button")
        self.btn_unlisted.clicked.connect(self._on_unlisted_clicked)

        self.btn_cancel = QPushButton("انصراف و ویرایش")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setObjectName("secondary_button")
        self.btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_register, 2)
        btn_row.addWidget(self.btn_unlisted, 2)
        btn_row.addWidget(self.btn_cancel, 1)
        layout.addLayout(btn_row)

    def _toggle_items_list(self):
        is_visible = not self.scroll_area.isVisible()
        self.scroll_area.setVisible(is_visible)
        if is_visible:
            self.btn_toggle_list.setText(f"لیست موارد ثبت‌نشده ({len(self.unregistered_items)} مورد)  [بستن]")
        else:
            self.btn_toggle_list.setText(f"لیست موارد ثبت‌نشده ({len(self.unregistered_items)} مورد)  [نمایش]")
        self.adjustSize()

    def _on_register_clicked(self):
        self.action_result = self.ACTION_REGISTER
        self.accept()

    def _on_unlisted_clicked(self):
        self.action_result = self.ACTION_UNLISTED
        self.accept()
