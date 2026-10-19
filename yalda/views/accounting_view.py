import csv
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QFileDialog, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from yalda.services.accounting_service import AccountingService
from yalda.views.components.expense_form_dialog import ExpenseFormDialog
from yalda.views.components.tuition_payment_dialog import TuitionPaymentDialog
from yalda.views.components.jalali_calendar_widget import JalaliDatePicker
from yalda.utils.jalali_date import get_today_shamsi, get_now_shamsi_for_filename, is_valid_shamsi
from yalda.pdf.pdf_generator import PDFGenerator
from yalda.utils.excel_generator import ExcelGenerator
from yalda.auth.authentication import CurrentUser

class AccountingView(QWidget):
    member_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.current_filter_key = "this_month"
        self.custom_start_date = None
        self.custom_end_date = None

        self.init_ui()
        self.load_data()
        try:
            from yalda.utils.theme_manager import ThemeManager
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, theme_key: str = ""):
        self.update()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ==========================================
        # ==========================================
        # 1. Header & Overview Stat Cards (Unified Grid)
        # ==========================================
        overview_grid = QGridLayout()
        overview_grid.setHorizontalSpacing(14)
        overview_grid.setVerticalSpacing(12)
        overview_grid.setContentsMargins(0, 0, 0, 0)
        for col in range(4):
            overview_grid.setColumnStretch(col, 1)

        # Title in Row 0, Cols 0-1
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_title = QLabel("💰 مدیریت امور مالی، درآمدها و هزینه‌های باشگاه")
        lbl_title.setObjectName("h1")
        lbl_sub = QLabel("محاسبه و نمایش دقیق درآمدها، هزینه‌ها، سود خالص و تفکیک عملکرد مربیان")
        lbl_sub.setObjectName("muted_text")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        overview_grid.addLayout(title_box, 0, 0, 1, 2)

        # Pair 1: Buttons over "سود و تراز خالص" (Col 2)
        pair_profit_buttons = QHBoxLayout()
        pair_profit_buttons.setSpacing(8)
        pair_profit_buttons.setContentsMargins(0, 0, 0, 0)

        self.btn_add_expense = QPushButton("➕ ثبت هزینه جدید")
        self.btn_add_expense.setFixedHeight(38)
        self.btn_add_expense.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_add_expense.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_expense.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                font-size: 12.5px;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.btn_add_expense.clicked.connect(self.open_add_expense_dialog)

        self.btn_add_tuition = QPushButton("💰 ثبت پرداخت شهریه")
        self.btn_add_tuition.setFixedHeight(38)
        self.btn_add_tuition.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_add_tuition.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_tuition.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                font-size: 12.5px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_add_tuition.clicked.connect(self.open_add_tuition_dialog)

        pair_profit_buttons.addWidget(self.btn_add_expense)
        pair_profit_buttons.addWidget(self.btn_add_tuition)
        overview_grid.addLayout(pair_profit_buttons, 0, 2)

        # Pair 2: Buttons over "تعداد تراکنش‌ها" (Col 3)
        pair_count_buttons = QHBoxLayout()
        pair_count_buttons.setSpacing(8)
        pair_count_buttons.setContentsMargins(0, 0, 0, 0)

        self.btn_export_pdf = QPushButton("📄 گزارش PDF")
        self.btn_export_pdf.setFixedHeight(38)
        self.btn_export_pdf.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                font-size: 12.5px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.btn_export_pdf.clicked.connect(self.export_pdf_report)

        self.btn_export_excel = QPushButton("📊 خروجی اکسل")
        self.btn_export_excel.setFixedHeight(38)
        self.btn_export_excel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_export_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_excel.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                font-weight: bold;
                border: 1px solid #4B5563;
                border-radius: 6px;
                font-size: 12.5px;
            }
            QPushButton:hover { background-color: #4B5563; color: #FFFFFF; }
        """)
        self.btn_export_excel.clicked.connect(self.export_excel_report)

        pair_count_buttons.addWidget(self.btn_export_pdf)
        pair_count_buttons.addWidget(self.btn_export_excel)
        overview_grid.addLayout(pair_count_buttons, 0, 3)

        # Row 1: Stat Cards
        self.card_income = self._create_stat_card("🟢 کل دریافتی‌ها (درآمد شهریه)", "۰ تومان", "#10B981")
        self.card_expense = self._create_stat_card("🔴 کل مخارج (هزینه‌های باشگاه)", "۰ تومان", "#EF4444")
        self.card_profit = self._create_stat_card("🔵 سود و تراز خالص", "۰ تومان", "#3B82F6")
        self.card_count = self._create_stat_card("📋 تعداد تراکنش‌ها", "۰", "#A855F7")

        overview_grid.addWidget(self.card_income, 1, 0)
        overview_grid.addWidget(self.card_expense, 1, 1)
        overview_grid.addWidget(self.card_profit, 1, 2)
        overview_grid.addWidget(self.card_count, 1, 3)

        main_layout.addLayout(overview_grid)

        # ==========================================
        # 3. Filters Panel
        # ==========================================
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        filter_grid = QGridLayout(filter_frame)
        filter_grid.setContentsMargins(10, 10, 10, 10)
        filter_grid.setHorizontalSpacing(14)
        filter_grid.setVerticalSpacing(10)

        # Row 0, Col 0: Trainer Filter + Transaction Type
        r1_right = QHBoxLayout()
        r1_right.setContentsMargins(0, 0, 0, 0)
        r1_right.setSpacing(10)

        self.lbl_trainer = QLabel("انتخاب مربی:")
        self.lbl_trainer.setFixedWidth(85)
        self.lbl_trainer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r1_right.addWidget(self.lbl_trainer)

        self.combo_trainer_filter = QComboBox()
        self.combo_trainer_filter.setFixedWidth(200)
        self.combo_trainer_filter.setFixedHeight(38)
        self.reload_trainers()
        self.combo_trainer_filter.currentIndexChanged.connect(self.on_filter_changed)
        r1_right.addWidget(self.combo_trainer_filter)

        self.lbl_type = QLabel("نوع تراکنش:")
        self.lbl_type.setFixedWidth(75)
        self.lbl_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r1_right.addWidget(self.lbl_type)

        # 1. طول فیلد لیست باکس همه تراکنش ها کمتر شه (210px) با حفظ کامل و خوانای متن
        self.combo_type_filter = QComboBox()
        self.combo_type_filter.setFixedWidth(210)
        self.combo_type_filter.setFixedHeight(38)
        self.combo_type_filter.addItem("همه تراکنش‌ها (درآمد و هزینه)", "all")
        self.combo_type_filter.addItem("🟢 فقط درآمدها (شهریه)", "income")
        self.combo_type_filter.addItem("🔴 فقط هزینه‌ها (مخارج)", "expense")
        self.combo_type_filter.currentIndexChanged.connect(self.on_filter_changed)
        r1_right.addWidget(self.combo_type_filter)
        filter_grid.addLayout(r1_right, 0, 0)

        # Labels for search and from (matched width 54 so both input boxes start at exact same line)
        self.lbl_search = QLabel("جستجو:")
        self.lbl_search.setFixedWidth(54)
        self.lbl_search.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Row 0, Col 1: Search Bar
        r1_left = QHBoxLayout()
        r1_left.setContentsMargins(0, 0, 0, 0)
        r1_left.setSpacing(8)
        r1_left.addWidget(self.lbl_search)
        self.txt_search = QLineEdit()
        self.txt_search.setFixedHeight(38)
        self.txt_search.setPlaceholderText("جستجو در عنوان، نام طرف حساب یا توضیحات...")
        self.txt_search.textChanged.connect(self.on_filter_changed)
        r1_left.addWidget(self.txt_search)
        filter_grid.addLayout(r1_left, 0, 1)

        # Row 1, Col 0: Quick Period Buttons
        r2_right = QHBoxLayout()
        r2_right.setContentsMargins(0, 0, 0, 0)
        r2_right.setSpacing(8)

        # 2. عرض کادر فیلد بازه زمانی به اندازه انتخاب مربی (85px) و وسط چین
        self.lbl_period = QLabel("بازه زمانی:")
        self.lbl_period.setFixedWidth(85)
        self.lbl_period.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r2_right.addWidget(self.lbl_period)
        r2_right.addSpacing(2)

        # 3. عرض فیلدهای بازه زمانی طوری که آخرین مورد (کل دوره) دقیقا تراز با انتهای همه تراکنش ها باشه
        self.btn_filter_today = self._create_quick_btn("امروز", "today", 66)
        self.btn_filter_week = self._create_quick_btn("هفته جاری", "this_week", 85)
        self.btn_filter_month = self._create_quick_btn("ماه جاری", "this_month", 80)
        self.btn_filter_year = self._create_quick_btn("سال جاری", "this_year", 80)
        self.btn_filter_last30 = self._create_quick_btn("۳۰ روز اخیر", "last_30_days", 85)
        self.btn_filter_all = self._create_quick_btn("کل دوره", "all", 69)

        self.quick_buttons = {
            "today": self.btn_filter_today,
            "this_week": self.btn_filter_week,
            "this_month": self.btn_filter_month,
            "this_year": self.btn_filter_year,
            "last_30_days": self.btn_filter_last30,
            "all": self.btn_filter_all
        }

        for btn in self.quick_buttons.values():
            r2_right.addWidget(btn)
        filter_grid.addLayout(r2_right, 1, 0)

        # Row 1, Col 1: Date Setting Group (perfectly aligned with Search)
        r2_left = QHBoxLayout()
        r2_left.setContentsMargins(0, 0, 0, 0)
        r2_left.setSpacing(8)

        # 4. متن از: رو وسط چین کن
        self.lbl_from = QLabel("از:")
        self.lbl_from.setFixedWidth(54)
        self.lbl_from.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r2_left.addWidget(self.lbl_from)

        # 5. تنظیم فیلدهای تاریخ و کادر تا: هم‌اندازه با از: و وسط‌چین
        self.date_from = JalaliDatePicker()
        self.date_from.setMinimumWidth(145)
        self.date_from.line_edit.setMinimumWidth(98)
        self.date_from.line_edit.setStyleSheet("padding: 6px 4px;")
        self.date_from.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r2_left.addWidget(self.date_from)

        self.lbl_to = QLabel("تا:")
        self.lbl_to.setFixedWidth(54)
        self.lbl_to.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r2_left.addWidget(self.lbl_to)

        self.date_to = JalaliDatePicker()
        self.date_to.setMinimumWidth(145)
        self.date_to.line_edit.setMinimumWidth(98)
        self.date_to.line_edit.setStyleSheet("padding: 6px 4px;")
        self.date_to.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r2_left.addWidget(self.date_to)

        self.btn_apply_custom_date = QPushButton("اعمال بازه")
        self.btn_apply_custom_date.setObjectName("primary_button")
        self.btn_apply_custom_date.setFixedHeight(38)
        self.btn_apply_custom_date.setFixedWidth(85)
        self.btn_apply_custom_date.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_custom_date.clicked.connect(self.apply_custom_date_range)
        r2_left.addWidget(self.btn_apply_custom_date)
        filter_grid.addLayout(r2_left, 1, 1)

        filter_grid.setColumnStretch(0, 0)
        filter_grid.setColumnStretch(1, 1)
        filter_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        main_layout.addWidget(filter_frame)

        # ==========================================
        # 4. Transactions Table
        # ==========================================
        self.table = QTableWidget()
        headers = [
            "ردیف", "نوع تراکنش", "عنوان / طرف حساب", "دسته‌بندی", "تاریخ شمسی", "مبلغ (تومان)", "مربی / ثبت‌کننده", "توضیحات", "عملیات"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for col in range(len(headers)):
            h_item = self.table.horizontalHeaderItem(col)
            if h_item:
                h_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 42)
        self.table.setColumnWidth(1, 138)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 122)
        self.table.setColumnWidth(4, 95)
        self.table.setColumnWidth(5, 112)
        self.table.setColumnWidth(6, 115)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 140)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table, 1)

        # Empty Label (with Expanding vertical size policy so top cards NEVER stretch when table is hidden)
        self.lbl_empty = QLabel("هیچ تراکنشی منطبق بر فیلترهای انتخابی یافت نشد.")
        self.lbl_empty.setObjectName("card")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_empty.setStyleSheet("font-size: 14px; padding: 40px;")
        self.lbl_empty.setVisible(False)
        main_layout.addWidget(self.lbl_empty, 1)

        # Update initial quick button active state and populate default date inputs
        self._highlight_quick_btn("this_month")
        init_start, init_end = AccountingService.get_date_range_for_filter("this_month")
        if init_start:
            self.date_from.setText(init_start)
            self.date_to.setText(init_end)

    def _create_stat_card(self, title: str, default_val: str, accent_color: str):
        try:
            from yalda.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        bg_card = palette.bg_card if palette else "#181818"
        border_col = palette.border if palette else "#2E2E2E"
        text_muted = palette.text_muted if palette else "#888888"
        text_primary = palette.text_primary if palette else "#FFFFFF"

        card = QFrame()
        card.setObjectName("statCard")
        card.setProperty("accent_color", accent_color)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setFixedHeight(78)
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {bg_card};
                border: 1px solid {border_col};
                border-right: 4px solid {accent_color};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(4)
        vbox.setContentsMargins(0, 0, 0, 0)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("titleLabel")
        lbl_t.setStyleSheet(f"color: {text_muted}; font-size: 12px; font-weight: normal; background: transparent;")
        lbl_v = QLabel(default_val)
        lbl_v.setObjectName("valLabel")
        lbl_v.setStyleSheet(f"color: {text_primary}; font-size: 18px; font-weight: bold; background: transparent;")

        vbox.addWidget(lbl_t)
        vbox.addWidget(lbl_v)
        return card

    def _update_stat_card_value(self, card: QFrame, val_str: str, color_override: str = None):
        try:
            from yalda.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None
        default_color = palette.text_primary if palette else "#FFFFFF"

        lbl = card.findChild(QLabel, "valLabel")
        if lbl:
            lbl.setText(val_str)
            if color_override:
                lbl.setStyleSheet(f"color: {color_override}; font-size: 18px; font-weight: bold; background: transparent;")
            else:
                lbl.setStyleSheet(f"color: {default_color}; font-size: 18px; font-weight: bold; background: transparent;")

    def _create_quick_btn(self, text: str, key: str, width: int = None):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        if width:
            btn.setFixedWidth(width)
        btn.clicked.connect(lambda _, k=key: self.on_quick_period_clicked(k))
        return btn

    def _highlight_quick_btn(self, active_key: str):
        try:
            from yalda.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            palette = None

        if palette:
            active_bg = palette.primary
            active_text = palette.primary_text
            active_hover = palette.primary_hover
            sec_bg = palette.btn_sec_bg
            sec_text = palette.btn_sec_text
            sec_border = palette.btn_sec_border
            sec_hover = palette.btn_sec_hover
        else:
            active_bg = "#DC2626"
            active_text = "#FFFFFF"
            active_hover = "#B91C1C"
            sec_bg = "#262626"
            sec_text = "#A0A0A0"
            sec_border = "#3A3A3A"
            sec_hover = "#333333"

        for k, btn in self.quick_buttons.items():
            if k == active_key:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_bg};
                        color: {active_text};
                        font-weight: bold;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 12px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {active_hover};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {sec_bg};
                        color: {sec_text};
                        border: 1px solid {sec_border};
                        border-radius: 6px;
                        padding: 4px 12px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {sec_hover};
                    }}
                """)

    def _on_theme_changed(self, theme_key: str):
        self._highlight_quick_btn(self.current_filter_key)
        self._refresh_stat_cards_theming()
        self.load_data()

    def _refresh_stat_cards_theming(self):
        try:
            from yalda.utils.theme_manager import ThemeManager
            palette = ThemeManager.get_current_palette()
        except Exception:
            return
        for card in [getattr(self, 'card_income', None), getattr(self, 'card_expense', None), getattr(self, 'card_profit', None), getattr(self, 'card_count', None)]:
            if card:
                accent = card.property("accent_color") or palette.primary
                card.setStyleSheet(f"""
                    QFrame#statCard {{
                        background-color: {palette.bg_card};
                        border: 1px solid {palette.border};
                        border-right: 4px solid {accent};
                        border-radius: 8px;
                        padding: 10px 14px;
                    }}
                """)
                lbl_t = card.findChild(QLabel, "titleLabel")
                if lbl_t:
                    lbl_t.setStyleSheet(f"color: {palette.text_muted}; font-size: 12px; font-weight: normal; background: transparent;")
                lbl_v = card.findChild(QLabel, "valLabel")
                if lbl_v:
                    lbl_v.setStyleSheet(f"color: {palette.text_primary}; font-size: 18px; font-weight: bold; background: transparent;")

    def on_quick_period_clicked(self, key: str):
        self.current_filter_key = key
        self.custom_start_date = None
        self.custom_end_date = None
        self._highlight_quick_btn(key)

        # Clear manual date inputs visual
        start_d, end_d = AccountingService.get_date_range_for_filter(key)
        if start_d:
            self.date_from.setText(start_d)
            self.date_to.setText(end_d)
        else:
            self.date_from.setText("")
            self.date_to.setText("")

        self.load_data()

    def apply_custom_date_range(self):
        d_from = self.date_from.get_date()
        d_to = self.date_to.get_date()
        if d_from and not is_valid_shamsi(d_from):
            QMessageBox.warning(self, "خطا", "تاریخ «از» نامعتبر است.")
            return
        if d_to and not is_valid_shamsi(d_to):
            QMessageBox.warning(self, "خطا", "تاریخ «تا» نامعتبر است.")
            return

        self.custom_start_date = d_from if d_from else None
        self.custom_end_date = d_to if d_to else None
        self.current_filter_key = "custom"
        self._highlight_quick_btn(None)
        self.load_data()

    def reload_trainers(self):
        current_data = self.combo_trainer_filter.currentData() if hasattr(self, 'combo_trainer_filter') and self.combo_trainer_filter.count() > 0 else -1
        self.combo_trainer_filter.blockSignals(True)
        self.combo_trainer_filter.clear()
        self.combo_trainer_filter.addItem("👥 همه مربیان (کل باشگاه)", -1)
        self.trainers = AccountingService.get_all_trainers()
        selected_idx = 0
        for idx, t in enumerate(self.trainers):
            self.combo_trainer_filter.addItem(f"👤 {t.display_name}", t.id)
            if current_data == t.id:
                selected_idx = idx + 1
        self.combo_trainer_filter.setCurrentIndex(selected_idx)
        self.combo_trainer_filter.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_trainers()
        self.load_data()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w < 1160:
            # Compact TV / small laptop mode: keep all dates (132px) and labels 100% readable while fitting 1050px width
            self.combo_trainer_filter.setFixedWidth(165)
            self.combo_type_filter.setFixedWidth(175)
            self.lbl_search.setFixedWidth(42)
            self.lbl_from.setFixedWidth(42)
            self.lbl_to.setFixedWidth(30)
            self.date_from.setMinimumWidth(132)
            self.date_to.setMinimumWidth(132)
            self.btn_apply_custom_date.setFixedWidth(74)
            compact_widths = {"today": 54, "this_week": 72, "this_month": 68, "this_year": 68, "last_30_days": 74, "all": 58}
            for k, bw in compact_widths.items():
                if k in self.quick_buttons:
                    self.quick_buttons[k].setFixedWidth(bw)
        else:
            # Standard desktop mode: full original widths
            self.combo_trainer_filter.setFixedWidth(200)
            self.combo_type_filter.setFixedWidth(210)
            self.lbl_search.setFixedWidth(54)
            self.lbl_from.setFixedWidth(54)
            self.lbl_to.setFixedWidth(54)
            self.date_from.setMinimumWidth(135)
            self.date_to.setMinimumWidth(135)
            self.btn_apply_custom_date.setFixedWidth(85)
            full_widths = {"today": 66, "this_week": 85, "this_month": 80, "this_year": 80, "last_30_days": 85, "all": 69}
            for k, bw in full_widths.items():
                if k in self.quick_buttons:
                    self.quick_buttons[k].setFixedWidth(bw)

    def on_filter_changed(self):
        self.load_data()

    def _get_active_date_range(self):
        if self.current_filter_key == "custom":
            return self.custom_start_date, self.custom_end_date
        return AccountingService.get_date_range_for_filter(self.current_filter_key)

    def load_data(self):
        start_date, end_date = self._get_active_date_range()

        # Trainer filter: -1 means all
        trainer_id = self.combo_trainer_filter.currentData()
        actual_uid = trainer_id if trainer_id and trainer_id > 0 else None

        # Type filter
        tx_type = self.combo_type_filter.currentData() or "all"
        search_q = self.txt_search.text().strip()

        # 1. Update Stat Cards Summary
        summary = AccountingService.get_financial_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=actual_uid
        )

        tot_inc = summary["total_income"]
        tot_exp = summary["total_expense"]
        profit = summary["net_profit"]
        tot_count = summary["total_transactions"]

        self._update_stat_card_value(self.card_income, f"{int(tot_inc):,} تومان", "#10B981")
        self._update_stat_card_value(self.card_expense, f"{int(tot_exp):,} تومان", "#EF4444")

        profit_prefix = "+" if profit > 0 else ""
        profit_color = "#10B981" if profit >= 0 else "#EF4444"
        self._update_stat_card_value(self.card_profit, f"{profit_prefix}{int(profit):,} تومان", profit_color)

        fa_count = str(tot_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self._update_stat_card_value(self.card_count, f"{fa_count} مورد", "#A855F7")

        # 2. Update Table
        transactions = AccountingService.get_transactions(
            start_date=start_date,
            end_date=end_date,
            user_id=actual_uid,
            transaction_type=tx_type,
            search_query=search_q
        )

        self.table.setRowCount(0)
        if not transactions:
            self.table.setVisible(False)
            self.lbl_empty.setVisible(True)
            return

        self.lbl_empty.setVisible(False)
        self.table.setVisible(True)
        self.table.setRowCount(len(transactions))

        for row, t in enumerate(transactions):
            # 0: Row Index
            fa_row = str(row + 1).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            it_idx = QTableWidgetItem(fa_row)
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, it_idx)

            # 1: Type Badge
            is_income = t["type"] == "income"
            type_text = "🟢 دریافت شهریه" if is_income else "🔴 هزینه باشگاه"
            it_type = QTableWidgetItem(type_text)
            it_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, it_type)

            # 2: Title / Party
            it_title = QTableWidgetItem(t["title"])
            it_title.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, it_title)

            # 3: Category
            it_cat = QTableWidgetItem(t["category"])
            it_cat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, it_cat)

            # 4: Date
            it_date = QTableWidgetItem(t["date_shamsi"])
            it_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, it_date)

            # 5: Amount
            amt_val = int(t["amount"])
            amt_prefix = "+" if is_income else "-"
            amt_text = f"{amt_prefix}{amt_val:,}"
            it_amt = QTableWidgetItem(amt_text)
            it_amt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_amt.setForeground(QBrush(QColor("#10B981" if is_income else "#EF4444")))
            font = it_amt.font()
            font.setBold(True)
            it_amt.setFont(font)
            self.table.setItem(row, 5, it_amt)

            # 6: Trainer
            it_trainer = QTableWidgetItem(t["trainer_name"])
            it_trainer.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, it_trainer)

            # 7: Description
            it_desc = QTableWidgetItem(t["description"])
            it_desc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, it_desc)

            # Lock all data items from in-cell editing
            for c in range(8):
                it = self.table.item(row, c)
                if it:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # 8: Operations
            btn_box = QWidget()
            btn_box.setStyleSheet("background: transparent;")
            b_layout = QHBoxLayout(btn_box)
            b_layout.setContentsMargins(6, 2, 6, 2)
            b_layout.setSpacing(6)
            b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setToolTip("ویرایش دریافت شهریه" if is_income else "ویرایش هزینه")
            btn_edit.setFixedSize(82, 30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 6px;
                    font-size: 11.5px;
                }
                QPushButton:hover { background-color: #B45309; }
            """)
            if is_income:
                btn_edit.clicked.connect(lambda _, tx=t: self.open_edit_tuition_dialog(tx))
            else:
                btn_edit.clicked.connect(lambda _, tx=t: self.open_edit_expense_dialog(tx))
            b_layout.addWidget(btn_edit)

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("حذف رکورد پرداخت شهریه" if is_income else "حذف هزینه")
            btn_del.setFixedSize(32, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #B91C1C; }
            """)
            if is_income:
                btn_del.clicked.connect(lambda _, tx=t: self.delete_tuition_payment(tx))
            else:
                btn_del.clicked.connect(lambda _, tx=t: self.delete_expense(tx))
            b_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 8, btn_box)

    def open_add_expense_dialog(self):
        dlg = ExpenseFormDialog(self)
        if dlg.exec():
            self.load_data()

    def open_edit_expense_dialog(self, expense_dict):
        dlg = ExpenseFormDialog(self, expense=expense_dict)
        if dlg.exec():
            self.load_data()

    def open_add_tuition_dialog(self):
        dlg = TuitionPaymentDialog(self)
        if dlg.exec():
            self.load_data()

    def open_edit_tuition_dialog(self, payment_dict):
        dlg = TuitionPaymentDialog(self, member_id=payment_dict.get("member_id"), payment=payment_dict)
        if dlg.exec():
            self.load_data()

    def delete_expense(self, tx):
        reply = QMessageBox.warning(
            self, "تایید حذف هزینه",
            f"آیا از حذف هزینه «{tx['title']}» به مبلغ {int(tx['amount']):,} تومان اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                AccountingService.delete_expense(tx["id"])
                self.load_data()
                QMessageBox.information(self, "موفقیت", "هزینه با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف هزینه: {str(e)}")

    def delete_tuition_payment(self, tx):
        reply = QMessageBox.warning(
            self, "تایید حذف پرداخت شهریه",
            f"آیا از حذف پرداخت «{tx['title']}» به مبلغ {int(tx['amount']):,} تومان اطمینان دارید؟\nاین مورد از تراز درآمد کسر خواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                AccountingService.delete_tuition_payment(tx["id"])
                self.load_data()
                QMessageBox.information(self, "موفقیت", "رکورد پرداخت شهریه با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف پرداخت: {str(e)}")

    def export_pdf_report(self):
        start_date, end_date = self._get_active_date_range()
        trainer_id = self.combo_trainer_filter.currentData()
        actual_uid = trainer_id if trainer_id and trainer_id > 0 else None
        tx_type = self.combo_type_filter.currentData() or "all"
        search_q = self.txt_search.text().strip()

        summary = AccountingService.get_financial_summary(start_date, end_date, actual_uid)
        transactions = AccountingService.get_transactions(start_date, end_date, actual_uid, tx_type, search_q)

        trainer_label = self.combo_trainer_filter.currentText()
        time_label = f"{start_date} الی {end_date}" if (start_date and end_date) else "کل دوره"

        now_str = get_now_shamsi_for_filename()
        default_name = f"گزارش مالی باشگاه یلدا_{now_str}.pdf"
        from yalda.utils.export_utils import resolve_gym_export_path
        filepath, gym_folder_name = resolve_gym_export_path(
            default_name, self, "ذخیره گزارش مالی PDF", "PDF Files (*.pdf)"
        )
        if filepath:
            try:
                PDFGenerator.generate_financial_pdf(
                    output_filepath=filepath,
                    summary=summary,
                    transactions=transactions,
                    filter_info={"time_label": time_label, "trainer_label": trainer_label}
                )
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل گزارش مالی PDF با موفقیت در پوشه اختصاصی «{gym_folder_name}» ذخیره شد:\n\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ایجاد گزارش PDF: {str(e)}")

    def export_excel_report(self):
        start_date, end_date = self._get_active_date_range()
        trainer_id = self.combo_trainer_filter.currentData()
        actual_uid = trainer_id if trainer_id and trainer_id > 0 else None
        tx_type = self.combo_type_filter.currentData() or "all"
        search_q = self.txt_search.text().strip()

        summary = AccountingService.get_financial_summary(start_date, end_date, actual_uid)
        transactions = AccountingService.get_transactions(start_date, end_date, actual_uid, tx_type, search_q)

        trainer_label = self.combo_trainer_filter.currentText()
        time_label = f"{start_date} الی {end_date}" if (start_date and end_date) else "کل دوره"

        now_str = get_now_shamsi_for_filename()
        default_name = f"صورت وضعیت مالی باشگاه یلدا_{now_str}.xlsx"
        from yalda.utils.export_utils import resolve_gym_export_path
        filepath, gym_folder_name = resolve_gym_export_path(
            default_name, self, "ذخیره گزارش اکسل", "فایل اکسل (*.xlsx);;Excel Workbook (*.xlsx)"
        )
        if filepath:
            try:
                ExcelGenerator.generate_financial_excel(
                    output_filepath=filepath,
                    summary=summary,
                    transactions=transactions,
                    filter_info={"time_label": time_label, "trainer_label": trainer_label}
                )
                QMessageBox.information(
                    self,
                    "موفقیت",
                    f"فایل اکسل با موفقیت در پوشه اختصاصی «{gym_folder_name}» ذخیره شد:\n\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ایجاد خروجی اکسل: {str(e)}")
