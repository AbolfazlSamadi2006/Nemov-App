import sys
import os
import time
sys.path.insert(0, os.path.abspath("."))
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from nemov.views.main_window import MainWindow
from nemov.utils.theme_manager import apply_theme

app = QApplication.instance() or QApplication(sys.argv)
apply_theme("crimson_fury")

win = MainWindow()
win.resize(1440, 900)
win.show()
app.processEvents()
time.sleep(0.5)

out_dir = Path("scratch/figma_new_screens_fixed")
out_dir.mkdir(parents=True, exist_ok=True)

screens = [
    ("dashboard", "01_Dashboard.png"),
    ("workouts", "02_Workout_Plan_Builder.png"),
    ("nutrition", "03_Nutrition_Planner.png"),
    ("foods", "04_Food_Library.png"),
    ("exercises", "05_Exercise_Library_Dark.png"),
]

for nav_id, filename in screens:
    print(f"Navigating to {nav_id}...")
    win.sidebar.navigate(nav_id)
    # Process events to allow repolishing and rendering
    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)
        
    # Check that sidebar active button is indeed nav_id
    active_btn = win.sidebar.buttons.get(nav_id)
    is_active = active_btn.property("active") if active_btn else False
    print(f"  {nav_id} active property: {is_active}, current_nav_id: {win.sidebar._current_nav_id}")
    
    save_path = str(out_dir / filename)
    win.grab().save(save_path)
    print(f"  Saved {filename} to {save_path}")

win.close()
print("All 5 corrected screens captured successfully!")
