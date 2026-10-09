import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from yalda.views.login_view import LoginView
from yalda.utils.credential_manager import CredentialManager

QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok

app = QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

# Clean any existing temp credentials for clean test
CredentialManager.clear_all()

# Setup test credentials
CredentialManager.save_credential("mehrab_coach", "SecurePass@2026")
CredentialManager.save_credential("admin_system", "AdminKey!7711")

login_view = LoginView()
login_view.resize(700, 750)
login_view.show()
app.processEvents()
time.sleep(0.3)
app.processEvents()

# Test 1: Verify Auto-Fill of Last User
print("--- TEST 1: AUTO-FILL LAST USER ---")
current_u = login_view.txt_username.text()
current_p = login_view.txt_password.text()
is_chk = login_view.chk_remember.isChecked()

print(f"Username filled: {current_u}")
print(f"Password filled length: {len(current_p)}")
print(f"Remember checkbox checked: {is_chk}")

assert current_u in ["mehrab_coach", "admin_system"], f"Unexpected auto-filled user: {current_u}"
assert is_chk is True, "Checkbox should be checked for remembered user!"

# Capture screenshot of auto-filled state
pix1 = login_view.grab()
p_img1 = output_dir / "qa_login_remembered_autofilled.png"
pix1.save(str(p_img1))
print("Saved screenshot 1:", p_img1)

# Test 2: Typing letter to trigger completer
print("\n--- TEST 2: AUTOCOMPLETE PREFIX ---")
login_view.txt_username.clear()
login_view.txt_password.clear()
app.processEvents()

# Type 'm' (or 'م')
login_view.txt_username.setText("m")
login_view.completer.setCompletionPrefix("m")
login_view.completer.complete()
app.processEvents()

comp_count = login_view.completer.completionCount()
print("Completions for 'm':", comp_count)
for i in range(comp_count):
    login_view.completer.setCurrentRow(i)
    print(f" - {login_view.completer.currentCompletion()}")

# Select the account via completer
login_view.on_account_selected("mehrab_coach")
app.processEvents()

print(f"After selecting: username={login_view.txt_username.text()}, chk={login_view.chk_remember.isChecked()}")
assert login_view.txt_username.text() == "mehrab_coach"
assert login_view.txt_password.text() == "SecurePass@2026"
assert login_view.chk_remember.isChecked() is True

# Test 3: Unchecking Remember Me
print("\n--- TEST 3: UNCHECK REMEMBER ME ---")
login_view.chk_remember.setChecked(False)
app.processEvents()

# Check that 'mehrab_coach' was removed from CredentialManager
has_it = CredentialManager.has_credential("mehrab_coach")
print("Has 'mehrab_coach' in storage after uncheck:", has_it)
assert has_it is False, "'mehrab_coach' should have been removed from storage after unchecking!"

pix2 = login_view.grab()
p_img2 = output_dir / "qa_login_remember_unchecked.png"
pix2.save(str(p_img2))
print("Saved screenshot 2:", p_img2)

# Clean up test credentials
CredentialManager.clear_all()
print("\nALL REMEMBER ME TESTS PASSED SUCCESSFULLY!")
