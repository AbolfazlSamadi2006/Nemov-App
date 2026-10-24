"""
nemov/views/components/cloud_backup_choice_dialog.py
Interactive confirmation dialog when unsynced workout videos are detected during cloud backup.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from nemov.utils.theme_manager import ThemeManager


class CloudBackupChoiceDialog(QDialog):
    CHOICE_SYNC_AND_BACKUP = "sync_and_backup"
    CHOICE_DATA_ONLY = "data_only"
    CHOICE_CANCEL = "cancel"

    def __init__(self, pending_count: int, parent=None):
        super().__init__(parent)
        self.pending_count = pending_count
        self.selected_choice = self.CHOICE_CANCEL

        self.setWindowTitle("☁️ پشتیبان‌گیری در سرور")
        self.setFixedWidth(480)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.init_ui()

    def init_ui(self):
        palette = ThemeManager.get_current_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header Title
        lbl_title = QLabel("☁️ پشتیبان‌گیری در سرور")
        lbl_title.setObjectName("h1")
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {palette.primary}; font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;")
        layout.addWidget(lbl_title)

        # Message Text
        fa_count = str(self.pending_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        msg_text = (
            f"تعداد {fa_count} ویدیوی تمرینی جدید شناسایی شد که هنوز در سرور ذخیره نشده‌اند.\n"
            f"مایل هستید چگونه پشتیبان‌گیری انجام شود؟"
        )
        lbl_msg = QLabel(msg_text)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"font-size: 12px; color: {palette.text_primary}; line-height: 1.5; font-family: 'Vazirmatn', sans-serif;")
        layout.addWidget(lbl_msg)

        layout.addSpacing(4)

        # Option 1: Sync videos and full backup
        btn_sync = QPushButton("🌐 همگام‌سازی ویدیوها و پشتیبان‌گیری کامل")
        btn_sync.setFixedHeight(40)
        btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {palette.primary};
                color: #FFFFFF;
                border: 1px solid {palette.primary};
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;
                padding: 0 14px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {palette.primary_hover};
            }}
        """)
        btn_sync.clicked.connect(lambda: self._select_choice(self.CHOICE_SYNC_AND_BACKUP))
        layout.addWidget(btn_sync)

        # Option 2: Data only backup
        btn_data = QPushButton("⚡ فقط پشتیبان‌گیری از داده‌ها")
        btn_data.setFixedHeight(38)
        btn_data.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_data.setStyleSheet(f"""
            QPushButton {{
                background-color: {palette.btn_sec_bg};
                color: {palette.btn_sec_text};
                border: 1px solid {palette.btn_sec_border};
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;
                padding: 0 14px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {palette.btn_sec_hover};
                border: 1px solid {palette.primary};
            }}
        """)
        btn_data.clicked.connect(lambda: self._select_choice(self.CHOICE_DATA_ONLY))
        layout.addWidget(btn_data)

        # Option 3: Cancel
        btn_cancel = QPushButton("❌ انصراف")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border};
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Vazirmatn', sans-serif;
                padding: 0 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: #27272A;
                color: #EF4444;
                border-color: #EF4444;
            }}
        """)
        btn_cancel.clicked.connect(lambda: self._select_choice(self.CHOICE_CANCEL))
        layout.addWidget(btn_cancel)

    def _select_choice(self, choice: str):
        self.selected_choice = choice
        if choice == self.CHOICE_CANCEL:
            self.reject()
        else:
            self.accept()
