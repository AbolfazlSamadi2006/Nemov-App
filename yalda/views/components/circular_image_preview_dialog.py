import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QColor
from yalda.utils.image_utils import get_circular_pixmap

class CircularImagePreviewDialog(QDialog):
    """A beautiful frameless translucent popup dialog displaying a zoomed circular profile picture."""
    
    def __init__(self, photo_path: str, title: str = "", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.photo_path = photo_path
        self.title_text = title
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)

        # Circular Image Label
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_image.setToolTip("برای بستن کلیک کنید")
        self.lbl_image.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        SIZE = 340
        if self.photo_path and os.path.exists(self.photo_path):
            pix = QPixmap(self.photo_path)
            if not pix.isNull():
                try:
                    from yalda.utils.theme_manager import ThemeManager
                    accent = ThemeManager.get_current_palette().primary
                except Exception:
                    accent = "#3B82F6"
                circ = get_circular_pixmap(pix, SIZE, border_color=accent, border_width=4)
                self.lbl_image.setPixmap(circ)

        # Glowing dark shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(45)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 8)
        self.lbl_image.setGraphicsEffect(shadow)

        layout.addWidget(self.lbl_image)

        if self.title_text:
            lbl_title = QLabel(self.title_text)
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl_title.setStyleSheet("""
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
                background-color: rgba(20, 20, 20, 220);
                border: 1px solid #555555;
                border-radius: 12px;
                padding: 6px 18px;
                margin-top: 10px;
            """)
            layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        event.accept()
        self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Space):
            event.accept()
            self.accept()
        else:
            super().keyPressEvent(event)
