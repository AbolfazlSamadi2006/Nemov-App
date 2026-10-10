import sys
import os
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set offscreen for headless render
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent, QFont, QFontDatabase

from yalda.views.workout_library_view import ExerciseFormDialog, WorkoutLibraryView
from yalda.services.workout_service import WorkoutService
from yalda.models.database_models import Exercise
import config

ARTIFACTS_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def run_qa():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    # Load Vazirmatn font
    font_p = config.BASE_DIR / "resources" / "fonts" / "Vazirmatn-Regular.ttf"
    if font_p.exists():
        fid = QFontDatabase.addApplicationFont(str(font_p))
        fams = QFontDatabase.applicationFontFamilies(fid)
        if fams:
            app.setFont(QFont(fams[0], 10))
    else:
        app.setFont(QFont("Segoe UI", 10))

    # Load stylesheet
    qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            content = f.read()
            arrow_down_path = (config.BASE_DIR / "resources" / "images" / "arrow_down.svg").as_posix()
            content = content.replace("url(resources/images/arrow_down.svg)", f"url({arrow_down_path})")
            app.setStyleSheet(content)

    print("--- 1. Testing ExerciseFormDialog (New Exercise) ---")
    dlg = ExerciseFormDialog()
    dlg.show()
    app.processEvents()

    # Initial state: should have no muscle selected by default
    assert dlg.combo_muscle.currentData() == "", f"Expected empty initial muscle, got {dlg.combo_muscle.currentData()}"
    assert dlg.muscle_selector.canvas.selected_muscle is None, f"Expected None initial mannequin selection, got {dlg.muscle_selector.canvas.selected_muscle}"
    dlg.grab().save(str(ARTIFACTS_DIR / "qa_dialog_initial.png"))
    print("Saved qa_dialog_initial.png - Verified clean unselected initial state!")

    # Select Biceps from dropdown
    idx_biceps = dlg.combo_muscle.findData("biceps")
    assert idx_biceps >= 0, "Biceps not found in combo_muscle"
    dlg.combo_muscle.setCurrentIndex(idx_biceps)
    app.processEvents()

    assert dlg.muscle_selector.canvas.selected_muscle == "biceps", f"Expected biceps, got {dlg.muscle_selector.canvas.selected_muscle}"
    dlg.grab().save(str(ARTIFACTS_DIR / "qa_dialog_biceps_selected.png"))
    print("Saved qa_dialog_biceps_selected.png - Dropdown to Mannequin sync verified!")

    # Click on Mannequin (Chest position: e.g. x=130, y=110 on base coordinates)
    canvas = dlg.muscle_selector.canvas
    r = canvas._get_target_rect()
    scale_x = r.width() / canvas.BASE_W
    scale_y = r.height() / canvas.BASE_H
    click_x = r.x() + 130 * scale_x
    click_y = r.y() + 110 * scale_y

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(click_x, click_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(event)
    app.processEvents()

    assert canvas.selected_muscle == "chest", f"Expected chest clicked, got {canvas.selected_muscle}"
    assert dlg.combo_muscle.currentData() == "chest", f"Expected combo to be chest, got {dlg.combo_muscle.currentData()}"
    dlg.grab().save(str(ARTIFACTS_DIR / "qa_dialog_chest_clicked.png"))
    print("Saved qa_dialog_chest_clicked.png - Mannequin click to Dropdown sync verified!")

    # Test Mannequin 'Clear' button resets combo to index 0
    dlg.muscle_selector.btn_reset.click()
    app.processEvents()
    assert canvas.selected_muscle is None, f"Expected None after reset, got {canvas.selected_muscle}"
    assert dlg.combo_muscle.currentData() == "", f"Expected combo index 0 after reset, got {dlg.combo_muscle.currentData()}"
    dlg.grab().save(str(ARTIFACTS_DIR / "qa_dialog_reset_cleared.png"))
    print("Saved qa_dialog_reset_cleared.png - Mannequin clear to Dropdown reset verified!")

    dlg.close()

    print("\n--- 2. Testing ExerciseFormDialog (Edit Existing Exercise) ---")
    all_ex = WorkoutService.get_all_exercises()
    sample_ex = all_ex[0] if all_ex else Exercise(id=1, name_fa="پرس سینه هالتر", primary_muscle="chest")
    dlg_edit = ExerciseFormDialog(exercise_data=sample_ex)
    dlg_edit.show()
    app.processEvents()
    dlg_edit.grab().save(str(ARTIFACTS_DIR / "qa_dialog_edit_exercise.png"))
    print(f"Saved qa_dialog_edit_exercise.png - Loaded exercise '{sample_ex.name_fa}' with muscle '{sample_ex.primary_muscle}'")
    dlg_edit.close()

    print("\n--- 3. Testing WorkoutLibraryView & Filter ---")
    resolutions = [
        ("1024x768", 1024, 768),
        ("1280x780", 1280, 780),
        ("1366x768", 1366, 768),
        ("1920x1080", 1920, 1080)
    ]

    for res_name, w, h in resolutions:
        view = WorkoutLibraryView()
        view.resize(w, h)
        view.show()
        app.processEvents()

        # Capture default full library view
        view.grab().save(str(ARTIFACTS_DIR / f"qa_library_{res_name}_default.png"))
        print(f"Saved qa_library_{res_name}_default.png")

        # Test selecting biceps via mannequin filter
        m_canvas = view.anat_selector.canvas
        mr = m_canvas._get_target_rect()
        msx = mr.width() / m_canvas.BASE_W
        msy = mr.height() / m_canvas.BASE_H
        # Click on Biceps (left biceps around bx=70, by=145)
        mevent = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(mr.x() + 70 * msx, mr.y() + 145 * msy),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        m_canvas.mousePressEvent(mevent)
        app.processEvents()

        assert view.combo_muscle.currentData() == "biceps", f"Expected combo to be biceps, got {view.combo_muscle.currentData()}"
        row_count = view.table.rowCount()
        print(f"  [{res_name}] Filtered by Biceps: {row_count} exercises found in table")
        assert row_count > 0, "Expected exercises for biceps filter!"

        view.grab().save(str(ARTIFACTS_DIR / f"qa_library_{res_name}_biceps_filtered.png"))
        print(f"Saved qa_library_{res_name}_biceps_filtered.png")

        # Test toggle collapse
        view.btn_toggle_mannequin.setChecked(False)
        app.processEvents()
        assert not view.anat_filter_frame.isVisible(), "Expected anat_filter_frame to be collapsed"
        view.grab().save(str(ARTIFACTS_DIR / f"qa_library_{res_name}_collapsed.png"))
        print(f"Saved qa_library_{res_name}_collapsed.png")

        # Test toggle expand back
        view.btn_toggle_mannequin.setChecked(True)
        app.processEvents()
        assert view.anat_filter_frame.isVisible(), "Expected anat_filter_frame to be visible"

        view.close()

    print("\nALL QA TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_qa()
