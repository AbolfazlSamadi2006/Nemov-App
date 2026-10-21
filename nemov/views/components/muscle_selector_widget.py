import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QToolTip
)
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QBrush, QPolygonF, QCursor, QFont, QFontDatabase
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QEvent

MUSCLE_DEFINITIONS = {
    "neck": {
        "name_fa": "گردن",
        "color": "#EC4899",
        "legacy": "shoulders",
        "view": "front",
        "polys": [
            [(124, 60), (150, 60), (156, 84), (118, 84)]
        ]
    },
    "shoulders": {
        "name_fa": "سرشانه",
        "color": "#F97316",
        "legacy": "shoulders",
        "view": "front",
        "polys": [
            [(68, 95), (96, 75), (97, 90), (90, 126), (68, 115)],
            [(177, 90), (178, 75), (206, 95), (206, 115), (184, 126)]
        ]
    },
    "chest": {
        "name_fa": "سینه",
        "color": "#EF4444",
        "legacy": "chest",
        "view": "front",
        "polys": [
            [(98, 90), (137, 92), (137, 132), (96, 128)],
            [(137, 92), (176, 90), (178, 128), (137, 132)]
        ]
    },
    "biceps": {
        "name_fa": "جلو بازو",
        "color": "#06B6D4",
        "legacy": "arms",
        "view": "front",
        "polys": [
            [(60, 130), (88, 125), (82, 172), (52, 165)],
            [(186, 125), (214, 130), (222, 165), (192, 172)]
        ]
    },
    "forearms": {
        "name_fa": "ساعد",
        "color": "#A855F7",
        "legacy": "arms",
        "view": "front",
        "polys": [
            [(45, 172), (80, 178), (62, 235), (25, 222)],
            [(194, 178), (229, 172), (249, 222), (212, 235)]
        ]
    },
    "abs": {
        "name_fa": "شکم و مرکز بدن",
        "color": "#EAB308",
        "legacy": "abs",
        "view": "front",
        "polys": [
            [(100, 135), (174, 135), (166, 218), (108, 218)]
        ]
    },
    "legs_front": {
        "name_fa": "جلو ران (چهارسر)",
        "color": "#DC2626",
        "legacy": "legs",
        "view": "front",
        "polys": [
            [(85, 225), (135, 228), (125, 325), (85, 320)],
            [(139, 228), (189, 225), (189, 320), (149, 325)]
        ]
    },
    "traps": {
        "name_fa": "کول (تراپزیوس)",
        "color": "#F59E0B",
        "legacy": "back",
        "view": "back",
        "polys": [
            [(395, 62), (430, 62), (452, 95), (412, 108), (372, 95)]
        ]
    },
    "upper_back": {
        "name_fa": "بالای کمر",
        "color": "#6366F1",
        "legacy": "back",
        "view": "back",
        "polys": [
            [(370, 96), (412, 108), (454, 96), (460, 138), (412, 146), (364, 138)]
        ]
    },
    "triceps": {
        "name_fa": "پشت بازو",
        "color": "#3B82F6",
        "legacy": "arms",
        "view": "back",
        "polys": [
            [(334, 112), (362, 106), (356, 168), (328, 155)],
            [(462, 106), (490, 112), (496, 155), (468, 168)]
        ]
    },
    "lats": {
        "name_fa": "زیر بغل (پشت)",
        "color": "#10B981",
        "legacy": "back",
        "view": "back",
        "polys": [
            [(362, 138), (412, 146), (412, 186), (372, 185)],
            [(412, 146), (462, 138), (452, 185), (412, 186)]
        ]
    },
    "lower_back": {
        "name_fa": "پایین کمر (فیله)",
        "color": "#84CC16",
        "legacy": "back",
        "view": "back",
        "polys": [
            [(385, 186), (439, 186), (434, 218), (390, 218)]
        ]
    },
    "glutes": {
        "name_fa": "باسن (سرینی)",
        "color": "#FB7185",
        "legacy": "legs",
        "view": "back",
        "polys": [
            [(366, 218), (458, 218), (462, 266), (412, 268), (362, 266)]
        ]
    },
    "legs_back": {
        "name_fa": "پشت ران (همسترینگ)",
        "color": "#C084FC",
        "legacy": "legs",
        "view": "back",
        "polys": [
            [(362, 268), (408, 268), (402, 342), (366, 335)],
            [(416, 268), (462, 268), (458, 335), (422, 342)]
        ]
    },
    "calves": {
        "name_fa": "ساق پا",
        "color": "#38BDF8",
        "legacy": "legs",
        "view": "back",
        "polys": [
            [(366, 340), (404, 344), (398, 425), (370, 422)],
            [(420, 344), (458, 340), (454, 422), (426, 425)]
        ]
    }
}

