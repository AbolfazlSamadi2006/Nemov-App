#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThemeManager alias in nemov.services for backward and cross-import compatibility.
"""
from nemov.utils.theme_manager import (
    ThemeManager,
    ThemePalette,
    PALETTES,
    apply_theme,
    apply_saved_theme,
    get_current_theme_key,
    get_current_palette,
    theme_changed,
)

__all__ = [
    "ThemeManager",
    "ThemePalette",
    "PALETTES",
    "apply_theme",
    "apply_saved_theme",
    "get_current_theme_key",
    "get_current_palette",
    "theme_changed",
]
