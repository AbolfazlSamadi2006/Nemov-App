import sys
import traceback
from datetime import datetime
from functools import wraps

import html
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QApplication, QWidget, QTabWidget,
    QComboBox, QSpinBox, QLineEdit, QFrame, QTextBrowser,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from yalda.utils.logger import (
    log_error, open_logs_folder, get_log_content, clear_logs, get_logs_dir,
    get_parsed_log_entries
)


class ErrorDialog(QDialog):
    """A user-friendly, non-crashing Persian error dialog for trainers with copy & log folder actions."""
    def __init__(self, parent=None, title: str = "خطا در اجرای عملیات", message: str = "", technical_details: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(560)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.message = message or "متاسفانه در حین انجام این عملیات خطایی رخ داد. جای نگرانی نیست؛ برنامه به کار خود ادامه می‌دهد و اطلاعات شما محفوظ است."
        self.technical_details = technical_details
        self.details_visible = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        lbl_title = QLabel("خطایی در انجام عملیات رخ داد")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #EF4444;")
        title_layout.addWidget(lbl_title)

        lbl_sub = QLabel("این خطا در سیستم لاگ ثبت شد تا بتوانید آن را برای توسعه‌دهنده ارسال فرمایید.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        title_layout.addWidget(lbl_sub)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # User Message
        msg_lbl = QLabel(self.message)
        msg_lbl.setStyleSheet("color: #E5E7EB; font-size: 13px; line-height: 1.5;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        # Toggle Technical Details button
        self.btn_toggle = QPushButton("مشاهده جزئیات فنی خطا ▾")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #262626;
                color: #A3A3A3;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                text-align: right;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #F3F4F6;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_details)
        layout.addWidget(self.btn_toggle)

        # Collapsible Technical details area
        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        full_details_text = f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        full_details_text += f"مسیر لاگ‌ها: {get_logs_dir()}\n"
        full_details_text += "-" * 50 + "\n"
        full_details_text += self.technical_details or "جزئیات فنی بیشتری ثبت نشده است."
        self.txt_details.setPlainText(full_details_text)
        self.txt_details.setFixedHeight(150)
        self.txt_details.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.txt_details.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                color: #F87171;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.txt_details.setVisible(False)
        layout.addWidget(self.txt_details)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Copy Error Text Button
        self.btn_copy = QPushButton("📋 کپی متن خطا")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setFixedHeight(38)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(self.btn_copy)

        # Open Logs Folder Button
        btn_folder = QPushButton("📁 پوشه لاگ‌ها")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.setFixedHeight(38)
        btn_folder.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #F3F4F6;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        btn_folder.clicked.connect(open_logs_folder)
        btn_layout.addWidget(btn_folder)

        btn_layout.addStretch()

        # Close Button
        btn_close = QPushButton("بستن")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedHeight(38)
        btn_close.setFixedWidth(80)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1F2937;
                color: #D1D5DB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def toggle_details(self):
        self.details_visible = not self.details_visible
        self.txt_details.setVisible(self.details_visible)
        if self.details_visible:
            self.btn_toggle.setText("مخفی‌سازی جزئیات فنی ▴")
            self.adjustSize()
        else:
            self.btn_toggle.setText("مشاهده جزئیات فنی خطا ▾")
            self.adjustSize()

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        report = (
            f"=== گزارش خطای نرم‌افزار یلدا ===\n"
            f"تاریخ و زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"پیام: {self.message}\n\n"
            f"جزئیات فنی:\n{self.technical_details}\n"
            f"================================"
        )
        clipboard.setText(report)
        self.btn_copy.setText("کپی شد! ✓")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 13px;
            }
        """)
        QTimer.singleShot(2500, self.reset_copy_button)

    def reset_copy_button(self):
        self.btn_copy.setText("📋 کپی متن خطا")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)


class LogViewerDialog(QDialog):
    """An advanced log viewer dialog with color-coding, numbered entries, 3-way filtering, search, and easy copy."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📑 گزارشات و وقایع سیستم یلدا")
        self.resize(980, 660)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.entries = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Title and path
        header_box = QHBoxLayout()
        title_lbl = QLabel("📑 گزارشات، وقایع و لاگ‌های سیستم")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        header_box.addWidget(title_lbl)

        path_lbl = QLabel(f"مسیر پوشه لاگ‌ها: {get_logs_dir()}")
        path_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        header_box.addStretch()
        header_box.addWidget(path_lbl)
        layout.addLayout(header_box)

        # Filter & Search Card
        filter_card = QFrame()
        from yalda.utils.theme_manager import ThemeManager
        palette = ThemeManager.get_current_palette()
        filter_card.setStyleSheet(f"background-color: {palette.bg_surface}; border: 1px solid {palette.border_light}; border-radius: 8px; padding: 4px;")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(10, 6, 10, 6)
        filter_layout.setSpacing(10)

        lbl_filter = QLabel("🎯 فیلتر نمایش:")
        lbl_filter.setStyleSheet("color: #CCCCCC; font-weight: bold; font-size: 12px;")
        filter_layout.addWidget(lbl_filter)

        self.combo_filter = QComboBox()
        self.combo_filter.addItem("🌐 همه لاگ‌ها (All Logs)", "all")
        self.combo_filter.addItem("🟢 لاگ‌های سیستمی (System Logs)", "system")
        self.combo_filter.addItem("🔴 لاگ‌های خطا و باگ (Error Logs)", "error")
        self.combo_filter.setFixedHeight(34)
        self.combo_filter.setStyleSheet("min-width: 175px; font-size: 12px; font-weight: bold;")
        self.combo_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.combo_filter)

        lbl_order = QLabel("🔃 ترتیب:")
        lbl_order.setStyleSheet("color: #CCCCCC; font-weight: bold; font-size: 12px;")
        filter_layout.addWidget(lbl_order)

        self.combo_order = QComboBox()
        self.combo_order.addItem("نزولی (جدیدترین اول)", "desc")
        self.combo_order.addItem("صعودی (قدیمی‌ترین اول)", "asc")
        self.combo_order.setFixedHeight(34)
        self.combo_order.setStyleSheet("min-width: 165px; font-size: 12px; font-weight: bold; padding: 0 10px;")
        self.combo_order.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.combo_order)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 جستجو در متن یا شماره لاگ‌ها...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.setMinimumWidth(160)
        self.txt_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.txt_search.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.txt_search, 1)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold;")
        filter_layout.addWidget(self.lbl_stats)

        layout.addWidget(filter_card)

        # Main Log Display Area
        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setOpenLinks(False)
        self.browser.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #101216;
                color: #FFFFFF;
                border: 1px solid #282C34;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Vazirmatn', 'Segoe UI', Tahoma, sans-serif;
            }
        """)
        self.browser.anchorClicked.connect(self.handle_link_clicked)
        layout.addWidget(self.browser, 1)

        # Status toast label
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px; min-height: 18px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # Bottom Bar: Quick Copy tools & Action buttons
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        lbl_copy_num = QLabel("کپی لاگ مشخص:")
        lbl_copy_num.setStyleSheet("color: #D1D5DB; font-size: 12px; font-weight: bold;")
        bottom_bar.addWidget(lbl_copy_num)

        self.spin_copy = QSpinBox()
        self.spin_copy.setMinimum(1)
        self.spin_copy.setMaximum(9999)
        self.spin_copy.setFixedHeight(34)
        self.spin_copy.setFixedWidth(75)
        self.spin_copy.setStyleSheet("font-size: 12px; font-weight: bold;")
        bottom_bar.addWidget(self.spin_copy)

        self.btn_copy_single = QPushButton("📋 کپی لاگ این شماره")
        self.btn_copy_single.setFixedHeight(34)
        self.btn_copy_single.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_single.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 0 12px; font-size: 12px;")
        self.btn_copy_single.clicked.connect(self.copy_single_log)
        bottom_bar.addWidget(self.btn_copy_single)

        self.btn_copy_filtered = QPushButton("📋 کپی تمام لاگ‌های نمایشی")
        self.btn_copy_filtered.setFixedHeight(34)
        self.btn_copy_filtered.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_filtered.setStyleSheet("background-color: #374151; color: #F3F4F6; border-radius: 6px; padding: 0 12px; font-size: 12px;")
        self.btn_copy_filtered.clicked.connect(self.copy_filtered_logs)
        bottom_bar.addWidget(self.btn_copy_filtered)

        bottom_bar.addStretch()

        btn_refresh = QPushButton("🔄 بروزرسانی")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("background-color: #1F2937; color: #D1D5DB; border: 1px solid #4B5563; border-radius: 6px; padding: 0 12px; font-size: 12px;")
        btn_refresh.clicked.connect(self.load_logs)
        bottom_bar.addWidget(btn_refresh)

        btn_open_folder = QPushButton("📁 پوشه لاگ‌ها")
        btn_open_folder.setFixedHeight(34)
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet("background-color: #1F2937; color: #D1D5DB; border: 1px solid #4B5563; border-radius: 6px; padding: 0 12px; font-size: 12px;")
        btn_open_folder.clicked.connect(open_logs_folder)
        bottom_bar.addWidget(btn_open_folder)

        btn_clear = QPushButton("🗑️ پاک‌سازی")
        btn_clear.setFixedHeight(34)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("background-color: #7F1D1D; color: #FCA5A5; border-radius: 6px; padding: 0 12px; font-size: 12px;")
        btn_clear.clicked.connect(self.handle_clear_logs)
        bottom_bar.addWidget(btn_clear)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(34)
        btn_close.setFixedWidth(75)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #1F2937; color: #D1D5DB; border: 1px solid #4B5563; border-radius: 6px; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

        self.load_logs()

    def load_logs(self):
        self.entries = get_parsed_log_entries(max_lines=600)
        if self.entries:
            self.spin_copy.setMaximum(len(self.entries))
            self.spin_copy.setValue(len(self.entries))
        self.apply_filter()

    def apply_filter(self):
        filter_type = self.combo_filter.currentData()
        search_query = self.txt_search.text().strip().lower()

        filtered = []
        for e in self.entries:
            is_error = e["level"] in ("ERROR", "CRITICAL")
            if filter_type == "error" and not is_error:
                continue
            if filter_type == "system" and is_error:
                continue

            if search_query:
                combined = f"{e['num']}: {e['message']} {' '.join(e['body'])} {e['timestamp']} {e['level']}".lower()
                if search_query not in combined:
                    continue

            filtered.append(e)

        # Apply sort order: default "desc" (newest first) vs "asc" (oldest first)
        sort_order = self.combo_order.currentData() if hasattr(self, "combo_order") and self.combo_order else "desc"
        if sort_order == "desc":
            filtered.reverse()

        # Update stats
        total_err = sum(1 for e in self.entries if e["level"] in ("ERROR", "CRITICAL"))
        total_sys = len(self.entries) - total_err
        self.lbl_stats.setText(f"نمایش: {len(filtered)} از {len(self.entries)} لاگ ({total_err} خطا، {total_sys} سیستمی)")

        # Render HTML
        html_parts = []
        html_parts.append("<div style='font-family: Vazirmatn, Segoe UI, Tahoma, sans-serif;'>")

        if not filtered:
            html_parts.append("<div style='text-align: center; color: #9CA3AF; padding: 40px; font-size: 14px;'>هیچ لاگی با فیلتر یا جستجوی انتخابی یافت نشد.</div>")
        else:
            for e in filtered:
                is_err = e["level"] in ("ERROR", "CRITICAL")
                num = e["num"]
                ts = e["timestamp"]
                msg = html.escape(e["message"])

                if is_err:
                    bg_color = "#1F0F12"
                    border_color = "#DC2626"
                    header_bg = "#2D1418"
                    badge_color = "#EF4444"
                    badge_text = "🔴 لاگ خطا و باگ سیستم"
                    text_color = "#FCA5A5"
                    body_bg = "#15080A"
                else:
                    bg_color = "#0A1F17"
                    border_color = "#059669"
                    header_bg = "#0F2E22"
                    badge_color = "#10B981"
                    badge_text = "🟢 لاگ سیستمی و موفقیت‌آمیز"
                    text_color = "#6EE7B7"
                    body_bg = "#071711"

                card = f"""
                <table width='100%' border='0' cellpadding='8' cellspacing='0' style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; margin-bottom: 12px;'>
                    <tr style='background-color: {header_bg};'>
                        <td align='left' width='35%' style='color: #9CA3AF; font-size: 11px;'>
                            <a href='copy:{num}' style='color: #60A5FA; text-decoration: none; font-weight: bold; margin-left: 10px;'>📋 کپی این لاگ</a>
                            <span style='font-family: Consolas, monospace;'>📅 {ts}</span>
                        </td>
                        <td align='right' width='65%' style='color: {badge_color}; font-size: 13px; font-weight: bold;' dir='rtl'>
                            <span style='background-color: {border_color}; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; margin-left: 8px;'>{num}:</span>
                            {badge_text}
                        </td>
                    </tr>
                    <tr>
                        <td colspan='2' align='right' style='color: {text_color}; font-size: 12px; padding: 10px 12px; font-family: Vazirmatn, Segoe UI, Tahoma, sans-serif; font-weight: 500; line-height: 1.5;' dir='rtl'>
                            {msg}
                        </td>
                    </tr>
                """

                if e["body"]:
                    body_text = html.escape("\n".join(e["body"]))
                    card += f"""
                    <tr>
                        <td colspan='2' style='padding: 0 12px 12px 12px;'>
                            <div style='background-color: {body_bg}; border: 1px dashed {border_color}; border-radius: 6px; color: #FECACA; font-family: Consolas, monospace; font-size: 11px; padding: 8px; direction: ltr; text-align: left; white-space: pre-wrap;'>{body_text}</div>
                        </td>
                    </tr>
                    """

                card += "</table>"
                html_parts.append(card)

        html_parts.append("</div>")
        self.browser.setHtml("".join(html_parts))

    def handle_link_clicked(self, url: QUrl):
        s = url.toString()
        if s.startswith("copy:"):
            try:
                num = int(s.split(":", 1)[1])
                self.copy_by_number(num)
            except Exception:
                pass

    def copy_single_log(self):
        target_num = self.spin_copy.value()
        self.copy_by_number(target_num)

    def copy_by_number(self, num: int):
        found = next((e for e in self.entries if e["num"] == num), None)
        if not found:
            self.show_toast(f"❌ لاگ {num}: یافت نشد.", error=True)
            return
        text = self._format_entry_plain(found)
        QApplication.clipboard().setText(text)
        self.show_toast(f"✅ متن کامل لاگ {num}: با موفقیت در کلیپ‌بورد کپی شد.")

    def copy_filtered_logs(self):
        filter_type = self.combo_filter.currentData()
        search_query = self.txt_search.text().strip().lower()
        parts = []
        for e in self.entries:
            is_error = e["level"] in ("ERROR", "CRITICAL")
            if filter_type == "error" and not is_error:
                continue
            if filter_type == "system" and is_error:
                continue
            if search_query:
                combined = f"{e['num']}: {e['message']} {' '.join(e['body'])} {e['timestamp']} {e['level']}".lower()
                if search_query not in combined:
                    continue
            parts.append(self._format_entry_plain(e))

        sort_order = self.combo_order.currentData() if hasattr(self, "combo_order") and self.combo_order else "desc"
        if sort_order == "desc":
            parts.reverse()

        if not parts:
            self.show_toast("موردی برای کپی وجود ندارد.", error=True)
            return

        delimiter = "\n\n" + ("=" * 55) + "\n\n"
        full_text = delimiter.join(parts)
        QApplication.clipboard().setText(full_text)
        self.show_toast(f"✅ تعداد {len(parts)} لاگ فیلتر شده با موفقیت کپی شد.")

    def show_toast(self, msg: str, error: bool = False):
        color = "#EF4444" if error else "#10B981"
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px; min-height: 18px;")
        self.lbl_status.setText(msg)
        QTimer.singleShot(3000, lambda: self.lbl_status.setText(""))

    def _format_entry_plain(self, e: dict) -> str:
        border = "=" * 55
        badge = "🔴 [خطا و باگ سیستم]" if e["level"] in ("ERROR", "CRITICAL") else "🟢 [لاگ سیستمی]"
        res = [
            border,
            f"{e['num']}: | {badge} | زمان: {e['timestamp']}",
            "-" * 55,
            e["message"]
        ]
        if e["body"]:
            res.append("\n--- جزئیات و Traceback خطا ---")
            res.extend(e["body"])
        res.append(border)
        return "\n".join(res)

    def handle_clear_logs(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "تایید پاک‌سازی",
            "آیا مطمئن هستید که می‌خواهید فایل‌های لاگ فعلی را پاک‌سازی کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_logs()
            self.load_logs()


def show_error_dialog(parent=None, message: str = "", technical_details: str = "", title: str = "خطای برنامه"):
    """Safely displays the ErrorDialog on the UI."""
    try:
        resolved_parent = parent
        if resolved_parent is not None and hasattr(resolved_parent, "window") and resolved_parent.window():
            resolved_parent = resolved_parent.window()
        dlg = ErrorDialog(
            parent=resolved_parent,
            title=title,
            message=message,
            technical_details=technical_details
        )
        dlg.exec()
    except Exception as e:
        print(f"[ErrorDialog] Fallback display failure: {e}\n{technical_details}", file=sys.stderr)


def safe_action(action_name: str = "عملیات"):
    """Decorator to wrap UI slots/methods in safe error handling and logging."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb_str = traceback.format_exc()
                log_error(f"Error in {action_name} ({func.__name__}): {e}\n{tb_str}")
                parent = None
                if args and isinstance(args[0], QWidget):
                    parent = args[0]
                user_msg = f"متاسفانه در حین «{action_name}» خطایی رخ داد.\n{str(e)}"
                show_error_dialog(
                    parent=parent,
                    message=user_msg,
                    technical_details=tb_str,
                    title=f"خطا در {action_name}"
                )
                return None
        return wrapper
    return decorator
