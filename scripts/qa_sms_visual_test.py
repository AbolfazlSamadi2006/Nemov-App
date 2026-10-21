import sys
import os
import time
from pathlib import Path

# Add project root
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from nemov.views.main_window import MainWindow

app = QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

mw = MainWindow()
mw.resize(1280, 768)
mw.show()

# Navigate to SMS Center
mw.switch_page("sms")
app.processEvents()
time.sleep(0.5)
app.processEvents()

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

# Mock balance on view_sms for crisp UI
sms_v = mw.view_sms
sms_v.on_balance_received({
    "success": True,
    "remaining": 100,
    "total_credited": 100,
    "total_used": 24,
    "status": "active"
})
app.processEvents()

# 1. Grab Tab 1 (Broadcast & Smartphone Preview)
sms_v.tabs.setCurrentIndex(0)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix1 = mw.grab()
p1 = output_dir / "qa_sms_tab1_broadcast.png"
pix1.save(str(p1))
print(f"SAVED: {p1} ({p1.stat().st_size} bytes)")

# 2. Grab Tab 2 (Automated Rules)
sms_v.tabs.setCurrentIndex(1)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix2 = mw.grab()
p2 = output_dir / "qa_sms_tab2_automated.png"
pix2.save(str(p2))
print(f"SAVED: {p2} ({p2.stat().st_size} bytes)")

# 3. Grab Tab 3 (History Logs)
sms_v.tabs.setCurrentIndex(2)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix3 = mw.grab()
p3 = output_dir / "qa_sms_tab3_history.png"
pix3.save(str(p3))
print(f"SAVED: {p3} ({p3.stat().st_size} bytes)")

mw.close()
print("VISUAL_QA_COMPLETED_SUCCESSFULLY")
