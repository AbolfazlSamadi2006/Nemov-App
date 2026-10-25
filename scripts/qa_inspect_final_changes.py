import sys, os
sys.path.insert(0, os.path.abspath("."))
from PyQt6.QtWidgets import QApplication
from nemov.utils.theme_manager import ThemeManager
from nemov.views.nutrition_editor_view import NutritionEditorView
from nemov.views.workout_editor_view import WorkoutEditorView

def run_qa():
    app = QApplication.instance() or QApplication(sys.argv)
    ThemeManager.apply_theme("dark")

    # 1. Nutrition Editor View - Expanded Mode
    v_nut = NutritionEditorView()
    v_nut.resize(1180, 850)
    v_nut.show()
    app.processEvents()

    pix_nut_exp = v_nut.grab()
    out_nut_exp = r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\qa_nutrition_final_expanded.png"
    pix_nut_exp.save(out_nut_exp)
    print("Saved:", out_nut_exp)

    # 2. Nutrition Editor View - Test Toggle Collapse
    if hasattr(v_nut, "toggle_form_collapse"):
        v_nut.toggle_form_collapse()
        app.processEvents()
        pix_nut_col = v_nut.grab()
        out_nut_col = r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\qa_nutrition_final_collapsed.png"
        pix_nut_col.save(out_nut_col)
        print("Saved:", out_nut_col)

        # Toggle back to expanded to test reversible behavior
        v_nut.toggle_form_collapse()
        app.processEvents()

    # 3. Workout Editor View
    v_wo = WorkoutEditorView()
    v_wo.resize(1180, 850)
    v_wo.show()
    app.processEvents()

    pix_wo = v_wo.grab()
    out_wo = r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\qa_workout_final.png"
    pix_wo.save(out_wo)
    print("Saved:", out_wo)

    print("ALL QA RENDERINGS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_qa()
