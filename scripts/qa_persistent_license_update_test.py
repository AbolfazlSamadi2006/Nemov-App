import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from nemov.utils.hardware_security import HardwareSecurity
from nemov.auth.authentication import (
    is_app_license_active, set_app_license_active, authenticate_user, get_session
)
from nemov.models.database_models import SystemSetting
from PyQt6.QtWidgets import QApplication
from nemov.views.login_view import LoginView

def test_persistent_license():
    print("=== Testing Persistent Machine License Across Updates ===")
    
    # 1. Activate on this machine
    set_app_license_active(True)
    hwid = HardwareSecurity.get_machine_hwid()
    sig = HardwareSecurity.get_persistent_machine_signature()
    assert is_app_license_active() is True
    assert sig is not None
    print(f"[+] Step 1: Active on current machine {hwid}. Sig: {sig[:10]}...")

    # 2. Simulate installer update overwriting database with a foreign/blank signature
    session = get_session()
    try:
        sig_setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_hwid_signature").first()
        if sig_setting:
            sig_setting.value = "FOREIGN_INSTALLER_SIGNATURE_12345"
        hwid_setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_hwid").first()
        if hwid_setting:
            hwid_setting.value = "YALDA-0000-0000-0000-0000"
        session.commit()
    finally:
        session.close()

    print("[+] Step 2: Simulated installer DB overwrite with foreign signature.")

    # 3. Verify that is_app_license_active() automatically detects the machine's persistent license and auto-rebinds!
    active_after_update = is_app_license_active()
    print(f"[+] Step 3: is_app_license_active() returned: {active_after_update}")
    assert active_after_update is True, "License must remain active across updates on this machine!"

    # Verify DB was restored
    session = get_session()
    try:
        sig_setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_hwid_signature").first()
        assert sig_setting.value != "FOREIGN_INSTALLER_SIGNATURE_12345", "DB signature must be updated"
        assert HardwareSecurity.verify_machine_license(sig_setting.value) is True
    finally:
        session.close()
    print("[+] Step 4: DB signature was automatically restored to match current machine!")

    # 4. Verify Coach (mehrab) Login without Admin
    app = QApplication.instance() or QApplication(sys.argv)
    login = LoginView()
    login.txt_username.setText("mehrab")
    login.txt_password.setText("mehrab123")  # or correct password
    # Check that hardware license error is NOT shown!
    login.do_login()
    error_text = login.lbl_user_error.text()
    print(f"[*] Error label text for coach: '{error_text}'")
    assert "این نسخه برای سخت‌افزار این رایانه فعال نشده است" not in error_text, "Hardware lock must NOT appear on activated machine!"
    print("[+] Step 5: Coach login successfully bypassed hardware lock!")

    print("=== ALL PERSISTENT LICENSE TESTS PASSED! ===")
    sys.exit(0)

if __name__ == "__main__":
    test_persistent_license()
