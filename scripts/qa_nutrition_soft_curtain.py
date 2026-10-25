import sys
import os
sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation
from PIL import Image

app = QApplication.instance() or QApplication(sys.argv)

from nemov.views.nutrition_editor_view import NutritionEditorView
from nemov.utils.theme_manager import ThemeManager

ThemeManager.apply_theme("crimson_fury", app)

view = NutritionEditorView()
view.resize(1280, 800)
view.show()
QApplication.processEvents()

# 1. Verify Goal items have NO English
expected_goals = [
    ("عضله‌سازی", "muscle_gain"),
    ("کاهش وزن و چربی‌سوزی", "weight_loss"),
    ("افزایش وزن", "weight_gain"),
    ("تثبیت وزن", "maintenance"),
]
for i, (text, key) in enumerate(expected_goals):
    actual_text = view.combo_goal.itemText(i)
    actual_key = view.combo_goal.itemData(i)
    assert actual_text == text, f"Mismatch at {i}: {actual_text} != {text}"
    assert actual_key == key, f"Key mismatch at {i}: {actual_key} != {key}"
    assert "(" not in actual_text and ")" not in actual_text, f"English text found in {actual_text}"

print("✅ All 4 Goal items verified free of English words.")

# Select "کاهش وزن و چربی‌سوزی"
view.combo_goal.setCurrentIndex(1)
QApplication.processEvents()

# Capture Full Expanded View
pix_expanded = view.grab()
path_expanded = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_curtain_expanded.png"
pix_expanded.save(path_expanded)
print("Saved expanded view.")

# Capture close-up of Goal Combobox area
crop_goal = Image.open(path_expanded).crop((350, 100, 950, 180))
crop_goal.save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_goal_combobox_crop.png")
print("Saved goal combobox crop.")

# 2. Test Animated Collapse
anim_frames = []
view.btn_toggle_form.click()
curtain = view.form_details_curtain

# Step through animation
while curtain.anim.state() == QPropertyAnimation.State.Running:
    p = curtain.anim_progress
    cur_h = curtain.height()
    pix = view.grab()
    anim_frames.append((p, cur_h, pix))
    QApplication.processEvents()

# Capture final Collapsed View
pix_collapsed = view.grab()
path_collapsed = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_curtain_collapsed.png"
pix_collapsed.save(path_collapsed)
print("Saved collapsed view. Total animation frames captured:", len(anim_frames))

# Verify collapsed state
assert curtain.is_collapsed() is True, "Curtain should be collapsed"
assert curtain.height() == 0, f"Curtain height should be 0, got {curtain.height()}"
assert "🔽 باز کردن و ویرایش فرم" in view.btn_toggle_form.text()
assert "کاهش وزن و چربی‌سوزی" in view.lbl_form_sub.text()
print("✅ Collapsed state verified: summary contains 'کاهش وزن و چربی‌سوزی'.")

# 3. Test Expand Back
view.btn_toggle_form.click()
while curtain.anim.state() == QPropertyAnimation.State.Running:
    QApplication.processEvents()

assert curtain.is_collapsed() is False, "Curtain should be expanded"
assert "🔼 جمع کردن مشخصات" in view.btn_toggle_form.text()
print("✅ Expanded state verified: form fully restored.")

app.quit()
print("All QA tests completed successfully!")
