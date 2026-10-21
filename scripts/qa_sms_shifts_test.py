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

# Verify Tab 1 template items
sms_v.tabs.setCurrentIndex(0)
app.processEvents()

days_items = [sms_v.combo_hours_days.itemText(i) for i in range(sms_v.combo_hours_days.count())]
print("HOURS DAYS ITEMS:", days_items)

# Assert 'شنبه تا چهارشنبه' is NOT present
assert "شنبه تا چهارشنبه" not in days_items, "'شنبه تا چهارشنبه' should have been removed!"
assert "روزهای زوج (ویژه آقایان)" not in days_items, "روزهای زوج should have been removed!"
assert "روزهای فرد (ویژه بانوان)" not in days_items, "روزهای فرد should have been removed!"

# Assert days present
for expected_day in ["همه روزه", "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شیفت صبح بانوان", "شیفت ظهر آقایان", "شیفت عصر بانوان", "شیفت شب آقایان"]:
    assert expected_day in days_items, f"Missing: {expected_day}"

# Switch to hours template
sms_v.combo_templates.setCurrentIndex(1) # hours
app.processEvents()

# Test 1: Full schedule
sms_v.set_hours_preset("همه روزه: بانوان (۸ الی ۱۲ و ۱۵ الی ۱۹) | آقایان (۱۲ الی ۱۵ و ۱۹ الی ۲۳)", "", "", "")
app.processEvents()
full_msg = sms_v.lbl_preview_msg.text()
print("FULL SCHEDULE MSG:", full_msg)
assert "همه روزه: بانوان (۸ الی ۱۲ و ۱۵ الی ۱۹) | آقایان (۱۲ الی ۱۵ و ۱۹ الی ۲۳)" in full_msg

# Test 2: Women morning
sms_v.set_hours_preset("شیفت صبح بانوان", "۰۸:۰۰", "۱۲:۰۰", "")
app.processEvents()
w_m_msg = sms_v.lbl_preview_msg.text()
print("WOMEN MORNING MSG:", w_m_msg)
assert "شیفت صبح بانوان از ساعت ۰۸:۰۰ الی ۱۲:۰۰" in w_m_msg

# Test 3: Men noon
sms_v.set_hours_preset("شیفت ظهر آقایان", "۱۲:۰۰", "۱۵:۰۰", "")
app.processEvents()
m_n_msg = sms_v.lbl_preview_msg.text()
print("MEN NOON MSG:", m_n_msg)
assert "شیفت ظهر آقایان از ساعت ۱۲:۰۰ الی ۱۵:۰۰" in m_n_msg

# Test 4: Women evening
sms_v.set_hours_preset("شیفت عصر بانوان", "۱۵:۰۰", "۱۹:۰۰", "")
app.processEvents()
w_e_msg = sms_v.lbl_preview_msg.text()
print("WOMEN EVENING MSG:", w_e_msg)
assert "شیفت عصر بانوان از ساعت ۱۵:۰۰ الی ۱۹:۰۰" in w_e_msg

# Test 5: Men night
sms_v.set_hours_preset("شیفت شب آقایان", "۱۹:۰۰", "۲۳:۰۰", "")
app.processEvents()
m_night_msg = sms_v.lbl_preview_msg.text()
print("MEN NIGHT MSG:", m_night_msg)
assert "شیفت شب آقایان از ساعت ۱۹:۰۰ الی ۲۳:۰۰" in m_night_msg

# Save screenshot of the hours template with the full schedule displayed
sms_v.set_hours_preset("همه روزه: بانوان (۸ الی ۱۲ و ۱۵ الی ۱۹) | آقایان (۱۲ الی ۱۵ و ۱۹ الی ۲۳)", "", "", "")
app.processEvents()

pix = mw.grab()
p_img = output_dir / "qa_sms_hours_shifts_updated.png"
pix.save(str(p_img))
print("SAVED QA SCREENSHOT:", p_img)
print("ALL TESTS PASSED SUCCESSFULLY!")
