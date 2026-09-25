from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

class UndoDeleteBanner(QFrame):
    """
    A 10-second countdown notification banner that allows coaches to Undo accidental deletions.
    If 'بازگردانی' is clicked within the countdown, the deletion is cancelled.
    If the countdown expires or 'تأیید فوری' is clicked, the deletion is permanently committed.
    """
    undone = pyqtSignal()
    committed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.remaining_seconds = 10
        self.total_seconds = 10
        self.pending_items = []
        self.on_commit_callback = None
        self.on_undo_callback = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self.init_ui()
        self.hide()

    def init_ui(self):
        self.setObjectName("undo_banner")
        self.setStyleSheet("""
            QFrame#undo_banner {
                background-color: #261616;
                border: 1px solid #E53935;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#btn_undo {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#btn_undo:hover {
                background-color: #059669;
            }
            QPushButton#btn_dismiss {
                background-color: transparent;
                color: #AAAAAA;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton#btn_dismiss:hover {
                color: #FFFFFF;
                border-color: #888888;
                background-color: #333333;
            }
            QProgressBar {
                border: none;
                background-color: #331A1A;
                height: 4px;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #E53935;
                border-radius: 2px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        self.lbl_message = QLabel("🗑️ موارد انتخاب‌شده حذف شدند.")
        self.lbl_countdown = QLabel("⏱️ فرصت بازگردانی: ۱۰ ثانیه")
        self.lbl_countdown.setStyleSheet("color: #FFA726; font-weight: bold;")

        self.btn_undo = QPushButton("↺ بازگردانی (Undo)")
        self.btn_undo.setObjectName("btn_undo")
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self.trigger_undo)

        self.btn_dismiss = QPushButton("✕ تأیید فوری")
        self.btn_dismiss.setObjectName("btn_dismiss")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setToolTip("حذف دائمی بدون معطلی ۱۰ ثانیه‌ای")
        self.btn_dismiss.clicked.connect(self.commit_now)

        layout.addWidget(self.lbl_message)
        layout.addWidget(self.lbl_countdown)
        layout.addStretch()
        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_dismiss)

    def start_countdown(self, item_count: int, pending_items: list, on_commit, on_undo, item_label: str = "مورد", duration_seconds: int = 10):
        """
        Starts the 10-second undo countdown.
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
