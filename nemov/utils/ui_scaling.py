from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication, QFrame, QScrollArea, QWidget


class HorizontalWheelNormalizer(QObject):
    """
    Normalizes horizontal wheel/touchpad swipe direction on Windows Qt6 so
    swiping left/right on a touchpad moves content consistently with Windows 11.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._forwarded_ids: set[int] = set()

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel:
            return False

        if id(event) in self._forwarded_ids:
            return False

        angle = event.angleDelta()
        pixel = event.pixelDelta()
        if angle.x() == 0 and pixel.x() == 0:
            return False

        if not isinstance(watched, QWidget):
            return False

        new_angle = QPoint(-angle.x(), angle.y())
        new_pixel = QPoint(-pixel.x(), pixel.y())
        try:
            src = event.source()
        except Exception:
            src = None

        gpos = event.globalPosition()
        target = watched
        while target is not None:
            pos_f = QPointF(event.position()) if target is watched else QPointF(target.mapFromGlobal(gpos.toPoint()))
            bubbled = QWheelEvent(
                pos_f,
                gpos,
                new_pixel,
                new_angle,
                event.buttons(),
                event.modifiers(),
                event.phase(),
                event.inverted(),
                *((src,) if src is not None else ()),
            )
            self._forwarded_ids.add(id(bubbled))
            try:
                QApplication.sendEvent(target, bubbled)
                if bubbled.isAccepted():
                    event.accept()
                    return True
            finally:
                self._forwarded_ids.discard(id(bubbled))
            if target.isWindow():
                break
            target = target.parentWidget()
        return False


def get_available_screen_size(widget: QWidget = None) -> tuple[int, int]:
    """Returns logical available screen (width, height) in device-independent pixels."""
    screen = None
    try:
        if widget is not None and hasattr(widget, "screen"):
            screen = widget.screen()
    except Exception:
        screen = None
    if screen is None:
        try:
            screen = QApplication.primaryScreen()
        except Exception:
            screen = None
    if screen is not None:
        avail = screen.availableGeometry()
        if avail.width() > 0 and avail.height() > 0:
            return avail.width(), avail.height()
    return 1280, 800


def compute_responsive_size(
    preferred_w: int,
    preferred_h: int,
    *,
    widget: QWidget = None,
    min_w: int = 320,
    min_h: int = 320,
    margin_w: int = 24,
    margin_h: int = 36,
) -> tuple[int, int]:
    """
    Returns exact (preferred_w, preferred_h) when the screen has enough room,
    clamping cleanly inside availableGeometry on small/high-DPI laptops.
    """
    avail_w, avail_h = get_available_screen_size(widget)
    cap_w = max(240, avail_w - margin_w)
    cap_h = max(240, avail_h - margin_h)
    w = min(preferred_w, max(min(min_w, cap_w), cap_w)) if cap_w < preferred_w else preferred_w
    h = min(preferred_h, max(min(min_h, cap_h), cap_h)) if cap_h < preferred_h else preferred_h
    return w, h


def clamp_minimum_size(
    preferred_min_w: int,
    preferred_min_h: int,
    *,
    widget: QWidget = None,
    floor_w: int = 320,
    floor_h: int = 320,
    margin_w: int = 24,
    margin_h: int = 36,
) -> tuple[int, int]:
    """Keeps preferred minimum size on normal displays while allowing small screens to fit."""
    avail_w, avail_h = get_available_screen_size(widget)
    cap_w = max(240, avail_w - margin_w)
    cap_h = max(240, avail_h - margin_h)
    w = min(preferred_min_w, max(min(floor_w, cap_w), cap_w)) if cap_w < preferred_min_w else preferred_min_w
    h = min(preferred_min_h, max(min(floor_h, cap_h), cap_h)) if cap_h < preferred_min_h else preferred_min_h
    return w, h


def create_transparent_scroll_area(content: QWidget, obj_prefix: str) -> QScrollArea:
    """Wraps content inside a frameless scroll area with strictly scoped transparent styling."""
    scroll = QScrollArea()
    scroll.setObjectName(f"{obj_prefix}_scroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea#{obj_prefix}_scroll {{ background: transparent; border: none; }}")
    vp = scroll.viewport()
    if vp is not None:
        vp.setObjectName(f"{obj_prefix}_viewport")
        vp.setStyleSheet(f"QWidget#{obj_prefix}_viewport {{ background: transparent; border: none; }}")
    if content.objectName() == "":
        content.setObjectName(f"{obj_prefix}_content")
    cname = content.objectName()
    content.setStyleSheet(f"QWidget#{cname} {{ background: transparent; }}")
    scroll.setWidget(content)
    return scroll
