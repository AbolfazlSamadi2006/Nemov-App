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

from nemov.services.sms_service import SmsService, DEFAULT_SMS_TEMPLATES
import config

print("=== STEP 1: Verifying DEFAULT_SMS_TEMPLATES ===")
expected_templates = {
    "birthday": {
        "id": 875172,
        "pattern": "ورزشکار گرامی #NAME#، زادروزتان خجسته باد! با آرزوی تندرستی، باشگاه ورزشی #GYM#",
        "vars": ["NAME", "GYM"]
    },
    "tuition": {
        "id": 183344,
        "pattern": "ورزشکار گرامی #NAME#، اعتبار دوره عضویت شما در تاریخ #DATE# به پایان می‌رسد. جهت تمدید دوره، به مدیریت باشگاه مراجعه فرمایید. باشگاه #GYM#",
        "vars": ["NAME", "DATE", "GYM"]
    },
    "welcome": {
        "id": 676700,
        "pattern": "ورزشکار گرامی #NAME#، ثبت‌نام شما در باشگاه #GYM# با موفقیت انجام شد. از همراهی شما سپاسگزاریم",
        "vars": ["NAME", "GYM"]
    },
    "holiday": {
        "id": 146877,
        "pattern": "ورزشکار محترم باشگاه #GYM#، به اطلاع می‌رساند باشگاه در تاریخ #DATE# به علت #REASON# تعطیل می‌باشد.",
        "vars": ["GYM", "DATE", "REASON"]
    },
    "hours": {
        "id": 385003,
        "pattern": "ورزشکار محترم، زمان‌بندی جدید سانس‌های باشگاه ورزشی #GYM#:\nروزها: #DAYS#\nبانوان: #WOMEN#\nآقایان: #MEN#\nتوضیحات: #NOTE#",
        "vars": ["GYM", "DAYS", "WOMEN", "MEN", "NOTE"]
    }
}

for k, exp in expected_templates.items():
    tpl = DEFAULT_SMS_TEMPLATES[k]
    assert tpl["template_id"] == exp["id"], f"Template ID mismatch for {k}: {tpl['template_id']} != {exp['id']}"
    assert tpl["pattern"] == exp["pattern"], f"Pattern mismatch for {k}"
    assert tpl["variables"] == exp["vars"], f"Variables mismatch for {k}: {tpl['variables']} != {exp['vars']}"
    print(f"✅ Template [{k}] verified: ID={tpl['template_id']}, Variables={tpl['variables']}")

print("\n=== STEP 2: Verifying Phone Normalization ===")
test_phones = [
    ("+989123456789", "09123456789"),
    ("00989123456789", "09123456789"),
    ("989123456789", "09123456789"),
    ("09123456789", "09123456789"),
    ("۰۹۱۲۳۴۵۶۷۸۹", "09123456789"),
    ("0912-345-6789", "09123456789"),
    (" 0912 345 6789 ", "09123456789"),
    ("9123456789", "09123456789"),
    ("۹۱۲۳۴۵۶۷۸۹", "09123456789")
]
for raw, expected in test_phones:
    res = SmsService.normalize_phone_number(raw)
    assert res == expected, f"Phone normalization failed for '{raw}': got '{res}', expected '{expected}'"
print(f"✅ All {len(test_phones)} phone normalization test cases passed!")

print("\n=== STEP 3: Verifying UI and Live Previews ===")
from PyQt6.QtWidgets import QApplication, QMessageBox, QLabel
from PyQt6.QtCore import Qt
from nemov.views.main_window import MainWindow

QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes

app = QApplication.instance() or QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

mw = MainWindow()
mw.resize(1340, 800)
mw.show()

# Switch to SMS Center
mw.switch_page("sms")
app.processEvents()
time.sleep(0.3)
app.processEvents()

sms_v = mw.view_sms
sms_v.on_balance_received({
    "success": True,
    "remaining": 500,
    "total_credited": 500,
    "total_used": 0,
    "status": "active"
})
app.processEvents()

