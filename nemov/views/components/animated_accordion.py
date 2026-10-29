"""
Animated Accordion Curtain Component
====================================
Provides a luxury, silky-smooth animated curtain container (collapsible accordion)
using a zero-jitter QScrollArea viewport with sinusoidal easing curve and opacity fade.
"""

from PyQt6.QtWidgets import (
    QWidget, QFrame, QScrollArea, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal


class AnimatedAccordionCurtain(QScrollArea):
    """
    A luxury, zero-jitter collapsible accordion curtain container that smoothly
    animates collapse and expansion of its content widget without squishing or
    distorting child widgets.
    """

    toggled = pyqtSignal(bool)  # Emits is_collapsed
    anim_finished = pyqtSignal(bool)  # Emits is_collapsed when finished

    def __init__(self, content_widget: QWidget, parent: QWidget = None, duration_ms: int = 340):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self.content_widget = content_widget
        self._is_collapsed = False
        self._anim_progress = 1.0  # 1.0 = expanded, 0.0 = collapsed
        self._cached_height = 0

        # Viewport configuration for clipping without native window limits
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Smooth opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self.content_widget)
        self.content_widget.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.setWidget(self.content_widget)

        # Sinusoidal liquid animation
        self.anim = QPropertyAnimation(self, b"anim_progress", self)
        self.anim.setDuration(self.duration_ms)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.finished.connect(self._on_anim_finished)

    def get_anim_progress(self) -> float:
        return self._anim_progress

    def set_anim_progress(self, p: float):
        self._anim_progress = p
        # Compute smooth height
        full_h = self._get_full_height()
        target_h = int(full_h * p)
        self.setFixedHeight(target_h)
        # Smooth alpha fade (fades slightly faster on collapse, dissolves gently)
        self.opacity_effect.setOpacity(max(0.0, min(1.0, p * 1.25)))

    anim_progress = pyqtProperty(float, get_anim_progress, set_anim_progress)

    def _get_full_height(self) -> int:
        if self._cached_height > 0 and self._is_collapsed:
            return self._cached_height
        layout = self.content_widget.layout()
        if layout:
            h = layout.sizeHint().height()
            if h > 0:
                self._cached_height = h
                return h
        h = self.content_widget.sizeHint().height()
        if h > 0:
            self._cached_height = h
            return h
        return max(self._cached_height, 160)

    def is_collapsed(self) -> bool:
        return self._is_collapsed

    def toggle(self):
        if self._is_collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self):
        self._is_collapsed = True
        self._cached_height = self._get_full_height()
        self.anim.stop()
        self.anim.setStartValue(self._anim_progress)
        self.anim.setEndValue(0.0)
        self.toggled.emit(True)
        self.anim.start()

    def expand(self):
        self._is_collapsed = False
        self.show()
        self.anim.stop()
        self.anim.setStartValue(self._anim_progress)
        self.anim.setEndValue(1.0)
        self.toggled.emit(False)
        self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.content_widget and self.viewport():
            vp_w = self.viewport().width()
            if vp_w > 0:
                self.content_widget.resize(vp_w, self.content_widget.height())

    def _on_anim_finished(self):
        if self._is_collapsed:
            self.setFixedHeight(0)
            self.hide()
            self.opacity_effect.setOpacity(0.0)
        else:
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
            self.opacity_effect.setOpacity(1.0)
        self.anim_finished.emit(self._is_collapsed)
