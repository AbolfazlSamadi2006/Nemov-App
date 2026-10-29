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
        "name_fa": "قرمز (پیش‌فرض)",
        "name_en": "Crimson",
        "is_dark": True,
        "colors": ["#121212", "#1E1E1E", "#8B0000", "#A91D22"],
        "accent": "#8B0000",
    },
    {
        "id": "royal_gold",
        "name_fa": "طلایی",
        "name_en": "Gold",
        "is_dark": True,
        "colors": ["#14130F", "#23201A", "#D4AF37", "#DFBE5B"],
        "accent": "#D4AF37",
    },
    {
        "id": "neon_pulse",
        "name_fa": "سبز روشن",
        "name_en": "Bright Green",
        "is_dark": True,
        "colors": ["#0F1715", "#1B2B27", "#10B981", "#34D399"],
        "accent": "#10B981",
    },
    {
        "id": "electric_cyan",
        "name_fa": "فیروزه‌ای",
        "name_en": "Cyan",
        "is_dark": True,
        "colors": ["#0E1720", "#1B2E42", "#06B6D4", "#22D3EE"],
        "accent": "#06B6D4",
    },
    {
        "id": "cyber_amethyst",
        "name_fa": "بنفش",
        "name_en": "Purple",
        "is_dark": True,
        "colors": ["#13101C", "#241E36", "#8B5CF6", "#A78BFA"],
        "accent": "#8B5CF6",
    },
    {
        "id": "solar_blaze",
        "name_fa": "نارنجی",
        "name_en": "Orange",
        "is_dark": True,
        "colors": ["#16120E", "#2C221B", "#F97316", "#FB923C"],
        "accent": "#F97316",
    },
    {
        "id": "stealth_silver",
        "name_fa": "طوسی نقره‌ای",
        "name_en": "Silver",
        "is_dark": True,
        "colors": ["#141619", "#262B31", "#94A3B8", "#CBD5E1"],
        "accent": "#94A3B8",
    },
    {
        "id": "arctic_ice",
        "name_fa": "آبی روشن",
        "name_en": "Light Blue",
        "is_dark": True,
        "colors": ["#0C1622", "#192C44", "#38BDF8", "#7DD3FC"],
        "accent": "#38BDF8",
    },
    {
        "id": "magenta_force",
        "name_fa": "صورتی",
        "name_en": "Pink",
        "is_dark": True,
        "colors": ["#180F16", "#301D2C", "#EC4899", "#F472B6"],
        "accent": "#EC4899",
    },
    {
        "id": "bronze_titan",
        "name_fa": "برنزی",
        "name_en": "Bronze",
        "is_dark": True,
        "colors": ["#15120E", "#2B231B", "#CD7F32", "#D98C42"],
        "accent": "#CD7F32",
    },
    {
        "id": "national_pride",
        "name_fa": "سبز پررنگ",
        "name_en": "Dark Green",
        "is_dark": True,
        "colors": ["#0F1713", "#1B2E26", "#15803D", "#DC2626"],
        "accent": "#15803D",
    },
    {
        "id": "oled_obsidian",
        "name_fa": "مشکی خالص",
        "name_en": "Pure Black",
        "is_dark": True,
        "colors": ["#000000", "#141414", "#E11D48", "#F43F5E"],
        "accent": "#E11D48",
    },
    # 5 Light Themes
    {
        "id": "olympic_white",
        "name_fa": "سفید آبی",
        "name_en": "White Blue",
        "is_dark": False,
        "colors": ["#F8FAFC", "#FFFFFF", "#2563EB", "#3B82F6"],
        "accent": "#2563EB",
    },
    {
        "id": "clinical_cyan",
        "name_fa": "فیروزه‌ای روشن",
        "name_en": "Light Cyan",
        "is_dark": False,
        "colors": ["#F0FDFA", "#FFFFFF", "#0891B2", "#06B6D4"],
        "accent": "#0891B2",
    },
    {
        "id": "fresh_mint",
        "name_fa": "سبز کم‌رنگ",
        "name_en": "Mint Green",
        "is_dark": False,
        "colors": ["#F0FDF4", "#FFFFFF", "#059669", "#10B981"],
        "accent": "#059669",
    },
    {
        "id": "champagne_gold",
        "name_fa": "کرم طلایی",
        "name_en": "Champagne Gold",
        "is_dark": False,
        "colors": ["#FEFCE8", "#FFFFFF", "#D97706", "#F59E0B"],
        "accent": "#D97706",
    },
    {
        "id": "soft_orchid",
        "name_fa": "یاسی",
        "name_en": "Lavender",
        "is_dark": False,
        "colors": ["#FAF5FF", "#FFFFFF", "#7C3AED", "#8B5CF6"],
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

        # Connect to dynamic ThemeManager signal for live adaptation
        try:
            from nemov.utils.theme_manager import ThemeManager
            ThemeManager.theme_changed.connect(self._on_global_theme_changed)
        except Exception:
            pass

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header Row: Persian Name + Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.lbl_title = QLabel(self.name_fa)
        self.lbl_title.setWordWrap(False)

        self.badge_selected = QLabel("✓")
        self.badge_selected.setFixedSize(18, 18)
        self.badge_selected.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_selected.setVisible(self.is_selected)

        header_layout.addWidget(self.lbl_title, 1)
        header_layout.addWidget(self.badge_selected)
        layout.addLayout(header_layout)

        # Subtitle: English Name
        self.lbl_subtitle = QLabel(self.name_en)
        layout.addWidget(self.lbl_subtitle)

        layout.addStretch(1)

        # Swatches Row: 4 circular preview swatches
        swatches_layout = QHBoxLayout()
        swatches_layout.setContentsMargins(0, 2, 0, 2)
        swatches_layout.setSpacing(8)

        swatch_labels = ["پس‌زمینه", "کارت", "رنگ اصلی", "هاور"]
        self.swatch_widgets = []
        for idx, color_hex in enumerate(self.colors[:4]):
            swatch = QLabel()
            swatch.setFixedSize(22, 22)
            swatch.setToolTip(f"{swatch_labels[idx]}: {color_hex}")
            swatches_layout.addWidget(swatch)
            self.swatch_widgets.append((swatch, color_hex))

        swatches_layout.addStretch(1)
        layout.addLayout(swatches_layout)

    def _on_global_theme_changed(self, theme_key: str = ""):
        """Slot called whenever the global theme changes to live-adapt card styles."""
        self._update_appearance()

    def refresh_theme(self):
        """Forces refreshing the card appearance based on the active theme."""
        self._update_appearance()

    def _update_appearance(self):
        """Updates frame border, background, typography, and swatches based on active app theme and selection."""
        try:
            from nemov.utils.theme_manager import ThemeManager
            current_palette = ThemeManager.get_current_palette()
            is_app_dark = current_palette.is_dark if current_palette else True
        except Exception:
            is_app_dark = True
            current_palette = None

        obj_name = self.objectName()

        if is_app_dark:
            # ---------------------------------------------------------
            # Active App Theme is DARK: Render Dark Surface Card
            # ---------------------------------------------------------
            if hasattr(self, "lbl_title"):
                self.lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF; background: transparent;")
            if hasattr(self, "lbl_subtitle"):
                self.lbl_subtitle.setStyleSheet("font-size: 10px; color: #8E8E93; font-family: Segoe UI, sans-serif; background: transparent;")

            if self.is_selected:
                self.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: #242428;
                        border: 2px solid {self.accent_color};
                        border-radius: 10px;
                    }}
                """)
                if hasattr(self, "badge_selected"):
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

            # Swatch outlines for dark mode
            if hasattr(self, "swatch_widgets"):
                for swatch, color_hex in self.swatch_widgets:
                    swatch.setStyleSheet(f"""
                        QLabel {{
                            background-color: {color_hex};
                            border-radius: 11px;
                            border: 1px solid rgba(255, 255, 255, 0.25);
                        }}
                    """)
        else:
            # ---------------------------------------------------------
            # Active App Theme is LIGHT: Render Light Surface Card
            # Harmonized with the active light theme's palette & colors!
            # ---------------------------------------------------------
            card_bg = "#FFFFFF"
            hover_bg = current_palette.bg_base if (current_palette and hasattr(current_palette, "bg_base")) else "#F0FDF4"
            border_color = current_palette.border_light if (current_palette and hasattr(current_palette, "border_light")) else "#CBD5E1"
            title_color = current_palette.text_primary if (current_palette and hasattr(current_palette, "text_primary")) else "#0F172A"
            subtitle_color = current_palette.text_muted if (current_palette and hasattr(current_palette, "text_muted")) else "#64748B"
            app_accent = current_palette.primary if (current_palette and hasattr(current_palette, "primary")) else self.accent_color

            if hasattr(self, "lbl_title"):
                self.lbl_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {title_color}; background: transparent;")
            if hasattr(self, "lbl_subtitle"):
                self.lbl_subtitle.setStyleSheet(f"font-size: 10px; color: {subtitle_color}; font-family: Segoe UI, sans-serif; background: transparent;")

            if self.is_selected:
                self.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: {hover_bg};
                        border: 2.5px solid {self.accent_color};
                        border-radius: 10px;
                    }}
                """)
                if hasattr(self, "badge_selected"):
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
                    self.badge_selected.setVisible(True)
            else:
                self.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: {card_bg};
                        border: 1px solid {border_color};
                        border-radius: 10px;
                    }}
                    QFrame#{obj_name}:hover {{
                        background-color: {hover_bg};
                        border: 1.5px solid {app_accent};
                    }}
                """)
                if hasattr(self, "badge_selected"):
                    self.badge_selected.setVisible(False)

            # Swatch outlines for light mode: crisp subtle border so light colors pop
            if hasattr(self, "swatch_widgets"):
                for swatch, color_hex in self.swatch_widgets:
                    swatch.setStyleSheet(f"""
                        QLabel {{
                            background-color: {color_hex};
                            border-radius: 11px;
                            border: 1px solid rgba(0, 0, 0, 0.18);
                        }}
                    """)

    def set_selected(self, selected: bool):
        """Sets the selected state and refreshes appearance."""
        self.is_selected = selected
        self._update_appearance()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.theme_id)
        super().mousePressEvent(event)
