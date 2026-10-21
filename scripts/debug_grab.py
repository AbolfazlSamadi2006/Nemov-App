import os
import sys
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

with open("debug_grab.log", "w", encoding="utf-8") as f:
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        from nemov.views.sms_view import SmsView
        sms_view = SmsView()
        f.write("SmsView created.\n")
        sms_view.resize(1024, 700)
        sms_view.show()
        f.write("SmsView shown.\n")
        pix = sms_view.grab()
        f.write(f"Grabbed pixmap size: {pix.width()}x{pix.height()}\n")
        save_path = os.path.join(os.getcwd(), "qa_sms_test.png")
        ok = pix.save(save_path)
        f.write(f"Saved: {ok} to {save_path}\n")
    except Exception as e:
        f.write(f"Exception: {e}\n")
        traceback.print_exc(file=f)

print("DONE_GRAB_TEST")