# Legacy category fallback map (e.g. if DB has 'back', map to list of keys)
LEGACY_TO_KEYS = {
    "chest": ["chest"],
    "shoulders": ["shoulders"],
    "back": ["upper_back", "lats", "lower_back", "traps"],
    "arms": ["biceps", "triceps", "forearms"],
    "abs": ["abs"],
    "legs": ["legs_front", "legs_back", "glutes", "calves"],
}

LEGACY_NAMES_FA = {
    "chest": "سینه (کلی)",
    "shoulders": "سرشانه (کلی)",
    "back": "پشت و زیربغل (کلی)",
    "arms": "بازو (کلی)",
    "abs": "شکم و مرکز بدن (کلی)",
    "legs": "پا و سرینی (کلی)",
}

KEY_TO_LEGACY = {k: v["legacy"] for k, v in MUSCLE_DEFINITIONS.items()}

_FONTS_INITIALIZED = False

def _ensure_fonts_loaded():
    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return
    _FONTS_INITIALIZED = True
    font_paths = [
        Path("resources/fonts/Vazirmatn-Regular.ttf"),
        Path("resources/fonts/Vazirmatn-Bold.ttf"),
        Path(__file__).resolve().parent.parent.parent.parent / "resources" / "fonts" / "Vazirmatn-Regular.ttf",
        Path(__file__).resolve().parent.parent.parent.parent / "resources" / "fonts" / "Vazirmatn-Bold.ttf",
    ]
    try:
        import config
        if hasattr(config, "BASE_DIR"):
            font_paths.insert(0, Path(config.BASE_DIR) / "resources" / "fonts" / "Vazirmatn-Regular.ttf")
            font_paths.insert(1, Path(config.BASE_DIR) / "resources" / "fonts" / "Vazirmatn-Bold.ttf")
    except Exception:
        pass
    for fp in font_paths:
        if fp.exists():
            try:
                QFontDatabase.addApplicationFont(str(fp))
            except Exception:
                pass


