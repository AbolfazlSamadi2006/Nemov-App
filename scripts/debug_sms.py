import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

app = QApplication([])
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

from nemov.views.sms_view import SmsView

sms_view = SmsView()
# Mock balance for realistic visual QA
sms_view.on_balance_received({
    "success": True,
    "remaining": 100,
    "total_credited": 100,
    "total_used": 24,
    "status": "active"
})

sms_view.resize(1024, 700)
sms_view.show()
app.processEvents()

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

# Tab 1: Broadcast & Smartphone Preview
sms_view.tabs.setCurrentIndex(0)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix1 = sms_view.grab()
pix1.save(str(output_dir / "qa_sms_tab1_broadcast.png"))
print("SAVED_TAB1")

# Tab 2: Automated Settings
sms_view.tabs.setCurrentIndex(1)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix2 = sms_view.grab()
pix2.save(str(output_dir / "qa_sms_tab2_automated.png"))
print("SAVED_TAB2")

# Tab 3: History Log
sms_view.tabs.setCurrentIndex(2)
app.processEvents()
time.sleep(0.3)
app.processEvents()
pix3 = sms_view.grab()
pix3.save(str(output_dir / "qa_sms_tab3_history.png"))
print("SAVED_TAB3")

if hasattr(sms_view, "bal_thread") and sms_view.bal_thread.isRunning():
    sms_view.bal_thread.quit()
    sms_view.bal_thread.wait(2000)

sms_view.close()
print("ALL_CAPTURES_SUCCESS")
