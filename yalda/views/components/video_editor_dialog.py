import os
import sys
import tempfile
import time
import uuid
import numpy as np
import cv2
import re
from pathlib import Path
from PIL import Image, ImageEnhance
from yalda.views.components.image_editor_dialog import CropCanvas, pil_to_pixmap

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QCheckBox, QSlider, QDoubleSpinBox, QSpinBox, QGroupBox,
    QTabWidget, QWidget, QProgressDialog, QFileDialog, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt, QRectF, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush

import config
from yalda.utils.image_utils import extract_video_thumbnail


class VideoPlayerWidget(QLabel):
    """
    Subclass of QLabel that renders the current video frame with an optional
    crop overlay rectangle.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(420, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #0d0d0d; border: 2px solid #2a2a2a; border-radius: 8px;")

        self.current_qimage = None
        self.crop_margins = (0, 0, 0, 0)  # top, bottom, left, right (pixels in source frame)
        self.source_dims = (0, 0)  # width, height
        self.show_cropped_only = False

    def set_frame(self, qimage: QImage, source_w: int, source_h: int, margins: tuple, show_cropped_only: bool):
        self.current_qimage = qimage
        self.source_dims = (source_w, source_h)
        self.crop_margins = margins
        self.show_cropped_only = show_cropped_only
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#0d0d0d"))

        if not self.current_qimage or self.current_qimage.isNull():
            painter.setPen(QColor("#666666"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "پیش‌نمایش ویدیو آماده نیست")
            return

        w_w = self.width()
        w_h = self.height()
        img_w = self.current_qimage.width()
        img_h = self.current_qimage.height()

        scale = min(w_w / img_w, w_h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        disp_x = (w_w - disp_w) / 2.0
        disp_y = (w_h - disp_h) / 2.0

        disp_rect = QRectF(disp_x, disp_y, disp_w, disp_h)
        painter.drawImage(disp_rect, self.current_qimage)

        # If not showing cropped only, draw overlay box
        if not self.show_cropped_only and self.source_dims[0] > 0 and self.source_dims[1] > 0:
            top_m, bot_m, left_m, right_m = self.crop_margins
            src_w, src_h = self.source_dims

            if top_m > 0 or bot_m > 0 or left_m > 0 or right_m > 0:
                crop_x_norm = left_m / src_w
                crop_y_norm = top_m / src_h
                crop_w_norm = max(0.01, (src_w - left_m - right_m) / src_w)
                crop_h_norm = max(0.01, (src_h - top_m - bot_m) / src_h)

                crop_rect = QRectF(
                    disp_rect.left() + crop_x_norm * disp_rect.width(),
                    disp_rect.top() + crop_y_norm * disp_rect.height(),
                    crop_w_norm * disp_rect.width(),
                    crop_h_norm * disp_rect.height()
                )

                # Dim outside
                dim_color = QColor(0, 0, 0, 150)
                painter.fillRect(QRectF(disp_rect.left(), disp_rect.top(), disp_rect.width(), crop_rect.top() - disp_rect.top()), dim_color)
                painter.fillRect(QRectF(disp_rect.left(), crop_rect.bottom(), disp_rect.width(), disp_rect.bottom() - crop_rect.bottom()), dim_color)
                painter.fillRect(QRectF(disp_rect.left(), crop_rect.top(), crop_rect.left() - disp_rect.left(), crop_rect.height()), dim_color)
                painter.fillRect(QRectF(crop_rect.right(), crop_rect.top(), disp_rect.right() - crop_rect.right(), crop_rect.height()), dim_color)

                # Bright crop border
                border_pen = QPen(QColor("#00E5FF"), 2)
                painter.setPen(border_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(crop_rect)


class VideoRecorderAndEditorDialog(QDialog):
    """
    Unified dialog for:
    1. Live video recording from webcam/connected camera with timer and 30 FPS encoding.
    2. Video editing suite:
       - Time trimming (start/end seconds)
       - Intermediate segment removal ('حذف بازه‌ی انتخاب شده')
       - Pixel cropping (top, bottom, left, right)
       - 90-degree rotation and horizontal flip
       - Real-time scrubbable preview player
       - Retake button (back to camera)
       - High-quality MP4 export and automatic thumbnail generation
    """
    def __init__(self, parent=None, video_path: str = None, image_path: str = None, mode: str = "record", exercise_title: str = None):
        super().__init__(parent)
        self.setWindowTitle("استودیوی رسانه آموزشی حرکت (ضبط و عکس‌برداری با دوربین / ویرایش)")
        # Adapt dialog size intelligently to available screen work area so it never overflows taskbar
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1180, max(850, int(avail.width() * 0.92)))
            target_h = min(780, max(640, int(avail.height() * 0.90)))
        else:
            target_w, target_h = 1080, 720

        self.resize(target_w, target_h)
        self.setMinimumSize(850, 600)

        if screen:
            self.move(avail.x() + (avail.width() - target_w) // 2, avail.y() + (avail.height() - target_h) // 2)

        self.initial_mode = mode  # 'record', 'photo', 'edit_image', 'edit'
        self.current_video_path = video_path
        self.current_image_path = image_path
        self.exercise_title = exercise_title
        self.result_video_path = None
        self.result_thumbnail_path = None
        self.result_image_path = None
        self.result_media_type = None  # 'video' or 'image'

        # Camera state
        self.cam_cap = None
        self.cam_timer = QTimer(self)
        self.cam_timer.setInterval(33)
        self.cam_timer.timeout.connect(self._on_cam_frame)
        self.is_recording = False
        self.record_writer = None
        self.record_temp_path = None
        self.record_start_time = 0
        self.record_frame_count = 0
        self.latest_cam_frame = None

        # Photo capture state
        self.photo_timer = QTimer(self)
        self.photo_timer.timeout.connect(self._on_photo_countdown_tick)
        self.photo_countdown_remaining = 0

        # Photo Editor state
        self.photo_orig_pil: Image.Image = None
        self.photo_transformed_pil: Image.Image = None
        self.photo_display_pil: Image.Image = None

        # Video Editor state
        self.edit_cap = None
        self.edit_timer = QTimer(self)
        self.edit_timer.timeout.connect(self._on_playback_tick)
        self.is_playing = False
        self.total_frames = 0
        self.video_fps = 30.0
        self.video_duration = 0.0
        self.src_w = 0
        self.src_h = 0
        self.current_frame_idx = 0
        self.rotation_angle = 0  # 0, 90, 180, 270
        self.is_flipped_h = False
        self.selected_poster_frame_idx = 0

        self.init_ui()

        if self.initial_mode == "record":
            self.tabs.setCurrentIndex(0)
            self.detect_and_start_camera()
        elif self.initial_mode == "photo":
            self.tabs.setCurrentIndex(1)
            self.detect_and_start_camera()
        elif self.initial_mode in ("edit_image", "image"):
            self.tabs.setCurrentIndex(2)
            if self.current_image_path and os.path.exists(self.current_image_path):
                self.load_image_for_editing(self.current_image_path)
        else:
            self.tabs.setCurrentIndex(3)
            if self.current_video_path and os.path.exists(self.current_video_path):
                self.load_video_for_editing(self.current_video_path)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #333333; background: #161616; border-radius: 6px; } "
            "QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 20px; color: #aaaaaa; } "
            "QTabBar::tab:selected { color: #ffffff; background: #242424; border-bottom: 2px solid #00E5FF; }"
        )

        # Tab 0: Camera Video Recording
        tab_cam = QWidget()
        self._build_camera_tab(tab_cam)
        self.tabs.addTab(tab_cam, "🎥 ضبط زنده با دوربین")

        # Tab 1: Camera Photo Capture
        tab_photo = QWidget()
        self._build_photo_capture_tab(tab_photo)
        self.tabs.addTab(tab_photo, "📷 عکس‌برداری با دوربین")

        # Tab 2: Photo Editor
        tab_photo_edit = QWidget()
        self._build_photo_editor_tab(tab_photo_edit)
        self.tabs.addTab(tab_photo_edit, "🎨 ویرایش و برش تصویر")

        # Tab 3: Video Editor
        tab_edit = QWidget()
        self._build_editor_tab(tab_edit)
        self.tabs.addTab(tab_edit, "✂️ ویرایش و برش ویدیو")

        main_layout.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_camera_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Camera header row
        h_row = QHBoxLayout()
        lbl_cam = QLabel("انتخاب دوربین:")
        lbl_cam.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.combo_cam = QComboBox()
        self.combo_cam.setMinimumWidth(200)
        self.combo_cam.currentIndexChanged.connect(self._on_cam_combo_changed)

        btn_rescan = QPushButton("🔄 جستجو")
        btn_rescan.setObjectName("secondary_button")
        btn_rescan.clicked.connect(self.populate_cameras)

        self.chk_cam_flip = QCheckBox("تصویر واقعی (غیرآینه‌ای)")
        self.chk_cam_flip.setChecked(True)
        self.chk_cam_flip.toggled.connect(self._sync_flip_from_video)

        h_row.addWidget(lbl_cam)
        h_row.addWidget(self.combo_cam)
        h_row.addWidget(btn_rescan)
        h_row.addSpacing(15)
        h_row.addWidget(self.chk_cam_flip)
        h_row.addStretch()
        layout.addLayout(h_row)

        # Live Camera Screen
        self.lbl_cam_screen = QLabel("در حال اتصال به دوربین...")
        self.lbl_cam_screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cam_screen.setMinimumSize(420, 240)
        self.lbl_cam_screen.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_cam_screen.setStyleSheet("background-color: #0d0d0d; border: 2px solid #2a2a2a; border-radius: 8px; font-size: 14px; color: #888888;")
        layout.addWidget(self.lbl_cam_screen, stretch=1)

        # Recording Status & Timer Indicator
        rec_status_row = QHBoxLayout()
        self.lbl_rec_timer = QLabel("آماده برای ضبط ویدیو")
        self.lbl_rec_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rec_timer.setStyleSheet("font-size: 15px; font-weight: bold; color: #aaaaaa; padding: 4px;")
        rec_status_row.addWidget(self.lbl_rec_timer)
        layout.addLayout(rec_status_row)

        # Camera Actions Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.btn_rec_toggle = QPushButton("🔴 شروع ضبط ویدیو")
        self.btn_rec_toggle.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px 24px; background-color: #e53935; color: white; border-radius: 6px;")
        self.btn_rec_toggle.clicked.connect(self.toggle_recording)

        self.btn_cam_cancel = QPushButton("انصراف")
        self.btn_cam_cancel.setObjectName("secondary_button")
        self.btn_cam_cancel.setStyleSheet("font-size: 13px; padding: 9px 20px; border-radius: 6px;")
        self.btn_cam_cancel.clicked.connect(self.reject)

        actions_row.addWidget(self.btn_rec_toggle)
        actions_row.addStretch()
        actions_row.addWidget(self.btn_cam_cancel)
        layout.addLayout(actions_row)

    def _sync_flip_from_video(self, checked: bool):
        if hasattr(self, "chk_photo_flip") and self.chk_photo_flip.isChecked() != checked:
            self.chk_photo_flip.blockSignals(True)
            self.chk_photo_flip.setChecked(checked)
            self.chk_photo_flip.blockSignals(False)

    def _sync_flip_from_photo(self, checked: bool):
        if hasattr(self, "chk_cam_flip") and self.chk_cam_flip.isChecked() != checked:
            self.chk_cam_flip.blockSignals(True)
            self.chk_cam_flip.setChecked(checked)
            self.chk_cam_flip.blockSignals(False)

    def _build_photo_capture_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Photo Header Row
        h_row = QHBoxLayout()
        lbl_cam = QLabel("انتخاب دوربین:")
        lbl_cam.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.combo_photo_cam = QComboBox()
        self.combo_photo_cam.setMinimumWidth(200)
        self.combo_photo_cam.currentIndexChanged.connect(self._on_photo_cam_combo_changed)

        btn_rescan = QPushButton("🔄 جستجو")
        btn_rescan.setObjectName("secondary_button")
        btn_rescan.clicked.connect(self.populate_cameras)

        self.chk_photo_flip = QCheckBox("تصویر واقعی (غیرآینه‌ای)")
        self.chk_photo_flip.setChecked(True)
        self.chk_photo_flip.toggled.connect(self._sync_flip_from_photo)

        # Shutter timer selector
        lbl_timer = QLabel("⏱️ تایمر شاتر:")
        lbl_timer.setStyleSheet("font-size: 13px; font-weight: bold; margin-right: 8px;")
        self.combo_photo_timer = QComboBox()
        self.combo_photo_timer.addItem("فوری (بدون تاخیر)", 0)
        self.combo_photo_timer.addItem("۳ ثانیه", 3)
        self.combo_photo_timer.addItem("۵ ثانیه", 5)
        self.combo_photo_timer.addItem("۱۰ ثانیه", 10)
        self.combo_photo_timer.setFixedWidth(130)

        h_row.addWidget(lbl_cam)
        h_row.addWidget(self.combo_photo_cam)
        h_row.addWidget(btn_rescan)
        h_row.addSpacing(12)
        h_row.addWidget(self.chk_photo_flip)
        h_row.addSpacing(12)
        h_row.addWidget(lbl_timer)
        h_row.addWidget(self.combo_photo_timer)
        h_row.addStretch()
        layout.addLayout(h_row)

        # Live Camera Screen for Photo
        self.lbl_photo_screen = QLabel("در حال اتصال به دوربین...")
        self.lbl_photo_screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo_screen.setMinimumSize(420, 240)
        self.lbl_photo_screen.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_photo_screen.setStyleSheet("background-color: #0d0d0d; border: 2px solid #2a2a2a; border-radius: 8px; font-size: 14px; color: #888888;")
        layout.addWidget(self.lbl_photo_screen, stretch=1)

        # Status text
        self.lbl_photo_status = QLabel("آماده برای عکس‌برداری. جهت ژست گرفتن می‌توانید تایمر را روی ۳ یا ۵ ثانیه بگذارید.")
        self.lbl_photo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_photo_status.setStyleSheet("font-size: 13px; color: #aaaaaa; padding: 2px;")
        layout.addWidget(self.lbl_photo_status)

        # Actions row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.btn_take_photo = QPushButton("📸 ثبت عکس با دوربین (شاتر)")
        self.btn_take_photo.setFixedHeight(42)
        self.btn_take_photo.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px 28px; background-color: #0088cc; color: white; border-radius: 6px;")
        self.btn_take_photo.clicked.connect(self.trigger_photo_shutter)

        self.btn_cancel_countdown = QPushButton("لغو شمارش معکوس")
        self.btn_cancel_countdown.setObjectName("secondary_button")
        self.btn_cancel_countdown.setFixedHeight(42)
        self.btn_cancel_countdown.setStyleSheet("font-size: 13px; padding: 8px 16px; border-radius: 6px; background-color: #e53935; color: white;")
        self.btn_cancel_countdown.clicked.connect(self.cancel_photo_countdown)
        self.btn_cancel_countdown.hide()

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet("font-size: 13px; padding: 8px 20px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)

        actions_row.addWidget(self.btn_take_photo)
        actions_row.addWidget(self.btn_cancel_countdown)
        actions_row.addStretch()
        actions_row.addWidget(btn_cancel)
        layout.addLayout(actions_row)

    def _build_photo_editor_tab(self, tab: QWidget):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # Left: Interactive Crop Canvas
        self.photo_canvas = CropCanvas(self)
        self.photo_canvas.cropChanged.connect(self._sync_photo_dimensions_label)
        layout.addWidget(self.photo_canvas, stretch=5)

        # Right sidebar: Editing controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setSpacing(8)
        panel_layout.setContentsMargins(4, 2, 4, 2)

        # 1. Crop & Aspect Ratio Group
        group_crop = QGroupBox("تنظیمات کادر و نسبت ابعاد (Crop)")
        group_crop.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_crop = QVBoxLayout(group_crop)
        vbox_crop.setContentsMargins(10, 10, 10, 8)
        vbox_crop.setSpacing(6)

        grid_ratios = QHBoxLayout()
        grid_ratios.setSpacing(4)

        self.btn_photo_ratio_free = QPushButton("آزاد")
        self.btn_photo_ratio_free.setToolTip("برش دلخواه بدون محدودیت نسبت ابعاد")
        self.btn_photo_ratio_free.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_photo_ratio_free.clicked.connect(lambda: self.set_photo_aspect_ratio(None))

        self.btn_photo_ratio_1_1 = QPushButton("۱:۱ (مربع)")
        self.btn_photo_ratio_1_1.setToolTip("کادر مربع ۱:۱ مناسب تصویر حرکت و پروفایل")
        self.btn_photo_ratio_1_1.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_photo_ratio_1_1.clicked.connect(lambda: self.set_photo_aspect_ratio(1.0))

        self.btn_photo_ratio_4_3 = QPushButton("۴:۳")
        self.btn_photo_ratio_4_3.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_photo_ratio_4_3.clicked.connect(lambda: self.set_photo_aspect_ratio(4.0 / 3.0))

        self.btn_photo_ratio_16_9 = QPushButton("۱۶:۹")
        self.btn_photo_ratio_16_9.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_photo_ratio_16_9.clicked.connect(lambda: self.set_photo_aspect_ratio(16.0 / 9.0))

        self.btn_photo_ratio_9_16 = QPushButton("۹:۱۶")
        self.btn_photo_ratio_9_16.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_photo_ratio_9_16.clicked.connect(lambda: self.set_photo_aspect_ratio(9.0 / 16.0))

        grid_ratios.addWidget(self.btn_photo_ratio_free)
        grid_ratios.addWidget(self.btn_photo_ratio_1_1)
        grid_ratios.addWidget(self.btn_photo_ratio_4_3)
        grid_ratios.addWidget(self.btn_photo_ratio_16_9)
        grid_ratios.addWidget(self.btn_photo_ratio_9_16)
        vbox_crop.addLayout(grid_ratios)

        btn_reset_crop = QPushButton("↺ بازنشانی کادر به تمام تصویر")
        btn_reset_crop.setObjectName("secondary_button")
        btn_reset_crop.setStyleSheet("font-size: 11px; padding: 5px; color: #BBDEFB;")
        btn_reset_crop.clicked.connect(self.photo_canvas.reset_crop)
        vbox_crop.addWidget(btn_reset_crop)

        self.lbl_photo_dims = QLabel("ابعاد انتخابی: -")
        self.lbl_photo_dims.setStyleSheet("font-size: 11px; color: #00E5FF; font-weight: bold;")
        vbox_crop.addWidget(self.lbl_photo_dims)

        panel_layout.addWidget(group_crop)

        # 2. Transformations (Rotate & Flip)
        group_trans = QGroupBox("چرخش و قرینه‌سازی (Transform)")
        group_trans.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_trans = QVBoxLayout(group_trans)
        vbox_trans.setContentsMargins(10, 10, 10, 8)
        vbox_trans.setSpacing(6)

        row_rot = QHBoxLayout()
        btn_rot_cw = QPushButton("↷ چرخش ۹۰°")
        btn_rot_cw.setStyleSheet("font-size: 11px; padding: 5px;")
        btn_rot_cw.clicked.connect(lambda: self.transform_photo("rot_cw"))

        btn_rot_ccw = QPushButton("↶ چرخش ۹۰°-")
        btn_rot_ccw.setStyleSheet("font-size: 11px; padding: 5px;")
        btn_rot_ccw.clicked.connect(lambda: self.transform_photo("rot_ccw"))

        row_rot.addWidget(btn_rot_cw)
        row_rot.addWidget(btn_rot_ccw)
        vbox_trans.addLayout(row_rot)

        row_flip = QHBoxLayout()
        btn_flip_h = QPushButton("↔️ آینه افقی")
        btn_flip_h.setStyleSheet("font-size: 11px; padding: 5px;")
        btn_flip_h.clicked.connect(lambda: self.transform_photo("flip_h"))

        btn_flip_v = QPushButton("↕️ آینه عمودی")
        btn_flip_v.setStyleSheet("font-size: 11px; padding: 5px;")
        btn_flip_v.clicked.connect(lambda: self.transform_photo("flip_v"))

        row_flip.addWidget(btn_flip_h)
        row_flip.addWidget(btn_flip_v)
        vbox_trans.addLayout(row_flip)

        panel_layout.addWidget(group_trans)

        # 3. Image Adjustments (Brightness, Contrast, Color, Sharpness)
        group_adj = QGroupBox("تنظیمات نور و رنگ (Adjustments)")
        group_adj.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_adj = QVBoxLayout(group_adj)
        vbox_adj.setContentsMargins(10, 10, 10, 8)
        vbox_adj.setSpacing(5)

        # Brightness
        row_b = QHBoxLayout()
        lbl_b = QLabel("روشنایی:")
        lbl_b.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_photo_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_photo_brightness.setRange(50, 150)
        self.slider_photo_brightness.setValue(100)
        self.lbl_photo_b_val = QLabel("۱۰۰٪")
        self.lbl_photo_b_val.setStyleSheet("font-size: 11px; min-width: 35px; color: #AAA;")
        self.slider_photo_brightness.valueChanged.connect(self._on_photo_adjustment_changed)
        row_b.addWidget(lbl_b)
        row_b.addWidget(self.slider_photo_brightness)
        row_b.addWidget(self.lbl_photo_b_val)
        vbox_adj.addLayout(row_b)

        # Contrast
        row_c = QHBoxLayout()
        lbl_c = QLabel("کنتراست:")
        lbl_c.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_photo_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_photo_contrast.setRange(50, 150)
        self.slider_photo_contrast.setValue(100)
        self.lbl_photo_c_val = QLabel("۱۰۰٪")
        self.lbl_photo_c_val.setStyleSheet("font-size: 11px; min-width: 35px; color: #AAA;")
        self.slider_photo_contrast.valueChanged.connect(self._on_photo_adjustment_changed)
        row_c.addWidget(lbl_c)
        row_c.addWidget(self.slider_photo_contrast)
        row_c.addWidget(self.lbl_photo_c_val)
        vbox_adj.addLayout(row_c)

        # Saturation / Color
        row_s = QHBoxLayout()
        lbl_s = QLabel("اشباع رنگ:")
        lbl_s.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_photo_color = QSlider(Qt.Orientation.Horizontal)
        self.slider_photo_color.setRange(0, 200)
        self.slider_photo_color.setValue(100)
        self.lbl_photo_s_val = QLabel("۱۰۰٪")
        self.lbl_photo_s_val.setStyleSheet("font-size: 11px; min-width: 35px; color: #AAA;")
        self.slider_photo_color.valueChanged.connect(self._on_photo_adjustment_changed)
        row_s.addWidget(lbl_s)
        row_s.addWidget(self.slider_photo_color)
        row_s.addWidget(self.lbl_photo_s_val)
        vbox_adj.addLayout(row_s)

        # Sharpness
        row_sh = QHBoxLayout()
        lbl_sh = QLabel("وضوح:")
        lbl_sh.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_photo_sharpness = QSlider(Qt.Orientation.Horizontal)
        self.slider_photo_sharpness.setRange(0, 200)
        self.slider_photo_sharpness.setValue(100)
        self.lbl_photo_sh_val = QLabel("۱۰۰٪")
        self.lbl_photo_sh_val.setStyleSheet("font-size: 11px; min-width: 35px; color: #AAA;")
        self.slider_photo_sharpness.valueChanged.connect(self._on_photo_adjustment_changed)
        row_sh.addWidget(lbl_sh)
        row_sh.addWidget(self.slider_photo_sharpness)
        row_sh.addWidget(self.lbl_photo_sh_val)
        vbox_adj.addLayout(row_sh)

        btn_reset_adj = QPushButton("↺ بازنشانی نور و رنگ")
        btn_reset_adj.setObjectName("secondary_button")
        btn_reset_adj.setStyleSheet("font-size: 11px; padding: 4px; color: #FFCC80;")
        btn_reset_adj.clicked.connect(self._reset_photo_adjustments)
        vbox_adj.addWidget(btn_reset_adj)

        panel_layout.addWidget(group_adj)

        # 4. Action Buttons
        self.btn_photo_reset_all = QPushButton("🔄 بازنشانی کامل به تصویر اولیه")
        self.btn_photo_reset_all.setObjectName("secondary_button")
        self.btn_photo_reset_all.setStyleSheet("font-size: 11px; padding: 5px; background-color: #2D2D2D; color: #FFCDD2; border: 1px solid #555;")
        self.btn_photo_reset_all.clicked.connect(self._reset_photo_to_original)
        panel_layout.addWidget(self.btn_photo_reset_all)

        self.btn_photo_retake = QPushButton("🔄 عکس‌برداری مجدد با دوربین")
        self.btn_photo_retake.setObjectName("secondary_button")
        self.btn_photo_retake.setFixedHeight(34)
        self.btn_photo_retake.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px; background-color: #555555; color: white; border-radius: 5px;")
        self.btn_photo_retake.clicked.connect(self._on_photo_retake_clicked)
        panel_layout.addWidget(self.btn_photo_retake)

        self.btn_save_photo = QPushButton("✅ تایید و ذخیره نهایی تصویر")
        self.btn_save_photo.setFixedHeight(40)
        self.btn_save_photo.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px; background-color: #2e7d32; color: white; border-radius: 5px;")
        self.btn_save_photo.clicked.connect(self.save_and_apply_photo)
        panel_layout.addWidget(self.btn_save_photo)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(30)
        btn_cancel.setStyleSheet("font-size: 12px; padding: 6px; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        panel_layout.addWidget(btn_cancel)

        scroll.setWidget(panel_widget)
        layout.addWidget(scroll, stretch=3)

    def trigger_photo_shutter(self):
        if self.latest_cam_frame is None:
            QMessageBox.warning(self, "خطا", "تصویر دوربین هنوز آماده نیست.")
            return

        delay = self.combo_photo_timer.currentData()
        if delay and delay > 0:
            self.photo_countdown_remaining = delay
            self.btn_take_photo.setEnabled(False)
            self.btn_cancel_countdown.show()
            self.lbl_photo_status.setText(f"⏳ عکس در {self.photo_countdown_remaining} ثانیه دیگر گرفته می‌شود...")
            self.lbl_photo_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #00E5FF; padding: 2px;")
            self.photo_timer.start(1000)
        else:
            self.execute_take_photo()

    def _on_photo_countdown_tick(self):
        self.photo_countdown_remaining -= 1
        if self.photo_countdown_remaining > 0:
            self.lbl_photo_status.setText(f"⏳ عکس در {self.photo_countdown_remaining} ثانیه دیگر گرفته می‌شود...")
        else:
            self.photo_timer.stop()
            self.cancel_photo_countdown()
            self.execute_take_photo()

    def cancel_photo_countdown(self):
        if self.photo_timer.isActive():
            self.photo_timer.stop()
        self.photo_countdown_remaining = 0
        self.btn_take_photo.setEnabled(True)
        self.btn_cancel_countdown.hide()
        self.lbl_photo_status.setText("آماده برای عکس‌برداری. جهت ژست گرفتن می‌توانید تایمر را روی ۳ یا ۵ ثانیه بگذارید.")
        self.lbl_photo_status.setStyleSheet("font-size: 13px; color: #aaaaaa; padding: 2px;")

    def execute_take_photo(self):
        if self.latest_cam_frame is None:
            return
        frame = self.latest_cam_frame.copy()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        self.stop_camera()
        self.load_pil_image_for_editing(pil_img)
        self.tabs.setCurrentIndex(2)

    def load_image_for_editing(self, path: str):
        if not path or not os.path.exists(path):
            return
        try:
            loaded = Image.open(path)
            if loaded.mode != "RGB":
                loaded = loaded.convert("RGB")
            self.load_pil_image_for_editing(loaded)
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"امکان بارگذاری تصویر جهت ویرایش وجود ندارد:\n{str(e)}")

    def load_pil_image_for_editing(self, pil_img: Image.Image):
        self.photo_orig_pil = pil_img.copy()
        self.photo_transformed_pil = pil_img.copy()
        self.slider_photo_brightness.blockSignals(True)
        self.slider_photo_contrast.blockSignals(True)
        self.slider_photo_color.blockSignals(True)
        self.slider_photo_sharpness.blockSignals(True)
        self.slider_photo_brightness.setValue(100)
        self.slider_photo_contrast.setValue(100)
        self.slider_photo_color.setValue(100)
        self.slider_photo_sharpness.setValue(100)
        self.slider_photo_brightness.blockSignals(False)
        self.slider_photo_contrast.blockSignals(False)
        self.slider_photo_color.blockSignals(False)
        self.slider_photo_sharpness.blockSignals(False)
        self.lbl_photo_b_val.setText("۱۰۰٪")
        self.lbl_photo_c_val.setText("۱۰۰٪")
        self.lbl_photo_s_val.setText("۱۰۰٪")
        self.lbl_photo_sh_val.setText("۱۰۰٪")
        self.apply_photo_adjustments(reset_crop=True)

    def set_photo_aspect_ratio(self, ratio: float | None):
        self.photo_canvas.set_aspect_ratio(ratio)

    def _sync_photo_dimensions_label(self):
        if not hasattr(self, 'lbl_photo_dims') or not self.photo_display_pil:
            return
        w = self.photo_display_pil.width
        h = self.photo_display_pil.height
        norm = self.photo_canvas.crop_norm
        crop_w = int(norm.width() * w)
        crop_h = int(norm.height() * h)
        to_fa = lambda n: str(n).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_photo_dims.setText(f"ابعاد برش: {to_fa(crop_w)} × {to_fa(crop_h)} پیکسل")

    def transform_photo(self, action: str):
        if not self.photo_transformed_pil:
            return
        if action == "rot_cw":
            self.photo_transformed_pil = self.photo_transformed_pil.rotate(-90, expand=True)
        elif action == "rot_ccw":
            self.photo_transformed_pil = self.photo_transformed_pil.rotate(90, expand=True)
        elif action == "flip_h":
            self.photo_transformed_pil = self.photo_transformed_pil.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif action == "flip_v":
            self.photo_transformed_pil = self.photo_transformed_pil.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        self.apply_photo_adjustments(reset_crop=True)

    def _on_photo_adjustment_changed(self):
        b_val = self.slider_photo_brightness.value()
        c_val = self.slider_photo_contrast.value()
        s_val = self.slider_photo_color.value()
        sh_val = self.slider_photo_sharpness.value()

        to_fa = lambda n: str(n).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_photo_b_val.setText(f"{to_fa(b_val)}٪")
        self.lbl_photo_c_val.setText(f"{to_fa(c_val)}٪")
        self.lbl_photo_s_val.setText(f"{to_fa(s_val)}٪")
        self.lbl_photo_sh_val.setText(f"{to_fa(sh_val)}٪")

        self.apply_photo_adjustments(reset_crop=False)

    def _reset_photo_adjustments(self):
        self.slider_photo_brightness.setValue(100)
        self.slider_photo_contrast.setValue(100)
        self.slider_photo_color.setValue(100)
        self.slider_photo_sharpness.setValue(100)
        self.apply_photo_adjustments(reset_crop=False)

    def _reset_photo_to_original(self):
        if self.photo_orig_pil:
            self.photo_transformed_pil = self.photo_orig_pil.copy()
            self.slider_photo_brightness.setValue(100)
            self.slider_photo_contrast.setValue(100)
            self.slider_photo_color.setValue(100)
            self.slider_photo_sharpness.setValue(100)
            self.apply_photo_adjustments(reset_crop=True)

    def apply_photo_adjustments(self, reset_crop: bool = False):
        if not self.photo_transformed_pil:
            return

        img = self.photo_transformed_pil

        b = self.slider_photo_brightness.value() / 100.0
        if b != 1.0:
            img = ImageEnhance.Brightness(img).enhance(b)

        c = self.slider_photo_contrast.value() / 100.0
        if c != 1.0:
            img = ImageEnhance.Contrast(img).enhance(c)

        col = self.slider_photo_color.value() / 100.0
        if col != 1.0:
            img = ImageEnhance.Color(img).enhance(col)

        sh = self.slider_photo_sharpness.value() / 100.0
        if sh != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(sh)

        self.photo_display_pil = img
        pixmap = pil_to_pixmap(self.photo_display_pil)
        self.photo_canvas.set_pixmap(pixmap, reset_crop=reset_crop)
        self._sync_photo_dimensions_label()

    def _on_photo_retake_clicked(self):
        reply = QMessageBox.question(
            self,
            "عکس‌برداری مجدد با دوربین",
            "آیا مایل به بازگشت به دوربین و ثبت مجدد عکس هستید؟ تغییرات تصویر فعلی نادیده گرفته خواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tabs.setCurrentIndex(1)
            self.detect_and_start_camera()

    def save_and_apply_photo(self):
        if not self.photo_display_pil:
            QMessageBox.warning(self, "خطا", "تصویری جهت ذخیره وجود ندارد.")
            return

        try:
            w = self.photo_display_pil.width
            h = self.photo_display_pil.height
            norm = self.photo_canvas.crop_norm

            crop_x = max(0, int(norm.left() * w))
            crop_y = max(0, int(norm.top() * h))
            crop_w = min(w - crop_x, int(norm.width() * w))
            crop_h = min(h - crop_y, int(norm.height() * h))

            if crop_w <= 0 or crop_h <= 0:
                crop_x, crop_y, crop_w, crop_h = 0, 0, w, h

            cropped_img = self.photo_display_pil.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

            out_dir = config.EXERCISE_MEDIA_DIR
            out_dir.mkdir(parents=True, exist_ok=True)

            clean_title = ""
            if getattr(self, "exercise_title", None):
                clean_title = re.sub(r'[^\w\d_\-\.\u0600-\u06FF]', '_', self.exercise_title.strip()).strip('_')

            if clean_title:
                base_name = f"{clean_title}_photo_{int(time.time())}"
            else:
                base_name = f"exercise_photo_{int(time.time())}_{uuid.uuid4().hex[:4]}"

            filename = f"{base_name}.jpg"
            out_path = str(out_dir / filename)

            cropped_img.save(out_path, format="JPEG", quality=95, optimize=True, subsampling=0)

            self.result_image_path = out_path
            self.result_media_type = "image"
            self.stop_camera()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در پردازش و ذخیره تصویر: {str(e)}")

    def _build_editor_tab(self, tab: QWidget):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # Left/Center: Video Player & Timeline controls
        player_col = QVBoxLayout()
        player_col.setSpacing(8)

        self.video_player = VideoPlayerWidget(self)
        player_col.addWidget(self.video_player, stretch=1)

        # Timeline Slider & Time Label
        timeline_box = QHBoxLayout()
        self.lbl_time = QLabel("00:00.0 / 00:00.0")
        self.lbl_time.setStyleSheet("font-size: 12px; font-weight: bold; color: #00E5FF; min-width: 140px;")

        self.slider_timeline = QSlider(Qt.Orientation.Horizontal)
        self.slider_timeline.setRange(0, 100)
        self.slider_timeline.sliderMoved.connect(self._on_slider_moved)
        self.slider_timeline.sliderPressed.connect(self._on_slider_pressed)
        self.slider_timeline.sliderReleased.connect(self._on_slider_released)

        timeline_box.addWidget(self.lbl_time)
        timeline_box.addWidget(self.slider_timeline)
        player_col.addLayout(timeline_box)

        # Playback Controls Row
        ctrl_row = QHBoxLayout()
        self.btn_play = QPushButton("▶️ پخش")
        self.btn_play.setStyleSheet("font-size: 13px; font-weight: bold; padding: 6px 18px; background-color: #0088cc; color: white; border-radius: 5px;")
        self.btn_play.clicked.connect(self.toggle_playback)

        self.btn_step_bwd = QPushButton("⏪ -۰.۵s")
        self.btn_step_bwd.setToolTip("نیم ثانیه به عقب")
        self.btn_step_bwd.setObjectName("secondary_button")
        self.btn_step_bwd.clicked.connect(lambda: self.step_frames(-15))

        self.btn_step_fwd = QPushButton("⏩ +۰.۵s")
        self.btn_step_fwd.setToolTip("نیم ثانیه به جلو")
        self.btn_step_fwd.setObjectName("secondary_button")
        self.btn_step_fwd.clicked.connect(lambda: self.step_frames(15))

        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_step_bwd)
        ctrl_row.addWidget(self.btn_step_fwd)
        ctrl_row.addStretch()

        # Rotation & Flip buttons
        btn_rot = QPushButton("🔄 چرخش ۹۰°")
        btn_rot.setObjectName("secondary_button")
        btn_rot.clicked.connect(self.rotate_video)

        btn_flip = QPushButton("↔️ آینه افقی")
        btn_flip.setObjectName("secondary_button")
        btn_flip.clicked.connect(self.flip_video)

        ctrl_row.addWidget(btn_rot)
        ctrl_row.addWidget(btn_flip)

        player_col.addLayout(ctrl_row)

        layout.addLayout(player_col, stretch=6)

        # Right sidebar: Trimming & Cropping controls (in smooth scroll area)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        sidebar_container = QWidget()
        sidebar_container.setStyleSheet("background: transparent;")
        sidebar = QVBoxLayout(sidebar_container)
        sidebar.setContentsMargins(4, 2, 4, 2)
        sidebar.setSpacing(6)

        # 1. Trimming Group
        group_trim = QGroupBox("⏱️ برش زمانی (کات فیلم)")
        group_trim.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; color: #E0E0E0; }")
        vbox_trim = QVBoxLayout(group_trim)
        vbox_trim.setContentsMargins(10, 10, 10, 8)
        vbox_trim.setSpacing(5)

        # Start time row
        row_s = QHBoxLayout()
        row_s.setSpacing(6)
        lbl_s = QLabel("شروع:")
        lbl_s.setFixedWidth(42)
        lbl_s.setStyleSheet("font-size: 13px; color: #FFFFFF;")
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0.0, 9999.0)
        self.spin_start.setSingleStep(0.1)
        self.spin_start.setDecimals(1)
        self.spin_start.setSuffix(" ثانیه")
        self.spin_start.setFixedHeight(30)
        self.spin_start.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_start.valueChanged.connect(self._on_trim_changed)
        btn_set_s = QPushButton("⏱️ این لحظه")
        btn_set_s.setObjectName("secondary_button")
        btn_set_s.setToolTip("تنظیم ثانیه شروع بر اساس موقعیت فعلی فیلم")
        btn_set_s.setMinimumWidth(85)
        btn_set_s.setFixedHeight(30)
        btn_set_s.setStyleSheet("font-size: 11px; font-weight: bold; padding: 3px 6px;")
        btn_set_s.clicked.connect(self._set_start_current)
        row_s.addWidget(lbl_s)
        row_s.addWidget(self.spin_start, stretch=1)
        row_s.addWidget(btn_set_s)
        vbox_trim.addLayout(row_s)

        # End time row
        row_e = QHBoxLayout()
        row_e.setSpacing(6)
        lbl_e = QLabel("پایان:")
        lbl_e.setFixedWidth(42)
        lbl_e.setStyleSheet("font-size: 13px; color: #FFFFFF;")
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setRange(0.0, 9999.0)
        self.spin_end.setSingleStep(0.1)
        self.spin_end.setDecimals(1)
        self.spin_end.setSuffix(" ثانیه")
        self.spin_end.setFixedHeight(30)
        self.spin_end.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_end.valueChanged.connect(self._on_trim_changed)
        btn_set_e = QPushButton("⏱️ این لحظه")
        btn_set_e.setObjectName("secondary_button")
        btn_set_e.setToolTip("تنظیم ثانیه پایان بر اساس موقعیت فعلی فیلم")
        btn_set_e.setMinimumWidth(85)
        btn_set_e.setFixedHeight(30)
        btn_set_e.setStyleSheet("font-size: 11px; font-weight: bold; padding: 3px 6px;")
        btn_set_e.clicked.connect(self._set_end_current)
        row_e.addWidget(lbl_e)
        row_e.addWidget(self.spin_end, stretch=1)
        row_e.addWidget(btn_set_e)
        vbox_trim.addLayout(row_e)

        # Dedicated Feature Requested by User: Checkbox 'حذف بازه‌ی انتخاب شده'
        self.chk_delete_interval = QCheckBox("✂️ حذف بازه‌ی انتخاب شده (برش از وسط)")
        self.chk_delete_interval.setChecked(False)
        self.chk_delete_interval.setStyleSheet("font-weight: bold; color: #ffab40; font-size: 12px; margin-top: 2px;")
        self.chk_delete_interval.toggled.connect(self._on_mode_toggled)
        vbox_trim.addWidget(self.chk_delete_interval)

        self.lbl_trim_explanation = QLabel("🟢 فقط بازه مشخص‌شده ذخیره می‌شود.")
        self.lbl_trim_explanation.setStyleSheet("font-size: 11px; color: #81c784;")
        self.lbl_trim_explanation.setWordWrap(True)
        vbox_trim.addWidget(self.lbl_trim_explanation)

        sidebar.addWidget(group_trim)

        # 2. Pixel Cropping Group
        group_crop = QGroupBox("📐 کراپ پیکسلی کادر (حذف حواشی)")
        group_crop.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; color: #E0E0E0; }")
        vbox_crop = QVBoxLayout(group_crop)
        vbox_crop.setContentsMargins(10, 10, 10, 8)
        vbox_crop.setSpacing(5)

        lbl_w = 120
        # Top Margin
        row_ct = QHBoxLayout()
        lbl_ct = QLabel("حاشیه بالا (Top):")
        lbl_ct.setFixedWidth(lbl_w)
        lbl_ct.setStyleSheet("font-size: 12px; color: #E0E0E0;")
        self.spin_crop_top = QSpinBox()
        self.spin_crop_top.setRange(0, 1000)
        self.spin_crop_top.setSingleStep(5)
        self.spin_crop_top.setSuffix(" px")
        self.spin_crop_top.setFixedHeight(28)
        self.spin_crop_top.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_crop_top.valueChanged.connect(self._on_crop_changed)
        row_ct.addWidget(lbl_ct)
        row_ct.addWidget(self.spin_crop_top)
        vbox_crop.addLayout(row_ct)

        # Bottom Margin
        row_cb = QHBoxLayout()
        lbl_cb = QLabel("حاشیه پایین (Bottom):")
        lbl_cb.setFixedWidth(lbl_w)
        lbl_cb.setStyleSheet("font-size: 12px; color: #E0E0E0;")
        self.spin_crop_bottom = QSpinBox()
        self.spin_crop_bottom.setRange(0, 1000)
        self.spin_crop_bottom.setSingleStep(5)
        self.spin_crop_bottom.setSuffix(" px")
        self.spin_crop_bottom.setFixedHeight(28)
        self.spin_crop_bottom.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_crop_bottom.valueChanged.connect(self._on_crop_changed)
        row_cb.addWidget(lbl_cb)
        row_cb.addWidget(self.spin_crop_bottom)
        vbox_crop.addLayout(row_cb)

        # Left Margin
        row_cl = QHBoxLayout()
        lbl_cl = QLabel("حاشیه چپ (Left):")
        lbl_cl.setFixedWidth(lbl_w)
        lbl_cl.setStyleSheet("font-size: 12px; color: #E0E0E0;")
        self.spin_crop_left = QSpinBox()
        self.spin_crop_left.setRange(0, 1000)
        self.spin_crop_left.setSingleStep(5)
        self.spin_crop_left.setSuffix(" px")
        self.spin_crop_left.setFixedHeight(28)
        self.spin_crop_left.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_crop_left.valueChanged.connect(self._on_crop_changed)
        row_cl.addWidget(lbl_cl)
        row_cl.addWidget(self.spin_crop_left)
        vbox_crop.addLayout(row_cl)

        # Right Margin
        row_cr = QHBoxLayout()
        lbl_cr = QLabel("حاشیه راست (Right):")
        lbl_cr.setFixedWidth(lbl_w)
        lbl_cr.setStyleSheet("font-size: 12px; color: #E0E0E0;")
        self.spin_crop_right = QSpinBox()
        self.spin_crop_right.setRange(0, 1000)
        self.spin_crop_right.setSingleStep(5)
        self.spin_crop_right.setSuffix(" px")
        self.spin_crop_right.setFixedHeight(28)
        self.spin_crop_right.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.spin_crop_right.valueChanged.connect(self._on_crop_changed)
        row_cr.addWidget(lbl_cr)
        row_cr.addWidget(self.spin_crop_right)
        vbox_crop.addLayout(row_cr)

        # Quick preset buttons
        row_crop_btns = QHBoxLayout()
        row_crop_btns.setSpacing(6)
        btn_preset_120 = QPushButton("حذف ۱۲۰px بالا")
        btn_preset_120.setToolTip("تنظیم سریع برش ۱۲۰ پیکسل از بالا (حذف واترمارک)")
        btn_preset_120.setObjectName("secondary_button")
        btn_preset_120.setFixedHeight(28)
        btn_preset_120.setStyleSheet("font-size: 11px; font-weight: bold; padding: 3px 6px;")
        btn_preset_120.clicked.connect(lambda: self.spin_crop_top.setValue(120))

        btn_reset_crop = QPushButton("↺ ریست کادر")
        btn_reset_crop.setObjectName("secondary_button")
        btn_reset_crop.setFixedHeight(28)
        btn_reset_crop.setStyleSheet("font-size: 11px; font-weight: bold; padding: 3px 6px;")
        btn_reset_crop.clicked.connect(self.reset_crop_margins)

        row_crop_btns.addWidget(btn_preset_120)
        row_crop_btns.addWidget(btn_reset_crop)
        vbox_crop.addLayout(row_crop_btns)

        self.chk_show_cropped_direct = QCheckBox("نمایش کادر برش‌خورده نهایی")
        self.chk_show_cropped_direct.setChecked(False)
        self.chk_show_cropped_direct.setStyleSheet("font-size: 12px; color: #E0E0E0; margin-top: 2px;")
        self.chk_show_cropped_direct.toggled.connect(self._on_crop_changed)
        vbox_crop.addWidget(self.chk_show_cropped_direct)

        sidebar.addWidget(group_crop)

        # Action Buttons
        self.btn_retake = QPushButton("🔄 ضبط مجدد ویدیو")
        self.btn_retake.setObjectName("secondary_button")
        self.btn_retake.setFixedHeight(34)
        self.btn_retake.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px; background-color: #555555; color: white; border-radius: 6px;")
        self.btn_retake.clicked.connect(self.on_retake_clicked)
        sidebar.addWidget(self.btn_retake)

        self.btn_save_video = QPushButton("✅ تایید و ذخیره نهایی ویدیو")
        self.btn_save_video.setFixedHeight(40)
        self.btn_save_video.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; background-color: #2e7d32; color: white; border-radius: 6px;")
        self.btn_save_video.clicked.connect(self.process_and_save_video)
        sidebar.addWidget(self.btn_save_video)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setFixedHeight(30)
        btn_cancel.setStyleSheet("font-size: 12px; padding: 6px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        sidebar.addWidget(btn_cancel)

        sidebar_scroll.setWidget(sidebar_container)
        layout.addWidget(sidebar_scroll, stretch=4)

    # -------------------------------------------------------------------------
    # Camera Stream & Recording Engine
    # -------------------------------------------------------------------------
    def detect_and_start_camera(self):
        self.populate_cameras()

    def populate_cameras(self):
        self.stop_camera()
        self.combo_cam.blockSignals(True)
        self.combo_cam.clear()
        if hasattr(self, "combo_photo_cam"):
            self.combo_photo_cam.blockSignals(True)
            self.combo_photo_cam.clear()

        devices_found = []
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            qt_devices = QMediaDevices.videoInputs()
            for idx, dev in enumerate(qt_devices):
                desc = dev.description() or f"دوربین {idx + 1}"
                devices_found.append((desc, idx))
        except Exception:
            pass

        if not devices_found:
            for i in range(3):
                cap = None
                try:
                    if os.name == 'nt':
                        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            cap.release()
                            cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
                    else:
                        cap = cv2.VideoCapture(i)
                    if cap and cap.isOpened():
                        devices_found.append((f"دوربین {i + 1}", i))
                except Exception:
                    pass
                finally:
                    if cap:
                        cap.release()

        if devices_found:
            for label, cam_id in devices_found:
                self.combo_cam.addItem(label, cam_id)
                if hasattr(self, "combo_photo_cam"):
                    self.combo_photo_cam.addItem(label, cam_id)
            self.combo_cam.blockSignals(False)
            if hasattr(self, "combo_photo_cam"):
                self.combo_photo_cam.blockSignals(False)
            self.btn_rec_toggle.setEnabled(True)
            if hasattr(self, "btn_take_photo"):
                self.btn_take_photo.setEnabled(True)
            self.open_camera(devices_found[0][1])
        else:
            self.combo_cam.addItem("دوربینی یافت نشد", None)
            self.combo_cam.blockSignals(False)
            if hasattr(self, "combo_photo_cam"):
                self.combo_photo_cam.addItem("دوربینی یافت نشد", None)
                self.combo_photo_cam.blockSignals(False)
            self.btn_rec_toggle.setEnabled(False)
            if hasattr(self, "btn_take_photo"):
                self.btn_take_photo.setEnabled(False)
            self.lbl_cam_screen.setText("❌ هیچ دوربینی شناسایی نشد.\nلطفاً اتصال وبکم را بررسی کنید.")
            if hasattr(self, "lbl_photo_screen"):
                self.lbl_photo_screen.setText("❌ هیچ دوربینی شناسایی نشد.\nلطفاً اتصال وبکم را بررسی کنید.")

    def open_camera(self, cam_index: int):
        if cam_index is None:
            return
        self.stop_camera()

        if os.name == 'nt':
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        opened_cap = None
        for b in backends:
            try:
                cap = cv2.VideoCapture(cam_index, b)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        opened_cap = cap
                        break
                    else:
                        cap.release()
            except Exception:
                pass

        if opened_cap is not None:
            self.cam_cap = opened_cap
            try:
                self.cam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cam_cap.set(cv2.CAP_PROP_FPS, 30)
            except Exception:
                pass
            self.btn_rec_toggle.setEnabled(True)
            if hasattr(self, "btn_take_photo"):
                self.btn_take_photo.setEnabled(True)
            self.cam_timer.start()
        else:
            self.btn_rec_toggle.setEnabled(False)
            if hasattr(self, "btn_take_photo"):
                self.btn_take_photo.setEnabled(False)
            self.lbl_cam_screen.setText("❌ عدم دسترسی به تصویر دوربین.")
            if hasattr(self, "lbl_photo_screen"):
                self.lbl_photo_screen.setText("❌ عدم دسترسی به تصویر دوربین.")

    def _on_cam_combo_changed(self, idx: int):
        if hasattr(self, "combo_photo_cam") and self.combo_photo_cam.currentIndex() != idx:
            self.combo_photo_cam.blockSignals(True)
            self.combo_photo_cam.setCurrentIndex(idx)
            self.combo_photo_cam.blockSignals(False)
        cam_id = self.combo_cam.currentData()
        if cam_id is not None:
            self.open_camera(cam_id)

    def _on_photo_cam_combo_changed(self, idx: int):
        if hasattr(self, "combo_cam") and self.combo_cam.currentIndex() != idx:
            self.combo_cam.blockSignals(True)
            self.combo_cam.setCurrentIndex(idx)
            self.combo_cam.blockSignals(False)
        cam_id = self.combo_photo_cam.currentData()
        if cam_id is not None:
            self.open_camera(cam_id)

    def _on_cam_frame(self):
        if not self.cam_cap or not self.cam_cap.isOpened():
            return
        ret, frame = self.cam_cap.read()
        if not ret or frame is None:
            return

        flip_active = self.chk_cam_flip.isChecked() if hasattr(self, "chk_cam_flip") else True
        if flip_active:
            frame = cv2.flip(frame, 1)

        self.latest_cam_frame = frame.copy()

        # If recording, write to VideoWriter
        if self.is_recording and self.record_writer:
            self.record_writer.write(frame)
            self.record_frame_count += 1
            elapsed = time.time() - self.record_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self.lbl_rec_timer.setText(f"🔴 در حال ضبط: {mins:02d}:{secs:02d}")

        current_tab_idx = self.tabs.currentIndex()

        if current_tab_idx == 0 and hasattr(self, "lbl_cam_screen"):
            # Render video recording preview
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            scaled = pix.scaled(self.lbl_cam_screen.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_cam_screen.setPixmap(scaled)
        elif current_tab_idx == 1 and hasattr(self, "lbl_photo_screen"):
            # Render photo capture preview
            display_frame = frame.copy()
            if self.photo_countdown_remaining > 0:
                h, w = display_frame.shape[:2]
                text = str(self.photo_countdown_remaining)
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 3.5
                thickness = 7
                text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
                tx = (w - text_size[0]) // 2
                ty = (h + text_size[1]) // 2
                cv2.putText(display_frame, text, (tx + 4, ty + 4), font, font_scale, (0, 0, 0), thickness + 4, cv2.LINE_AA)
                cv2.putText(display_frame, text, (tx, ty), font, font_scale, (0, 229, 255), thickness, cv2.LINE_AA)

            rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            scaled = pix.scaled(self.lbl_photo_screen.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_photo_screen.setPixmap(scaled)

    def toggle_recording(self):
        if not self.is_recording:
            # Start Recording
            if self.latest_cam_frame is None:
                QMessageBox.warning(self, "خطا", "تصویر دوربین هنوز آماده نیست.")
                return
            h, w = self.latest_cam_frame.shape[:2]
            temp_dir = tempfile.gettempdir()
            filename = f"recorded_raw_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4"
            self.record_temp_path = os.path.join(temp_dir, filename)

            # FourCC mp4v
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.record_writer = cv2.VideoWriter(self.record_temp_path, fourcc, 30.0, (w, h))
            if not self.record_writer.isOpened():
                QMessageBox.critical(self, "خطا", "امکان ایجاد فایل ویدیویی وجود ندارد.")
                return

            self.is_recording = True
            self.record_frame_count = 0
            self.record_start_time = time.time()
            self.btn_rec_toggle.setText("⏹️ پایان ضبط و ورود به ویرایشگر")
            self.btn_rec_toggle.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px 24px; background-color: #ff9800; color: black; border-radius: 6px;")
        else:
            # Stop Recording
            self.is_recording = False
            if self.record_writer:
                self.record_writer.release()
                self.record_writer = None

            self.btn_rec_toggle.setText("🔴 شروع ضبط مجدد")
            self.btn_rec_toggle.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px 24px; background-color: #e53935; color: white; border-radius: 6px;")
            self.lbl_rec_timer.setText("✅ ضبط به پایان رسید. در حال انتقال به ویرایشگر...")

            self.stop_camera()
            # Switch to Video Editor Tab (Index 3)
            if os.path.exists(self.record_temp_path) and os.path.getsize(self.record_temp_path) > 1000:
                self.load_video_for_editing(self.record_temp_path)
                self.tabs.setCurrentIndex(3)
            else:
                QMessageBox.warning(self, "خطا", "فایل ویدیویی به درستی ضبط نشد.")

    def stop_camera(self):
        if self.cam_timer.isActive():
            self.cam_timer.stop()
        if self.cam_cap:
            try:
                self.cam_cap.release()
            except Exception:
                pass
            self.cam_cap = None

    # -------------------------------------------------------------------------
    # Video Editor & Player Engine
    # -------------------------------------------------------------------------
    def load_video_for_editing(self, path: str):
        self.current_video_path = path
        if self.edit_timer.isActive():
            self.edit_timer.stop()
        if self.edit_cap:
            self.edit_cap.release()

        self.edit_cap = cv2.VideoCapture(path)
        if not self.edit_cap.isOpened():
            QMessageBox.critical(self, "خطا", f"امکان بازگشایی ویدیوی {os.path.basename(path)} وجود ندارد.")
            return

        self.total_frames = int(self.edit_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.edit_cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps <= 0 or np.isnan(self.video_fps):
            self.video_fps = 30.0
        self.src_w = int(self.edit_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.src_h = int(self.edit_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_duration = self.total_frames / self.video_fps if self.total_frames > 0 else 0.0

        # Configure sliders and spinboxes
        self.slider_timeline.setRange(0, max(0, self.total_frames - 1))
        self.slider_timeline.setValue(0)

        self.spin_start.blockSignals(True)
        self.spin_end.blockSignals(True)
        self.spin_start.setRange(0.0, self.video_duration)
        self.spin_start.setValue(0.0)
        self.spin_end.setRange(0.0, self.video_duration)
        self.spin_end.setValue(round(self.video_duration, 1))
        self.spin_start.blockSignals(False)
        self.spin_end.blockSignals(False)

        # Limits for crop
        self.spin_crop_top.setMaximum(self.src_h // 2 if self.src_h > 0 else 500)
        self.spin_crop_bottom.setMaximum(self.src_h // 2 if self.src_h > 0 else 500)
        self.spin_crop_left.setMaximum(self.src_w // 2 if self.src_w > 0 else 500)
        self.spin_crop_right.setMaximum(self.src_w // 2 if self.src_w > 0 else 500)

        self.rotation_angle = 0
        self.is_flipped_h = False
        self.selected_poster_frame_idx = 0
        self.seek_frame(0)
        self.update_poster_preview()

    def toggle_playback(self):
        if self.is_playing:
            self.edit_timer.stop()
            self.is_playing = False
            self.btn_play.setText("▶️ پخش")
            if hasattr(self, "chk_auto_poster") and self.chk_auto_poster.isChecked():
                self.selected_poster_frame_idx = self.current_frame_idx
                self.update_poster_preview()
        else:
            if not self.edit_cap or not self.edit_cap.isOpened():
                return
            interval = int(1000.0 / self.video_fps) if self.video_fps > 0 else 33
            self.edit_timer.setInterval(max(15, interval))
            self.edit_timer.start()
            self.is_playing = True
            self.btn_play.setText("⏸️ توقف")

    def _on_playback_tick(self):
        if not self.edit_cap or not self.edit_cap.isOpened():
            return
        next_idx = self.current_frame_idx + 1
        if next_idx >= self.total_frames:
            # Loop playback
            next_idx = 0
        self.seek_frame(next_idx)

    def seek_frame(self, frame_idx: int):
        if not self.edit_cap or not self.edit_cap.isOpened():
            return
        frame_idx = max(0, min(self.total_frames - 1, frame_idx))
        self.current_frame_idx = frame_idx
        self.edit_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.edit_cap.read()
        if ret and frame is not None:
            self._render_editor_frame(frame)

        self.slider_timeline.blockSignals(True)
        self.slider_timeline.setValue(frame_idx)
        self.slider_timeline.blockSignals(False)

        cur_sec = frame_idx / self.video_fps if self.video_fps > 0 else 0.0
        self.lbl_time.setText(f"{cur_sec:04.1f}s / {self.video_duration:04.1f}s")

    def _render_editor_frame(self, frame):
        # Rotation
        if self.rotation_angle == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_angle == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation_angle == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Flip
        if self.is_flipped_h:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        top_m = self.spin_crop_top.value()
        bot_m = self.spin_crop_bottom.value()
        left_m = self.spin_crop_left.value()
        right_m = self.spin_crop_right.value()

        show_cropped = self.chk_show_cropped_direct.isChecked()
        if show_cropped:
            c_top = min(top_m, h - 20)
            c_bot = h - bot_m if h - bot_m > c_top + 20 else h
            c_left = min(left_m, w - 20)
            c_right = w - right_m if w - right_m > c_left + 20 else w
            frame = frame[c_top:c_bot, c_left:c_right]
            h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()

        self.video_player.set_frame(
            qimg,
            source_w=w,
            source_h=h,
            margins=(top_m, bot_m, left_m, right_m),
            show_cropped_only=show_cropped
        )

    def step_frames(self, offset: int):
        self.seek_frame(self.current_frame_idx + offset)
        if hasattr(self, "chk_auto_poster") and self.chk_auto_poster.isChecked() and not self.is_playing:
            self.selected_poster_frame_idx = self.current_frame_idx
            self.update_poster_preview()

    def rotate_video(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.seek_frame(self.current_frame_idx)
        self.update_poster_preview()

    def flip_video(self):
        self.is_flipped_h = not self.is_flipped_h
        self.seek_frame(self.current_frame_idx)
        self.update_poster_preview()

    def _on_slider_moved(self, val: int):
        self.seek_frame(val)
        if hasattr(self, "chk_auto_poster") and self.chk_auto_poster.isChecked():
            self.selected_poster_frame_idx = val
            self.update_poster_preview()

    def _on_slider_pressed(self):
        if self.is_playing:
            self.edit_timer.stop()

    def _on_slider_released(self):
        if self.is_playing:
            self.edit_timer.start()
        elif hasattr(self, "chk_auto_poster") and self.chk_auto_poster.isChecked():
            self.selected_poster_frame_idx = self.current_frame_idx
            self.update_poster_preview()

    def _set_start_current(self):
        cur_sec = self.current_frame_idx / self.video_fps if self.video_fps > 0 else 0.0
        self.spin_start.setValue(round(cur_sec, 1))

    def _set_end_current(self):
        cur_sec = self.current_frame_idx / self.video_fps if self.video_fps > 0 else 0.0
        self.spin_end.setValue(round(cur_sec, 1))

    def _on_trim_changed(self):
        if self.spin_start.value() > self.spin_end.value():
            # Keep consistent
            pass
        self._update_trim_explanation()

    def _on_mode_toggled(self, checked: bool):
        self._update_trim_explanation()

    def _update_trim_explanation(self):
        s = self.spin_start.value()
        e = self.spin_end.value()
        if self.chk_delete_interval.isChecked():
            self.lbl_trim_explanation.setText(f"✂️ بازه {s:.1f} تا {e:.1f} ثانیه از فیلم حذف و ابتدا و انتهای آن به هم وصل می‌شود.")
            self.lbl_trim_explanation.setStyleSheet("font-size: 11px; color: #ffab40;")
        else:
            self.lbl_trim_explanation.setText(f"🟢 فقط بازه {s:.1f} تا {e:.1f} ثانیه حفظ شده و ثانیه‌های قبل/بعد حذف می‌شوند.")
            self.lbl_trim_explanation.setStyleSheet("font-size: 11px; color: #81c784;")

    def _on_crop_changed(self):
        self.seek_frame(self.current_frame_idx)
        self.update_poster_preview()

    def reset_crop_margins(self):
        self.spin_crop_top.setValue(0)
        self.spin_crop_bottom.setValue(0)
        self.spin_crop_left.setValue(0)
        self.spin_crop_right.setValue(0)
        self.update_poster_preview()

    def _on_set_poster_current(self):
        self.selected_poster_frame_idx = self.current_frame_idx
        self.update_poster_preview()
        cur_sec = self.current_frame_idx / self.video_fps if self.video_fps > 0 else 0.0
        self.lbl_poster_info.setText(f"✅ ثبت شد: {cur_sec:04.1f}s")

    def _get_transformed_frame_at(self, frame_idx: int):
        if not self.edit_cap or not self.edit_cap.isOpened():
            return None
        frame_idx = max(0, min(self.total_frames - 1, frame_idx))
        pos = self.edit_cap.get(cv2.CAP_PROP_POS_FRAMES)
        self.edit_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.edit_cap.read()
        self.edit_cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        if not ret or frame is None:
            return None

        # Apply rotation
        if self.rotation_angle == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_angle == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation_angle == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Apply flip
        if self.is_flipped_h:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        top_m = self.spin_crop_top.value()
        bot_m = self.spin_crop_bottom.value()
        left_m = self.spin_crop_left.value()
        right_m = self.spin_crop_right.value()

        c_top = min(top_m, h - 20)
        c_bot = h - bot_m if h - bot_m > c_top + 20 else h
        c_left = min(left_m, w - 20)
        c_right = w - right_m if w - right_m > c_left + 20 else w
        cropped = frame[c_top:c_bot, c_left:c_right]
        return cropped

    def update_poster_preview(self):
        if not hasattr(self, "lbl_poster_preview"):
            return
        frame = self._get_transformed_frame_at(self.selected_poster_frame_idx)
        if frame is None or frame.size == 0:
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(
            self.lbl_poster_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_poster_preview.setPixmap(scaled)

        cur_sec = self.selected_poster_frame_idx / self.video_fps if self.video_fps > 0 else 0.0
        self.lbl_poster_info.setText(f"ثانیه {cur_sec:04.1f}s (فریم {self.selected_poster_frame_idx})")

    def _on_tab_changed(self, idx: int):
        if idx in (0, 1):
            # Switched to Camera tabs (Video or Photo)
            if self.is_playing:
                self.toggle_playback()
            if not self.cam_cap or not self.cam_cap.isOpened():
                self.detect_and_start_camera()
            elif not self.cam_timer.isActive():
                self.cam_timer.start()
        elif idx == 2:
            # Switched to Photo Editor tab
            self.stop_camera()
            if self.is_playing:
                self.toggle_playback()
        elif idx == 3:
            # Switched to Video Editor tab
            self.stop_camera()
            if self.current_video_path and os.path.exists(self.current_video_path):
                if not self.edit_cap or not self.edit_cap.isOpened():
                    self.load_video_for_editing(self.current_video_path)

    def on_retake_clicked(self):
        # Pause editor and switch back to camera
        reply = QMessageBox.question(
            self,
            "ضبط مجدد ویدیو",
            "آیا مایل به ضبط مجدد ویدیو با دوربین هستید؟ تغییرات ویدیوی فعلی ذخیره نخواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.is_playing:
                self.toggle_playback()
            self.tabs.setCurrentIndex(0)
            self.detect_and_start_camera()

    # -------------------------------------------------------------------------
    # Final Video Processing & Saving Engine
    # -------------------------------------------------------------------------
    def process_and_save_video(self):
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            QMessageBox.warning(self, "خطا", "ویدیویی جهت پردازش و ذخیره بارگذاری نشده است.")
            return

        if self.is_playing:
            self.toggle_playback()

        start_sec = self.spin_start.value()
        end_sec = self.spin_end.value()
        if start_sec >= end_sec and not self.chk_delete_interval.isChecked():
            QMessageBox.warning(self, "خطا در برش زمانی", "ثانیه شروع باید کمتر از ثانیه پایان باشد.")
            return

        # Prepare output destination in EXERCISE_MEDIA_DIR
        out_dir = config.EXERCISE_MEDIA_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        orig_stem = ""
        if getattr(self, "current_video_path", None) and os.path.exists(self.current_video_path):
            orig_stem = Path(self.current_video_path).stem
            while orig_stem.endswith("_edited"):
                orig_stem = orig_stem[:-7]

        clean_title = ""
        if getattr(self, "exercise_title", None):
            clean_title = re.sub(r'[^\w\d_\-\.\u0600-\u06FF]', '_', self.exercise_title.strip()).strip('_')

        if clean_title:
            base_name = f"{clean_title}_edited"
        elif orig_stem and not orig_stem.startswith("recorded_raw_") and not orig_stem.startswith("temp_"):
            base_name = f"{orig_stem}_edited"
        else:
            base_name = f"exercise_video_{int(time.time())}"

        filename = f"{base_name}.mp4"
        if (out_dir / filename).exists():
            filename = f"{base_name}_{int(time.time())}.mp4"
        out_path = str(out_dir / filename)

        # Progress Dialog
        progress = QProgressDialog("در حال پردازش و برش ویدیو... لطفاً شکیبا باشید", "لغو", 0, self.total_frames, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        cap = cv2.VideoCapture(self.current_video_path)
        if not cap.isOpened():
            QMessageBox.critical(self, "خطا", "خطا در خواندن فایل ویدیویی جهت رندر نهایی.")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or np.isnan(fps):
            fps = 30.0

        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            cap.release()
            QMessageBox.critical(self, "خطا", "فریم‌های ویدیو قابل خواندن نیستند.")
            return

        # Calculate transformed & cropped frame dimensions
        if self.rotation_angle in (90, 270):
            test_frame = cv2.rotate(test_frame, cv2.ROTATE_90_CLOCKWISE)
        orig_h, orig_w = test_frame.shape[:2]

        top_m = self.spin_crop_top.value()
        bot_m = self.spin_crop_bottom.value()
        left_m = self.spin_crop_left.value()
        right_m = self.spin_crop_right.value()

        c_top = min(top_m, orig_h - 20)
        c_bot = orig_h - bot_m if orig_h - bot_m > c_top + 20 else orig_h
        c_left = min(left_m, orig_w - 20)
        c_right = orig_w - right_m if orig_w - right_m > c_left + 20 else orig_w

        out_w = c_right - c_left
        out_h = c_bot - c_top
        # Ensure dimensions are even numbers for codec stability
        out_w = out_w - (out_w % 2)
        out_h = out_h - (out_h % 2)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (out_w, out_h))
        if not writer.isOpened():
            cap.release()
            QMessageBox.critical(self, "خطا", "عدم امکان ساخت فایل خروجی با کدک mp4v.")
            return

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_idx = 0
        written_count = 0
        delete_interval_mode = self.chk_delete_interval.isChecked()

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if progress.wasCanceled():
                    break

                t = frame_idx / fps

                # Filter frame based on trimming logic
                keep_frame = False
                if delete_interval_mode:
                    # Cut out [start_sec, end_sec] segment from the middle!
                    if t < start_sec or t > end_sec:
                        keep_frame = True
                else:
                    # Normal trim: keep only [start_sec, end_sec]
                    if start_sec <= t <= end_sec:
                        keep_frame = True

                if keep_frame:
                    # Apply rotation
                    if self.rotation_angle == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif self.rotation_angle == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif self.rotation_angle == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

                    # Apply flip
                    if self.is_flipped_h:
                        frame = cv2.flip(frame, 1)

                    # Apply crop
                    cropped = frame[c_top:c_top + out_h, c_left:c_left + out_w]
                    writer.write(cropped)
                    written_count += 1

                frame_idx += 1
                if frame_idx % 10 == 0:
                    progress.setValue(frame_idx)

            progress.setValue(self.total_frames)
        finally:
            cap.release()
            writer.release()

        if progress.wasCanceled() or written_count == 0:
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except Exception:
                    pass
            if written_count == 0 and not progress.wasCanceled():
                QMessageBox.warning(self, "خطا", "هیچ فریمی در بازه زمانی تعیین‌شده جهت ذخیره یافت نشد.")
            return

        # Convert to web-standard H.264 MP4 with faststart for universal web & mobile playback
        try:
            import subprocess
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            h264_temp = out_path + ".h264.mp4"
            cmd = [
                ffmpeg_exe, "-y",
                "-i", out_path,
                "-c:v", "libx264",
                "-r", "30",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-an",
                h264_temp
            ]
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            res = subprocess.run(cmd, capture_output=True, creationflags=flags)
            if res.returncode == 0 and os.path.exists(h264_temp) and os.path.getsize(h264_temp) > 0:
                os.replace(h264_temp, out_path)
        except Exception:
            pass

        # Generate thumbnail for the chosen poster frame (exact frame selected by trainer)
        poster_bgr = self._get_transformed_frame_at(self.selected_poster_frame_idx)
        thumb_path = None
        if poster_bgr is not None and poster_bgr.size > 0:
            thumb_filename = f"thumb_{Path(out_path).stem}.jpg"
            thumb_path = str(out_dir / thumb_filename)
            try:
                success, enc_buffer = cv2.imencode(".jpg", poster_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                if success:
                    with open(thumb_path, "wb") as f:
                        f.write(enc_buffer.tobytes())
                else:
                    cv2.imwrite(thumb_path, poster_bgr)
            except Exception:
                thumb_path = None

        if not thumb_path or not os.path.exists(thumb_path):
            thumb_path = extract_video_thumbnail(out_path)

        self.result_video_path = out_path
        self.result_thumbnail_path = thumb_path
        self.result_media_type = "video"
        self.stop_camera()
        if self.edit_cap:
            self.edit_cap.release()
        self.accept()

    def closeEvent(self, event):
        self.stop_camera()
        if self.edit_cap:
            self.edit_cap.release()
        super().closeEvent(event)

    def reject(self):
        self.stop_camera()
        if self.edit_cap:
            self.edit_cap.release()
        super().reject()
