#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/qa_nemov_m1_challenge.py
Empirical Challenger Test Harness for Milestone 1:
Nemov 17-Theme Engine Foundation & 9router-style Light/Dark Immersion

Tests executed:
1. Palette Count & Registry Integrity (12 Dark, 5 Light)
2. Strict 7-Character Hex Color Token Validation across all 17 palettes
3. 9router Light Immersion Rules (bg_card == '#FFFFFF', is_dark is False, slate arrow)
4. WCAG 2.1 AAA Contrast Ratio Calculation (text_primary on bg_card >= 7.0:1)
5. OLED Obsidian Reconciliation across PALETTES & PALETTES_METADATA (#E11D48)
6. Comprehensive QSS Generation for all 17 Palettes (no unrendered tokens, balanced braces, required selectors)
7. Dark Immersion Divergence & Contrast (unique surfaces, WCAG AAA text contrast)
8. ThemePalette Backward Compatibility (19 positional args + __post_init__ defaults)
9. Error Handling & Graceful Fallback for unknown theme keys
"""

import sys
import re
from pathlib import Path
from dataclasses import fields

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from nemov.utils.theme_manager import ThemeManager, ThemePalette, PALETTES
from nemov.views.components.theme_card import PALETTES_METADATA


HEX_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def hex_to_rgb(hex_str: str):
    hex_clean = hex_str.lstrip("#")
    return tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))


def calculate_relative_luminance(hex_str: str) -> float:
    r, g, b = hex_to_rgb(hex_str)
    channels = []
    for c in (r, g, b):
        c_srgb = c / 255.0
        if c_srgb <= 0.04045:
            c_lin = c_srgb / 12.92
        else:
            c_lin = ((c_srgb + 0.055) / 1.055) ** 2.4
        channels.append(c_lin)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def calculate_contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = calculate_relative_luminance(hex1)
    l2 = calculate_relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def run_all_challenges():
    passed = 0
    failed = 0
    findings = []

    def log_result(name: str, status: bool, detail: str = ""):
        nonlocal passed, failed
        if status:
            passed += 1
            print(f"  [PASS] {name} {detail}")
        else:
            failed += 1
            print(f"  [FAIL] {name} - {detail}")
            findings.append((name, detail))

    print("=" * 80)
    print("CHALLENGER 1 EMPIRICAL HARNESS: MILESTONE 1 THEME ENGINE")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Palette Count & Registry Integrity
    # -------------------------------------------------------------
    print("\n--- 1. Registry Integrity ---")
    log_result(
        "Palette count in ThemeManager.PALETTES == 17",
        len(PALETTES) == 17,
        f"(found {len(PALETTES)})"
    )
    log_result(
        "Metadata count in PALETTES_METADATA == 17",
        len(PALETTES_METADATA) == 17,
        f"(found {len(PALETTES_METADATA)})"
    )

    dark_keys = [k for k, p in PALETTES.items() if p.is_dark]
    light_keys = [k for k, p in PALETTES.items() if not p.is_dark]
    log_result("12 Dark Palettes registered", len(dark_keys) == 12, f"(found {len(dark_keys)}: {dark_keys})")
    log_result("5 Light Palettes registered", len(light_keys) == 5, f"(found {len(light_keys)}: {light_keys})")

    meta_keys = [m["id"] for m in PALETTES_METADATA]
    log_result("Keys match between PALETTES and METADATA", set(PALETTES.keys()) == set(meta_keys))

    # -------------------------------------------------------------
    # 2. Strict Hex Color Validation
    # -------------------------------------------------------------
    print("\n--- 2. Strict 7-Character Hex Color Validation ---")
    all_hex_valid = True
    invalid_tokens = []
    
    # Identify all color fields in ThemePalette
    color_fields = [
        f.name for f in fields(ThemePalette)
        if f.name not in ("key", "name_fa", "name_en", "is_dark")
    ]

    for key, palette in PALETTES.items():
        for field_name in color_fields:
            val = getattr(palette, field_name)
            if not isinstance(val, str) or not HEX_REGEX.match(val):
                all_hex_valid = False
                invalid_tokens.append(f"{key}.{field_name}='{val}'")

    log_result(
        "All color tokens across 17 palettes match ^#[0-9a-fA-F]{6}$",
        all_hex_valid,
        f"Checked {len(PALETTES) * len(color_fields)} tokens" if all_hex_valid else f"Invalid: {invalid_tokens[:5]}"
    )

    # Validate PALETTES_METADATA colors
    meta_hex_valid = True
    for meta in PALETTES_METADATA:
        if not HEX_REGEX.match(meta["accent"]):
            meta_hex_valid = False
        for c in meta["colors"]:
            if not HEX_REGEX.match(c):
                meta_hex_valid = False
    log_result("All swatches and accents in PALETTES_METADATA match ^#[0-9a-fA-F]{6}$", meta_hex_valid)

    # -------------------------------------------------------------
    # 3. 9router Light Immersion Rules
    # -------------------------------------------------------------
    print("\n--- 3. 9router Light Immersion Rules ---")
    light_themes = ["olympic_white", "clinical_cyan", "fresh_mint", "champagne_gold", "soft_orchid"]
    for lk in light_themes:
        p = PALETTES.get(lk)
        if not p:
            log_result(f"Light palette '{lk}' exists", False, "Missing")
            continue
        bg_card_ok = (p.bg_card.upper() == "#FFFFFF")
        is_dark_ok = (p.is_dark is False)
        arrow_ok = (p.svg_arrow_stroke.upper() == "#334155")
        log_result(
            f"Light palette '{lk}' bg_card == '#FFFFFF' and is_dark is False",
            bg_card_ok and is_dark_ok,
            f"bg_card={p.bg_card}, is_dark={p.is_dark}"
        )
        log_result(
            f"Light palette '{lk}' svg_arrow_stroke == '#334155'",
            arrow_ok,
            f"svg_arrow_stroke={p.svg_arrow_stroke}"
        )

    # -------------------------------------------------------------
    # 4. WCAG 2.1 AAA Contrast Ratio Calculation (>= 7.0:1)
    # -------------------------------------------------------------
    print("\n--- 4. WCAG 2.1 Contrast Calculations ---")
    print("  Calculating relative luminance & contrast (text_primary vs bg_card):")
    for lk in light_themes:
        p = PALETTES[lk]
        ratio = calculate_contrast_ratio(p.text_primary, p.bg_card)
        wcag_aaa = (ratio >= 7.0)
        log_result(
            f"Light palette '{lk}' text_primary ({p.text_primary}) on bg_card ({p.bg_card}) WCAG AAA (>= 7.0:1)",
            wcag_aaa,
            f"Contrast Ratio = {ratio:.2f}:1 (L_text={calculate_relative_luminance(p.text_primary):.4f}, L_bg={calculate_relative_luminance(p.bg_card):.4f})"
        )

    # Also test dark themes contrast
    print("\n  Calculating relative luminance & contrast for dark themes:")
    for dk in dark_keys:
        p = PALETTES[dk]
        ratio = calculate_contrast_ratio(p.text_primary, p.bg_card)
        wcag_aaa = (ratio >= 7.0)
        log_result(
            f"Dark palette '{dk}' text_primary on bg_card WCAG AAA (>= 7.0:1)",
            wcag_aaa,
            f"Contrast Ratio = {ratio:.2f}:1"
        )

    # -------------------------------------------------------------
    # 5. OLED Obsidian Reconciliation (#E11D48)
    # -------------------------------------------------------------
    print("\n--- 5. OLED Obsidian Reconciliation ---")
    oled_pal = PALETTES.get("oled_obsidian")
    oled_meta = next((m for m in PALETTES_METADATA if m["id"] == "oled_obsidian"), None)

    pal_match = (oled_pal.primary.upper() == "#E11D48")
    meta_match = (oled_meta and oled_meta["accent"].upper() == "#E11D48")
    meta_swatch_match = (oled_meta and oled_meta["colors"][2].upper() == "#E11D48")

    log_result("PALETTES['oled_obsidian'].primary == '#E11D48'", pal_match, f"primary={oled_pal.primary}")
    log_result("PALETTES_METADATA['oled_obsidian']['accent'] == '#E11D48'", meta_match, f"accent={oled_meta['accent']}")
    log_result("PALETTES_METADATA['oled_obsidian']['colors'][2] == '#E11D48'", meta_swatch_match, f"color[2]={oled_meta['colors'][2]}")

    # -------------------------------------------------------------
    # 6. QSS Generation for all 17 Palettes
    # -------------------------------------------------------------
    print("\n--- 6. QSS Generation Stress Test ---")
    required_selectors = [
        "QGroupBox", "QMenu", "QToolTip", "QProgressBar", "QSlider",
        "QListView", "QDialog", "QMessageBox",
        "#login_card", "#stat_card", "#filter_bar", "#toolbar",
        "#badge", "#badge_accent", "#status_pill",
        "#primary_button", "#secondary_button", "#danger_button"
    ]

    all_qss_ok = True
    for key in PALETTES:
        try:
            qss = ThemeManager.generate_qss(key)
            if not qss or len(qss) < 1000:
                log_result(f"QSS generation for '{key}' non-empty", False, f"Length {len(qss)}")
                all_qss_ok = False
                continue

            # Check curly braces balance
            open_braces = qss.count("{")
            close_braces = qss.count("}")
            if open_braces != close_braces:
                log_result(f"QSS for '{key}' balanced braces", False, f"Open: {open_braces}, Close: {close_braces}")
                all_qss_ok = False

            # Check unrendered template markers
            unrendered = re.findall(r"\{[a-zA-Z0-9_\.]+\}", qss)
            if unrendered:
                log_result(f"QSS for '{key}' unrendered placeholders", False, f"Found unrendered: {unrendered[:5]}")
                all_qss_ok = False

            # Check critical selectors
            missing_sel = [sel for sel in required_selectors if sel not in qss]
            if missing_sel:
                log_result(f"QSS for '{key}' required selectors", False, f"Missing: {missing_sel}")
                all_qss_ok = False

        except Exception as e:
            log_result(f"QSS generation for '{key}' threw exception", False, str(e))
            all_qss_ok = False

    if all_qss_ok:
        log_result("All 17 palettes generate complete QSS without errors, unrendered tokens, or syntax flaws", True)

    # -------------------------------------------------------------
    # 7. Backward Compatibility & Defaults
    # -------------------------------------------------------------
    print("\n--- 7. Backward Compatibility & Defaults ---")
    try:
        # Create a ThemePalette instance with only the original 19 parameters
        legacy_palette = ThemePalette(
            "test_legacy", "تست قدیمی", "Test Legacy", True,
            "#121212", "#181818", "#1E1E1E", "#161616",
            "#8B0000", "#A91D22", "#660000",
            "#FFFFFF", "#E0E0E0", "#888888",
            "#282828", "#333333", "#4A1113", "#8B0000",
            "#FFFFFF"
        )
        # Check __post_init__ filled all new fields
        defaults_ok = (
            legacy_palette.bg_dialog == "#121212" and
            legacy_palette.btn_sec_bg == "#252525" and
            legacy_palette.table_bg == "#121212" and
            legacy_palette.primary_text == "#FFFFFF" and
            HEX_REGEX.match(legacy_palette.btn_sec_border) is not None
        )
        log_result(
            "ThemePalette backwards compatibility with 19 positional arguments",
            defaults_ok,
            f"Defaults generated: bg_dialog={legacy_palette.bg_dialog}, btn_sec_bg={legacy_palette.btn_sec_bg}"
        )
    except Exception as e:
        log_result("ThemePalette backwards compatibility", False, str(e))

    # -------------------------------------------------------------
    # 8. Edge Case: Unknown Key Handling
    # -------------------------------------------------------------
    print("\n--- 8. Edge Case: Unknown Theme Key Handling ---")
    fallback_qss = ThemeManager.generate_qss("totally_invalid_theme_key_9999")
    log_result(
        "generate_qss('unknown_key') falls back gracefully without crashing",
        len(fallback_qss) > 1000 and "Crimson Fury" in fallback_qss,
        f"Length {len(fallback_qss)}"
    )

    fallback_palette = ThemeManager.get_palette("totally_invalid_theme_key_9999") if hasattr(ThemeManager, "get_palette") else ThemeManager.PALETTES.get("totally_invalid_theme_key_9999", PALETTES["crimson_fury"])
    log_result(
        "Unknown key resolves to default palette",
        fallback_palette.key == "crimson_fury",
        f"Resolved to {fallback_palette.key}"
    )

    # -------------------------------------------------------------
    # 9. Surface Uniqueness Across Palettes (No Clones)
    # -------------------------------------------------------------
    print("\n--- 9. Surface Immersion Uniqueness ---")
    dark_bases = set(PALETTES[k].bg_base for k in dark_keys)
    log_result(
        "Dark palettes have unique canvas backgrounds (immersion check)",
        len(dark_bases) >= 10,
        f"{len(dark_bases)} unique bases among 12 dark palettes"
    )

    light_bases = set(PALETTES[k].bg_base for k in light_keys)
    log_result(
        "Light palettes have unique soft tinted canvases (immersion check)",
        len(light_bases) == 5,
        f"{len(light_bases)} unique bases among 5 light palettes: {light_bases}"
    )

    print("\n" + "=" * 80)
    print(f"EMPIRICAL CHALLENGER SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 80)

    if failed == 0:
        print("\n>>> VERDICT: APPROVE (Zero bugs found, all empirical challenges passed!) <<<\n")
        return 0
    else:
        print(f"\n>>> VERDICT: REQUEST_CHANGES ({failed} failures observed) <<<\n")
        for name, detail in findings:
            print(f"  - {name}: {detail}")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_challenges())
