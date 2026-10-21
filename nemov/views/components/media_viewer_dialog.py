import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

class MediaViewerDialog(QDialog):
    """
    Dialog for displaying exercise media (images, local videos, and online video URLs).
    """
    def __init__(self, title: str, media_path: str = None, media_type: str = "image", video_url: str = None, parent=None):
        super().__init__(parent)
        self.title_str = title
        self.media_path = media_path
        self.media_type = media_type or "image"
        self.video_url = video_url

        self.setWindowTitle(f"رسانه و ویدیو آموزشی: {title}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumSize(560, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_header = QLabel(f"🎬 رسانه و راهنمای اجرای حرکت: {self.title_str}")
        lbl_header.setObjectName("h2")
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_header)

        # 1. Local Media Section
        has_local_media = self.media_path and os.path.exists(self.media_path)
        if has_local_media:
            ext = os.path.splitext(self.media_path)[1].lower()
            is_video = ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.webm'] or self.media_type == 'video'

            if not is_video:
                # Image Display
                lbl_image = QLabel()
                lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pixmap = QPixmap(self.media_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(500, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    lbl_image.setPixmap(scaled_pixmap)
                    layout.addWidget(lbl_image)
            else:
                # Local Video Player Option
                lbl_video_info = QLabel("🎥 فایل ویدیوی آفلاین:")
                lbl_video_info.setStyleSheet("font-size: 13px; color: #FFFFFF;")
                layout.addWidget(lbl_video_info)

                btn_play = QPushButton("▶️ پخش فایل ویدیویی محلی")
                btn_play.setObjectName("primary_button")
                btn_play.setFixedHeight(40)
                btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_play.clicked.connect(self.play_video)
                layout.addWidget(btn_play)

        # 2. Online Video URL Section
        if self.video_url and self.video_url.strip():
            url_box = QVBoxLayout()
            lbl_url_title = QLabel("🌐 لینک آموزش آنلاین (ویدیو / تصویر):")
            lbl_url_title.setStyleSheet("font-weight: bold; color: #60A5FA; font-size: 13px;")
            
            lbl_url_text = QLabel(f"🔗 {self.video_url.strip()}")
            lbl_url_text.setStyleSheet("color: #E2E8F0; font-size: 12px; background: #1E293B; padding: 8px; border-radius: 6px;")
            lbl_url_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl_url_text.setWordWrap(True)

            btn_open_url = QPushButton("🌐 مشاهده رسانه آموزشی در مرورگر")
            btn_open_url.setFixedHeight(40)
            btn_open_url.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #1D4ED8;
                }
            """)
            btn_open_url.clicked.connect(self.open_video_url)

            url_box.addWidget(lbl_url_title)
            url_box.addWidget(lbl_url_text)
            url_box.addWidget(btn_open_url)
            layout.addLayout(url_box)

        if not has_local_media and (not self.video_url or not self.video_url.strip()):
            lbl_no_file = QLabel("❌ هیچ فایل یا لینک اینترنتی برای آموزش این حرکت ثبت نشده است.")
            lbl_no_file.setStyleSheet("color: #888888; font-size: 14px; padding: 25px;")
            lbl_no_file.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_no_file)

        btn_close = QPushButton("بستن")
        btn_close.setObjectName("secondary_button")
        btn_close.setFixedHeight(38)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def play_video(self):
        if self.media_path and os.path.exists(self.media_path):
            url = QUrl.fromLocalFile(self.media_path)
            QDesktopServices.openUrl(url)
        else:
            QMessageBox.warning(self, "خطا", "فایل ویدیو یافت نشد.")

    def open_video_url(self):
        if self.video_url and self.video_url.strip():
            url_str = self.video_url.strip()
            if not (url_str.startswith("http://") or url_str.startswith("https://")):
                url_str = "https://" + url_str
            if "workers.dev" in url_str and "title=" not in url_str and self.title_str:
                from urllib.parse import quote
                sep = "&" if "?" in url_str else "?"
                url_str = f"{url_str}{sep}title={quote(self.title_str)}"
            QDesktopServices.openUrl(QUrl(url_str))
        else:
            QMessageBox.warning(self, "خطا", "لینک ویدیو موجود نیست.")
