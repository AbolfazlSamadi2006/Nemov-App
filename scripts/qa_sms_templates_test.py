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
from nemov.views.main_window import MainWindow

QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok

app = QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

mw = MainWindow()
mw.resize(1300, 780)
mw.show()

# Navigate to SMS Center
mw.switch_page("sms")
app.processEvents()
time.sleep(0.3)
app.processEvents()

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

sms_v = mw.view_sms
sms_v.on_balance_received({
    "success": True,
    "remaining": 250,
    "total_credited": 250,
    "total_used": 0,
    "status": "active"
})
app.processEvents()

# Test 1: Verify Tab 1 template items
sms_v.tabs.setCurrentIndex(0)
app.processEvents()
items = [sms_v.combo_templates.itemText(i) for i in range(sms_v.combo_templates.count())]
print("TAB 1 TEMPLATES:", items)
assert "خوش‌آمدگویی" not in "".join(items), "Welcome template should not be in manual broadcast"

# Test 2: Check hours days combo items
days_items = [sms_v.combo_hours_days.itemText(i) for i in range(sms_v.combo_hours_days.count())]
print("HOURS DAYS ITEMS:", days_items)
for expected_day in ["همه روزه", "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]:
    assert expected_day in days_items, f"Missing day: {expected_day}"

# Switch to hours template and test quick chips
sms_v.combo_templates.setCurrentIndex(1) # hours
app.processEvents()

# Test chip: بانوان
sms_v.set_hours_days_preset("روزهای فرد (ویژه بانوان)")
app.processEvents()
print("HOURS PREVIEW AFTER WOMEN CHIP:", sms_v.lbl_preview_msg.text())

# Test chip: جمعه
sms_v.combo_hours_days.setCurrentText("جمعه")
sms_v.combo_hours_from.setCurrentText("۱۰:۰۰")
sms_v.combo_hours_to.setCurrentText("۱۵:۰۰")
sms_v.input_hours_note.setText("پذیرش تا ساعت ۱۴:۰۰")
app.processEvents()
print("HOURS PREVIEW SINGLE DAY (FRIDAY):", sms_v.lbl_preview_msg.text())

pix_hours = mw.grab()
p_hours = output_dir / "qa_sms_hours_refined.png"
pix_hours.save(str(p_hours))
print("SAVED:", p_hours)

# Test 3: Tab 2 (Automated Triggers) with Welcome SMS card
sms_v.tabs.setCurrentIndex(1)
app.processEvents()
time.sleep(0.3)
app.processEvents()

# Test auto welcome checkbox toggle & save
sms_v.chk_auto_welcome.setChecked(True)
sms_v.chk_auto_birthday.setChecked(True)
sms_v.chk_auto_tuition.setChecked(True)
app.processEvents()

pix_auto = mw.grab()
p_auto = output_dir / "qa_sms_tab2_auto_welcome.png"
pix_auto.save(str(p_auto))
print("SAVED:", p_auto)

# Verify settings persistence
sms_v.save_auto_settings()
app.processEvents()

# Reload settings
sms_v.load_auto_settings()
print("AUTO WELCOME ENABLED:", sms_v.chk_auto_welcome.isChecked())
assert sms_v.chk_auto_welcome.isChecked() == True, "Welcome SMS setting failed to persist"

print("ALL_QA_AUTO_WELCOME_AND_HOURS_PASSED_SUCCESSFULLY")
sys.exit(0)
