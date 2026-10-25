import sys
import os
sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation
from PyQt6.QtGui import QFontDatabase, QFont
from PIL import Image, ImageDraw, ImageFont

app = QApplication.instance() or QApplication(sys.argv)

QFontDatabase.addApplicationFont("resources/fonts/Vazirmatn-Regular.ttf")
QFontDatabase.addApplicationFont("resources/fonts/Vazirmatn-Bold.ttf")
app.setFont(QFont("Vazirmatn", 10))

from nemov.views.nutrition_editor_view import NutritionEditorView
from nemov.utils.theme_manager import ThemeManager

ThemeManager.apply_theme("crimson_fury", app)

view = NutritionEditorView()
view.combo_goal.setCurrentIndex(1)  # "کاهش وزن و چربی‌سوزی"
view.resize(1280, 800)
view.show()
QApplication.processEvents()

# 1. Expanded view
pix_exp = view.grab()
path_exp = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/temp_exp.png"
pix_exp.save(path_exp)

# 2. Curtain roll frames
curtain = view.form_details_curtain

curtain.set_anim_progress(0.66)
QApplication.processEvents()
pix_66 = view.grab()
path_66 = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/temp_66.png"
pix_66.save(path_66)

curtain.set_anim_progress(0.33)
QApplication.processEvents()
pix_33 = view.grab()
path_33 = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/temp_33.png"
pix_33.save(path_33)

# 3. Fully collapsed
view.btn_toggle_form.click()
while curtain.anim.state() == QPropertyAnimation.State.Running:
    QApplication.processEvents()
pix_col = view.grab()
path_col = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/temp_col.png"
pix_col.save(path_col)

# 4. Open popup grab
view.btn_toggle_form.click()
while curtain.anim.state() == QPropertyAnimation.State.Running:
    QApplication.processEvents()
view.combo_goal.showPopup()
QApplication.processEvents()
pix_popup = view.combo_goal.view().grab()
path_popup = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/temp_popup.png"
pix_popup.save(path_popup)

# Compose final master showcase
img_exp = Image.open(path_exp)
img_66 = Image.open(path_66)
img_33 = Image.open(path_33)
img_col = Image.open(path_col)
img_popup = Image.open(path_popup)

c_exp = img_exp.crop((20, 60, 1260, 310))
c_66 = img_66.crop((20, 60, 1260, 240))
c_33 = img_33.crop((20, 60, 1260, 170))
c_col = img_col.crop((20, 60, 1260, 520))

# Before user image for Goal
user_before = Image.open("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/.user_uploaded/media_1792920166397_ae5827de.png")

canvas_w = 1240
canvas_h = c_exp.height + 230 + c_66.height + 30 + c_33.height + 30 + c_col.height + 40
canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 17, 23))
draw = ImageDraw.Draw(canvas)

# Top section: Goal comparison
draw.rectangle([(10, 10), (canvas_w - 10, 210)], fill=(23, 27, 38), outline=(55, 65, 81), width=1)
draw.text((25, 20), "A) Goal Dropdown: Before (Clipped & English) vs After (Clean Persian & Safe Padding)", fill=(243, 244, 246))

# Paste user before (scaled to height 150)
ratio_b = 150.0 / user_before.height
w_b = int(user_before.width * ratio_b)
user_b_scaled = user_before.resize((w_b, 150), Image.Resampling.LANCZOS)
canvas.paste(user_b_scaled, (40, 50))
draw.text((40, 48 + 155), "[Before: Truncated '(eight Loss...)' & English text]", fill=(248, 113, 113))

# Paste new popup
ratio_p = 150.0 / img_popup.height
w_p = int(img_popup.width * ratio_p)
popup_scaled = img_popup.resize((w_p, 150), Image.Resampling.LANCZOS)
canvas.paste(popup_scaled, (320, 50))
draw.text((320, 48 + 155), "[After: 100% Pure Persian, 195px Width, Zero Clipping]", fill=(52, 211, 153))

# Paste closed combobox crop
pos = view.combo_goal.mapTo(view, view.combo_goal.rect().topLeft())
crop_closed = img_exp.crop((pos.x() - 15, pos.y() - 5, pos.x() + view.combo_goal.width() + 15, pos.y() + view.combo_goal.height() + 5))
canvas.paste(crop_closed, (680, 95))
draw.text((680, 70), "Closed ComboBox in Row 2 (Full Visibility):", fill=(229, 231, 235))
draw.text((680, 140), "Text: 'کاهش وزن و چربی‌سوزی' (No Ellipsis)", fill=(52, 211, 153))

y = 230
# Section B: Full Expanded Form
draw.text((25, y), "B) Full Nutrition Form (Expanded State)", fill=(243, 244, 246))
y += 22
canvas.paste(c_exp, (0, y))
y += c_exp.height + 20

# Section C: Animation Stages
draw.text((25, y), "C) Smooth Curtain Rollup & Soft Alpha Dissolve (Progress 66% -> 33%)", fill=(147, 197, 253))
y += 22
canvas.paste(c_66, (0, y))
y += c_66.height + 15
canvas.paste(c_33, (0, y))
y += c_33.height + 20

# Section D: Maximized Collapsed Table
draw.text((25, y), "D) Maximized Food Library Table (Collapsed State with Live Summary Bar)", fill=(52, 211, 153))
y += 22
canvas.paste(c_col, (0, y))

out_path = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_nutrition_soft_curtain_showcase.png"
canvas.save(out_path)
print(f"Master showcase saved: {out_path}")

# Cleanup
for p in [path_exp, path_66, path_33, path_col, path_popup]:
    try:
        os.remove(p)
    except:
        pass

app.quit()