output_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

# Test Tab 1: Holiday Preview
sms_v.tabs.setCurrentIndex(0)
sms_v.combo_templates.setCurrentIndex(0) # holiday
sms_v.input_dyn_date.setText("جمعه ۲۵ مهر")
sms_v.input_dyn_reason.setText("تعمیرات سالن و بهسازی")
app.processEvents()

holiday_preview = sms_v.lbl_preview_msg.text()
print("Holiday Preview:\n", holiday_preview)
assert f"ورزشکار محترم باشگاه {config.APP_NAME}، به اطلاع می‌رساند باشگاه در تاریخ جمعه ۲۵ مهر به علت تعمیرات سالن و بهسازی تعطیل می‌باشد." == holiday_preview
print("✅ Holiday live preview matched 100%!")

pix_hol = mw.grab()
p_hol = output_dir / "qa_sms_holiday_official.png"
pix_hol.save(str(p_hol))
print("SAVED:", p_hol)

# Test Tab 1: Hours Preview
sms_v.combo_templates.setCurrentIndex(1) # hours
sms_v.combo_hours_days.setCurrentText("شنبه تا پنجشنبه")
sms_v.combo_hours_women.setCurrentText("۸ الی ۱۲ و ۱۵ الی ۱۹")
sms_v.combo_hours_men.setCurrentText("۱۲ الی ۱۵ و ۱۹ الی ۲۳")
sms_v.input_hours_note.setText("جمعه‌ها سالن تعطیل است")
app.processEvents()

hours_preview = sms_v.lbl_preview_msg.text()
print("Hours Preview:\n", hours_preview)
expected_hours_preview = (
    f"ورزشکار محترم، زمان‌بندی جدید سانس‌های باشگاه ورزشی {config.APP_NAME}:\n"
    f"روزها: شنبه تا پنجشنبه\n"
    f"بانوان: ۸ الی ۱۲ و ۱۵ الی ۱۹\n"
    f"آقایان: ۱۲ الی ۱۵ و ۱۹ الی ۲۳\n"
    f"توضیحات: جمعه‌ها سالن تعطیل است"
)
assert hours_preview == expected_hours_preview, f"Hours preview mismatch:\n{hours_preview}\n!=\n{expected_hours_preview}"
print("✅ Hours live preview matched 100%!")

pix_hours = mw.grab()
p_hours = output_dir / "qa_sms_hours_official.png"
pix_hours.save(str(p_hours))
print("SAVED:", p_hours)

# Test Tab 2: Automated Settings and Labels
sms_v.tabs.setCurrentIndex(1)
app.processEvents()
time.sleep(0.3)
app.processEvents()

# Find Tab 2 labels
all_labels = sms_v.tab_automated.findChildren(QLabel)
labels_text = [l.text() for l in all_labels]

wel_found = any("۶۷۶۷۰۰" in t and "ثبت‌نام شما در باشگاه" in t for t in labels_text)
bday_found = any("۸۷۵۱۷۲" in t and "باشگاه ورزشی" in t for t in labels_text)
tui_found = any("۱۸۳۳۴۴" in t and "جهت تمدید دوره، به مدیریت باشگاه مراجعه فرمایید" in t for t in labels_text)

assert wel_found, "Welcome template ID 676700 label not found or text mismatch in Tab 2"
assert bday_found, "Birthday template ID 875172 label not found or text mismatch in Tab 2"
assert tui_found, "Tuition template ID 183344 label not found or text mismatch in Tab 2"
print("✅ Tab 2 official template badges and texts verified!")

pix_auto = mw.grab()
p_auto = output_dir / "qa_sms_tab2_official.png"
pix_auto.save(str(p_auto))
print("SAVED:", p_auto)

print("\n============================================================")
print("🎉 ALL SMS TEMPLATES, NORMALIZERS, PREVIEWS & QA TESTS PASSED!")
print("============================================================")
