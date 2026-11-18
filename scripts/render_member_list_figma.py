import sys
import os
import time
sys.path.insert(0, os.path.abspath("."))
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from nemov.views.main_window import MainWindow
from nemov.utils.theme_manager import apply_theme

app = QApplication.instance() or QApplication(sys.argv)
apply_theme("crimson_fury")

win = MainWindow()
win.resize(1600, 1000)
win.show()
app.processEvents()
time.sleep(0.3)

out_dir = Path("scratch/figma_new_screens")
out_dir.mkdir(parents=True, exist_ok=True)

print("Navigating to members...")
win.sidebar.navigate("members")

for _ in range(15):
    app.processEvents()
    time.sleep(0.05)

save_path = str(out_dir / "03_Club_Members.png")
win.grab().save(save_path)
print(f"Saved Club Members screen to {save_path}")

win.close()
print("Render completed successfully!")
