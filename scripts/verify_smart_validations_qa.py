# scripts/verify_smart_validations_qa.py
import sys
import os

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
app = QApplication.instance() or QApplication(sys.argv)

from nemov.views.member_form_dialog import MemberFormDialog
from nemov.views.assessment_view import AssessmentView
from nemov.views.food_library_dialog import FoodFormDialog
from nemov.views.components.tuition_payment_dialog import TuitionPaymentDialog
from nemov.utils.theme_manager import ThemeManager

ThemeManager.apply_theme("crimson_fury")

artifacts_dir = r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6"

print("--- Testing MemberFormDialog Validations ---")
dlg_member = MemberFormDialog()
dlg_member.show()

# 1. Test invalid phone
dlg_member.txt_phone.setText("0912")
dlg_member.txt_phone.editingFinished.emit()
assert dlg_member.lbl_phone_warn.isVisible(), "Phone warning should be visible"
assert "۰۹" in dlg_member.lbl_phone_warn.text(), f"Unexpected phone warn text: {dlg_member.lbl_phone_warn.text()}"
print(f"  Phone Warning: {dlg_member.lbl_phone_warn.text()}")

# 2. Test invalid weight
dlg_member.spin_weight.setValue(15.0)
dlg_member.spin_weight.editingFinished.emit()
assert dlg_member.lbl_hw_warn.isVisible(), "Weight warning should be visible"
assert dlg_member.lbl_hw_warn.text() == "⚠️ وزن وارد شده غیرمعمول است.", f"Unexpected: {dlg_member.lbl_hw_warn.text()}"
print(f"  Weight Warning: {dlg_member.lbl_hw_warn.text()}")

# 3. Test invalid tuition
dlg_member.txt_tuition_fee.setText("0")
dlg_member.txt_tuition_fee.editingFinished.emit()
assert dlg_member.lbl_tuition_warn.isVisible(), "Tuition warning should be visible"
print(f"  Tuition Warning: {dlg_member.lbl_tuition_warn.text()}")

pix = dlg_member.grab()
pix.save(os.path.join(artifacts_dir, "qa_member_form_micro_warnings.png"))
print("  Saved qa_member_form_micro_warnings.png")

# 4. Test correcting values clears warnings
dlg_member.txt_phone.setText("09112223344")
dlg_member.txt_phone.editingFinished.emit()
assert not dlg_member.lbl_phone_warn.isVisible(), "Phone warning should be cleared"

dlg_member.spin_weight.setValue(75.0)
dlg_member.spin_weight.editingFinished.emit()
assert not dlg_member.lbl_hw_warn.isVisible(), "Weight warning should be cleared"
print("  Correction cleared warnings successfully!")

print("\n--- Testing AssessmentView Validations ---")
view_ass = AssessmentView(member_id=1)
view_ass.resize(800, 600)
view_ass.show()

view_ass.spin_thigh.setValue(135.0)
view_ass.spin_thigh.editingFinished.emit()
assert view_ass.lbl_assessment_warn.isVisible(), "Assessment warning should be visible"
assert view_ass.lbl_assessment_warn.text() == "⚠️ دور ران/ساق خارج از محدوده طبیعی آناتومیک است.", f"Unexpected: {view_ass.lbl_assessment_warn.text()}"
print(f"  Thigh Warning: {view_ass.lbl_assessment_warn.text()}")

pix_ass = view_ass.grab()
pix_ass.save(os.path.join(artifacts_dir, "qa_assessment_micro_warnings.png"))
print("  Saved qa_assessment_micro_warnings.png")

print("\n--- Testing FoodFormDialog Validations ---")
dlg_food = FoodFormDialog()
dlg_food.show()

dlg_food.spin_cal.setValue(980.0)
dlg_food.spin_cal.editingFinished.emit()
assert dlg_food.lbl_food_warn.isVisible(), "Food cal warning should be visible"
assert "۹۰۰" in dlg_food.lbl_food_warn.text(), f"Unexpected: {dlg_food.lbl_food_warn.text()}"
print(f"  Food Calorie Warning: {dlg_food.lbl_food_warn.text()}")

dlg_food.spin_cal.setValue(150.0)
dlg_food.spin_protein.setValue(50.0)
dlg_food.spin_carbs.setValue(40.0)
dlg_food.spin_fat.setValue(30.0)
dlg_food.spin_protein.editingFinished.emit()
assert dlg_food.lbl_food_warn.isVisible(), "Food macros warning should be visible"
assert "۱۰۰ گرم" in dlg_food.lbl_food_warn.text(), f"Unexpected: {dlg_food.lbl_food_warn.text()}"
print(f"  Food Macros Warning: {dlg_food.lbl_food_warn.text()}")

pix_food = dlg_food.grab()
pix_food.save(os.path.join(artifacts_dir, "qa_food_dialog_micro_warnings.png"))
print("  Saved qa_food_dialog_micro_warnings.png")

print("\n--- Testing TuitionPaymentDialog Validations ---")
dlg_tui = TuitionPaymentDialog()
dlg_tui.show()

dlg_tui.txt_amount.setText("0")
dlg_tui.txt_amount.editingFinished.emit()
assert dlg_tui.lbl_amount_warn.isVisible(), "Tuition warning should be visible"
print(f"  Tuition Payment Warning: {dlg_tui.lbl_amount_warn.text()}")

pix_tui = dlg_tui.grab()
pix_tui.save(os.path.join(artifacts_dir, "qa_tuition_dialog_micro_warnings.png"))
print("  Saved qa_tuition_dialog_micro_warnings.png")

print("\nALL QA VALIDATION TESTS PASSED WITH 100% ACCURACY!")
