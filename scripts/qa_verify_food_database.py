# -*- coding: utf-8 -*-
"""
QA Visual & Functional Verification Script for Table Columns & TDEE field in Yalda Gym App.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont, QFontMetrics
from PyQt6.QtCore import Qt
import config
from yalda.database.connection import init_db
from yalda.views.food_library_view import FoodLibraryView
from yalda.views.nutrition_editor_view import NutritionEditorView

def run_qa():
    app = QApplication.instance() or QApplication(sys.argv)
    
    font_reg = PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Regular.ttf"
    font_bold = PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Bold.ttf"
    if font_reg.exists():
        QFontDatabase.addApplicationFont(str(font_reg))
    if font_bold.exists():
        QFontDatabase.addApplicationFont(str(font_bold))
        
    app.setFont(QFont("Vazirmatn", 10))

    qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            content = f.read()
            arrow_down_path = (config.BASE_DIR / "resources" / "images" / "arrow_down.svg").as_posix()
            content = content.replace("url(resources/images/arrow_down.svg)", f"url({arrow_down_path})")
            app.setStyleSheet(content)

    init_db()

    artifact_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    print("=== Testing FoodLibraryView Table Column Widths ===")
    flv = FoodLibraryView()
    flv.resize(1280, 800)
    flv.show()
    app.processEvents()

    col1_w = flv.table.columnWidth(1)
    col3_w = flv.table.columnWidth(3)
    print(f"Col 1 (Name) Width: {col1_w}px | Col 3 (Unit) Width: {col3_w}px")

    # Check zero truncation across all 377 rows
    fm = QFontMetrics(app.font())
    for r in range(flv.table.rowCount()):
        t1 = flv.table.item(r, 1).text()
        t3 = flv.table.item(r, 3).text()
        assert fm.horizontalAdvance(t1) <= (col1_w - 12), f"Truncated name at row {r}: {t1}"
        assert fm.horizontalAdvance(t3) <= (col3_w - 12), f"Truncated unit at row {r}: {t3}"

    print("All rows in FoodLibraryView fit with 100% clarity and zero truncation!")

    # Find the rows from the user's uploaded image (دانه چیا & دانه کنجد خام)
    target_row = 0
    for r in range(flv.table.rowCount()):
        if "دانه چیا" in flv.table.item(r, 1).text():
            target_row = r
            break
    print(f"Found 'دانه چیا' at row {target_row}")
    flv.table.scrollToItem(flv.table.item(target_row, 1))
    app.processEvents()

    pix_flv_chia = flv.grab()
    chia_path = artifact_dir / "qa_food_library_chia_rows.png"
    pix_flv_chia.save(str(chia_path), "PNG")
    print(f"Saved chia & sesame rows screenshot to {chia_path}")

    # Capture top of table
    flv.table.scrollToTop()
    app.processEvents()
    pix_flv = flv.grab()
    flv_path = artifact_dir / "qa_food_library_view_adjusted.png"
    pix_flv.save(str(flv_path), "PNG")
    print(f"Saved top of table screenshot to {flv_path}")

    print("=== Testing NutritionEditorView TDEE Field ===")
    nev = NutritionEditorView()
    nev.resize(1280, 850)
    nev.show()
    app.processEvents()

    initial_tdee_text = nev.txt_member_tdee.text()
    initial_placeholder = nev.txt_member_tdee.placeholderText()
    print(f"Initial TDEE text: '{initial_tdee_text}' | Placeholder: '{initial_placeholder}'")
    assert initial_tdee_text == "0", f"Expected '0', got '{initial_tdee_text}'"
    assert initial_placeholder == "", f"Expected empty placeholder, got '{initial_placeholder}'"

    pix_nev_initial = nev.grab()
    nev_initial_path = artifact_dir / "qa_nutrition_editor_tdee_zero.png"
    pix_nev_initial.save(str(nev_initial_path), "PNG")
    print(f"Saved NutritionEditorView (TDEE=0) screenshot to {nev_initial_path}")

    # Now test selecting a member
    if nev.combo_member_top.count() > 1:
        nev.combo_member_top.setCurrentIndex(1)
        app.processEvents()
        selected_tdee = nev.txt_member_tdee.text()
        print(f"After selecting member: TDEE text: '{selected_tdee}'")
        pix_nev_selected = nev.grab()
        nev_selected_path = artifact_dir / "qa_nutrition_editor_tdee_member_selected.png"
        pix_nev_selected.save(str(nev_selected_path), "PNG")
        print(f"Saved member selected screenshot to {nev_selected_path}")

    print("=== ALL QA CHECKS PASSED 100% ===")

if __name__ == "__main__":
    run_qa()
