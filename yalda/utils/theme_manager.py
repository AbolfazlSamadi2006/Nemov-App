#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThemeManager: Centralized Dynamic Multi-Theme Engine for Nemov Sports Management Desktop.
Defines all 17 palettes (12 Dark, 5 Light), tokenized QSS generator, dynamic SVG arrow adaptation,
and live runtime stylesheet application without requiring application restart.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import re

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

import config


@dataclass
class ThemePalette:
    key: str
    name_fa: str
    name_en: str
    is_dark: bool
    bg_base: str
    bg_surface: str
    bg_card: str
    bg_sidebar: str
    primary: str
    primary_hover: str
    primary_pressed: str
    text_primary: str
    text_secondary: str
    text_muted: str
    border: str
    border_light: str
    table_item_selected: str
    header_border: str
    svg_arrow_stroke: str  # '#FFFFFF' (dark) or '#334155' (light)


class _ThemeSignalEmitter(QObject):
    theme_changed = pyqtSignal(str)


_emitter = _ThemeSignalEmitter()


class ThemeManager:
    """
    Centralized dynamic theme manager.
    Coordinates palette definitions, tokenized QSS interpolation,
    vector SVG icon adaptation, and live application switching.
    """

    theme_changed = _emitter.theme_changed
    _current_theme_key: str = "crimson_fury"

    PALETTES: Dict[str, ThemePalette] = {
        # -------------------------------------------------------------
        # 12 Dark Palettes
        # -------------------------------------------------------------
        "crimson_fury": ThemePalette(
            key="crimson_fury",
            name_fa="قرمز آتشین (پیش‌فرض)",
            name_en="Crimson Fury",
            is_dark=True,
            bg_base="#121212",
            bg_surface="#181818",
            bg_card="#1E1E1E",
            bg_sidebar="#161616",
            primary="#8B0000",
            primary_hover="#A91D22",
            primary_pressed="#660000",
            text_primary="#FFFFFF",
            text_secondary="#E0E0E0",
            text_muted="#888888",
            border="#282828",
            border_light="#333333",
            table_item_selected="#4A1113",
            header_border="#8B0000",
            svg_arrow_stroke="#FFFFFF",
        ),
        "royal_gold": ThemePalette(
            key="royal_gold",
            name_fa="طلایی سلطنتی",
            name_en="Royal Gold",
            is_dark=True,
            bg_base="#121212",
            bg_surface="#181816",
            bg_card="#1E1E1B",
            bg_sidebar="#161614",
            primary="#D4AF37",
            primary_hover="#DFBE5B",
            primary_pressed="#B89324",
            text_primary="#FFFFFF",
            text_secondary="#E5E0D0",
            text_muted="#9E9A8A",
            border="#2C2920",
            border_light="#3D382B",
            table_item_selected="#423817",
            header_border="#D4AF37",
            svg_arrow_stroke="#FFFFFF",
        ),
        "neon_pulse": ThemePalette(
            key="neon_pulse",
            name_fa="سبز نئون",
            name_en="Neon Pulse",
            is_dark=True,
            bg_base="#0F1715",
            bg_surface="#14201D",
            bg_card="#1B2B27",
            bg_sidebar="#111C19",
            primary="#10B981",
            primary_hover="#34D399",
            primary_pressed="#059669",
            text_primary="#FFFFFF",
            text_secondary="#D1FAE5",
            text_muted="#6EE7B7",
            border="#203831",
            border_light="#2C4F45",
            table_item_selected="#064E3B",
            header_border="#10B981",
            svg_arrow_stroke="#FFFFFF",
        ),
        "electric_cyan": ThemePalette(
            key="electric_cyan",
            name_fa="آبی الکتریک",
            name_en="Electric Cyan",
            is_dark=True,
            bg_base="#0E1720",
            bg_surface="#142230",
            bg_card="#1B2E42",
            bg_sidebar="#101C28",
            primary="#06B6D4",
            primary_hover="#22D3EE",
            primary_pressed="#0891B2",
            text_primary="#FFFFFF",
            text_secondary="#CFFAFE",
            text_muted="#67E8F9",
            border="#213952",
            border_light="#2E4F72",
            table_item_selected="#164E63",
            header_border="#06B6D4",
            svg_arrow_stroke="#FFFFFF",
        ),
        "cyber_amethyst": ThemePalette(
            key="cyber_amethyst",
            name_fa="بنفش سایبری",
            name_en="Cyber Amethyst",
            is_dark=True,
            bg_base="#13101C",
            bg_surface="#1A1627",
            bg_card="#241E36",
            bg_sidebar="#161321",
            primary="#8B5CF6",
            primary_hover="#A78BFA",
            primary_pressed="#7C3AED",
            text_primary="#FFFFFF",
            text_secondary="#EDE9FE",
            text_muted="#A78BFA",
            border="#2F2648",
            border_light="#413463",
            table_item_selected="#4C1D95",
            header_border="#8B5CF6",
            svg_arrow_stroke="#FFFFFF",
        ),
        "solar_blaze": ThemePalette(
            key="solar_blaze",
            name_fa="شعله خورشیدی",
            name_en="Solar Blaze",
            is_dark=True,
            bg_base="#16120E",
            bg_surface="#201914",
            bg_card="#2C221B",
            bg_sidebar="#1A1410",
            primary="#F97316",
            primary_hover="#FB923C",
            primary_pressed="#EA580C",
            text_primary="#FFFFFF",
            text_secondary="#FFEDD5",
            text_muted="#FDBA74",
            border="#392B21",
            border_light="#4F3A2B",
            table_item_selected="#7C2D12",
            header_border="#F97316",
            svg_arrow_stroke="#FFFFFF",
        ),
        "stealth_silver": ThemePalette(
            key="stealth_silver",
            name_fa="نقره‌ای سربی",
            name_en="Stealth Silver",
            is_dark=True,
            bg_base="#141619",
            bg_surface="#1C2024",
            bg_card="#262B31",
            bg_sidebar="#181B1F",
            primary="#94A3B8",
            primary_hover="#CBD5E1",
            primary_pressed="#64748B",
            text_primary="#FFFFFF",
            text_secondary="#F1F5F9",
            text_muted="#94A3B8",
            border="#333942",
            border_light="#47505C",
            table_item_selected="#334155",
            header_border="#94A3B8",
            svg_arrow_stroke="#FFFFFF",
        ),
        "arctic_ice": ThemePalette(
            key="arctic_ice",
            name_fa="آبی یخی",
            name_en="Arctic Ice",
            is_dark=True,
            bg_base="#0C1622",
            bg_surface="#122031",
            bg_card="#192C44",
            bg_sidebar="#0E1B2B",
            primary="#38BDF8",
            primary_hover="#7DD3FC",
            primary_pressed="#0284C7",
            text_primary="#FFFFFF",
            text_secondary="#E0F2FE",
            text_muted="#7DD3FC",
            border="#1E3553",
            border_light="#2B4A73",
            table_item_selected="#075985",
            header_border="#38BDF8",
            svg_arrow_stroke="#FFFFFF",
        ),
        "magenta_force": ThemePalette(
            key="magenta_force",
            name_fa="ماژنتای پرقدرت",
            name_en="Magenta Force",
            is_dark=True,
            bg_base="#180F16",
            bg_surface="#231520",
            bg_card="#301D2C",
            bg_sidebar="#1C111A",
            primary="#EC4899",
            primary_hover="#F472B6",
            primary_pressed="#DB2777",
            text_primary="#FFFFFF",
            text_secondary="#FCE7F3",
            text_muted="#F472B6",
            border="#3D2437",
            border_light="#54314C",
            table_item_selected="#831843",
            header_border="#EC4899",
            svg_arrow_stroke="#FFFFFF",
        ),
        "bronze_titan": ThemePalette(
            key="bronze_titan",
            name_fa="تایتان برنزی",
            name_en="Bronze Titan",
            is_dark=True,
            bg_base="#15120E",
            bg_surface="#1F1A14",
            bg_card="#2B231B",
            bg_sidebar="#18140F",
            primary="#CD7F32",
            primary_hover="#D98C42",
            primary_pressed="#B45309",
            text_primary="#FFFFFF",
            text_secondary="#FEF3C7",
            text_muted="#D97706",
            border="#382E23",
            border_light="#4D3F30",
            table_item_selected="#78350F",
            header_border="#CD7F32",
            svg_arrow_stroke="#FFFFFF",
        ),
        "national_pride": ThemePalette(
            key="national_pride",
            name_fa="غرور ملی (ایران)",
            name_en="National Pride",
            is_dark=True,
            bg_base="#0F1713",
            bg_surface="#14221C",
            bg_card="#1B2E26",
            bg_sidebar="#111C17",
            primary="#15803D",
            primary_hover="#16A34A",
            primary_pressed="#166534",
            text_primary="#FFFFFF",
            text_secondary="#DCFCE7",
            text_muted="#86EFAC",
            border="#203C30",
            border_light="#2B5342",
            table_item_selected="#14532D",
            header_border="#DC2626",
            svg_arrow_stroke="#FFFFFF",
        ),
        "oled_obsidian": ThemePalette(
            key="oled_obsidian",
            name_fa="مشکی خالص OLED",
            name_en="OLED Obsidian",
            is_dark=True,
            bg_base="#000000",
            bg_surface="#0A0A0A",
            bg_card="#141414",
            bg_sidebar="#050505",
            primary="#E11D48",
            primary_hover="#F43F5E",
            primary_pressed="#BE123C",
            text_primary="#FFFFFF",
            text_secondary="#E5E5E5",
            text_muted="#737373",
            border="#262626",
            border_light="#404040",
            table_item_selected="#4C0519",
            header_border="#E11D48",
            svg_arrow_stroke="#FFFFFF",
        ),
        # -------------------------------------------------------------
        # 5 Light Palettes
        # -------------------------------------------------------------
        "olympic_white": ThemePalette(
            key="olympic_white",
            name_fa="سفید المپیک",
            name_en="Olympic White",
            is_dark=False,
            bg_base="#F8FAFC",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F1F5F9",
            primary="#2563EB",
            primary_hover="#3B82F6",
            primary_pressed="#1D4ED8",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_item_selected="#DBEAFE",
            header_border="#2563EB",
            svg_arrow_stroke="#334155",
        ),
        "clinical_cyan": ThemePalette(
            key="clinical_cyan",
            name_fa="فیروزه‌ای درمانی",
            name_en="Clinical Cyan",
            is_dark=False,
            bg_base="#F0FDFA",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#CCFBF1",
            primary="#0891B2",
            primary_hover="#06B6D4",
            primary_pressed="#0E7490",
            text_primary="#134E4A",
            text_secondary="#115E59",
            text_muted="#64748B",
            border="#99F6E4",
            border_light="#5EEAD4",
            table_item_selected="#CFFAFE",
            header_border="#0891B2",
            svg_arrow_stroke="#334155",
        ),
        "fresh_mint": ThemePalette(
            key="fresh_mint",
            name_fa="نعناع تازه",
            name_en="Fresh Mint",
            is_dark=False,
            bg_base="#F0FDF4",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#DCFCE7",
            primary="#059669",
            primary_hover="#10B981",
            primary_pressed="#047857",
            text_primary="#064E3B",
            text_secondary="#065F46",
            text_muted="#6B7280",
            border="#A7F3D0",
            border_light="#6EE7B7",
            table_item_selected="#D1FAE5",
            header_border="#059669",
            svg_arrow_stroke="#334155",
        ),
        "champagne_gold": ThemePalette(
            key="champagne_gold",
            name_fa="طلایی شامپاینی",
            name_en="Champagne Gold",
            is_dark=False,
            bg_base="#FEFCE8",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#FEF9C3",
            primary="#B45309",
            primary_hover="#D97706",
            primary_pressed="#92400E",
            text_primary="#451A03",
            text_secondary="#78350F",
            text_muted="#78716C",
            border="#FDE68A",
            border_light="#FCD34D",
            table_item_selected="#FEF3C7",
            header_border="#B45309",
            svg_arrow_stroke="#334155",
        ),
        "soft_orchid": ThemePalette(
            key="soft_orchid",
            name_fa="ارکیده ملایم",
            name_en="Soft Orchid",
            is_dark=False,
            bg_base="#FAF5FF",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F3E8FF",
            primary="#7C3AED",
            primary_hover="#8B5CF6",
            primary_pressed="#6D28D9",
            text_primary="#3B0764",
            text_secondary="#581C87",
            text_muted="#701A75",
            border="#E9D5FF",
            border_light="#D8B4FE",
            table_item_selected="#EDE9FE",
            header_border="#7C3AED",
            svg_arrow_stroke="#334155",
        ),
    }

    @classmethod
    def get_current_theme_key(cls) -> str:
        """Returns the currently active theme identifier."""
        return cls._current_theme_key

    @classmethod
    def get_current_palette(cls) -> ThemePalette:
        """Returns ThemePalette for the currently active theme."""
        return cls.PALETTES.get(cls._current_theme_key, cls.PALETTES["crimson_fury"])

    @classmethod
    def get_active_theme(cls) -> ThemePalette:
        """Alias for get_current_palette for consistent API access."""
        return cls.get_current_palette()

    @classmethod
    def update_svg_arrows(cls, stroke_color: str):
        """
        Adapts SVG arrow icons so they remain crisp against light or dark inputs.
        Injects stroke_color ('#334155' for light, '#FFFFFF' for dark).
        """
        for filename in ["arrow_down.svg", "arrow_up.svg"]:
            svg_path = config.BASE_DIR / "resources" / "images" / filename
            if svg_path.exists():
                try:
                    content = svg_path.read_text(encoding="utf-8")
                    new_content = re.sub(r'stroke="[^"]+"', f'stroke="{stroke_color}"', content)
                    if new_content != content:
                        svg_path.write_text(new_content, encoding="utf-8")
                except Exception:
                    pass

    @classmethod
    def generate_qss(cls, theme_key: str) -> str:
        """
        Generates fully interpolated QSS stylesheet string for the specified theme key.
        Replaces all color tokens with palette values and resolves absolute SVG paths.
        """
        palette = cls.PALETTES.get(theme_key, cls.PALETTES["crimson_fury"])

        # Asset paths
        arrow_down_path = (config.BASE_DIR / "resources" / "images" / "arrow_down.svg").as_posix()
        arrow_up_path = (config.BASE_DIR / "resources" / "images" / "arrow_up.svg").as_posix()
        check_path = (config.BASE_DIR / "resources" / "images" / "check.svg").as_posix()

        # Derived tokens for dark vs light modes
        if palette.is_dark:
            btn_sec_bg = "#2D2D2D"
            btn_sec_text = "#CCCCCC"
            btn_sec_border = "#444444"
            btn_sec_hover = "#3D3D3D"
            header_bg = "#222222"
            header_text = "#FFFFFF"
            input_bg = palette.bg_card
            table_bg = palette.bg_base
            scrollbar_bg = palette.bg_base
            scrollbar_handle = "#333333"
            indicator_bg = "#1A1A1A"
            indicator_border = "#666666"
        else:
            btn_sec_bg = "#F1F5F9"
            btn_sec_text = "#334155"
            btn_sec_border = "#CBD5E1"
            btn_sec_hover = "#E2E8F0"
            header_bg = "#F8FAFC"
            header_text = "#0F172A"
            input_bg = "#FFFFFF"
            table_bg = "#FFFFFF"
            scrollbar_bg = "#F1F5F9"
            scrollbar_handle = "#CBD5E1"
            indicator_bg = "#FFFFFF"
            indicator_border = "#94A3B8"

        qss = f"""
/* Generated by Nemov ThemeManager for '{palette.name_en}' ({palette.key}) */

QWidget {{
    background-color: {palette.bg_base};
    color: {palette.text_primary};
    font-family: "Vazirmatn", "Segoe UI", sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {palette.bg_base};
}}

/* Header Bar & Frames */
QFrame#sidebar {{
    background-color: {palette.bg_sidebar};
    border-left: 1px solid {palette.border};
}}

QFrame#card {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: 8px;
    padding: 12px;
}}

/* Headings & Labels */
QLabel {{
    background-color: transparent;
    color: {palette.text_primary};
}}

QLabel#h1 {{
    font-size: 20px;
    font-weight: bold;
    color: {palette.text_primary};
}}

QLabel#h2 {{
    font-size: 16px;
    font-weight: bold;
    color: {palette.primary};
}}

QLabel#accent_text {{
    color: {palette.primary_hover};
    font-weight: bold;
}}

QLabel#muted_text {{
    color: {palette.text_muted};
}}

/* Buttons */
QPushButton {{
    background-color: {palette.primary};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {palette.primary_hover};
}}

QPushButton:pressed {{
    background-color: {palette.primary_pressed};
}}

QPushButton:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
}}

QPushButton#secondary_button {{
    background-color: {btn_sec_bg};
    color: {btn_sec_text};
    border: 1px solid {btn_sec_border};
}}

QPushButton#secondary_button:hover {{
    background-color: {btn_sec_hover};
    color: {palette.text_primary};
}}

QPushButton#secondary_button:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
    border: 1px solid {btn_sec_border};
}}

QPushButton#back_button {{
    background-color: {btn_sec_bg};
    color: {btn_sec_text};
    border: 1px solid {btn_sec_border};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 13px;
}}

QPushButton#back_button:hover {{
    background-color: {btn_sec_hover};
    color: {palette.text_primary};
    border-color: {palette.primary};
}}

QPushButton#back_button:pressed {{
    background-color: {palette.bg_base};
}}

QPushButton#undo_button, QPushButton#redo_button {{
    background-color: {btn_sec_bg};
    color: {btn_sec_text};
    border: 1px solid {btn_sec_border};
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: bold;
    font-size: 12px;
}}

QPushButton#undo_button:hover, QPushButton#redo_button:hover {{
    background-color: {btn_sec_hover};
    color: {palette.text_primary};
    border-color: {palette.primary};
}}

QPushButton#undo_button:disabled, QPushButton#redo_button:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
    border: 1px solid {palette.border};
}}

QPushButton#danger_button {{
    background-color: #DC2626;
    color: #FFFFFF;
}}

QPushButton#danger_button:hover {{
    background-color: #B91C1C;
}}

/* Inputs & ComboBox */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QComboBox {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border_light};
    border-radius: 6px;
    padding: 6px 12px;
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {palette.primary};
}}

QComboBox {{
    padding-left: 32px;
    padding-right: 12px;
}}

QComboBox:editable {{
    background-color: {input_bg};
    color: {palette.text_primary};
}}

QComboBox QLineEdit {{
    background: transparent;
    color: {palette.text_primary};
    border: none;
    padding: 0px 4px;
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top left;
    width: 28px;
    border-right: 1px solid {palette.border_light};
    background-color: {btn_sec_bg};
    border-top-left-radius: 5px;
    border-bottom-left-radius: 5px;
}}

QComboBox::down-arrow {{
    image: url({arrow_down_path});
    width: 14px;
    height: 14px;
}}

QComboBox QAbstractItemView {{
    background-color: {palette.bg_card};
    color: {palette.text_primary};
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
    padding: 4px;
    border: 1px solid {palette.border};
}}

/* SpinBox & DoubleSpinBox Styling */
QSpinBox, QDoubleSpinBox {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border_light};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 13px;
    font-weight: bold;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top left;
    width: 24px;
    border-right: 1px solid {palette.border_light};
    border-bottom: 1px solid {palette.border_light};
    background-color: {btn_sec_bg};
    border-top-left-radius: 5px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({arrow_up_path});
    width: 12px;
    height: 12px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom left;
    width: 24px;
    border-right: 1px solid {palette.border_light};
    background-color: {btn_sec_bg};
    border-bottom-left-radius: 5px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({arrow_down_path});
    width: 12px;
    height: 12px;
}}

/* Tables */
QTableWidget {{
    background-color: {table_bg};
    color: {palette.text_primary};
    gridline-color: {palette.border};
    border: 1px solid {palette.border};
    border-radius: 6px;
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
    outline: 0;
}}

QTableWidget::item {{
    padding: 6px 8px;
    font-size: 13px;
    color: {palette.text_primary};
}}

QTableWidget::item:selected,
QTableWidget::item:alternate:selected {{
    background-color: {palette.table_item_selected};
    color: {palette.text_primary};
}}

QHeaderView::section {{
    background-color: {header_bg};
    color: {header_text};
    padding: 10px 6px;
    font-weight: bold;
    font-size: 13px;
    border: none;
    border-bottom: 2px solid {palette.header_border};
}}

/* Specific styling for inputs embedded inside QTableWidget */
QTableWidget QLineEdit {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border_light};
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 32px;
    font-size: 13px;
}}

QTableWidget QLineEdit:focus {{
    border: 1px solid {palette.primary};
    background-color: {input_bg};
}}

QTableWidget QComboBox {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border_light};
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 32px;
    font-size: 13px;
}}

QTableWidget QComboBox:focus {{
    border: 1px solid {palette.primary};
}}

QTableWidget QPushButton {{
    min-height: 30px;
    padding: 2px 4px;
    font-size: 12px;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {palette.border};
    background-color: {palette.bg_card};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {palette.bg_base};
    color: {palette.text_muted};
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-left: 2px;
}}

QTabBar::tab:selected {{
    background-color: {palette.bg_card};
    color: {palette.text_primary};
    border-top: 3px solid {palette.primary};
    font-weight: bold;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {scrollbar_bg};
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {palette.primary};
}}

QScrollBar:horizontal {{
    background: {scrollbar_bg};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: {scrollbar_handle};
    border-radius: 5px;
}}

/* Radio Buttons */
QRadioButton {{
    color: {palette.text_primary};
    spacing: 10px;
    font-size: 13px;
    background: transparent;
    padding: 3px 0px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid {indicator_border};
    background-color: {indicator_bg};
}}

QRadioButton::indicator:hover {{
    border: 2px solid {palette.primary_hover};
}}

QRadioButton::indicator:checked {{
    border: 2px solid {palette.primary};
    background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.45, fx: 0.5, fy: 0.5,
        stop: 0 #FFFFFF, stop: 0.45 #FFFFFF,
        stop: 0.46 {palette.primary}, stop: 1 {palette.primary});
}}

QRadioButton::indicator:checked:hover {{
    border: 2px solid {palette.primary_hover};
    background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.45, fx: 0.5, fy: 0.5,
        stop: 0 #FFFFFF, stop: 0.45 #FFFFFF,
        stop: 0.46 {palette.primary_hover}, stop: 1 {palette.primary_hover});
}}

QRadioButton::indicator:disabled {{
    border: 2px solid {palette.border};
    background-color: {btn_sec_bg};
}}

/* Checkboxes */
QCheckBox {{
    color: {palette.text_primary};
    spacing: 10px;
    font-size: 13px;
    background: transparent;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {indicator_border};
    background-color: {indicator_bg};
}}

QCheckBox::indicator:hover {{
    border: 2px solid {palette.primary_hover};
}}

QCheckBox::indicator:checked {{
    border: 2px solid {palette.primary};
    background-color: {palette.primary};
    image: url({check_path});
}}

QCheckBox::indicator:checked:hover {{
    border: 2px solid {palette.primary_hover};
    background-color: {palette.primary_hover};
}}

QCheckBox::indicator:disabled {{
    border: 2px solid {palette.border};
    background-color: {btn_sec_bg};
}}
"""
        return qss

    @classmethod
    def apply_theme(cls, theme_key: str, app: Optional[QApplication] = None) -> bool:
        """
        Applies specified theme live to QApplication instance.
        If theme_key is unknown, gracefully falls back to 'crimson_fury'.
        Emits theme_changed(theme_key) Qt signal.
        """
        target_key = theme_key if theme_key in cls.PALETTES else "crimson_fury"
        cls._current_theme_key = target_key
        palette = cls.PALETTES[target_key]

        # 1. Adapt vector SVG arrows (white for dark themes, dark slate for light themes)
        cls.update_svg_arrows(palette.svg_arrow_stroke)

        # 2. Generate and apply tokenized QSS stylesheet
        qss_content = cls.generate_qss(target_key)
        target_app = app or QApplication.instance()
        if target_app:
            target_app.setStyleSheet(qss_content)

        # 3. Notify all listeners live via Qt signal
        cls.theme_changed.emit(target_key)
        return True

    @classmethod
    def apply_saved_theme(cls, app: Optional[QApplication] = None) -> bool:
        """
        Reads stored selected_theme_id from BrandingService and applies it on startup.
        """
        try:
            from yalda.services.branding_service import BrandingService
            saved_key = BrandingService.get_selected_theme_id()
        except Exception:
            saved_key = "crimson_fury"

        return cls.apply_theme(saved_key, app)


# Module-level convenience bindings
PALETTES = ThemeManager.PALETTES
apply_theme = ThemeManager.apply_theme
apply_saved_theme = ThemeManager.apply_saved_theme
get_current_theme_key = ThemeManager.get_current_theme_key
get_current_palette = ThemeManager.get_current_palette
theme_changed = ThemeManager.theme_changed