class BodyCanvasWidget(QWidget):
    muscle_clicked = pyqtSignal(str, str)
    muscle_hovered = pyqtSignal(str, str)

    BASE_W = 550
    BASE_H = 466

    def __init__(self, parent=None):
        super().__init__(parent)
        _ensure_fonts_loaded()
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.selected_muscle = None
        self.hovered_muscle = None
        self.pixmap = None
        self._load_pixmap()
        self._qpolys = {
            m_key: [QPolygonF([QPointF(x, y) for x, y in poly]) for poly in m_info["polys"]]
            for m_key, m_info in MUSCLE_DEFINITIONS.items()
        }

    def _load_pixmap(self):
        candidate_paths = [
            Path("resources/images/muscle_mannequin.png"),
            Path(__file__).resolve().parent.parent.parent.parent / "resources" / "images" / "muscle_mannequin.png",
            Path("dist/Yalda/_internal/resources/images/muscle_mannequin.png"),
        ]
        try:
            import config
            if hasattr(config, "BASE_DIR"):
                candidate_paths.insert(0, Path(config.BASE_DIR) / "resources" / "images" / "muscle_mannequin.png")
        except Exception:
            pass
        if getattr(sys, 'frozen', False):
            candidate_paths.insert(0, Path(sys._MEIPASS) / "resources" / "images" / "muscle_mannequin.png")
            candidate_paths.insert(1, Path(sys.executable).resolve().parent / "_internal" / "resources" / "images" / "muscle_mannequin.png")
            candidate_paths.insert(2, Path(sys.executable).resolve().parent / "resources" / "images" / "muscle_mannequin.png")

        for p in candidate_paths:
            if p.exists():
                self.pixmap = QPixmap(str(p))
                if not self.pixmap.isNull():
                    break

    def get_active_muscles(self):
        if self.selected_muscle in LEGACY_TO_KEYS:
            return LEGACY_TO_KEYS[self.selected_muscle]
        elif self.selected_muscle in MUSCLE_DEFINITIONS:
            return [self.selected_muscle]
        return []

    def set_selected_muscle(self, muscle_key: str):
        if self.selected_muscle != muscle_key:
            if muscle_key in LEGACY_TO_KEYS or muscle_key in MUSCLE_DEFINITIONS:
                self.selected_muscle = muscle_key
            else:
                self.selected_muscle = None
            self.update()

    def clear_selection(self):
        if self.selected_muscle is not None:
            self.selected_muscle = None
            self.update()

    def _get_target_rect(self) -> QRectF:
        vw = self.width()
        vh = self.height()
        if vw <= 0 or vh <= 0:
            return QRectF(0, 0, self.BASE_W, self.BASE_H)

        aspect = self.BASE_W / self.BASE_H
        v_aspect = vw / vh

        if v_aspect > aspect:
            # Constrained by height
            th = vh
            tw = th * aspect
            tx = (vw - tw) / 2
            ty = 0
        else:
            # Constrained by width
            tw = vw
            th = tw / aspect
            tx = 0
            ty = (vh - th) / 2
        return QRectF(tx, ty, tw, th)

    def _map_to_base_coords(self, px: float, py: float):
        r = self._get_target_rect()
        if not r.contains(px, py):
            return None, None
        scale_x = self.BASE_W / r.width()
        scale_y = self.BASE_H / r.height()
        bx = (px - r.x()) * scale_x
        by = (py - r.y()) * scale_y
        return bx, by

    def _find_muscle_at(self, bx: float, by: float):
        if bx is None or by is None:
            return None
        pt = QPointF(bx, by)
        for m_key, qpolys in self._qpolys.items():
            for qpoly in qpolys:
                if qpoly.containsPoint(pt, Qt.FillRule.OddEvenFill):
                    return m_key
        return None

    def event(self, event):
        if event.type() in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            points = event.points()
            if points:
                pt = points[0]
                pos = pt.position() if not pt.position().isNull() else pt.scenePosition()
                bx, by = self._map_to_base_coords(pos.x(), pos.y())
                muscle = self._find_muscle_at(bx, by)
                if event.type() == QEvent.Type.TouchEnd:
                    self.hovered_muscle = None
                    if muscle:
                        self.selected_muscle = muscle
                        info = MUSCLE_DEFINITIONS[muscle]
                        self.muscle_clicked.emit(muscle, info["name_fa"])
                        self.update()
                    else:
                        self.update()
                elif event.type() == QEvent.Type.TouchBegin:
                    if muscle:
                        self.hovered_muscle = muscle
                        info = MUSCLE_DEFINITIONS[muscle]
                        self.muscle_hovered.emit(muscle, info["name_fa"])
                        self.update()
            event.accept()
            return True
        return super().event(event)

    def mouseMoveEvent(self, event):
        bx, by = self._map_to_base_coords(event.position().x(), event.position().y())
        muscle = self._find_muscle_at(bx, by)
        if muscle != self.hovered_muscle:
            self.hovered_muscle = muscle
            if muscle:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                info = MUSCLE_DEFINITIONS[muscle]
                self.muscle_hovered.emit(muscle, info["name_fa"])
                QToolTip.showText(event.globalPosition().toPoint(), f"🎯 {info['name_fa']}", self)
            else:
                self.unsetCursor()
                self.muscle_hovered.emit("", "")
                QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_muscle:
            self.hovered_muscle = None
            self.unsetCursor()
            self.muscle_hovered.emit("", "")
            self.update()
        QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            bx, by = self._map_to_base_coords(event.position().x(), event.position().y())
            muscle = self._find_muscle_at(bx, by)
            if muscle:
                self.selected_muscle = muscle
                info = MUSCLE_DEFINITIONS[muscle]
                self.muscle_clicked.emit(muscle, info["name_fa"])
                self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        r = self._get_target_rect()

        # Draw base mannequin with exact sub-pixel QRectF alignment
        if self.pixmap and not self.pixmap.isNull():
            painter.drawPixmap(r, self.pixmap, QRectF(self.pixmap.rect()))


        scale_x = r.width() / self.BASE_W
        scale_y = r.height() / self.BASE_H
        off_x = r.x()
        off_y = r.y()

        def draw_polys(m_key, fill_alpha, stroke_alpha, stroke_width, glow=False):
            info = MUSCLE_DEFINITIONS[m_key]
            hex_c = info["color"]
            base_col = QColor(hex_c)

            fill_c = QColor(base_col.red(), base_col.green(), base_col.blue(), fill_alpha)
            stroke_c = QColor(base_col.red(), base_col.green(), base_col.blue(), stroke_alpha)

            if glow:
                # Outer soft glow
                glow_c = QColor(base_col.red(), base_col.green(), base_col.blue(), 50)
                painter.setPen(QPen(glow_c, stroke_width + 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for poly in info["polys"]:
                    screen_poly = QPolygonF([QPointF(off_x + x * scale_x, off_y + y * scale_y) for x, y in poly])
                    painter.drawPolygon(screen_poly)

            painter.setPen(QPen(stroke_c, stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(QBrush(fill_c))

            for poly in info["polys"]:
                screen_poly = QPolygonF([QPointF(off_x + x * scale_x, off_y + y * scale_y) for x, y in poly])
                painter.drawPolygon(screen_poly)

        active_muscles = self.get_active_muscles()

        # Draw hovered (if not in active_muscles)
        if self.hovered_muscle and self.hovered_muscle not in active_muscles:
            draw_polys(self.hovered_muscle, fill_alpha=80, stroke_alpha=200, stroke_width=1.8, glow=True)

        # Draw selected (single muscle or all constituent muscles of legacy group)
        for sel_m in active_muscles:
            draw_polys(sel_m, fill_alpha=160, stroke_alpha=255, stroke_width=2.5, glow=True)


class MuscleSelectorWidget(QFrame):
    muscle_changed = pyqtSignal(str, str)  # (muscle_key, name_fa)

    def __init__(self, parent=None, is_filter_mode=False):
        super().__init__(parent)
        self.is_filter_mode = is_filter_mode
        self.setObjectName("muscleSelectorFrame")
        self.setStyleSheet("""
            QFrame#muscleSelectorFrame {
                background-color: #12151B;
                border: 1px solid #2D333B;
                border-radius: 12px;
            }
            QToolTip {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 4px 8px;
                font-family: "Vazirmatn", "Segoe UI", sans-serif;
                font-size: 11px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(10, 8, 10, 8)
        vlay.setSpacing(6)

        # Header status row
        h_row = QHBoxLayout()
        h_row.setContentsMargins(0, 0, 0, 0)
        h_row.setSpacing(8)

        self.lbl_status = QLabel("🎯 عضله: انتخاب نشده" if not self.is_filter_mode else "🎯 فیلتر: همه عضلات")
        self.lbl_status.setStyleSheet("""
            QLabel {
                color: #C9D1D9;
                font-family: "Vazirmatn", "Segoe UI", sans-serif;
                font-size: 11.5px;
                font-weight: bold;
                background-color: #1C2128;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)

        self.btn_reset = QPushButton("همه عضلات" if self.is_filter_mode else "پاک کردن")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #8B949E;
                font-family: "Vazirmatn", "Segoe UI", sans-serif;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363D;
                color: #FFFFFF;
            }
        """)
        self.btn_reset.clicked.connect(lambda: self.clear_selection(emit_signal=True))

        h_row.addWidget(self.lbl_status, 1)
        h_row.addWidget(self.btn_reset)
        vlay.addLayout(h_row)

        # Mannequin canvas
        self.canvas = BodyCanvasWidget(self)
        self.canvas.muscle_clicked.connect(self._on_canvas_clicked)
        self.canvas.muscle_hovered.connect(self._on_canvas_hovered)
        vlay.addWidget(self.canvas, 1)

        # Footer hint (only in dialog mode; filter card has its own dedicated description)
        if not self.is_filter_mode:
            lbl_hint = QLabel("💡 با کلیک روی بدن یا انتخاب از لیست، عضله را برگزینید.")
            lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_hint.setStyleSheet("""
                QLabel {
                    color: #94A3B8;
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-size: 11px;
                    background: transparent;
                }
            """)
            vlay.addWidget(lbl_hint)

    def _on_canvas_clicked(self, muscle_key: str, name_fa: str):
        self._update_status_chip(muscle_key, name_fa)
        self.muscle_changed.emit(muscle_key, name_fa)

    def _on_canvas_hovered(self, muscle_key: str, name_fa: str):
        if not self.canvas.selected_muscle:
            if muscle_key:
                prefix = "👆 فیلتر:" if self.is_filter_mode else "👆 عضله:"
                self.lbl_status.setText(f"{prefix} {name_fa}")
            else:
                self.lbl_status.setText("🎯 عضله: انتخاب نشده" if not self.is_filter_mode else "🎯 فیلتر: همه عضلات")

    def _update_status_chip(self, muscle_key: str, name_fa: str):
        if muscle_key and muscle_key in MUSCLE_DEFINITIONS:
            color = MUSCLE_DEFINITIONS[muscle_key]["color"]
            prefix = "🎯 فیلتر:" if self.is_filter_mode else "🎯 عضله:"
            self.lbl_status.setText(f"{prefix} {name_fa}")
            self.lbl_status.setStyleSheet(f"""
                QLabel {{
                    color: #FFFFFF;
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-size: 11.5px;
                    font-weight: bold;
                    background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.25);
                    border: 1px solid {color};
                    border-radius: 6px;
                    padding: 4px 10px;
                }}
            """)
        elif muscle_key and muscle_key in LEGACY_NAMES_FA:
            color = "#3B82F6"
            display_name = name_fa or LEGACY_NAMES_FA[muscle_key]
            prefix = "🎯 فیلتر:" if self.is_filter_mode else "🎯 عضله:"
            self.lbl_status.setText(f"{prefix} {display_name}")
            self.lbl_status.setStyleSheet(f"""
                QLabel {{
                    color: #FFFFFF;
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-size: 11.5px;
                    font-weight: bold;
                    background-color: rgba(59, 130, 246, 0.25);
                    border: 1px solid {color};
                    border-radius: 6px;
                    padding: 4px 10px;
                }}
            """)
        else:
            self.lbl_status.setText("🎯 عضله: انتخاب نشده" if not self.is_filter_mode else "🎯 فیلتر: همه عضلات")
            self.lbl_status.setStyleSheet("""
                QLabel {{
                    color: #C9D1D9;
                    font-family: "Vazirmatn", "Segoe UI", sans-serif;
                    font-size: 11.5px;
                    font-weight: bold;
                    background-color: #1C2128;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                    padding: 4px 10px;
                }}
            """)

    def set_selected_muscle(self, muscle_key: str, emit_signal: bool = False):
        self.canvas.set_selected_muscle(muscle_key)
        sel = self.canvas.selected_muscle
        if sel and sel in MUSCLE_DEFINITIONS:
            name_fa = MUSCLE_DEFINITIONS[sel]["name_fa"]
            self._update_status_chip(sel, name_fa)
            if emit_signal:
                self.muscle_changed.emit(sel, name_fa)
        elif sel and sel in LEGACY_NAMES_FA:
            name_fa = LEGACY_NAMES_FA[sel]
            self._update_status_chip(sel, name_fa)
            if emit_signal:
                self.muscle_changed.emit(sel, name_fa)
        else:
            self._update_status_chip("", "")
            if emit_signal:
                self.muscle_changed.emit("", "")

    def get_selected_muscle(self) -> str:
        return self.canvas.selected_muscle or ""

    def clear_selection(self, *args, emit_signal: bool = True):
        self.canvas.clear_selection()
        self._update_status_chip("", "")
        if emit_signal:
            self.muscle_changed.emit("", "")
