from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from nemov.utils.theme_manager import ThemeManager

class UndoDeleteBanner(QFrame):
    """
    A 5-second countdown notification banner that allows coaches to Undo accidental deletions.
    If 'بازگردانی' is clicked within the countdown, the deletion is cancelled.
    If the countdown expires or 'تأیید فوری' is clicked, the deletion is permanently committed.
    """
    undone = pyqtSignal()
    committed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.remaining_seconds = 5
        self.total_seconds = 5
        self.pending_items = []
        self.on_commit_callback = None
        self.on_undo_callback = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self.init_ui()
        self._apply_theme_style()
        try:
            ThemeManager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        self.hide()

    def _on_theme_changed(self, _theme_key: str):
        self._apply_theme_style()

    def _apply_theme_style(self):
        pal = ThemeManager.get_current_palette()
        r_bg, r_fg, r_bd, _ = ThemeManager.get_tone_colors("rose", pal)
        banner_bg = "#261616" if pal.is_dark else r_bg
        cd_col = "#FFA726" if pal.is_dark else "#B45309"
        track_bg = "#331A1A" if pal.is_dark else pal.border_light

        self.setStyleSheet(f"""
            QFrame#undo_banner {{
                background-color: {banner_bg};
                border: 1px solid #E53935;
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QLabel {{
                color: {pal.text_primary};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
            }}
            QPushButton#btn_undo {{
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#btn_undo:hover {{
                background-color: #059669;
            }}
            QPushButton#btn_dismiss {{
                background-color: {pal.btn_sec_bg};
                color: {pal.btn_sec_text};
                border: 1px solid {pal.btn_sec_border};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton#btn_dismiss:hover {{
                color: {pal.text_primary};
                border-color: {pal.border};
                background-color: {pal.btn_sec_hover};
            }}
            QProgressBar {{
                border: none;
                background-color: {track_bg};
                height: 4px;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: #E53935;
                border-radius: 2px;
            }}
        """)
        if hasattr(self, "lbl_countdown"):
            self.lbl_countdown.setStyleSheet(f"color: {cd_col}; font-weight: bold; background: transparent;")

    def init_ui(self):
        self.setObjectName("undo_banner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        self.lbl_message = QLabel("🗑️ موارد انتخاب‌شده حذف شدند.")
        self.lbl_countdown = QLabel("⏱️ فرصت بازگردانی: ۵ ثانیه")

        self.btn_undo = QPushButton("↺ بازگردانی (Undo)")
        self.btn_undo.setObjectName("btn_undo")
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self.trigger_undo)

        self.btn_dismiss = QPushButton("✕ تأیید فوری")
        self.btn_dismiss.setObjectName("btn_dismiss")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setToolTip("حذف دائمی بدون معطلی ۵ ثانیه‌ای")
        self.btn_dismiss.clicked.connect(self.commit_now)

        layout.addWidget(self.lbl_message)
        layout.addWidget(self.lbl_countdown)
        layout.addStretch()
        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_dismiss)

    def start_countdown(self, item_count: int, pending_items: list, on_commit, on_undo, item_label: str = "مورد", duration_seconds: int = 5):
        """
        Starts the 5-second undo countdown.
        """
        # If there's an existing countdown running, commit it first
        if self.timer.isActive():
            self.commit_now()

        self.total_seconds = duration_seconds
        self.remaining_seconds = duration_seconds
        self.pending_items = list(pending_items)
        self.on_commit_callback = on_commit
        self.on_undo_callback = on_undo
        self.item_label = item_label

        fa_count = str(item_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        fa_sec = str(self.remaining_seconds).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_message.setText(f"🗑️ تعداد {fa_count} {item_label} حذف شد.")
        self.lbl_countdown.setText(f"⏱️ فرصت بازگردانی: {fa_sec} ثانیه")

        self.show()
        self.timer.start()

    def _on_tick(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.commit_now()
        else:
            fa_sec = str(self.remaining_seconds).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.lbl_countdown.setText(f"⏱️ فرصت بازگردانی: {fa_sec} ثانیه")

    def trigger_undo(self):
        """Cancels deletion and restores items."""
        if self.timer.isActive():
            self.timer.stop()
        self.hide()
        items_to_restore = list(self.pending_items)
        self.pending_items = []
        if self.on_undo_callback:
            self.on_undo_callback(items_to_restore)
        self.undone.emit()

    def commit_now(self):
        """Permanently commits the deletion."""
        if self.timer.isActive():
            self.timer.stop()
        self.hide()
        items_to_delete = list(self.pending_items)
        self.pending_items = []
        if self.on_commit_callback:
            self.on_commit_callback(items_to_delete)
        self.committed.emit()
