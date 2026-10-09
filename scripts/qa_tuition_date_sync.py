import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
import config
from yalda.models.database_models import User
from yalda.auth.authentication import CurrentUser
from yalda.views.components.tuition_payment_dialog import TuitionPaymentDialog
from yalda.services.member_service import MemberService
from yalda.services.accounting_service import AccountingService
from yalda.utils.jalali_date import get_today_shamsi, parse_shamsi

def run_qa():
    app = QApplication(sys.argv)
    
    # Set mock admin user
    mock_user = User(
        id=1,
        username="admin",
        password_hash="",
        full_name="مدیر سیستم",
        role="admin",
        is_active=True
    )
    CurrentUser.set(mock_user)
    
    qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
            
    today_str = get_today_shamsi()
    today_dt = parse_shamsi(today_str)
    print(f"DEBUG: Today is {today_str} (Day: {today_dt.day})")
    
    # 1. Dialog for Member 8 (Mohsen Samadi, start date: 1405/07/06, day 6)
    dlg8 = TuitionPaymentDialog(member_id=8)
    dlg8.show()
    
    # 2. General Dialog for Member switching
    dlg_gen = TuitionPaymentDialog()
    dlg_gen.show()
    
    def process_and_capture():
        # Member 8 check
        date8 = dlg8.date_picker.get_date()
        dt8 = parse_shamsi(date8)
        print(f"DEBUG: Dlg8 initial payment date: {date8} (Day: {dt8.day})")
        assert dt8.day == 6, f"Expected day 6 for Mohsen Samadi, got {dt8.day}"
        assert "شروع ثبت‌نام: 1405/07/06" in dlg8.lbl_member_info.text()
        
        pix8 = dlg8.grab()
        pix8.save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_tuition_dialog_member8.png")
        print("SUCCESS: Saved qa_tuition_dialog_member8.png")
        dlg8.close()

        # Switch to Member 4 (Erfan Nik Khoo, start date 1405/07/04)
        for i in range(dlg_gen.combo_member.count()):
            if dlg_gen.combo_member.itemData(i) == 4:
                dlg_gen.combo_member.setCurrentIndex(i)
                break
        app.processEvents()
        
        date4 = dlg_gen.date_picker.get_date()
        dt4 = parse_shamsi(date4)
        print(f"DEBUG: Dlg switched to Member 4: payment date={date4} (Day: {dt4.day})")
        assert dt4.day == 4, f"Expected day 4 for Erfan Nik Khoo, got {dt4.day}"
        assert "شروع ثبت‌نام: 1405/07/04" in dlg_gen.lbl_member_info.text()
        
        pix4 = dlg_gen.grab()
        pix4.save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_tuition_dialog_member4.png")
        print("SUCCESS: Saved qa_tuition_dialog_member4.png")

        # Switch to Member 1 (Abolfazl Samadi, start date 1405/07/01)
        for i in range(dlg_gen.combo_member.count()):
            if dlg_gen.combo_member.itemData(i) == 1:
                dlg_gen.combo_member.setCurrentIndex(i)
                break
        app.processEvents()
        
        date1 = dlg_gen.date_picker.get_date()
        dt1 = parse_shamsi(date1)
        print(f"DEBUG: Dlg switched to Member 1: payment date={date1} (Day: {dt1.day})")
        assert dt1.day == 1, f"Expected day 1 for Abolfazl Samadi, got {dt1.day}"
        assert "شروع ثبت‌نام: 1405/07/01" in dlg_gen.lbl_member_info.text()
        
        pix1 = dlg_gen.grab()
        pix1.save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_tuition_dialog_member1.png")
        print("SUCCESS: Saved qa_tuition_dialog_member1.png")
        dlg_gen.close()

        # Edit mode check
        test_payment = {
            "id": 9999,
            "member_id": 8,
            "amount": 2500000,
            "date_shamsi": "1405/06/15",
            "category": "شهریه دوره ماهانه",
            "description": "تست عدم دستکاری در ویرایش"
        }
        dlg_edit = TuitionPaymentDialog(payment=test_payment)
        assert dlg_edit.date_picker.get_date() == "1405/06/15", "Edit mode must preserve saved date"
        print("SUCCESS: Edit mode preserves original date.")
        
        print("\nALL QA TESTS PASSED SUCCESSFULLY!")
        app.quit()

    QTimer.singleShot(300, process_and_capture)
    app.exec()

if __name__ == "__main__":
    run_qa()
