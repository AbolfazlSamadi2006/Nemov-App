import sys
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from yalda.utils.hardware_security import HardwareSecurity
from yalda.auth.authentication import (
    is_app_license_active, set_app_license_active, authenticate_user, CurrentUser, get_session
)
from yalda.models.database_models import SystemSetting, User
from yalda.views.developer_view import DeveloperView
from yalda.views.login_view import LoginView

def run_tests():
    print("==================================================")
    print("🚀 STARTING HARDWARE LICENSE QA TEST SUITE")
    print("==================================================")

    # 1. Hardware Security Unit Tests
    mb = HardwareSecurity.get_motherboard_serial()
    cpu = HardwareSecurity.get_cpu_id()
    hwid = HardwareSecurity.get_machine_hwid()
    print(f"[*] Motherboard Serial: '{mb}'")
    print(f"[*] CPU Processor ID:   '{cpu}'")
    print(f"[*] Generated HWID:     '{hwid}'")
    assert mb and len(mb) > 0, "Motherboard serial must not be empty"
    assert cpu and len(cpu) > 0, "CPU ID must not be empty"
    assert hwid.startswith("YALDA-"), "HWID must start with YALDA-"

    # 2. Cryptographic signature verification
    real_sig = HardwareSecurity.generate_activation_signature(hwid)
    assert HardwareSecurity.verify_machine_license(real_sig) is True, "Real signature must verify as True"

    fake_hwid = "YALDA-9999-8888-7777-6666"
    fake_sig = HardwareSecurity.generate_activation_signature(fake_hwid)
    assert HardwareSecurity.verify_machine_license(fake_sig) is False, "Fake HWID signature must verify as False"
    print("[+] Cryptographic HMAC-SHA256 signature verification PASSED!")

    # 3. Active binding test on current DB
    set_app_license_active(True)
    assert is_app_license_active() is True, "License must be active on this PC"
    print("[+] Current machine license activation PASSED!")

    # 4. Simulate Folder Copy to Foreign PC
    session = get_session()
    try:
        sig_setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_hwid_signature").first()
        sig_setting.value = fake_sig
        session.commit()
    finally:
        session.close()

    assert is_app_license_active() is False, "License must evaluate to False when foreign signature is in DB"
    print("[+] Foreign machine simulation detected license mismatch successfully!")

    # 5. UI and Login Behavior
    app = QApplication.instance() or QApplication(sys.argv)
    
    login = LoginView()
    login.show()
    
    # Simulate coach login on locked machine
    coach_user = authenticate_user("testcoach", "123456")
    if not coach_user:
        # Create a test coach if none exists
        session = get_session()
        coach_user = session.query(User).filter(User.role != "admin").first()
        session.close()

    if coach_user:
        login.txt_username.setText(coach_user.username)
        login.txt_password.setText("wrong_or_right")
        # Direct trigger check
        login.do_login()
        print(f"[*] Login attempt on unlicensed PC - Error visible: {login.lbl_user_error.isVisible()}")
        print(f"[*] Error message: {login.lbl_user_error.text()}")

    # Capture locked screenshot
    brain_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
    pix_locked = login.grab()
    pix_locked.save(str(brain_dir / "qa_login_license_locked.png"))
    print("[+] Saved qa_login_license_locked.png")

    # 6. Admin Login Bypass & Re-activation
    from datetime import datetime
    now_hm = datetime.now().strftime("%H%M")
    admin_auth = authenticate_user("admin", f"2006{now_hm}") or authenticate_user("admin", "2006")
    assert admin_auth is not None, "Admin must be able to authenticate on unlicensed PC"
    assert admin_auth.role == "admin", "Admin role must be 'admin'"
    print(f"[+] Admin bypass successful! Master password authentication succeeded for user: {admin_auth.username}")

    # Reactivate via admin
    set_app_license_active(True)
    assert is_app_license_active() is True, "License must be restored to active after admin re-activation"
    print("[+] Admin re-activation and HWID re-binding PASSED!")

    # 7. Visual Render of Developer View
    dev_view = DeveloperView()
    dev_view.resize(900, 750)
    dev_view.show()
    dev_view.load_data()
    pix_dev = dev_view.grab()
    pix_dev.save(str(brain_dir / "qa_developer_view_hwid.png"))
    print("[+] Saved qa_developer_view_hwid.png")

    print("==================================================")
    print("✅ ALL HARDWARE LICENSE QA TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
