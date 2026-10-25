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

    # Surfaces & Canvas
    bg_dialog: str = ""

    # Interactive Accents
    primary_text: str = "#FFFFFF"

    # Secondary Buttons & Controls
    btn_sec_bg: str = ""
    btn_sec_text: str = ""
    btn_sec_border: str = ""
    btn_sec_hover: str = ""

    # Tables & Headers
    table_bg: str = ""
    table_grid: str = ""
    table_header_bg: str = ""
    table_header_text: str = ""

    # Form Inputs
    input_bg: str = ""
    input_border: str = ""
    input_focus_border: str = ""

    # Scrollbars & Indicators
    scrollbar_bg: str = ""
    scrollbar_handle: str = ""
    scrollbar_handle_hover: str = ""
    indicator_bg: str = ""
    indicator_border: str = ""

    # Status & Badges
    badge_bg: str = ""
    badge_text: str = ""

    def __post_init__(self):
        if not self.bg_dialog:
            self.bg_dialog = self.bg_base
        if not self.primary_text:
            self.primary_text = "#FFFFFF"
        if not self.btn_sec_bg:
            self.btn_sec_bg = "#252525" if self.is_dark else "#F1F5F9"
        if not self.btn_sec_text:
            self.btn_sec_text = "#CCCCCC" if self.is_dark else "#334155"
        if not self.btn_sec_border:
            self.btn_sec_border = self.border_light if self.is_dark else "#CBD5E1"
        if not self.btn_sec_hover:
            self.btn_sec_hover = "#303030" if self.is_dark else "#E2E8F0"
        if not self.table_bg:
            self.table_bg = self.bg_base if self.is_dark else "#FFFFFF"
        if not self.table_grid:
            self.table_grid = self.border
        if not self.table_header_bg:
            self.table_header_bg = self.bg_surface if self.is_dark else "#F8FAFC"
        if not self.table_header_text:
            self.table_header_text = "#FFFFFF" if self.is_dark else "#0F172A"
        if not self.input_bg:
            self.input_bg = self.bg_card if self.is_dark else "#FFFFFF"
        if not self.input_border:
            self.input_border = self.border_light
        if not self.input_focus_border:
            self.input_focus_border = self.primary
        if not self.scrollbar_bg:
            self.scrollbar_bg = self.bg_base if self.is_dark else "#F1F5F9"
        if not self.scrollbar_handle:
            self.scrollbar_handle = self.border_light if self.is_dark else "#CBD5E1"
        if not self.scrollbar_handle_hover:
            self.scrollbar_handle_hover = self.primary
        if not self.indicator_bg:
            self.indicator_bg = self.bg_card if self.is_dark else "#FFFFFF"
        if not self.indicator_border:
            self.indicator_border = self.border_light if self.is_dark else "#94A3B8"
        if not self.badge_bg:
            self.badge_bg = self.bg_card
        if not self.badge_text:
            self.badge_text = self.primary_hover if self.is_dark else self.primary

    @property
    def bg_input(self) -> str:
        return self.input_bg

    @property
    def text_on_primary(self) -> str:
        return self.primary_text

    @property
    def bg_elevated(self) -> str:
        return self.bg_surface


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
            bg_dialog="#121212",
            primary="#8B0000",
            primary_hover="#A91D22",
            primary_pressed="#660000",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#E0E0E0",
            text_muted="#888888",
            btn_sec_bg="#252525",
            btn_sec_text="#E0E0E0",
            btn_sec_border="#3D3D3D",
            btn_sec_hover="#303030",
            border="#282828",
            border_light="#333333",
            table_bg="#121212",
            table_grid="#282828",
            table_header_bg="#1A1A1A",
            table_header_text="#FFFFFF",
            table_item_selected="#4A1113",
            header_border="#8B0000",
            input_bg="#1E1E1E",
            input_border="#333333",
            input_focus_border="#8B0000",
            scrollbar_bg="#121212",
            scrollbar_handle="#333333",
            scrollbar_handle_hover="#8B0000",
            indicator_bg="#1E1E1E",
            indicator_border="#666666",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#1E1E1E",
            badge_text="#A91D22",
        ),
        "royal_gold": ThemePalette(
            key="royal_gold",
            name_fa="طلایی سلطنتی",
            name_en="Royal Gold",
            is_dark=True,
            bg_base="#14130F",
            bg_surface="#1B1914",
            bg_card="#23201A",
            bg_sidebar="#171511",
            bg_dialog="#14130F",
            primary="#D4AF37",
            primary_hover="#DFBE5B",
            primary_pressed="#B89324",
            primary_text="#14130F",
            text_primary="#FFFFFF",
            text_secondary="#E5E0D0",
            text_muted="#9E9A8A",
            btn_sec_bg="#2A261D",
            btn_sec_text="#E5E0D0",
            btn_sec_border="#453E2E",
            btn_sec_hover="#383325",
            border="#383325",
            border_light="#4D4633",
            table_bg="#14130F",
            table_grid="#383325",
            table_header_bg="#1B1914",
            table_header_text="#FFFFFF",
            table_item_selected="#423817",
            header_border="#D4AF37",
            input_bg="#23201A",
            input_border="#4D4633",
            input_focus_border="#D4AF37",
            scrollbar_bg="#14130F",
            scrollbar_handle="#453E2E",
            scrollbar_handle_hover="#D4AF37",
            indicator_bg="#23201A",
            indicator_border="#665D46",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#23201A",
            badge_text="#DFBE5B",
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
            bg_dialog="#0F1715",
            primary="#10B981",
            primary_hover="#34D399",
            primary_pressed="#059669",
            primary_text="#0F1715",
            text_primary="#FFFFFF",
            text_secondary="#D1FAE5",
            text_muted="#6EE7B7",
            btn_sec_bg="#1E302B",
            btn_sec_text="#D1FAE5",
            btn_sec_border="#2C4F45",
            btn_sec_hover="#263D37",
            border="#203831",
            border_light="#2C4F45",
            table_bg="#0F1715",
            table_grid="#203831",
            table_header_bg="#14201D",
            table_header_text="#FFFFFF",
            table_item_selected="#064E3B",
            header_border="#10B981",
            input_bg="#1B2B27",
            input_border="#2C4F45",
            input_focus_border="#10B981",
            scrollbar_bg="#0F1715",
            scrollbar_handle="#2C4F45",
            scrollbar_handle_hover="#10B981",
            indicator_bg="#1B2B27",
            indicator_border="#407062",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#1B2B27",
            badge_text="#34D399",
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
            bg_dialog="#0E1720",
            primary="#06B6D4",
            primary_hover="#22D3EE",
            primary_pressed="#0891B2",
            primary_text="#0E1720",
            text_primary="#FFFFFF",
            text_secondary="#CFFAFE",
            text_muted="#67E8F9",
            btn_sec_bg="#1F3349",
            btn_sec_text="#CFFAFE",
            btn_sec_border="#2E4F72",
            btn_sec_hover="#284361",
            border="#213952",
            border_light="#2E4F72",
            table_bg="#0E1720",
            table_grid="#213952",
            table_header_bg="#142230",
            table_header_text="#FFFFFF",
            table_item_selected="#164E63",
            header_border="#06B6D4",
            input_bg="#1B2E42",
            input_border="#2E4F72",
            input_focus_border="#06B6D4",
            scrollbar_bg="#0E1720",
            scrollbar_handle="#2E4F72",
            scrollbar_handle_hover="#06B6D4",
            indicator_bg="#1B2E42",
            indicator_border="#3E6B99",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#1B2E42",
            badge_text="#22D3EE",
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
            bg_dialog="#13101C",
            primary="#8B5CF6",
            primary_hover="#A78BFA",
            primary_pressed="#7C3AED",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#EDE9FE",
            text_muted="#A78BFA",
            btn_sec_bg="#2A2240",
            btn_sec_text="#EDE9FE",
            btn_sec_border="#413463",
            btn_sec_hover="#372D54",
            border="#2F2648",
            border_light="#413463",
            table_bg="#13101C",
            table_grid="#2F2648",
            table_header_bg="#1A1627",
            table_header_text="#FFFFFF",
            table_item_selected="#4C1D95",
            header_border="#8B5CF6",
            input_bg="#241E36",
            input_border="#413463",
            input_focus_border="#8B5CF6",
            scrollbar_bg="#13101C",
            scrollbar_handle="#413463",
            scrollbar_handle_hover="#8B5CF6",
            indicator_bg="#241E36",
            indicator_border="#5C4A8A",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#241E36",
            badge_text="#A78BFA",
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
            bg_dialog="#16120E",
            primary="#F97316",
            primary_hover="#FB923C",
            primary_pressed="#EA580C",
            primary_text="#18120C",
            text_primary="#FFFFFF",
            text_secondary="#FFEDD5",
            text_muted="#FDBA74",
            btn_sec_bg="#33251D",
            btn_sec_text="#FFEDD5",
            btn_sec_border="#4F3A2B",
            btn_sec_hover="#423026",
            border="#392B21",
            border_light="#4F3A2B",
            table_bg="#16120E",
            table_grid="#392B21",
            table_header_bg="#201914",
            table_header_text="#FFFFFF",
            table_item_selected="#7C2D12",
            header_border="#F97316",
            input_bg="#2C221B",
            input_border="#4F3A2B",
            input_focus_border="#F97316",
            scrollbar_bg="#16120E",
            scrollbar_handle="#4F3A2B",
            scrollbar_handle_hover="#F97316",
            indicator_bg="#2C221B",
            indicator_border="#70533E",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#2C221B",
            badge_text="#FB923C",
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
            bg_dialog="#141619",
            primary="#94A3B8",
            primary_hover="#CBD5E1",
            primary_pressed="#64748B",
            primary_text="#121316",
            text_primary="#FFFFFF",
            text_secondary="#F1F5F9",
            text_muted="#94A3B8",
            btn_sec_bg="#282E36",
            btn_sec_text="#F1F5F9",
            btn_sec_border="#47505C",
            btn_sec_hover="#363D47",
            border="#333942",
            border_light="#47505C",
            table_bg="#141619",
            table_grid="#333942",
            table_header_bg="#1C2024",
            table_header_text="#FFFFFF",
            table_item_selected="#334155",
            header_border="#94A3B8",
            input_bg="#262B31",
            input_border="#47505C",
            input_focus_border="#94A3B8",
            scrollbar_bg="#141619",
            scrollbar_handle="#47505C",
            scrollbar_handle_hover="#94A3B8",
            indicator_bg="#262B31",
            indicator_border="#64748B",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#262B31",
            badge_text="#CBD5E1",
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
            bg_dialog="#0C1622",
            primary="#38BDF8",
            primary_hover="#7DD3FC",
            primary_pressed="#0284C7",
            primary_text="#0B131B",
            text_primary="#FFFFFF",
            text_secondary="#E0F2FE",
            text_muted="#7DD3FC",
            btn_sec_bg="#1B2F48",
            btn_sec_text="#E0F2FE",
            btn_sec_border="#2B4A73",
            btn_sec_hover="#243E5E",
            border="#1E3553",
            border_light="#2B4A73",
            table_bg="#0C1622",
            table_grid="#1E3553",
            table_header_bg="#122031",
            table_header_text="#FFFFFF",
            table_item_selected="#075985",
            header_border="#38BDF8",
            input_bg="#192C44",
            input_border="#2B4A73",
            input_focus_border="#38BDF8",
            scrollbar_bg="#0C1622",
            scrollbar_handle="#2B4A73",
            scrollbar_handle_hover="#38BDF8",
            indicator_bg="#192C44",
            indicator_border="#3D689E",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#192C44",
            badge_text="#7DD3FC",
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
            bg_dialog="#180F16",
            primary="#EC4899",
            primary_hover="#F472B6",
            primary_pressed="#DB2777",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#FCE7F3",
            text_muted="#F472B6",
            btn_sec_bg="#341E30",
            btn_sec_text="#FCE7F3",
            btn_sec_border="#54314C",
            btn_sec_hover="#44273E",
            border="#3D2437",
            border_light="#54314C",
            table_bg="#180F16",
            table_grid="#3D2437",
            table_header_bg="#231520",
            table_header_text="#FFFFFF",
            table_item_selected="#831843",
            header_border="#EC4899",
            input_bg="#301D2C",
            input_border="#54314C",
            input_focus_border="#EC4899",
            scrollbar_bg="#180F16",
            scrollbar_handle="#54314C",
            scrollbar_handle_hover="#EC4899",
            indicator_bg="#301D2C",
            indicator_border="#7A456E",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#301D2C",
            badge_text="#F472B6",
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
            bg_dialog="#15120E",
            primary="#CD7F32",
            primary_hover="#D98C42",
            primary_pressed="#B45309",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#FEF3C7",
            text_muted="#D97706",
            btn_sec_bg="#30261D",
            btn_sec_text="#FEF3C7",
            btn_sec_border="#4D3F30",
            btn_sec_hover="#403327",
            border="#382E23",
            border_light="#4D3F30",
            table_bg="#15120E",
            table_grid="#382E23",
            table_header_bg="#1F1A14",
            table_header_text="#FFFFFF",
            table_item_selected="#78350F",
            header_border="#CD7F32",
            input_bg="#2B231B",
            input_border="#4D3F30",
            input_focus_border="#CD7F32",
            scrollbar_bg="#15120E",
            scrollbar_handle="#4D3F30",
            scrollbar_handle_hover="#CD7F32",
            indicator_bg="#2B231B",
            indicator_border="#6E5944",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#2B231B",
            badge_text="#D98C42",
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
            bg_dialog="#0F1713",
            primary="#15803D",
            primary_hover="#16A34A",
            primary_pressed="#166534",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#DCFCE7",
            text_muted="#86EFAC",
            btn_sec_bg="#1E332B",
            btn_sec_text="#DCFCE7",
            btn_sec_border="#2B5342",
            btn_sec_hover="#284439",
            border="#203C30",
            border_light="#2B5342",
            table_bg="#0F1713",
            table_grid="#203C30",
            table_header_bg="#14221C",
            table_header_text="#FFFFFF",
            table_item_selected="#14532D",
            header_border="#DC2626",
            input_bg="#1B2E26",
            input_border="#2B5342",
            input_focus_border="#15803D",
            scrollbar_bg="#0F1713",
            scrollbar_handle="#2B5342",
            scrollbar_handle_hover="#15803D",
            indicator_bg="#1B2E26",
            indicator_border="#3E755D",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#1B2E26",
            badge_text="#16A34A",
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
            bg_dialog="#000000",
            primary="#E11D48",
            primary_hover="#F43F5E",
            primary_pressed="#BE123C",
            primary_text="#FFFFFF",
            text_primary="#FFFFFF",
            text_secondary="#E5E5E5",
            text_muted="#737373",
            btn_sec_bg="#1A1A1A",
            btn_sec_text="#E5E5E5",
            btn_sec_border="#404040",
            btn_sec_hover="#262626",
            border="#262626",
            border_light="#404040",
            table_bg="#000000",
            table_grid="#262626",
            table_header_bg="#0A0A0A",
            table_header_text="#FFFFFF",
            table_item_selected="#4C0519",
            header_border="#E11D48",
            input_bg="#141414",
            input_border="#404040",
            input_focus_border="#E11D48",
            scrollbar_bg="#000000",
            scrollbar_handle="#404040",
            scrollbar_handle_hover="#E11D48",
            indicator_bg="#141414",
            indicator_border="#525252",
            svg_arrow_stroke="#FFFFFF",
            badge_bg="#141414",
            badge_text="#F43F5E",
        ),
        # -------------------------------------------------------------
        # 5 Light Palettes (Strict 9router Architecture)
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
            bg_dialog="#F8FAFC",
            primary="#2563EB",
            primary_hover="#3B82F6",
            primary_pressed="#1D4ED8",
            primary_text="#FFFFFF",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            btn_sec_bg="#F1F5F9",
            btn_sec_text="#334155",
            btn_sec_border="#CBD5E1",
            btn_sec_hover="#E2E8F0",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_bg="#FFFFFF",
            table_grid="#E2E8F0",
            table_header_bg="#F8FAFC",
            table_header_text="#0F172A",
            table_item_selected="#DBEAFE",
            header_border="#2563EB",
            input_bg="#FFFFFF",
            input_border="#CBD5E1",
            input_focus_border="#2563EB",
            scrollbar_bg="#F1F5F9",
            scrollbar_handle="#CBD5E1",
            scrollbar_handle_hover="#2563EB",
            indicator_bg="#FFFFFF",
            indicator_border="#94A3B8",
            svg_arrow_stroke="#334155",
            badge_bg="#F1F5F9",
            badge_text="#2563EB",
        ),
        "clinical_cyan": ThemePalette(
            key="clinical_cyan",
            name_fa="فیروزه‌ای درمانی",
            name_en="Clinical Cyan",
            is_dark=False,
            bg_base="#F0FDFA",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F8FAFC",
            bg_dialog="#F0FDFA",
            primary="#0891B2",
            primary_hover="#06B6D4",
            primary_pressed="#0E7490",
            primary_text="#FFFFFF",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            btn_sec_bg="#F1F5F9",
            btn_sec_text="#334155",
            btn_sec_border="#CBD5E1",
            btn_sec_hover="#E2E8F0",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_bg="#FFFFFF",
            table_grid="#E2E8F0",
            table_header_bg="#F8FAFC",
            table_header_text="#0F172A",
            table_item_selected="#CFFAFE",
            header_border="#0891B2",
            input_bg="#FFFFFF",
            input_border="#CBD5E1",
            input_focus_border="#0891B2",
            scrollbar_bg="#F0FDFA",
            scrollbar_handle="#CBD5E1",
            scrollbar_handle_hover="#0891B2",
            indicator_bg="#FFFFFF",
            indicator_border="#94A3B8",
            svg_arrow_stroke="#334155",
            badge_bg="#F1F5F9",
            badge_text="#0891B2",
        ),
        "fresh_mint": ThemePalette(
            key="fresh_mint",
            name_fa="نعناع تازه",
            name_en="Fresh Mint",
            is_dark=False,
            bg_base="#F0FDF4",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F8FAFC",
            bg_dialog="#F0FDF4",
            primary="#059669",
            primary_hover="#10B981",
            primary_pressed="#047857",
            primary_text="#FFFFFF",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            btn_sec_bg="#F1F5F9",
            btn_sec_text="#334155",
            btn_sec_border="#CBD5E1",
            btn_sec_hover="#E2E8F0",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_bg="#FFFFFF",
            table_grid="#E2E8F0",
            table_header_bg="#F8FAFC",
            table_header_text="#0F172A",
            table_item_selected="#D1FAE5",
            header_border="#059669",
            input_bg="#FFFFFF",
            input_border="#CBD5E1",
            input_focus_border="#059669",
            scrollbar_bg="#F0FDF4",
            scrollbar_handle="#CBD5E1",
            scrollbar_handle_hover="#059669",
            indicator_bg="#FFFFFF",
            indicator_border="#94A3B8",
            svg_arrow_stroke="#334155",
            badge_bg="#F1F5F9",
            badge_text="#059669",
        ),
        "champagne_gold": ThemePalette(
            key="champagne_gold",
            name_fa="طلایی شامپاینی",
            name_en="Champagne Gold",
            is_dark=False,
            bg_base="#FEFCE8",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F8FAFC",
            bg_dialog="#FEFCE8",
            primary="#D97706",
            primary_hover="#F59E0B",
            primary_pressed="#B45309",
            primary_text="#FFFFFF",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            btn_sec_bg="#F1F5F9",
            btn_sec_text="#334155",
            btn_sec_border="#CBD5E1",
            btn_sec_hover="#E2E8F0",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_bg="#FFFFFF",
            table_grid="#E2E8F0",
            table_header_bg="#F8FAFC",
            table_header_text="#0F172A",
            table_item_selected="#FEF3C7",
            header_border="#D97706",
            input_bg="#FFFFFF",
            input_border="#CBD5E1",
            input_focus_border="#D97706",
            scrollbar_bg="#FEFCE8",
            scrollbar_handle="#CBD5E1",
            scrollbar_handle_hover="#D97706",
            indicator_bg="#FFFFFF",
            indicator_border="#94A3B8",
            svg_arrow_stroke="#334155",
            badge_bg="#F1F5F9",
            badge_text="#D97706",
        ),
        "soft_orchid": ThemePalette(
            key="soft_orchid",
            name_fa="ارکیده ملایم",
            name_en="Soft Orchid",
            is_dark=False,
            bg_base="#FAF5FF",
            bg_surface="#FFFFFF",
            bg_card="#FFFFFF",
            bg_sidebar="#F8FAFC",
            bg_dialog="#FAF5FF",
            primary="#7C3AED",
            primary_hover="#8B5CF6",
            primary_pressed="#6D28D9",
            primary_text="#FFFFFF",
            text_primary="#0F172A",
            text_secondary="#334155",
            text_muted="#64748B",
            btn_sec_bg="#F1F5F9",
            btn_sec_text="#334155",
            btn_sec_border="#CBD5E1",
            btn_sec_hover="#E2E8F0",
            border="#E2E8F0",
            border_light="#CBD5E1",
            table_bg="#FFFFFF",
            table_grid="#E2E8F0",
            table_header_bg="#F8FAFC",
            table_header_text="#0F172A",
            table_item_selected="#EDE9FE",
            header_border="#7C3AED",
            input_bg="#FFFFFF",
            input_border="#CBD5E1",
            input_focus_border="#7C3AED",
            scrollbar_bg="#FAF5FF",
            scrollbar_handle="#CBD5E1",
            scrollbar_handle_hover="#7C3AED",
            indicator_bg="#FFFFFF",
            indicator_border="#94A3B8",
            svg_arrow_stroke="#334155",
            badge_bg="#F1F5F9",
            badge_text="#7C3AED",
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

        # Semantic tokens pulled directly from active palette
        btn_sec_bg = palette.btn_sec_bg
        btn_sec_text = palette.btn_sec_text
        btn_sec_border = palette.btn_sec_border
        btn_sec_hover = palette.btn_sec_hover
        header_bg = palette.table_header_bg
        header_text = palette.table_header_text
        input_bg = palette.input_bg
        input_border = palette.input_border
        input_focus_border = palette.input_focus_border
        table_bg = palette.table_bg
        table_grid = palette.table_grid
        scrollbar_bg = palette.scrollbar_bg
        scrollbar_handle = palette.scrollbar_handle
        scrollbar_handle_hover = palette.scrollbar_handle_hover
        indicator_bg = palette.indicator_bg
        indicator_border = palette.indicator_border
        badge_bg = palette.badge_bg
        badge_text = palette.badge_text
        tooltip_bg = palette.bg_surface if palette.is_dark else "#0F172A"
        tooltip_text = "#FFFFFF" if palette.is_dark else "#F8FAFC"

        if palette.key == "crimson_fury":
            brand_title_color = "#B91C1C"  # Rich slightly brighter crimson
        else:
            brand_title_color = palette.primary_hover if palette.is_dark else palette.primary

        qss = f"""
/* Generated by Nemov ThemeManager for '{palette.name_en}' ({palette.key}) */

QWidget {{
    background-color: {palette.bg_base};
    color: {palette.text_primary};
    font-family: "Vazirmatn", "Segoe UI", sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog, QMessageBox {{
    background-color: {palette.bg_dialog};
    color: {palette.text_primary};
}}

QMessageBox QLabel {{
    color: {palette.text_primary};
    font-size: 13px;
}}

/* Header Bar & Frames */
QFrame#sidebar {{
    background-color: {palette.bg_sidebar};
    border-left: 1px solid {palette.border};
}}

QFrame#card, QFrame#backupHeaderCard {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: 8px;
    padding: 12px;
}}

QFrame#login_card {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: 12px;
    padding: 24px;
}}

QFrame#stat_card {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: 8px;
    padding: 16px;
}}

QFrame#filter_bar, QFrame#toolbar {{
    background-color: {palette.bg_surface};
    border: 1px solid {palette.border};
    border-radius: 8px;
    padding: 8px 12px;
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

QLabel#sidebarBrandTitle {{
    color: {brand_title_color};
    font-size: 24px;
    font-weight: bold;
}}

QLabel#badge {{
    background-color: {btn_sec_bg};
    color: {btn_sec_text};
    border: 1px solid {btn_sec_border};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}}

QLabel#badge_accent {{
    background-color: {palette.table_item_selected};
    color: {palette.primary_hover if palette.is_dark else palette.primary};
    border: 1px solid {palette.primary};
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}}

QLabel#status_pill {{
    background-color: {btn_sec_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border_light};
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
}}

QLabel#logo_preview_box {{
    background-color: {palette.bg_surface};
    border: 2px dashed {palette.border_light};
    border-radius: 12px;
    color: {palette.text_muted};
    font-size: 26px;
}}

/* GroupBox */
QGroupBox {{
    background-color: {palette.bg_card};
    border: 1px solid {palette.border};
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 16px;
    padding-bottom: 12px;
    padding-left: 12px;
    padding-right: 12px;
    font-weight: bold;
    color: {palette.text_primary};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 6px;
    color: {palette.primary_hover if palette.is_dark else palette.primary};
    background-color: transparent;
}}

/* Assignment Box with Cutout Border and Transparent Background */
QGroupBox#assign_plan_box {{
    background-color: transparent;
    border: 1px solid {palette.border_light if palette.is_dark else palette.border};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    padding-bottom: 10px;
    padding-left: 14px;
    padding-right: 14px;
    font-weight: bold;
}}

QGroupBox#assign_plan_box::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 18px;
    top: 2px;
    padding: 0 8px;
    color: {palette.primary_hover if palette.is_dark else palette.primary};
    background-color: {palette.bg_base};
    font-size: 13px;
    font-weight: bold;
}}

/* Buttons */
QPushButton {{
    background-color: {palette.primary};
    color: {palette.primary_text};
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

QPushButton#primary_button {{
    background-color: {palette.primary};
    color: {palette.primary_text};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton#primary_button:hover {{
    background-color: {palette.primary_hover};
}}

QPushButton#primary_button:pressed {{
    background-color: {palette.primary_pressed};
}}

QPushButton#primary_button:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
}}

QPushButton#secondary_button {{
    background-color: {btn_sec_bg};
    color: {btn_sec_text};
    border: 1px solid {btn_sec_border};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton#secondary_button:hover {{
    background-color: {btn_sec_hover};
    color: {palette.text_primary};
}}

QPushButton#secondary_button:pressed {{
    background-color: {palette.bg_base};
}}

QPushButton#secondary_button:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
    border: 1px solid {palette.border};
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
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton#danger_button:hover {{
    background-color: #B91C1C;
}}

QPushButton#danger_button:pressed {{
    background-color: #991B1B;
}}

QPushButton#danger_button:disabled {{
    background-color: {btn_sec_bg};
    color: {palette.text_muted};
}}

/* Inputs & ComboBox */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QComboBox {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 6px 12px;
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {input_focus_border};
}}

QComboBox {{
    padding-left: 20px;
    padding-right: 8px;
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
    width: 20px;
    border-right: 1px solid {input_border};
    background-color: {btn_sec_bg};
    border-top-left-radius: 5px;
    border-bottom-left-radius: 5px;
}}

QComboBox::down-arrow {{
    image: url({arrow_down_path});
    width: 12px;
    height: 12px;
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
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 13px;
    font-weight: bold;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top left;
    width: 24px;
    border-right: 1px solid {input_border};
    border-bottom: 1px solid {input_border};
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
    border-right: 1px solid {input_border};
    background-color: {btn_sec_bg};
    border-bottom-left-radius: 5px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({arrow_down_path});
    width: 12px;
    height: 12px;
}}

/* Tables & Table Views */
QTableWidget, QTableView {{
    background-color: {table_bg};
    color: {palette.text_primary};
    gridline-color: {table_grid};
    border: 1px solid {palette.border};
    border-radius: 6px;
    selection-background-color: {palette.primary};
    selection-color: #FFFFFF;
    outline: 0;
}}

QTableWidget::item, QTableView::item {{
    padding: 6px 8px;
    font-size: 13px;
    color: {palette.text_primary};
}}

QTableWidget::item:selected,
QTableWidget::item:alternate:selected,
QTableView::item:selected,
QTableView::item:alternate:selected {{
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
    border: 1px solid {input_border};
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 32px;
    font-size: 13px;
}}

QTableWidget QLineEdit:focus {{
    border: 1px solid {input_focus_border};
    background-color: {input_bg};
}}

QTableWidget QComboBox {{
    background-color: {input_bg};
    color: {palette.text_primary};
    border: 1px solid {input_border};
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 32px;
    font-size: 13px;
}}

QTableWidget QComboBox:focus {{
    border: 1px solid {input_focus_border};
}}

QTableWidget QPushButton {{
    min-height: 30px;
    padding: 2px 4px;
    font-size: 12px;
}}

/* Lists & Trees */
QListView, QListWidget, QTreeView, QTreeWidget {{
    background-color: {table_bg};
    color: {palette.text_primary};
    border: 1px solid {palette.border};
    border-radius: 6px;
    padding: 4px;
    outline: 0;
}}

QListView::item, QListWidget::item, QTreeView::item, QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}

QListView::item:selected, QListWidget::item:selected,
QTreeView::item:selected, QTreeWidget::item:selected {{
    background-color: {palette.table_item_selected};
    color: {palette.text_primary};
}}

QListView::item:hover, QListWidget::item:hover,
QTreeView::item:hover, QTreeWidget::item:hover {{
    background-color: {btn_sec_hover};
}}

/* Context Menus */
QMenu {{
    background-color: {palette.bg_card};
    color: {palette.text_primary};
    border: 1px solid {palette.border};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    background-color: transparent;
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
    color: {palette.text_primary};
}}

QMenu::item:selected {{
    background-color: {palette.primary};
    color: #FFFFFF;
}}

QMenu::item:disabled {{
    color: {palette.text_muted};
    background-color: transparent;
}}

QMenu::separator {{
    height: 1px;
    background-color: {palette.border};
    margin: 4px 6px;
}}

/* ToolTip */
QToolTip {{
    background-color: {tooltip_bg};
    color: {tooltip_text};
    border: 1px solid {palette.border};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {input_bg};
    border: 1px solid {input_border};
    border-radius: 6px;
    text-align: center;
    color: {palette.text_primary};
    font-weight: bold;
    min-height: 14px;
}}

QProgressBar::chunk {{
    background-color: {palette.primary};
    border-radius: 5px;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {palette.border_light};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {palette.primary};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {palette.primary};
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {palette.primary_hover};
    border-color: {palette.primary_hover};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {palette.border};
    background-color: {palette.bg_card};
    border-radius: 6px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {palette.bg_base};
    color: {palette.text_muted};
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
    border-bottom: 1px solid {palette.border};
    margin-left: 3px;
}}

QTabBar::tab:hover:!selected {{
    background-color: {palette.bg_surface};
    color: {palette.text_primary};
}}

QTabBar::tab:selected {{
    background-color: {palette.bg_card};
    color: {palette.text_primary};
    border-top: 3px solid {palette.primary};
    border-left: 1px solid {palette.border};
    border-right: 1px solid {palette.border};
    border-bottom: 1px solid {palette.bg_card};
    margin-bottom: -1px;
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
    background: {scrollbar_handle_hover};
}}

QScrollBar:horizontal {{
    background: {scrollbar_bg};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: {scrollbar_handle};
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {scrollbar_handle_hover};
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
            from nemov.services.branding_service import BrandingService
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
