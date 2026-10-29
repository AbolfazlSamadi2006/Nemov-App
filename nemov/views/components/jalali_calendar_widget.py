from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QDialog, QVBoxLayout,
    QGridLayout, QLabel, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
import jdatetime
from nemov.utils.jalali_date import get_today_shamsi, format_shamsi
from nemov.utils.theme_manager import ThemeManager

class JalaliCalendarDialog(QDialog):
    date_selected = pyqtSignal(str)

    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)
        palette = ThemeManager.get_current_palette()
        self.setWindowTitle("انتخاب تاریخ شمسی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(360, 380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {palette.bg_card};
            }}
            QLabel {{
                color: {palette.text_primary};
                font-size: 13px;
            }}
            QComboBox {{
                background-color: {palette.bg_input};
                color: {palette.text_primary};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 90px;
            }}
            QPushButton#cal_day_btn {{
                background-color: {palette.bg_surface};
                color: {palette.text_primary};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 0px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#cal_day_btn:hover {{
                background-color: {palette.primary};
                border: 1px solid {palette.primary};
                color: {palette.text_primary};
            }}
            QPushButton#cal_day_btn[today="true"] {{
                border: 2px solid {palette.primary};
                background-color: {palette.bg_card};
            }}
        """)

        if initial_date:
            try:
                parts = format_shamsi(initial_date).split("/")
                self.current_year = int(parts[0])
                self.current_month = int(parts[1])
            except Exception:
                today = jdatetime.date.today()
                self.current_year, self.current_month = today.year, today.month
        else:
            today = jdatetime.date.today()
            self.current_year, self.current_month = today.year, today.month

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Year / Month Controls
        controls = QHBoxLayout()
        controls.setSpacing(8)

        lbl_month = QLabel("ماه:")
        self.month_combo = QComboBox()
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        for idx, m_name in enumerate(month_names, start=1):
            self.month_combo.addItem(m_name, idx)
        self.month_combo.setCurrentIndex(self.current_month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)

        lbl_year = QLabel("سال:")
        self.year_combo = QComboBox()
        for y in range(1300, 1451):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentText(str(self.current_year))
        self.year_combo.currentTextChanged.connect(self.on_year_changed)


        controls.addWidget(lbl_month)
        controls.addWidget(self.month_combo)
        controls.addSpacing(10)
        controls.addWidget(lbl_year)
        controls.addWidget(self.year_combo)
        controls.addStretch()

        layout.addLayout(controls)

        # Days Grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        layout.addLayout(self.grid_layout)

        self.render_days()

    def on_month_changed(self, idx):
        self.current_month = idx + 1
        self.render_days()

    def on_year_changed(self, text):
        if text.isdigit():
            self.current_year = int(text)
            self.render_days()

    def render_days(self):
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        palette = ThemeManager.get_current_palette()
        headers = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(28)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {palette.primary};
                    color: {palette.text_primary};
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 6px;
                    margin-bottom: 4px;
                }}
            """)
            self.grid_layout.addWidget(lbl, 0, col)

        # Calculate days in month
        try:
            first_day_of_month = jdatetime.date(self.current_year, self.current_month, 1)
            # weekday: 0 is Saturday in jdatetime
            start_weekday = first_day_of_month.weekday()

            if self.current_month <= 6:
                days_in_month = 31
            elif self.current_month <= 11:
                days_in_month = 30
            else:
                days_in_month = 29 if not first_day_of_month.isleap() else 30

            today = jdatetime.date.today()

            row = 1
            col = start_weekday
            for day in range(1, days_in_month + 1):
                btn = QPushButton(str(day))
                btn.setObjectName("cal_day_btn")
                btn.setFixedSize(40, 35)

                if self.current_year == today.year and self.current_month == today.month and day == today.day:
                    btn.setProperty("today", "true")

                btn.clicked.connect(lambda _, d=day: self.select_day(d))
                self.grid_layout.addWidget(btn, row, col)

                col += 1
                if col > 6:
                    col = 0
                    row += 1
        except Exception:
            pass

    def select_day(self, day):
        selected_str = f"{self.current_year:04d}/{self.current_month:02d}/{day:02d}"
        self.date_selected.emit(selected_str)
        self.accept()

class JalaliDatePicker(QWidget):
    """Custom composite widget with LineEdit and Calendar Popup for Shamsi Date"""
    date_changed = pyqtSignal(str)

    def __init__(self, parent=None, default_today=True):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("YYYY/MM/DD")
        if default_today:
            self.line_edit.setText(get_today_shamsi())

        self.line_edit.textChanged.connect(self.date_changed.emit)

        self.btn_calendar = QPushButton("📅")
        self.btn_calendar.setFixedWidth(42)
        self.btn_calendar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calendar.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                border: 1px solid #B91C1C;
                border-radius: 6px;
                font-size: 16px;
                font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        self.btn_calendar.clicked.connect(self.open_calendar)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.btn_calendar)
        self.setFixedHeight(38)


    def setFixedHeight(self, h: int):
        super().setFixedHeight(h)
        self.line_edit.setFixedHeight(h)
        self.btn_calendar.setFixedHeight(h)

    def setFixedWidth(self, w: int):
        super().setFixedWidth(w)
        self.line_edit.setFixedWidth(max(40, w - 48))

    def open_calendar(self):
        dialog = JalaliCalendarDialog(self, initial_date=self.line_edit.text())
        dialog.date_selected.connect(self.set_date)
        dialog.exec()

    def set_date(self, date_str):
        self.line_edit.setText(date_str or "")

    def get_date(self) -> str:
        return self.line_edit.text().strip()

    def text(self) -> str:
        return self.line_edit.text().strip()

    def setText(self, date_str):
        self.line_edit.setText(date_str or "")

