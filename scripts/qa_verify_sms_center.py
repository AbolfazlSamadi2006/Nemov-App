import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def run_qa():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    from yalda.views.sms_view import SmsView

    sms_view = SmsView()
    # Mock balance for realistic visual QA
    sms_view.on_balance_received({"success": True, "remaining": 100, "total_credited": 100, "total_used": 24, "status": "active"})
    sms_view.resize(1024, 680)
    sms_view.show()
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

    # 1. Capture Tab 1 (Broadcast & Smartphone Preview)
    sms_view.tabs.setCurrentIndex(0)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    pix1 = sms_view.grab()
    pix1.save(str(output_dir / "qa_sms_tab1_broadcast.png"))
    print("SAVED: qa_sms_tab1_broadcast.png")

    # 2. Capture Tab 2 (Automated Settings)
    sms_view.tabs.setCurrentIndex(1)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    pix2 = sms_view.grab()
    pix2.save(str(output_dir / "qa_sms_tab2_automated.png"))
    print("SAVED: qa_sms_tab2_automated.png")

    # 3. Capture Tab 3 (History Logs)
    sms_view.tabs.setCurrentIndex(2)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    pix3 = sms_view.grab()
    pix3.save(str(output_dir / "qa_sms_tab3_history.png"))
    print("SAVED: qa_sms_tab3_history.png")

    sms_view.close()
    print("ALL_QA_SMS_CAPTURES_SUCCESS")

if __name__ == "__main__":
    run_qa()
