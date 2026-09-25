import os
import tempfile
import time
import uuid
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QSlider, QCheckBox, QGroupBox, QMessageBox, QWidget,
    QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QImage, QCursor, QGuiApplication
)
import config


def pil_to_pixmap(pil_img: Image.Image) -> QPixmap:
    """Safely converts a PIL Image to a PyQt6 QPixmap."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    data = pil_img.tobytes("raw", "RGB")
    qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class CropCanvas(QWidget):
    """
    Interactive canvas displaying an image with an overlay crop rectangle.
    Supports dragging corners/edges, moving crop box, and rule-of-thirds grid.
    """
    cropChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.original_pixmap = QPixmap()
        self.crop_norm = QRectF(0.0, 0.0, 1.0, 1.0)  # Normalized 0..1 relative to original image
        self.aspect_ratio: float | None = None  # None = Free crop, 1.0 = Square, etc.

        # Interaction state
        self._dragging_mode = None  # None, 'move', 'tl', 'tr', 'bl', 'br', 't', 'b', 'l', 'r'
        self._drag_start_pos = None
        self._drag_start_rect = None
        self._handle_size = 12

    def set_pixmap(self, pixmap: QPixmap, reset_crop: bool = False):
        self.original_pixmap = pixmap
        if reset_crop:
            self.reset_crop()
        self.cropChanged.emit()
        self.update()

    def reset_crop(self):
        if self.original_pixmap.isNull():
            self.crop_norm = QRectF(0.0, 0.0, 1.0, 1.0)
            self.cropChanged.emit()
            self.update()
            return

        w = self.original_pixmap.width()
        h = self.original_pixmap.height()

        if self.aspect_ratio is not None and self.aspect_ratio > 0:
            img_ratio = w / h
            target_ratio = self.aspect_ratio
            if img_ratio > target_ratio:
                target_w = h * target_ratio
                norm_w = max(0.01, min(1.0, target_w / w))
                self.crop_norm = QRectF((1.0 - norm_w) / 2.0, 0.0, norm_w, 1.0)
            else:
                target_h = w / target_ratio
                norm_h = max(0.01, min(1.0, target_h / h))
                self.crop_norm = QRectF(0.0, (1.0 - norm_h) / 2.0, 1.0, norm_h)
        else:
            self.crop_norm = QRectF(0.0, 0.0, 1.0, 1.0)

        self.cropChanged.emit()
        self.update()

    def set_aspect_ratio(self, ratio: float | None):
        self.aspect_ratio = ratio
        self.reset_crop()

    def set_square_locked(self, locked: bool):
        self.set_aspect_ratio(1.0 if locked else None)

    @property
    def is_square_locked(self) -> bool:
        return self.aspect_ratio == 1.0

    def get_image_display_rect(self) -> QRectF:
        if self.original_pixmap.isNull():
            return QRectF()
        widget_w = self.width()
        widget_h = self.height()
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()

        scale = min(widget_w / img_w, widget_h / img_h)
        scaled_w = img_w * scale
        scaled_h = img_h * scale

        offset_x = (widget_w - scaled_w) / 2.0
        offset_y = (widget_h - scaled_h) / 2.0
        return QRectF(offset_x, offset_y, scaled_w, scaled_h)

    def norm_to_widget_rect(self, norm_rect: QRectF) -> QRectF:
        disp_rect = self.get_image_display_rect()
        return QRectF(
            disp_rect.left() + norm_rect.left() * disp_rect.width(),
            disp_rect.top() + norm_rect.top() * disp_rect.height(),
            norm_rect.width() * disp_rect.width(),
            norm_rect.height() * disp_rect.height()
        )

    def widget_to_norm_rect(self, widget_rect: QRectF) -> QRectF:
        disp_rect = self.get_image_display_rect()
        if disp_rect.width() <= 0 or disp_rect.height() <= 0:
            return QRectF(0, 0, 1, 1)
        norm_x = (widget_rect.left() - disp_rect.left()) / disp_rect.width()
        norm_y = (widget_rect.top() - disp_rect.top()) / disp_rect.height()
        norm_w = widget_rect.width() / disp_rect.width()
        norm_h = widget_rect.height() / disp_rect.height()

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        norm_w = max(0.01, min(1.0 - norm_x, norm_w))
        norm_h = max(0.01, min(1.0 - norm_y, norm_h))
        return QRectF(norm_x, norm_y, norm_w, norm_h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#121212"))

        if self.original_pixmap.isNull():
            painter.setPen(QColor("#777777"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "تصویری جهت نمایش موجود نیست")
            return

        disp_rect = self.get_image_display_rect()
        painter.drawPixmap(disp_rect.toRect(), self.original_pixmap)

        crop_w_rect = self.norm_to_widget_rect(self.crop_norm)
        overlay_color = QColor(0, 0, 0, 160)

        painter.fillRect(QRectF(disp_rect.left(), disp_rect.top(), disp_rect.width(), crop_w_rect.top() - disp_rect.top()), overlay_color)
        painter.fillRect(QRectF(disp_rect.left(), crop_w_rect.bottom(), disp_rect.width(), disp_rect.bottom() - crop_w_rect.bottom()), overlay_color)
        painter.fillRect(QRectF(disp_rect.left(), crop_w_rect.top(), crop_w_rect.left() - disp_rect.left(), crop_w_rect.height()), overlay_color)
        painter.fillRect(QRectF(crop_w_rect.right(), crop_w_rect.top(), disp_rect.right() - crop_w_rect.right(), crop_w_rect.height()), overlay_color)

        border_pen = QPen(QColor("#00E5FF"), 2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_w_rect)

        grid_pen = QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        w3 = crop_w_rect.width() / 3.0
        h3 = crop_w_rect.height() / 3.0
        painter.drawLine(QPointF(crop_w_rect.left() + w3, crop_w_rect.top()), QPointF(crop_w_rect.left() + w3, crop_w_rect.bottom()))
        painter.drawLine(QPointF(crop_w_rect.left() + 2 * w3, crop_w_rect.top()), QPointF(crop_w_rect.left() + 2 * w3, crop_w_rect.bottom()))
        painter.drawLine(QPointF(crop_w_rect.left(), crop_w_rect.top() + h3), QPointF(crop_w_rect.right(), crop_w_rect.top() + h3))
        painter.drawLine(QPointF(crop_w_rect.left(), crop_w_rect.top() + 2 * h3), QPointF(crop_w_rect.right(), crop_w_rect.top() + 2 * h3))

        handle_brush = QBrush(QColor("#00E5FF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(handle_brush)
        hs = self._handle_size
        cx = crop_w_rect.center().x()
        cy = crop_w_rect.center().y()
        handles = [
            crop_w_rect.topLeft(),
            crop_w_rect.topRight(),
            crop_w_rect.bottomLeft(),
            crop_w_rect.bottomRight(),
            QPointF(cx, crop_w_rect.top()),
            QPointF(cx, crop_w_rect.bottom()),
            QPointF(crop_w_left := crop_w_rect.left(), cy),
            QPointF(crop_w_right := crop_w_rect.right(), cy)
        ]
        for c in handles:
            painter.drawRect(QRectF(c.x() - hs / 2, c.y() - hs / 2, hs, hs))

    def _hit_test(self, pos: QPointF):
        crop_w_rect = self.norm_to_widget_rect(self.crop_norm)
        hs = self._handle_size + 4

        if QRectF(crop_w_rect.left() - hs, crop_w_rect.top() - hs, hs * 2, hs * 2).contains(pos):
            return 'tl'
        if QRectF(crop_w_rect.right() - hs, crop_w_rect.top() - hs, hs * 2, hs * 2).contains(pos):
            return 'tr'
        if QRectF(crop_w_rect.left() - hs, crop_w_rect.bottom() - hs, hs * 2, hs * 2).contains(pos):
            return 'bl'
        if QRectF(crop_w_rect.right() - hs, crop_w_rect.bottom() - hs, hs * 2, hs * 2).contains(pos):
            return 'br'

        cx = crop_w_rect.center().x()
        cy = crop_w_rect.center().y()
        if QRectF(cx - hs, crop_w_rect.top() - hs, hs * 2, hs * 2).contains(pos):
            return 't'
        if QRectF(cx - hs, crop_w_rect.bottom() - hs, hs * 2, hs * 2).contains(pos):
            return 'b'
        if QRectF(crop_w_rect.left() - hs, cy - hs, hs * 2, hs * 2).contains(pos):
            return 'l'
        if QRectF(crop_w_rect.right() - hs, cy - hs, hs * 2, hs * 2).contains(pos):
            return 'r'

        if crop_w_rect.contains(pos):
            return 'move'

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            hit = self._hit_test(pos)
            if hit:
                self._dragging_mode = hit
                self._drag_start_pos = pos
                self._drag_start_rect = self.norm_to_widget_rect(self.crop_norm)
            else:
                disp_rect = self.get_image_display_rect()
                if disp_rect.contains(pos):
                    self._dragging_mode = 'br'
                    self._drag_start_pos = pos
                    new_rect = QRectF(pos.x(), pos.y(), 10, 10)
                    self.crop_norm = self.widget_to_norm_rect(new_rect)
                    self._drag_start_rect = new_rect
                    self.cropChanged.emit()
                    self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        if not self._dragging_mode:
            hit = self._hit_test(pos)
            if hit in ('tl', 'br'):
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            elif hit in ('tr', 'bl'):
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            elif hit in ('t', 'b'):
                self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
            elif hit in ('l', 'r'):
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            elif hit == 'move':
                self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            return

        disp_rect = self.get_image_display_rect()
        dx = pos.x() - self._drag_start_pos.x()
        dy = pos.y() - self._drag_start_pos.y()
        r = QRectF(self._drag_start_rect)

        if self._dragging_mode == 'move':
            r.translate(dx, dy)
            if r.left() < disp_rect.left():
                r.moveLeft(disp_rect.left())
            if r.right() > disp_rect.right():
                r.moveRight(disp_rect.right())
            if r.top() < disp_rect.top():
                r.moveTop(disp_rect.top())
            if r.bottom() > disp_rect.bottom():
                r.moveBottom(disp_rect.bottom())
        elif self._dragging_mode == 'tl':
            new_left = min(r.right() - 20, max(disp_rect.left(), r.left() + dx))
            new_top = min(r.bottom() - 20, max(disp_rect.top(), r.top() + dy))
            if self.aspect_ratio is not None and self.aspect_ratio > 0:
                side_w = r.right() - new_left
                side_h = side_w / self.aspect_ratio
                new_top = r.bottom() - side_h
            r.setLeft(new_left)
            r.setTop(new_top)
        elif self._dragging_mode == 'tr':
            new_right = max(r.left() + 20, min(disp_rect.right(), r.right() + dx))
            new_top = min(r.bottom() - 20, max(disp_rect.top(), r.top() + dy))
            if self.aspect_ratio is not None and self.aspect_ratio > 0:
                side_w = new_right - r.left()
                side_h = side_w / self.aspect_ratio
                new_top = r.bottom() - side_h
            r.setRight(new_right)
            r.setTop(new_top)
        elif self._dragging_mode == 'bl':
            new_left = min(r.right() - 20, max(disp_rect.left(), r.left() + dx))
            new_bottom = max(r.top() + 20, min(disp_rect.bottom(), r.bottom() + dy))
            if self.aspect_ratio is not None and self.aspect_ratio > 0:
                side_w = r.right() - new_left
                side_h = side_w / self.aspect_ratio
                new_bottom = r.top() + side_h
            r.setLeft(new_left)
            r.setBottom(new_bottom)
        elif self._dragging_mode == 'br':
            new_right = max(r.left() + 20, min(disp_rect.right(), r.right() + dx))
            new_bottom = max(r.top() + 20, min(disp_rect.bottom(), r.bottom() + dy))
            if self.aspect_ratio is not None and self.aspect_ratio > 0:
                side_w = new_right - r.left()
                side_h = side_w / self.aspect_ratio
                new_bottom = r.top() + side_h
            r.setRight(new_right)
            r.setBottom(new_bottom)
        elif self._dragging_mode in ('t', 'b'):
            if self._dragging_mode == 't':
                new_top = min(r.bottom() - 20, max(disp_rect.top(), r.top() + dy))
                r.setTop(new_top)
            else:
                new_bottom = max(r.top() + 20, min(disp_rect.bottom(), r.bottom() + dy))
                r.setBottom(new_bottom)
        elif self._dragging_mode in ('l', 'r'):
            if self._dragging_mode == 'l':
                new_left = min(r.right() - 20, max(disp_rect.left(), r.left() + dx))
                r.setLeft(new_left)
            else:
                new_right = max(r.left() + 20, min(disp_rect.right(), r.right() + dx))
                r.setRight(new_right)

        self.crop_norm = self.widget_to_norm_rect(r)
        self.cropChanged.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging_mode = None
        self._drag_start_pos = None
        self._drag_start_rect = None


class ImageEditorDialog(QDialog):
    """
    Advanced interactive image editor dialog.
    Provides visual cropping, aspect ratio presets (Free, 1:1, 4:3, 16:9, 9:16),
    90-degree rotations, horizontal/vertical flipping, image adjustments
    (Brightness, Contrast, Saturation, Sharpness), and retake/repick options.
    Screen-aware responsive geometry prevents taskbar collision.
    """
    retake_requested = pyqtSignal()

    def __init__(self, parent=None, image_path: str = None, title: str = "ویرایش و بهینه‌سازی تصویر", allow_retake: bool = False, is_square_default: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # Dynamic screen-aware sizing
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if avail:
            target_w = min(1060, max(780, int(avail.width() * 0.90)))
            target_h = min(660, max(460, int(avail.height() * 0.88)))
            self.resize(target_w, target_h)
            self.setMinimumSize(740, 440)
            self.move(avail.x() + (avail.width() - target_w) // 2, avail.y() + (avail.height() - target_h) // 2)
        else:
            self.resize(900, 600)
            self.setMinimumSize(740, 440)

        self.original_input_path = image_path
        self.allow_retake = allow_retake
        self.result_image_path = None
        self.retake_triggered = False

        # Image state
        self.original_pil_image: Image.Image = None
        self.transformed_pil_image: Image.Image = None
        self.display_pil_image: Image.Image = None

        if image_path and os.path.exists(image_path):
            try:
                loaded = Image.open(image_path)
                if loaded.mode != "RGB":
                    loaded = loaded.convert("RGB")
                self.original_pil_image = loaded.copy()
                self.transformed_pil_image = loaded.copy()
            except Exception:
                self.original_pil_image = None
                self.transformed_pil_image = None

        self.init_ui(is_square_default)
        self.apply_adjustments(reset_crop=True)

    def init_ui(self, is_square_default: bool):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # Left/Center: Interactive Canvas
        self.canvas = CropCanvas(self)
        self.canvas.cropChanged.connect(self.sync_dimensions_label)
        if is_square_default:
            self.canvas.set_aspect_ratio(1.0)
        main_layout.addWidget(self.canvas, stretch=5)

        # Right sidebar: Editing controls inside a clean scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setSpacing(10)
        panel_layout.setContentsMargins(0, 0, 4, 0)

        # ====================================================================
        # 1. Crop & Aspect Ratio Presets
        # ====================================================================
        group_crop = QGroupBox("تنظیمات کادر و نسبت ابعاد (Crop)")
        group_crop.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_crop = QVBoxLayout(group_crop)
        vbox_crop.setSpacing(6)

        grid_ratios = QHBoxLayout()
        grid_ratios.setSpacing(4)

        self.btn_ratio_free = QPushButton("آزاد")
        self.btn_ratio_free.setToolTip("برش دلخواه بدون محدودیت نسبت ابعاد")
        self.btn_ratio_free.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_ratio_free.clicked.connect(lambda: self.set_preset_aspect_ratio(None))

        self.btn_ratio_1_1 = QPushButton("۱:۱ (مربع)")
        self.btn_ratio_1_1.setToolTip("کادر مربع ۱:۱ مناسب پروفایل و تصویر حرکت")
        self.btn_ratio_1_1.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_ratio_1_1.clicked.connect(lambda: self.set_preset_aspect_ratio(1.0))

        self.btn_ratio_4_3 = QPushButton("۴:۳")
        self.btn_ratio_4_3.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_ratio_4_3.clicked.connect(lambda: self.set_preset_aspect_ratio(4.0 / 3.0))

        self.btn_ratio_16_9 = QPushButton("۱۶:۹")
        self.btn_ratio_16_9.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_ratio_16_9.clicked.connect(lambda: self.set_preset_aspect_ratio(16.0 / 9.0))

        self.btn_ratio_9_16 = QPushButton("۹:۱۶")
        self.btn_ratio_9_16.setStyleSheet("font-size: 11px; padding: 5px;")
        self.btn_ratio_9_16.clicked.connect(lambda: self.set_preset_aspect_ratio(9.0 / 16.0))

        grid_ratios.addWidget(self.btn_ratio_free)
        grid_ratios.addWidget(self.btn_ratio_1_1)
        grid_ratios.addWidget(self.btn_ratio_4_3)
        grid_ratios.addWidget(self.btn_ratio_16_9)
        grid_ratios.addWidget(self.btn_ratio_9_16)
        vbox_crop.addLayout(grid_ratios)

        btn_reset_crop = QPushButton("↺ بازنشانی کادر به تمام تصویر")
        btn_reset_crop.setObjectName("secondary_button")
        btn_reset_crop.setStyleSheet("font-size: 11px; padding: 5px; color: #BBDEFB;")
        btn_reset_crop.clicked.connect(self.canvas.reset_crop)
        vbox_crop.addWidget(btn_reset_crop)

        self.lbl_dims = QLabel("ابعاد انتخابی: -")
        self.lbl_dims.setStyleSheet("font-size: 11px; color: #00E5FF; font-weight: bold;")
        vbox_crop.addWidget(self.lbl_dims)

        panel_layout.addWidget(group_crop)

        # ====================================================================
        # 2. Transformations (Rotate & Flip)
        # ====================================================================
        group_trans = QGroupBox("چرخش و قرینه‌سازی (Transform)")
        group_trans.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_trans = QVBoxLayout(group_trans)
        vbox_trans.setSpacing(6)

        row_rot = QHBoxLayout()
        btn_rot_cw = QPushButton("↷ چرخش ۹۰°")
        btn_rot_cw.setToolTip("چرخش ۹۰ درجه ساعت‌گرد")
        btn_rot_cw.setStyleSheet("font-size: 11px; padding: 6px;")
        btn_rot_cw.clicked.connect(lambda: self.transform_image("rot_cw"))

        btn_rot_ccw = QPushButton("↶ چرخش ۹۰°-")
        btn_rot_ccw.setToolTip("چرخش ۹۰ درجه پادساعت‌گرد")
        btn_rot_ccw.setStyleSheet("font-size: 11px; padding: 6px;")
        btn_rot_ccw.clicked.connect(lambda: self.transform_image("rot_ccw"))

        row_rot.addWidget(btn_rot_cw)
        row_rot.addWidget(btn_rot_ccw)
        vbox_trans.addLayout(row_rot)

        row_flip = QHBoxLayout()
        btn_flip_h = QPushButton("↔️ آینه افقی")
        btn_flip_h.setStyleSheet("font-size: 11px; padding: 6px;")
        btn_flip_h.clicked.connect(lambda: self.transform_image("flip_h"))

        btn_flip_v = QPushButton("↕️ آینه عمودی")
        btn_flip_v.setStyleSheet("font-size: 11px; padding: 6px;")
        btn_flip_v.clicked.connect(lambda: self.transform_image("flip_v"))

        row_flip.addWidget(btn_flip_h)
        row_flip.addWidget(btn_flip_v)
        vbox_trans.addLayout(row_flip)

        panel_layout.addWidget(group_trans)

        # ====================================================================
        # 3. Image Adjustments (Brightness, Contrast, Color, Sharpness)
        # ====================================================================
        group_adj = QGroupBox("تنظیمات نور و رنگ (Adjustments)")
        group_adj.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; color: #E0E0E0; }")
        vbox_adj = QVBoxLayout(group_adj)
        vbox_adj.setSpacing(6)

        # Brightness
        row_b = QHBoxLayout()
        lbl_b = QLabel("روشنایی:")
        lbl_b.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(50, 150)
        self.slider_brightness.setValue(100)
        self.lbl_b_val = QLabel("۱۰۰٪")
        self.lbl_b_val.setStyleSheet("font-size: 11px; min-width: 40px; color: #AAA;")
        self.slider_brightness.valueChanged.connect(self.on_adjustment_changed)
        row_b.addWidget(lbl_b)
        row_b.addWidget(self.slider_brightness)
        row_b.addWidget(self.lbl_b_val)
        vbox_adj.addLayout(row_b)

        # Contrast
        row_c = QHBoxLayout()
        lbl_c = QLabel("کنتراست:")
        lbl_c.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_contrast.setRange(50, 150)
        self.slider_contrast.setValue(100)
        self.lbl_c_val = QLabel("۱۰۰٪")
        self.lbl_c_val.setStyleSheet("font-size: 11px; min-width: 40px; color: #AAA;")
        self.slider_contrast.valueChanged.connect(self.on_adjustment_changed)
        row_c.addWidget(lbl_c)
        row_c.addWidget(self.slider_contrast)
        row_c.addWidget(self.lbl_c_val)
        vbox_adj.addLayout(row_c)

        # Saturation / Color
        row_s = QHBoxLayout()
        lbl_s = QLabel("اشباع رنگ:")
        lbl_s.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_color = QSlider(Qt.Orientation.Horizontal)
        self.slider_color.setRange(0, 200)
        self.slider_color.setValue(100)
        self.lbl_s_val = QLabel("۱۰۰٪")
        self.lbl_s_val.setStyleSheet("font-size: 11px; min-width: 40px; color: #AAA;")
        self.slider_color.valueChanged.connect(self.on_adjustment_changed)
        row_s.addWidget(lbl_s)
        row_s.addWidget(self.slider_color)
        row_s.addWidget(self.lbl_s_val)
        vbox_adj.addLayout(row_s)

        # Sharpness
        row_sh = QHBoxLayout()
        lbl_sh = QLabel("وضوح:")
        lbl_sh.setStyleSheet("font-size: 11px; min-width: 55px;")
        self.slider_sharpness = QSlider(Qt.Orientation.Horizontal)
        self.slider_sharpness.setRange(0, 200)
        self.slider_sharpness.setValue(100)
        self.lbl_sh_val = QLabel("۱۰۰٪")
        self.lbl_sh_val.setStyleSheet("font-size: 11px; min-width: 40px; color: #AAA;")
        self.slider_sharpness.valueChanged.connect(self.on_adjustment_changed)
        row_sh.addWidget(lbl_sh)
        row_sh.addWidget(self.slider_sharpness)
        row_sh.addWidget(self.lbl_sh_val)
        vbox_adj.addLayout(row_sh)

        btn_reset_adj = QPushButton("↺ بازنشانی نور و رنگ")
        btn_reset_adj.setObjectName("secondary_button")
        btn_reset_adj.setStyleSheet("font-size: 11px; padding: 4px; color: #FFCC80;")
        btn_reset_adj.clicked.connect(self.reset_adjustments)
        vbox_adj.addWidget(btn_reset_adj)

        panel_layout.addWidget(group_adj)

        # ====================================================================
        # 4. Action Buttons
        # ====================================================================
        panel_layout.addStretch()

        btn_reset_all = QPushButton("🔄 بازنشانی کامل به تصویر اولیه")
        btn_reset_all.setObjectName("secondary_button")
        btn_reset_all.setStyleSheet("font-size: 11px; padding: 6px; background-color: #2D2D2D; color: #FFCDD2; border: 1px solid #555;")
        btn_reset_all.clicked.connect(self.reset_all_to_original)
        panel_layout.addWidget(btn_reset_all)

        if self.allow_retake:
            btn_retake = QPushButton("🔄 عکس مجدد با دوربین")
            btn_retake.setObjectName("secondary_button")
            btn_retake.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px; background-color: #555555; color: white; border-radius: 5px;")
            btn_retake.clicked.connect(self.on_retake_clicked)
            panel_layout.addWidget(btn_retake)

        btn_save = QPushButton("✅ تایید و ذخیره نهایی")
        btn_save.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px; background-color: #2e7d32; color: white; border-radius: 5px;")
        btn_save.clicked.connect(self.save_and_apply)
        panel_layout.addWidget(btn_save)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setObjectName("secondary_button")
        btn_cancel.setStyleSheet("font-size: 12px; padding: 7px; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        panel_layout.addWidget(btn_cancel)

        scroll.setWidget(panel_widget)
        main_layout.addWidget(scroll, stretch=2)

    def set_preset_aspect_ratio(self, ratio: float | None):
        self.canvas.set_aspect_ratio(ratio)

    def sync_dimensions_label(self):
        if not hasattr(self, 'lbl_dims') or not self.display_pil_image:
            return
        w = self.display_pil_image.width
        h = self.display_pil_image.height
        norm = self.canvas.crop_norm
        crop_w = int(norm.width() * w)
        crop_h = int(norm.height() * h)
        self.lbl_dims.setText(f"ابعاد برش: {crop_w} × {crop_h} پیکسل")

    def transform_image(self, action: str):
        if not self.transformed_pil_image:
            return

        if action == "rot_cw":
            self.transformed_pil_image = self.transformed_pil_image.rotate(-90, expand=True)
        elif action == "rot_ccw":
            self.transformed_pil_image = self.transformed_pil_image.rotate(90, expand=True)
        elif action == "flip_h":
            self.transformed_pil_image = self.transformed_pil_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif action == "flip_v":
            self.transformed_pil_image = self.transformed_pil_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        self.apply_adjustments(reset_crop=True)

    def on_adjustment_changed(self):
        b_val = self.slider_brightness.value()
        c_val = self.slider_contrast.value()
        s_val = self.slider_color.value()
        sh_val = self.slider_sharpness.value()

        to_fa = lambda n: str(n).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        self.lbl_b_val.setText(f"{to_fa(b_val)}٪")
        self.lbl_c_val.setText(f"{to_fa(c_val)}٪")
        self.lbl_s_val.setText(f"{to_fa(s_val)}٪")
        self.lbl_sh_val.setText(f"{to_fa(sh_val)}٪")

        self.apply_adjustments(reset_crop=False)

    def reset_adjustments(self):
        self.slider_brightness.setValue(100)
        self.slider_contrast.setValue(100)
        self.slider_color.setValue(100)
        self.slider_sharpness.setValue(100)
        self.apply_adjustments(reset_crop=False)

    def reset_all_to_original(self):
        if self.original_pil_image:
            self.transformed_pil_image = self.original_pil_image.copy()
            self.slider_brightness.setValue(100)
            self.slider_contrast.setValue(100)
            self.slider_color.setValue(100)
            self.slider_sharpness.setValue(100)
            self.apply_adjustments(reset_crop=True)

    def apply_adjustments(self, reset_crop: bool = False):
        if not self.transformed_pil_image:
            return

        img = self.transformed_pil_image

        b = self.slider_brightness.value() / 100.0
        if b != 1.0:
            img = ImageEnhance.Brightness(img).enhance(b)

        c = self.slider_contrast.value() / 100.0
        if c != 1.0:
            img = ImageEnhance.Contrast(img).enhance(c)

        col = self.slider_color.value() / 100.0
        if col != 1.0:
            img = ImageEnhance.Color(img).enhance(col)

        sh = self.slider_sharpness.value() / 100.0
        if sh != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(sh)

        self.display_pil_image = img
        pixmap = pil_to_pixmap(self.display_pil_image)
        self.canvas.set_pixmap(pixmap, reset_crop=reset_crop)
        self.sync_dimensions_label()

    def on_retake_clicked(self):
        self.retake_triggered = True
        self.retake_requested.emit()
        self.reject()

    def save_and_apply(self):
        if not self.display_pil_image:
            QMessageBox.warning(self, "خطا", "تصویری جهت ذخیره وجود ندارد.")
            return

        try:
            w = self.display_pil_image.width
            h = self.display_pil_image.height
            norm = self.canvas.crop_norm

            crop_x = max(0, int(norm.left() * w))
            crop_y = max(0, int(norm.top() * h))
            crop_w = min(w - crop_x, int(norm.width() * w))
            crop_h = min(h - crop_y, int(norm.height() * h))

            if crop_w <= 0 or crop_h <= 0:
                crop_x, crop_y, crop_w, crop_h = 0, 0, w, h

            cropped_img = self.display_pil_image.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

            out_dir = config.EXERCISE_MEDIA_DIR if hasattr(config, "EXERCISE_MEDIA_DIR") and config.EXERCISE_MEDIA_DIR.exists() else tempfile.gettempdir()
            filename = f"image_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            out_path = os.path.join(str(out_dir), filename)

            cropped_img.save(out_path, format="JPEG", quality=95, optimize=True, subsampling=0)

            self.result_image_path = out_path
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در پردازش و ذخیره تصویر: {str(e)}")
