import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication, QHeaderView
from PyQt6.QtCore import Qt, QTimer
import config
from nemov.models.database_models import User
from nemov.auth.authentication import CurrentUser
from nemov.views.main_window import MainWindow
from nemov.views.components.tuition_payment_dialog import TuitionPaymentDialog
from nemov.views.dashboard_view import DashboardView
from nemov.views.member_list_view import MemberListView

def run_qa():
    app = QApplication(sys.argv)
    
    # Mock admin user
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

    # 1. Capture stylish combo box in TuitionPaymentDialog
    dlg = TuitionPaymentDialog()
    dlg.resize(480, 580)
    dlg.show()
    
    # Assert combo properties
    assert dlg.combo_member.objectName() == "combo_member"
    assert dlg.combo_member.height() >= 40
    item0_text = dlg.combo_member.itemText(0)
    print("DEBUG: Combo Item 0:", item0_text)
    assert "محسن صمدی" in item0_text and "مربی:" in item0_text

    # Show popup to capture the stylish popup menu
    dlg.combo_member.showPopup()
    
    def step1_capture_combo():
        dlg.grab().save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_tuition_dialog_stylish_combo.png")
        print("SUCCESS: Saved qa_tuition_dialog_stylish_combo.png")
        dlg.close()
        step2_test_dashboard()

    # 2. Capture Dashboard with Quick Access Tuition button
    def step2_test_dashboard():
        mw = MainWindow()
        mw.resize(1280, 780)
        mw.show()
        
        # Verify button in dashboard
        dash = mw.view_dashboard
        btn_t = dash.findChild(object, "btn_quick_tuition")
        # Find QPushButton with text containing شهریه
        found_btn = False
        for btn in dash.findChildren(object):
            if "ثبت شهریه" in getattr(btn, 'text', lambda: '')():
                found_btn = True
                break
        assert found_btn, "Button 'ثبت شهریه' not found in Dashboard Quick Access"
        print("SUCCESS: Found 'ثبت شهریه' in Dashboard Quick Access")
        
        def step2_capture_dashboard():
            mw.grab().save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_dashboard_quick_tuition_button.png")
            print("SUCCESS: Saved qa_dashboard_quick_tuition_button.png")
            step3_test_members_table(mw)

        QTimer.singleShot(200, step2_capture_dashboard)

    # 3. Capture Members List with 4 action buttons
    def step3_test_members_table(mw):
        mw.sidebar.navigate("members")
        
        def step3_capture_members():
            app.processEvents()
            mem_view = mw.view_members
            # Check row 0 has tuition button
            cell_w = mem_view.table.cellWidget(0, 7)
            assert cell_w is not None, "Action buttons cell widget not found in row 0"
            buttons = [b.text() for b in cell_w.findChildren(object) if hasattr(b, 'text') and b.text()]
            print("DEBUG: Row 0 action buttons:", buttons)
            assert any("شهریه" in b for b in buttons), "Tuition button not found in row 0"
            
            mw.grab().save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_members_table_tuition_buttons.png")
            print("SUCCESS: Saved qa_members_table_tuition_buttons.png")
            
            # Also grab closeup of action buttons cell
            cell_w.grab().save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_members_row_action_buttons_closeup.png")
            print("SUCCESS: Saved qa_members_row_action_buttons_closeup.png")
            
            print("\nALL QUICK TUITION & STYLISH COMBO QA TESTS PASSED SUCCESSFULLY!")
            mw.close()
            app.quit()

        QTimer.singleShot(250, step3_capture_members)

    QTimer.singleShot(200, step1_capture_combo)
    app.exec()

if __name__ == "__main__":
    run_qa()
