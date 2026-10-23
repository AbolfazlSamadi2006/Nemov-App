#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThemeRippleOverlay: Liquid Circular Ripple & Neon Glow Ring transition animation
for dynamic theme switching across Nemov Sports Management Desktop.
Pours the selected theme outward from the clicked card coordinate like a vibrant wave.
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QPainterPath


class ThemeRippleOverlay(QWidget):
    """
    High-performance 60 FPS animation overlay that reveals the new theme
    through an expanding circular ripple bordered by a glowing neon wave ring.
    """

    def __init__(
        self,
        parent_window: QWidget,
        old_pixmap: QPixmap,
        new_pixmap: QPixmap,
        origin: QPoint,
        accent_color: str,
        duration_ms: int = 450
    ):
        super().__init__(parent_window)
        self.old_pixmap = old_pixmap
        self.new_pixmap = new_pixmap
        self.origin = origin
        self.accent_color = QColor(accent_color)
        self._radius = 0.0

        # Calculate max radius needed to comfortably cover all four corners of parent_window
        w = max(parent_window.width(), 800)
        h = max(parent_window.height(), 600)
        corners = [
            QPoint(0, 0),
            QPoint(w, 0),
            QPoint(0, h),
            QPoint(w, h)
        ]
        self.max_radius = max(math.hypot(c.x() - origin.x(), c.y() - origin.y()) for c in corners) + 60.0

        self.setGeometry(0, 0, parent_window.width(), parent_window.height())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.show()
        self.raise_()

        # Smooth deceleration curve (OutCubic) for natural liquid wave feeling
        self.anim = QPropertyAnimation(self, b"radius", self)
        self.anim.setDuration(duration_ms)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(self.max_radius)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

    @pyqtProperty(float)
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, val: float):
        self._radius = val
        self.update()

    def paintEvent(self, event):
        if not self.old_pixmap or self.old_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        r = self._radius
        max_r = max(self.max_radius, 1.0)
        progress = r / max_r

        # 1. Draw old snapshot as the outer background
        painter.drawPixmap(0, 0, self.old_pixmap)

        # 2. Draw new snapshot inside the expanding circular ripple
        if self.new_pixmap and not self.new_pixmap.isNull() and r > 0.5:
            painter.save()
            circle_path = QPainterPath()
            circle_path.addEllipse(
                self.origin.x() - r,
                self.origin.y() - r,
                r * 2.0,
                r * 2.0
            )
            painter.setClipPath(circle_path)
            painter.drawPixmap(0, 0, self.new_pixmap)
            painter.restore()

        # 3. Draw Neon Glow Wave Rings along the expanding wavefront
        if progress < 0.98 and r > 3.0:
            # Smoothly fade glow alpha as wave approaches outer boundaries
            fade = 1.0 if progress < 0.72 else (1.0 - (progress - 0.72) / 0.26)
            fade = max(0.0, min(1.0, fade))

            # Outer soft atmospheric glow ring
            c_glow_outer = QColor(self.accent_color)
            c_glow_outer.setAlpha(int(70 * fade))
            painter.setPen(QPen(c_glow_outer, 14.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(
                QPoint(int(self.origin.x()), int(self.origin.y())),
                int(r),
                int(r)
            )

            # Mid vibrant neon accent ring
            c_glow_mid = QColor(self.accent_color)
            c_glow_mid.setAlpha(int(190 * fade))
            painter.setPen(QPen(c_glow_mid, 5.0))
            painter.drawEllipse(
                QPoint(int(self.origin.x()), int(self.origin.y())),
                int(r),
                int(r)
            )

            # Core specular bright water-crest wave line
            c_crest = QColor(255, 255, 255, int(240 * fade))
            painter.setPen(QPen(c_crest, 2.0))
            painter.drawEllipse(
                QPoint(int(self.origin.x()), int(self.origin.y())),
                int(r),
                int(r)
            )

        painter.end()
