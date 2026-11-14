import sys
import os
sys.path.insert(0, os.path.abspath("."))
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSize
from nemov.views.main_window import MainWindow
from nemov.utils.theme_manager import apply_theme

app = QApplication.instance() or QApplication(sys.argv)
apply_theme("crimson_fury")

win = MainWindow()
win.resize(1440, 900)
win.show()
app.processEvents()

out_dir = Path("scratch/figma_new_screens")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Dashboard
win.stack.setCurrentWidget(win.view_dashboard)
app.processEvents()
win.grab().save(str(out_dir / "01_Dashboard.png"))
print("Saved 01_Dashboard.png")

# 2. Workout Plan Builder
win.stack.setCurrentWidget(win.view_workouts)
app.processEvents()
win.grab().save(str(out_dir / "02_Workout_Plan_Builder.png"))
print("Saved 02_Workout_Plan_Builder.png")

# 3. Nutrition Plan Editor
win.stack.setCurrentWidget(win.view_nutrition)
app.processEvents()
win.grab().save(str(out_dir / "03_Nutrition_Planner.png"))
print("Saved 03_Nutrition_Planner.png")

# 4. Food Library
win.stack.setCurrentWidget(win.view_foods)
app.processEvents()
win.grab().save(str(out_dir / "04_Food_Library.png"))
print("Saved 04_Food_Library.png")

# 5. Exercise Library (Dark Theme!)
win.stack.setCurrentWidget(win.view_exercises)
app.processEvents()
win.grab().save(str(out_dir / "05_Exercise_Library_Dark.png"))
print("Saved 05_Exercise_Library_Dark.png")

win.close()
print("All 5 views rendered and saved successfully in dark theme!")
