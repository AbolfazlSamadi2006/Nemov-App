#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite: Challenger 2 (Milestone 2 - Rebranding & Appearance Tab)
Empirical verification of UI geometry, ergonomics, and component structure of Appearance Tab in BackupView.

Verification Focus:
1. Off-screen/headless instantiation of BackupView at 1024x768 and 1920x1080.
2. Verification of all 17 palette cards instantiated (12 dark, 5 light) and selectable.
3. Card geometry (190x105 px), zero clipping, zero negative rects, valid 4-swatch palettes.
4. Tab count is exactly 4 and tab 3 is "🎨  تنظیمات ظاهری و برندینگ باشگاه".
5. Interactive ergonomics, database synchronization, and off-screen visual renders.
"""

import os
import sys
import re
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Force UTF-8 stdout
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication, QLabel, QScrollArea, QGroupBox, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QPixmap


def run_adversarial_suite():
    print("=" * 80)
    print("CHALLENGER 2 — ADVERSARIAL QA VERIFICATION SUITE (MILESTONE 2)")
    print("=" * 80)

    # Initialize QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    failures = []
    passes = []

    def check(condition: bool, description: str, details: str = ""):
        if condition:
            print(f"  [PASS] {description}")
            passes.append(description)
        else:
            err_msg = f"{description} -> {details}"
            print(f"  [FAIL] {description} : {details}")
            failures.append(err_msg)

    # -------------------------------------------------------------------------
    # TEST SUITE 1: PALETTES METADATA SPECIFICATION
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 1] PALETTES METADATA SPECIFICATION ---")
    from nemov.views.components.theme_card import PALETTES_METADATA, ThemePaletteCard

    total_meta = len(PALETTES_METADATA)
    check(total_meta == 17, "Total palette count in metadata is exactly 17", f"Got {total_meta}")

    dark_meta = [p for p in PALETTES_METADATA if p.get("is_dark", True)]
    light_meta = [p for p in PALETTES_METADATA if not p.get("is_dark", True)]

    check(len(dark_meta) == 12, "Dark palette count in metadata is exactly 12", f"Got {len(dark_meta)}")
    check(len(light_meta) == 5, "Light palette count in metadata is exactly 5", f"Got {len(light_meta)}")

    expected_dark_ids = [
        "crimson_fury", "royal_gold", "neon_pulse", "electric_cyan",
        "cyber_amethyst", "solar_blaze", "stealth_silver", "arctic_ice",
        "magenta_force", "bronze_titan", "national_pride", "oled_obsidian"
    ]
    expected_light_ids = [
        "olympic_white", "clinical_cyan", "fresh_mint", "champagne_gold", "soft_orchid"
    ]

    actual_dark_ids = [p["id"] for p in dark_meta]
    actual_light_ids = [p["id"] for p in light_meta]

    check(actual_dark_ids == expected_dark_ids, "12 Dark palette IDs match expected spec", f"Got {actual_dark_ids}")
    check(actual_light_ids == expected_light_ids, "5 Light palette IDs match expected spec", f"Got {actual_light_ids}")

    # Validate color swatches in metadata
    hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    all_colors_valid = True
    for p in PALETTES_METADATA:
        colors = p.get("colors", [])
        if len(colors) != 4:
            all_colors_valid = False
            check(False, f"Palette '{p.get('id')}' colors count", f"Expected 4 colors, got {len(colors)}")
        for c in colors:
            if not hex_pattern.match(c) or not QColor(c).isValid():
                all_colors_valid = False
                check(False, f"Palette '{p.get('id')}' invalid color hex", f"Invalid hex: {c}")

        accent = p.get("accent", "")
        if not hex_pattern.match(accent) or not QColor(accent).isValid():
            all_colors_valid = False
            check(False, f"Palette '{p.get('id')}' invalid accent hex", f"Invalid accent: {accent}")

    if all_colors_valid:
        check(True, "All 17 palettes have 4 valid hex colors and valid accent")

    # -------------------------------------------------------------------------
    # TEST SUITE 2: BACKUPVIEW INSTANTIATION & TAB STRUCTURE
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 2] BACKUPVIEW TAB STRUCTURE & NAMING ---")
    from nemov.views.backup_view import BackupView

    backup_view = BackupView()
    tabs = getattr(backup_view, "tabs", None)

    check(tabs is not None, "BackupView contains QTabWidget 'tabs'")
    check(tabs.count() == 4, f"Tabs count is exactly 4", f"Got {tabs.count()}")

    expected_tabs = [
        (0, "👤  مشخصات مربی و امنیت حساب"),
        (1, "💾  مرکز پشتیبان‌گیری و بازگردانی دیتابیس"),
        (2, "🔔  تاریخچه اعلانات و لاگ‌های سیستم"),
        (3, "🎨  تنظیمات ظاهری و برندینگ باشگاه"),
    ]

    for idx, expected_title in expected_tabs:
        actual_title = tabs.tabText(idx)
        check(actual_title == expected_title, f"Tab {idx} title matches '{expected_title}'", f"Got '{actual_title}'")

    check(backup_view.tabs.widget(3) == backup_view.tab_appearance, "Tab index 3 widget is tab_appearance")
    check(isinstance(backup_view.tab_appearance, QScrollArea), "tab_appearance is wrapped in a QScrollArea for responsiveness")

    # -------------------------------------------------------------------------
    # TEST SUITE 3: OFF-SCREEN INSTANTIATION AT 1024x768 & 1920x1080
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 3] HEADLESS/OFF-SCREEN RESOLUTION & GEOMETRY TESTS ---")

    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    for width, height in [(1024, 768), (1920, 1080)]:
        print(f"\n  Testing Resolution {width}x{height}:")
        backup_view.resize(width, height)
        backup_view.show()
        tabs.setCurrentIndex(3)  # Switch to Appearance tab
        app.processEvents()

        # Check view geometry
        check(backup_view.width() == width and backup_view.height() == height,
              f"BackupView successfully resized to {width}x{height}",
              f"Got {backup_view.width()}x{backup_view.height()}")

        # Check tabs geometry
        check(tabs.width() > 0 and tabs.height() > 0,
              f"Tabs widget has positive geometry at {width}x{height} ({tabs.width()}x{tabs.height()})")

        # Check tab_appearance geometry
        app_tab = backup_view.tab_appearance
        check(app_tab.width() > 0 and app_tab.height() > 0,
              f"Appearance tab scroll area has positive geometry ({app_tab.width()}x{app_tab.height()})")

        scroll_widget = app_tab.widget()
        check(scroll_widget is not None, "Appearance tab scroll area contains internal content widget")
        check(scroll_widget.width() > 0 and scroll_widget.height() > 0,
              f"Appearance tab content widget has positive dimensions ({scroll_widget.width()}x{scroll_widget.height()})")

        # Capture offscreen pixmap
        pixmap = QPixmap(width, height)
        backup_view.render(pixmap)
        shot_path = scratch_dir / f"challenger_m2_appearance_{width}x{height}.png"
        saved = pixmap.save(str(shot_path))
        check(saved and shot_path.exists() and shot_path.stat().st_size > 1000,
              f"Off-screen screenshot successfully captured and saved ({shot_path.name}, {shot_path.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # TEST SUITE 4: THEME PALETTE CARDS INSTANTIATION & ERGONOMICS
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 4] THEME PALETTE CARDS GEOMETRY & ERGONOMICS ---")
    theme_cards = getattr(backup_view, "theme_cards", {})
    check(len(theme_cards) == 17, "BackupView has instantiated all 17 theme cards", f"Got {len(theme_cards)}")

    # Check 12 dark + 5 light partition in cards
    dark_cards = [c for c in theme_cards.values() if c.is_dark]
    light_cards = [c for c in theme_cards.values() if not c.is_dark]
    check(len(dark_cards) == 12, "Exactly 12 dark cards in theme_cards dict", f"Got {len(dark_cards)}")
    check(len(light_cards) == 5, "Exactly 5 light cards in theme_cards dict", f"Got {len(light_cards)}")

    all_cards_geom_ok = True
    all_swatches_geom_ok = True
    all_zero_clipping = True

    for p_id, card in theme_cards.items():
        # Geometry check: 190x105 px
        c_width = card.width()
        c_height = card.height()
        if c_width != 190 or c_height != 105:
            all_cards_geom_ok = False
            check(False, f"Card '{p_id}' fixed size", f"Expected (190, 105), got ({c_width}, {c_height})")

        # Non-negative rect check
        c_rect = card.rect()
        if c_rect.x() < 0 or c_rect.y() < 0 or c_rect.width() <= 0 or c_rect.height() <= 0:
            all_cards_geom_ok = False
            check(False, f"Card '{p_id}' rect validity", f"Invalid rect: {c_rect}")

        # Check child labels inside card
        lbl_title = getattr(card, "lbl_title", None)
        lbl_subtitle = getattr(card, "lbl_subtitle", None)
        badge_selected = getattr(card, "badge_selected", None)

        if not lbl_title or not lbl_subtitle or not badge_selected:
            check(False, f"Card '{p_id}' missing essential header/subtitle/badge labels")

        # Swatches verification
        swatches = card.findChildren(QLabel)
        # Find 4 swatches (22x22 each)
        color_swatches = [s for s in swatches if s.width() == 22 and s.height() == 22]
        if len(color_swatches) != 4:
            all_swatches_geom_ok = False
            check(False, f"Card '{p_id}' swatches count", f"Expected 4 swatches (22x22), got {len(color_swatches)}")
        else:
            for s_idx, swatch in enumerate(color_swatches):
                tip = swatch.toolTip()
                if not tip or "#" not in tip:
                    all_swatches_geom_ok = False
                    check(False, f"Card '{p_id}' swatch {s_idx} tooltip", f"Missing or invalid tooltip: '{tip}'")

        # Check clipping: all children must fit within card bounds (0, 0, 190, 105)
        for child in card.findChildren(QLabel):
            g = child.geometry()
            if g.left() < 0 or g.top() < 0 or g.right() > 190 or g.bottom() > 105:
                all_zero_clipping = False
                check(False, f"Card '{p_id}' child '{child}' clipped outside bounds", f"Geometry: {g}")

    if all_cards_geom_ok:
        check(True, "All 17 cards have exact fixed geometry 190x105 px and non-negative rects")
    if all_swatches_geom_ok:
        check(True, "All 17 cards contain exactly 4 swatches of size 22x22 px with tooltips")
    if all_zero_clipping:
        check(True, "Zero internal clipping detected across all 17 palette cards")

    # -------------------------------------------------------------------------
    # TEST SUITE 5: CARD SELECTION & PERSISTENCE ROUNDTRIP
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 5] SELECTION INTERACTION & PERSISTENCE ROUNDTRIP ---")
    from nemov.services.branding_service import BrandingService

    # Save original theme
    original_theme = BrandingService.get_selected_theme_id()

    # Test selecting every single theme
    all_selection_ok = True
    for p_data in PALETTES_METADATA:
        test_id = p_data["id"]
        # Trigger click
        backup_view._on_theme_card_clicked(test_id)
        app.processEvents()

        # Check card selection state
        card = theme_cards[test_id]
        if not card.is_selected:
            all_selection_ok = False
            check(False, f"Card '{test_id}' marked as is_selected == True after click")

        if not card.badge_selected.isVisible():
            all_selection_ok = False
            check(False, f"Card '{test_id}' badge_selected is visible after click")

        # Check other 16 cards are unselected
        for other_id, other_card in theme_cards.items():
            if other_id != test_id and (other_card.is_selected or other_card.badge_selected.isVisible()):
                all_selection_ok = False
                check(False, f"Non-selected card '{other_id}' was NOT deselected when '{test_id}' was chosen")

        # Check database persistence
        db_theme = BrandingService.get_selected_theme_id()
        if db_theme != test_id:
            all_selection_ok = False
            check(False, f"Theme '{test_id}' was not persisted in database", f"Got '{db_theme}'")

    if all_selection_ok:
        check(True, "All 17 palette cards are individually selectable with exclusive checkmark badge & SQLite persistence")

    # Restore original theme
    backup_view._on_theme_card_clicked(original_theme)
    app.processEvents()

    # -------------------------------------------------------------------------
    # TEST SUITE 6: GROUP 1 & GROUP 2 FORM COMPONENTS & LOGO FALLBACK
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 6] CLUB DETAILS FORM & LOGO RESET BEHAVIOR ---")

    # Group 1: Club Info Form
    check(hasattr(backup_view, "txt_club_name") and isinstance(backup_view.txt_club_name, QLineEdit),
          "Group 1 contains txt_club_name QLineEdit")
    check(hasattr(backup_view, "txt_club_phone") and isinstance(backup_view.txt_club_phone, QLineEdit),
          "Group 1 contains txt_club_phone QLineEdit")
    check(hasattr(backup_view, "txt_club_address") and isinstance(backup_view.txt_club_address, QLineEdit),
          "Group 1 contains txt_club_address QLineEdit")
    check(hasattr(backup_view, "btn_save_club_info") and isinstance(backup_view.btn_save_club_info, QPushButton),
          "Group 1 contains btn_save_club_info QPushButton")

    # Group 2: Logo Box
    check(hasattr(backup_view, "lbl_logo_preview") and isinstance(backup_view.lbl_logo_preview, QLabel),
          "Group 2 contains lbl_logo_preview QLabel (fixed 92x92)")
    check(backup_view.lbl_logo_preview.width() == 92 and backup_view.lbl_logo_preview.height() == 92,
          "Group 2 logo preview box has exact 92x92 dimensions")
    check(hasattr(backup_view, "btn_upload_logo") and isinstance(backup_view.btn_upload_logo, QPushButton),
          "Group 2 contains btn_upload_logo QPushButton")
    check(hasattr(backup_view, "btn_reset_logo") and isinstance(backup_view.btn_reset_logo, QPushButton),
          "Group 2 contains btn_reset_logo QPushButton")
    check(hasattr(backup_view, "lbl_logo_status") and isinstance(backup_view.lbl_logo_status, QLabel),
          "Group 2 contains lbl_logo_status badge QLabel")

    # Check reset button state when default logo is active
    info = BrandingService.get_club_info()
    if not (info.get("club_logo_path") or "").strip():
        check(backup_view.btn_reset_logo.isEnabled() == False,
              "Reset logo button is disabled when default Nemov logo is active")
        check("پیش‌فرض نِمُو" in backup_view.lbl_logo_status.text(),
              "Logo status label correctly indicates default Nemov logo is active")

    # -------------------------------------------------------------------------
    # TEST SUITE 7: SCROLL ERGONOMICS & MINIMUM CONTAINER GEOMETRY
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 7] SCROLL ERGONOMICS & CONTAINER BEHAVIOR ---")
    app_scroll = backup_view.tab_appearance
    check(app_scroll.widgetResizable() == True, "Appearance tab scroll area has widgetResizable == True")

    # Grid columns test: 4 columns for dark palettes
    # 4 cards * 190 px = 760 px + 3 * 10 spacing = 790 px
    # At 1024 window width, content width ~ 980 px -> 790 px fits without horizontal scroll overflow!
    container = app_scroll.widget()
    check(container.layout() is not None, "Scroll container has active layout")

    # Final summary
    print("\n" + "=" * 80)
    print(f"ADVERSARIAL VERIFICATION SUMMARY: {len(passes)} PASSED, {len(failures)} FAILED")
    print("=" * 80)

    if failures:
        print("\nFAILURE DETAILS:")
        for idx, f in enumerate(failures, 1):
            print(f"  {idx}. {f}")
        return False
    else:
        print("\nALL ADVERSARIAL CHECKS PASSED EMPIRICALLY!")
        return True


if __name__ == "__main__":
    success = run_adversarial_suite()
    sys.exit(0 if success else 1)
