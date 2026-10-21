import sys
import os
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
import config
from nemov.views.templates_manager_view import TemplatesManagerView

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

font_p = config.BASE_DIR / "resources" / "fonts" / "Vazirmatn-Regular.ttf"
if font_p.exists():
    fid = QFontDatabase.addApplicationFont(str(font_p))
    fams = QFontDatabase.applicationFontFamilies(fid)
    if fams:
        app.setFont(QFont(fams[0], 10))

qss_p = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
if qss_p.exists():
    with open(qss_p, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

view = TemplatesManagerView()
view.resize(1366, 768)
view.show()
app.processEvents()

# Render whole view
full_path = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\qa_templates_1366x768.png")
view.grab().save(str(full_path))

# Crop the first row action buttons
# In RTL, column 8 (operations) is on the left side of the table (around x: 20 to 320)
im = Image.open(str(full_path))
# Find where the table starts vertically (around y: 180 to 280)
crop_crop = im.crop((15, 200, 320, 275))
cropped_path = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\qa_cropped_template_action_buttons.png")
crop_crop.save(str(cropped_path))
print("Saved qa_cropped_template_action_buttons.png successfully!")
