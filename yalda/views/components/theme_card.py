#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme Palette Card Widget for Nemov Sports Management Desktop.
Presents a compact visual card showing palette Persian/English names,
4 circular color swatches, active selection indicator, and click signal.
"""

from typing import Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)

# 17 Official Palettes Definition
PALETTES_METADATA: List[Dict[str, Any]] = [
    # 12 Dark Themes
    {
        "id": "crimson_fury",
        "name_fa": "قرمز آتشین (پیش‌فرض)",
        "name_en": "Crimson Fury",
        "is_dark": True,
        "colors": ["#121212", "#1E1E1E", "#8B0000", "#A91D22"],
        "accent": "#8B0000",
    },
    {
        "id": "royal_gold",
        "name_fa": "طلایی سلطنتی",
        "name_en": "Royal Gold",
        "is_dark": True,
        "colors": ["#141412", "#1F1E19", "#D4AF37", "#F59E0B"],
        "accent": "#D4AF37",
    },
    {
        "id": "neon_pulse",
        "name_fa": "سبز نئون",
        "name_en": "Neon Pulse",
        "is_dark": True,
        "colors": ["#0D1117", "#161B22", "#10B981", "#059669"],
        "accent": "#10B981",
    },
    {
        "id": "electric_cyan",
        "name_fa": "آبی الکتریک",
        "name_en": "Electric Cyan",
        "is_dark": True,
        "colors": ["#0B131E", "#131F2E", "#06B6D4", "#0891B2"],
        "accent": "#06B6D4",
    },
    {
        "id": "cyber_amethyst",
        "name_fa": "بنفش سایبری",
        "name_en": "Cyber Amethyst",
        "is_dark": True,
        "colors": ["#130E1F", "#1E1730", "#8B5CF6", "#7C3AED"],
        "accent": "#8B5CF6",
    },
    {
        "id": "solar_blaze",
        "name_fa": "شعله خورشیدی",
        "name_en": "Solar Blaze",
        "is_dark": True,
        "colors": ["#14100E", "#201914", "#F97316", "#EA580C"],
        "accent": "#F97316",
    },
    {
        "id": "stealth_silver",
        "name_fa": "نقره‌ای سربی",
        "name_en": "Stealth Silver",
        "is_dark": True,
        "colors": ["#0F172A", "#1E293B", "#94A3B8", "#64748B"],
        "accent": "#94A3B8",
    },
    {
        "id": "arctic_ice",
        "name_fa": "آبی یخی",
        "name_en": "Arctic Ice",
        "is_dark": True,
        "colors": ["#0C141F", "#142233", "#38BDF8", "#0284C7"],
        "accent": "#38BDF8",
    },
    {
        "id": "magenta_force",
        "name_fa": "ماژنتای پرقدرت",
        "name_en": "Magenta Force",
        "is_dark": True,
        "colors": ["#180D15", "#241420", "#EC4899", "#DB2777"],
        "accent": "#EC4899",
    },
    {
        "id": "bronze_titan",
        "name_fa": "تایتان برنزی",
        "name_en": "Bronze Titan",
        "is_dark": True,
        "colors": ["#14110E", "#211B15", "#CD7F32", "#B45309"],
        "accent": "#CD7F32",
    },
    {
        "id": "national_pride",
        "name_fa": "غرور ملی (ایران)",
        "name_en": "National Pride",
        "is_dark": True,
        "colors": ["#0F1713", "#16241D", "#15803D", "#DC2626"],
        "accent": "#15803D",
    },
    {
        "id": "oled_obsidian",
        "name_fa": "مشکی خالص OLED",
        "name_en": "OLED Obsidian",
        "is_dark": True,
        "colors": ["#000000", "#0C0C0C", "#3B82F6", "#60A5FA"],
        "accent": "#3B82F6",
    },
    # 5 Light Themes
    {
        "id": "olympic_white",
        "name_fa": "سفید المپیک",
        "name_en": "Olympic White",
        "is_dark": False,
        "colors": ["#F8FAFC", "#FFFFFF", "#2563EB", "#1D4ED8"],
        "accent": "#2563EB",
    },
    {
        "id": "clinical_cyan",
        "name_fa": "فیروزه‌ای درمانی",
        "name_en": "Clinical Cyan",
        "is_dark": False,
        "colors": ["#F0FDFA", "#FFFFFF", "#0891B2", "#0E7490"],
        "accent": "#0891B2",
    },
    {
        "id": "fresh_mint",
        "name_fa": "نعناع تازه",
        "name_en": "Fresh Mint",
        "is_dark": False,
        "colors": ["#F0FDF4", "#FFFFFF", "#059669", "#047857"],
        "accent": "#059669",
    },
    {
        "id": "champagne_gold",
        "name_fa": "طلایی شامپاینی",
        "name_en": "Champagne Gold",
        "is_dark": False,
        "colors": ["#FEFCE8", "#FFFFFF", "#B45309", "#92400E"],
        "accent": "#B45309",
    },
    {
        "id": "soft_orchid",
        "name_fa": "ارکیده ملایم",
        "name_en": "Soft Orchid",
        "is_dark": False,
        "colors": ["#FAF5FF", "#FFFFFF", "#7C3AED", "#6D28D9"],
        "accent": "#7C3AED",
    },
]


class ThemePaletteCard(QFrame):
    """Interactive visual card widget representing a single color theme palette."""

    clicked = pyqtSignal(str)

    def __init__(self, palette_data: Dict[str, Any], is_selected: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.palette_data = palette_data
        self.theme_id = palette_data.get("id", "")
        self.name_fa = palette_data.get("name_fa", "")
        self.name_en = palette_data.get("name_en", "")
        self.colors = palette_data.get("colors", ["#121212", "#1E1E1E", "#8B0000", "#A91D22"])
        self.accent_color = palette_data.get("accent", "#8B0000")
        self.is_dark = palette_data.get("is_dark", True)
        self.is_selected = is_selected

        self.setFixedSize(190, 105)
        self.setObjectName(f"themeCard_{self.theme_id}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._init_ui()
        self._update_appearance()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header Row: Persian Name + Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.lbl_title = QLabel(self.name_fa)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF; background: transparent;")
        self.lbl_title.setWordWrap(False)

        self.badge_selected = QLabel("✓")
        self.badge_selected.setFixedSize(18, 18)
        self.badge_selected.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_selected.setStyleSheet(f"""
            QLabel {{
                background-color: {self.accent_color};
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                font-weight: bold;
                border-radius: 9px;
            }}
        """)
        self.badge_selected.setVisible(self.is_selected)

        header_layout.addWidget(self.lbl_title, 1)
        header_layout.addWidget(self.badge_selected)
        layout.addLayout(header_layout)

        # Subtitle: English Name
        self.lbl_subtitle = QLabel(self.name_en)
        self.lbl_subtitle.setStyleSheet("font-size: 10px; color: #8E8E93; font-family: Segoe UI, sans-serif; background: transparent;")
        layout.addWidget(self.lbl_subtitle)

        layout.addStretch(1)

        # Swatches Row: 4 circular preview swatches
        swatches_layout = QHBoxLayout()
        swatches_layout.setContentsMargins(0, 2, 0, 2)
        swatches_layout.setSpacing(8)

        swatch_labels = ["پس‌زمینه", "کارت", "رنگ اصلی", "هاور"]
        for idx, color_hex in enumerate(self.colors[:4]):
            swatch = QLabel()
            swatch.setFixedSize(22, 22)
            swatch.setToolTip(f"{swatch_labels[idx]}: {color_hex}")
            # White/light border for contrast
            border_style = "border: 1px solid rgba(255, 255, 255, 0.25);" if self.is_dark else "border: 1px solid rgba(0, 0, 0, 0.15);"
            swatch.setStyleSheet(f"""
                QLabel {{
                    background-color: {color_hex};
                    border-radius: 11px;
                    {border_style}
                }}
            """)
            swatches_layout.addWidget(swatch)

        swatches_layout.addStretch(1)
        layout.addLayout(swatches_layout)

    def _update_appearance(self):
        """Updates frame border and background depending on selection state."""
        obj_name = self.objectName()
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame#{obj_name} {{
                    background-color: #242428;
                    border: 2px solid {self.accent_color};
                    border-radius: 10px;
                }}
            """)
            if hasattr(self, "badge_selected"):
                self.badge_selected.setVisible(True)
        else:
            self.setStyleSheet(f"""
                QFrame#{obj_name} {{
                    background-color: #18181A;
                    border: 1px solid #38383C;
                    border-radius: 10px;
                }}
                QFrame#{obj_name}:hover {{
                    background-color: #222226;
                    border: 1px solid #5A5A60;
                }}
            """)
            if hasattr(self, "badge_selected"):
                self.badge_selected.setVisible(False)

    def set_selected(self, selected: bool):
        """Sets the selected state and refreshes appearance."""
        if self.is_selected != selected:
            self.is_selected = selected
            self._update_appearance()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.theme_id)
        super().mousePressEvent(event)
