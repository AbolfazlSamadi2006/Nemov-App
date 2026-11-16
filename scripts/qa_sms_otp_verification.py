import os
import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, os.getcwd())
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from nemov.services.sms_service import SmsService, DEFAULT_SMS_TEMPLATES
from nemov.auth.authentication import authenticate_user, get_developer_info

print("=== STEP 1: Verifying SMS.ir OTP Template Configuration ===")
assert "otp" in DEFAULT_SMS_TEMPLATES, "otp template key missing in DEFAULT_SMS_TEMPLATES"
otp_tpl = DEFAULT_SMS_TEMPLATES["otp"]
assert otp_tpl["template_id"] == 585804, f"Expected template_id 585804, got {otp_tpl['template_id']}"
assert "CODE" in otp_tpl["variables"], "CODE variable missing in otp template"
print(f"✅ Template OTP verified: ID={otp_tpl['template_id']}, Title={otp_tpl['title']}, Vars={otp_tpl['variables']}")

print("\n=== STEP 2: Verifying In-Memory OTP Generation and Verification ===")
dev_info = get_developer_info()
phone = dev_info.get("phone", "09336427711")
otp_code = SmsService.generate_and_store_otp(phone)
assert len(otp_code) == 5, f"OTP should be 5 digits, got {otp_code}"
assert otp_code.isdigit(), f"OTP should be digits only, got {otp_code}"
print(f"✅ Generated secure 5-digit OTP: {otp_code} for phone {phone}")

# Test invalid code
ok_invalid, msg_inv = SmsService.verify_otp(phone, "00000")
assert not ok_invalid, "Invalid OTP should fail verification"
print(f"✅ Invalid OTP rejected correctly: {msg_inv}")

# Test valid code with Persian numerals
persian_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
persian_otp = otp_code.translate(persian_digits)
ok_valid, msg_val = SmsService.verify_otp(phone, persian_otp)
assert ok_valid, f"Persian numeral OTP verification failed: {msg_val}"
print(f"✅ Persian numeral OTP verified successfully: {msg_val}")

print("\n=== STEP 3: Verifying End-to-End SMS.ir Live Transmission ===")
success, sms_msg = SmsService.send_developer_activation_otp_sms(to_phone=phone)
assert success, f"Live SMS.ir OTP transmission failed: {sms_msg}"
print(f"✅ Live SMS.ir transmission succeeded without API errors: {sms_msg}")

# Retrieve newly generated OTP from cache
cached_record = SmsService._otp_cache.get(SmsService.normalize_phone_number(phone))
assert cached_record is not None, "OTP not stored in cache after send"
sent_otp = cached_record["code"]
print(f"✅ Cached live OTP for authentication: {sent_otp}")

print("\n=== STEP 4: Verifying Developer Login with SMS OTP ===")
auth_user = authenticate_user("abolfazl", sent_otp)
assert auth_user is not None, "Authentication with SMS OTP failed (returned None)"
assert auth_user.role == "admin", f"Expected role admin, got {auth_user.role}"
print(f"✅ Developer authenticated successfully via SMS OTP: username={auth_user.username}, role={auth_user.role}")

print("\n=== STEP 5: Visual QA of LoginView with SMS OTP UI ===")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from nemov.views.login_view import LoginView

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

login_view = LoginView()
login_view.resize(500, 680)
login_view.show()
app.processEvents()

# Simulate entering developer username to reveal OTP button
login_view.txt_username.setText("Abolfazl")
app.processEvents()
time.sleep(0.1)
app.processEvents()

assert login_view.btn_dev_otp.isVisible(), "OTP button should be visible for Abolfazl"
btn_text = login_view.btn_dev_otp.text()
assert "شماره" in btn_text or "OTP" in btn_text, f"Unexpected button text: {btn_text}"
print(f"✅ LoginView OTP button visible with text: '{btn_text}'")

# Capture screenshot before click
output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
pix_before = login_view.grab()
pix_before.save(str(output_dir / "qa_login_sms_otp_before.png"))
print(f"📸 Saved screenshot: qa_login_sms_otp_before.png")

# Trigger OTP request via slot simulation
login_view._on_dev_otp_finished(True, "کد ۵ رقمی امنیتی با موفقیت ارسال شد.")
app.processEvents()
time.sleep(0.1)
app.processEvents()

assert login_view.lbl_otp_info.isVisible(), "OTP info label should be visible after send"
info_text = login_view.lbl_otp_info.text()
assert "پیامک" in info_text, f"Info label should mention SMS/پیامک: {info_text}"
print(f"✅ LoginView info label verified: '{info_text[:60]}...'")

# Capture screenshot after SMS OTP sent
pix_after = login_view.grab()
pix_after.save(str(output_dir / "qa_login_sms_otp_sent.png"))
print(f"📸 Saved screenshot: qa_login_sms_otp_sent.png")

login_view.close()
print("\n🎉 ALL QA CHECKS FOR SMS.ir OTP INTEGRATION PASSED 100% PERFECTLY!")
