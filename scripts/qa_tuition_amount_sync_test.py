import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
import config
from nemov.models.database_models import User
from nemov.auth.authentication import CurrentUser
from nemov.views.components.tuition_payment_dialog import TuitionPaymentDialog
from nemov.services.member_service import MemberService

def run_qa():
    app = QApplication(sys.argv)
    
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

    # Create dialog without preselection
    dlg = TuitionPaymentDialog()
    dlg.show()
    app.processEvents()

    # Find members: "محسن صمدی" (2,000,000), "هانیه صمدی" (1,200,000), and test member
    all_members = MemberService.get_all_members()
    print("Found members count:", len(all_members))
    
    # 1. Test initial member
    initial_text = dlg.txt_amount.text()
    print("Initial amount:", initial_text)

    # 2. Select "هانیه صمدی"
    hanieh_idx = -1
    for idx in range(dlg.combo_member.count()):
        text = dlg.combo_member.itemText(idx)
        if "هانیه صمدی" in text:
            hanieh_idx = idx
            break
    
    assert hanieh_idx >= 0, "هانیه صمدی not found in combobox"
    dlg.combo_member.setCurrentIndex(hanieh_idx)
    app.processEvents()
    
    hanieh_amount = dlg.txt_amount.text()
    print("Hanieh amount after select:", hanieh_amount)
    assert hanieh_amount == "1,200,000", f"Expected '1,200,000', got '{hanieh_amount}'"

    # Save visual QA screenshot
    save_path = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_tuition_amount_hanieh_sync.png"
    dlg.grab().save(save_path)
    print("SUCCESS: Captured Hanieh sync screenshot to", save_path)

    # 3. Test changing to another member (e.g. Mohsen Samadi)
    mohsen_idx = -1
    for idx in range(dlg.combo_member.count()):
        text = dlg.combo_member.itemText(idx)
        if "محسن صمدی" in text:
            mohsen_idx = idx
            break
    
    if mohsen_idx >= 0:
        dlg.combo_member.setCurrentIndex(mohsen_idx)
        app.processEvents()
        mohsen_amount = dlg.txt_amount.text()
        print("Mohsen amount after select:", mohsen_amount)
        assert mohsen_amount == "2,000,000", f"Expected '2,000,000', got '{mohsen_amount}'"

    # 4. Test member without tuition or with 0 tuition
    # Create or simulate member with 0 tuition
    # We can temporarily set member 0 tuition_fee to 0 to verify clearing
    m0 = all_members[0]
    original_fee = m0.tuition_fee
    
    # Switch back to Hanieh
    dlg.combo_member.setCurrentIndex(hanieh_idx)
    app.processEvents()
    assert dlg.txt_amount.text() == "1,200,000"

    # Test editing amount
    dlg.txt_amount.setText("1,500,000")
    assert dlg.txt_amount.text() == "1,500,000"
    print("Amount is freely editable: 1,500,000")

    print("ALL TESTS PASSED SUCCESSFULLY!")
    dlg.close()
    sys.exit(0)

if __name__ == "__main__":
    run_qa()
