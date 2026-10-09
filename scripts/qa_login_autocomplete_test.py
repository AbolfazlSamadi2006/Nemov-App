import sys
import os
import time
from pathlib import Path

# Add project root
sys.path.insert(0, os.getcwd())

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from yalda.views.login_view import LoginView
from yalda.utils.credential_manager import CredentialManager

# Suppress message boxes
QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

# Save a test credential for 'mehrab' and 'admin' if not present
CredentialManager.save_credential("mehrab", "12345678")
CredentialManager.save_credential("admin", "admin123")

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

print("=== STEP 1: Launching LoginView ===")
login_view = LoginView()
login_view.resize(1100, 750)
login_view.show()
app.processEvents()
time.sleep(0.2)
app.processEvents()

# Test 1: Verify Initial State is Completely Empty
print("Checking initial fields...")
assert login_view.txt_username.text() == "", f"Expected empty username, got: {login_view.txt_username.text()}"
assert login_view.txt_password.text() == "", f"Expected empty password, got: {login_view.txt_password.text()}"
assert not login_view.chk_remember.isChecked(), "Expected remember checkbox to be unchecked"
assert CredentialManager.has_credential("mehrab"), "Credential for 'mehrab' must still exist in storage!"
print("✅ Test 1 Passed: Username and password are NOT pre-filled on launch!")

# Save screenshot of empty login view
pix_empty = login_view.grab()
p_empty = output_dir / "qa_login_initial_empty.png"
pix_empty.save(str(p_empty))
print("SAVED:", p_empty)

# Test 2: Typing first letter 'm' shows autocomplete suggestions
print("\n=== STEP 2: Typing first letter 'm' ===")
login_view.txt_username.setFocus()
QTest.keyClicks(login_view.txt_username, "m")
app.processEvents()
time.sleep(0.1)
app.processEvents()

popup = login_view.completer.popup()
print("Popup visible:", popup.isVisible())
assert popup.isVisible(), "Completer popup should be visible after typing 'm'"
print("Popup rows count:", popup.model().rowCount())
assert popup.model().rowCount() >= 1, "Popup should have at least 1 matching account ('mehrab')"

# Password must still be empty while typing!
assert login_view.txt_password.text() == "", "Password must NOT be filled while only typing a letter!"
assert not login_view.chk_remember.isChecked(), "Remember checkbox must NOT be checked while only typing!"
print("✅ Test 2 Passed: Suggestion popup is visible and password remains empty while typing!")

# Save screenshot of autocomplete popup
pix_popup = login_view.grab()
p_popup = output_dir / "qa_login_autocomplete_popup.png"
pix_popup.save(str(p_popup))
print("SAVED:", p_popup)

# Test 3: Select suggested username from popup
print("\n=== STEP 3: Selecting suggestion from popup ===")
# Click the first matching item in popup ('mehrab')
idx = popup.model().index(0, 0)
selected_user = idx.data()
print("Selecting user from popup:", selected_user)
rect = popup.visualRect(idx)
QTest.mouseClick(popup.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
app.processEvents()
time.sleep(0.1)
app.processEvents()

print("After selection - Username:", login_view.txt_username.text())
print("After selection - Password length:", len(login_view.txt_password.text()))
print("After selection - Remember checked:", login_view.chk_remember.isChecked())

assert login_view.txt_username.text() == "mehrab", f"Expected username 'mehrab', got: {login_view.txt_username.text()}"
assert login_view.txt_password.text() == "12345678", "Expected password '12345678' to be filled!"
assert login_view.chk_remember.isChecked(), "Remember checkbox must be checked after selection!"
print("✅ Test 3 Passed: Both fields are filled and Remember Me is checked after selecting suggestion!")

# Save screenshot of populated login view
pix_selected = login_view.grab()
p_selected = output_dir / "qa_login_account_selected.png"
pix_selected.save(str(p_selected))
print("SAVED:", p_selected)

# Test 4: Editing username clears password
print("\n=== STEP 4: Editing username clears password ===")
login_view.txt_username.setFocus()
QTest.keyClick(login_view.txt_username, Qt.Key.Key_Backspace)
app.processEvents()
print("After backspace - Username:", login_view.txt_username.text())
print("After backspace - Password:", repr(login_view.txt_password.text()))
print("After backspace - Remember checked:", login_view.chk_remember.isChecked())
assert login_view.txt_password.text() == "", "Password must be cleared when username is edited!"
assert not login_view.chk_remember.isChecked(), "Remember checkbox must be unchecked when username is edited!"
print("✅ Test 4 Passed: Password is automatically cleared if username is modified!")

print("\n============================================================")
print("🎉 ALL LOGIN AUTOCOMPLETE TESTS PASSED WITH 100% SUCCESS!")
print("============================================================")
