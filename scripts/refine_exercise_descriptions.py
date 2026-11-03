"""
Refine Exercise Descriptions Script
Removes step-by-step physical movement execution text from exercise descriptions
and replaces them with concise pro coaching cues, joint safety tips, and injury contraindications.
Constraint: Strictly 1 line (average 55 characters, strictly <= 65 chars).
"""

import sqlite3
import json
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_expert_cue(name, muscle, equip, contra):
    name = (name or '').strip()
    muscle = (muscle or '').strip()
    equip = (equip or '').strip()
    contra = (contra or '').strip()

    # 1. Jumps / High-impact / Plyo
    if any(k in name for k in ['جامپ', 'پرش', 'بارپی', 'بورپی', 'جهش', 'پلیومتریک', 'اسنپ جامپ', 'طناب']):
        tip = 'فرود نرم روی پنجه با زانوی منعطف؛ نامناسب در آسیب مچ و زانو'

    # 2. Triceps (BEFORE back)
    elif any(k in name for k in ['پشت بازو', 'پشت‌بازو', 'پشتبازو', 'کیک بک پشت بازو', 'پارالل', 'فرانسوی']) or (muscle == 'triceps' and 'پشت پا' not in name):
        if any(k in name for k in ['پارالل', 'دیپ']):
            tip = 'تثبیت شانه و عدم فرود بیش از ۹۰ درجه؛ احتیاط در درد شانه'
        elif any(k in name for k in ['طناب', 'سیمکش', 'سیم کش']):
            tip = 'ثابت ماندن آرنج در پهلو و انقباض ماکزیمم در انتهای دامنه'
        elif any(k in name for k in ['بالای سر', 'فرانسوی']):
            tip = 'ثابت ماندن بازو در کنار گوش بدون ضربه به مفصل آرنج'
        else:
            tip = 'تثبیت مفصل آرنج و انقباض ماکزیمم پشت‌بازو در انتهای حرکت'

    # 3. Biceps
    elif any(k in name for k in ['جلوبازو', 'جلو بازو', 'لاری', 'چکشی', 'فیگوری']) or muscle == 'biceps':
        if 'لاری' in name:
            tip = 'عدم قفل کامل آرنج در پایین برای محافظت از تاندون دو سر'
        elif 'چکشی' in name:
            tip = 'اجرا بدون تاب بالاتنه با تمرکز بر عضله براکیالیس و ساعد'
        else:
            tip = 'ثابت ماندن آرنج در پهلو بدون کمک گرفتن از تکان دادن کمر'

    # 4. Hamstrings & Glutes (BEFORE back)
    elif any(k in name for k in ['پشت پا', 'پشت‌پا', 'همسترینگ', 'سرینی', 'باسن', 'پل باسن', 'هیپ تراست', 'کیک بک باسن', 'کیک بک']) or muscle in ['glutes', 'legs_back']:
        if any(k in name for k in ['پل', 'هیپ تراست']):
            tip = 'فشار از پاشنه و انقباض کامل باسن در بالا بدون قوس کمر'
        elif any(k in name for k in ['دستگاه', 'خوابیده', 'نشسته', 'ایستاده']) and 'پشت پا' in name:
            tip = 'ثابت نگه داشتن لگن و مکث ۱ ثانیه‌ای در اوج انقباض پشت ران'
        elif 'کیک بک' in name:
            tip = 'انقباض متمرکز سرینی بدون چرخش لگن یا گودی اضافه کمر'
        elif any(k in name for k in ['رومانیایی', 'پشت پا دمبل', 'پشت پا هالتر']):
            tip = 'خم شدن از مفصل ران با ستون فقرات صاف و کشش عمیق پشت پا'
        else:
            tip = 'تمرکز بر انقباض سرینی و پشت ران با مکث کوتاه در اوج حرکت'

    # 5. Squats & Quads
    elif any(k in name for k in ['اسکوات', 'اسکات', 'پرس پا', 'هاگ', 'سی سی', 'جلو پا', 'جلوپا', 'لانج', 'لانگ']) or muscle in ['legs_front', 'legs']:
        if any(k in name for k in ['جلو پا', 'جلوپا']):
            tip = 'عدم ضربه زدن و خودداری از قفل کامل زانو برای حفظ مفصل'
        elif any(k in name for k in ['تک پا', 'بلغاری', 'تعادل']):
            tip = 'حفظ تعادل با ستون فقرات خنثی؛ هدایت زانو در راستای پنجه'
        elif any(k in name for k in ['لانج', 'لانگ']):
            tip = 'زاویه ۹۰ درجه زانو؛ عدم عبور زانوی جلو از نوک پنجه پا'
        elif 'پرشی' in name:
            tip = 'فرود نرم با زانوی منعطف بدون ضربه به ستون فقرات و مفاصل'
        else:
            tip = 'ستون فقرات خنثی؛ هدایت زانو در راستای پنجه بدون قفل مفصل'

    # 6. Chest
    elif any(k in name for k in ['شنا', 'سینه', 'پرس سینه', 'فلای', 'کراس', 'پک دک']) or muscle == 'chest':
        if 'شنا' in name:
            tip = 'حفظ خط مستقیم بدن و سینه صاف؛ احتیاط در آسیب مچ و شانه'
        elif any(k in name for k in ['فلای', 'کراس', 'پک دک']):
            tip = 'کشش کنترل‌شده سینه بدون کشش افراطی و آسیب مفصل شانه'
        elif any(k in name for k in ['بالاسینه', 'بالا سینه']):
            tip = 'تمرکز بر بخش بالای سینه؛ عدم قفل کردن آرنج در بالای حرکت'
        elif any(k in name for k in ['زیرسینه', 'زیر سینه']):
            tip = 'انقباض متمرکز بخش تحتانی سینه و کنترل کامل وزنه در فرود'
        else:
            tip = 'کشش عمیق سینه و انقباض در اوج؛ عدم قفل آرنج در بالای حرکت'

    # 7. Back & Lats & Deadlifts
    elif any(k in name for k in ['زیربغل', 'لت', 'پشت', 'قایقی', 'روئینگ', 'بارفیکس', 'تی‌بار', 'اچ', 'پول اور', 'ددلیفت', 'لیفت', 'فیله', 'سلام ژاپنی']) or muscle == 'back':
        if 'بارفیکس' in name:
            tip = 'پایین کشیدن کتف‌ها و بالا بردن سینه بدون تاب دادن بدن'
        elif any(k in name for k in ['لت', 'سیمکش', 'سیم کش']):
            tip = 'کشش در بالا و انقباض لت در پایین بدون خم شدن زیاد به عقب'
        elif any(k in name for k in ['روئینگ', 'قایقی', 'خم', 'تی‌بار', 'اچ']):
            tip = 'صاف نگه داشتن کمر و جمع کردن کتف‌ها در انتهای دامنه حرکت'
        elif any(k in name for k in ['پول اور', 'پلاور']):
            tip = 'دامنه کنترل‌شده بدون کشش افراطی در مفصل شانه در بالای سر'
        elif any(k in name for k in ['ددلیفت', 'لیفت']):
            tip = 'ستون فقرات کاملاً خنثی و میله نزدیک بدن؛ عدم قوز کمر'
        elif any(k in name for k in ['فیله', 'سلام ژاپنی']):
            tip = 'بالا آمدن با انقباض فیله و سرینی بدون قوس زدن افراطی کمر'
        else:
            tip = 'پایین کشیدن کتف‌ها و انقباض کامل عضلات پشت بدون قوز کمر'

    # 8. Shoulders & Traps
    elif any(k in name for k in ['سرشانه', 'نشر', 'کول', 'شانه', 'دلتا']) or muscle in ['shoulders', 'traps']:
        if 'نشر' in name:
            tip = 'کنترل کامل فاز منفی بدون پرتاب وزنه و با آرنج منعطف'
        elif 'کول' in name:
            tip = 'بالا کشیدن شانه با انقباض ذوزنقه بدون چرخش اضافی سرشانه'
        elif any(k in name for k in ['پرس سرشانه', 'پرس شانه', 'پرس نظامی']):
            tip = 'عدم قوس دادن به کمر در بالای سر و توقف وزنه در خط گوش‌ها'
        elif any(k in name for k in ['معکوس', 'فیس پول', 'پشت سرشانه']):
            tip = 'تمرکز بر بخش پشتی سرشانه و نزدیک کردن کتف‌ها بدون تاب بدن'
        else:
            tip = 'حرکت با دامنه کنترل‌شده؛ احتیاط در التهاب تاندون شانه'

    # 9. Abs & Core
    elif any(k in name for k in ['شکم', 'کرانچ', 'پلانک', 'پهلو', 'درازنشست', 'خلبانی', 'کوهنوردی', 'تو شکم', 'رول آوت', 'اینچ ورم', 'شکم خلبانی']) or muscle == 'abs':
        if 'پلانک' in name:
            tip = 'انقباض مداوم شکم و باسن در خط مستقیم بدون افتادگی لگن'
        elif any(k in name for k in ['پهلو', 'مورب', 'روسی']):
            tip = 'انقباض متمرکز عضلات مورب شکمی بدون چرخش ناگهانی مهره‌ها'
        elif any(k in name for k in ['خلبانی', 'بالا آوردن پا', 'زیرشکم']):
            tip = 'کنترل حرکت بدون تاب خوردن بدن و بالا بردن پا با چرخش لگن'
        elif any(k in name for k in ['رول آوت', 'اینچ ورم', 'چرخ شکم']):
            tip = 'حفظ ثبات تنه و پرهیز از گودی کمر؛ احتیاط کامل در درد کمر'
        else:
            tip = 'انقباض پیوسته شکم و جلوگیری از کشیدن گردن یا گودی کمر'

    # 10. Calves
    elif any(k in name for k in ['ساق', 'دوقلو']) or muscle == 'calves':
        tip = 'کشش کامل در پایین و مکث ۱ ثانیه‌ای در اوج انقباض روی پنجه'

    # 11. Forearms
    elif any(k in name for k in ['ساعد', 'مچ']) or muscle == 'forearms':
        tip = 'دامنه حرکتی متمرکز و آرام با مچ‌ها بدون حرکت اضافی در آرنج'

    # 12. Fallback
    else:
        tip = 'اجرای کنترل‌شده با تمرکز بر عضله هدف و تنفس منظم در حین حرکت'

    # Explicit contraindications
    if contra:
        if 'knee' in contra and 'زانو' not in tip:
            tip = 'حفظ ستون فقرات خنثی و زانو منعطف؛ احتیاط در آسیب زانو'
        elif 'back' in contra and 'کمر' not in tip:
            tip = 'تثبیت ستون فقرات بدون قوز؛ احتیاط در درد یا آسیب کمر'
        elif 'shoulder' in contra and 'شانه' not in tip:
            tip = 'دامنه کنترل‌شده و ثبات کتف‌ها؛ احتیاط در آسیب سرشانه'
        elif 'wrist' in contra and 'مچ' not in tip:
            tip = 'کنترل کامل راستای مچ دست؛ احتیاط در آسیب مچ'

    return tip

def apply_all():
    appdata_dir = os.environ.get('APPDATA', '')
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_paths = [
        os.path.join(base_dir, 'data', 'nemov.db'),
        os.path.join(base_dir, 'data', 'yalda.db'),
        os.path.join(appdata_dir, 'Nemov', 'data', 'nemov.db'),
        os.path.join(appdata_dir, 'Nemov', 'data', 'yalda.db'),
    ]

    for path in db_paths:
        if not os.path.exists(path):
            continue
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("SELECT id, name_fa, primary_muscle, equipment, contraindications FROM exercises")
        rows = c.fetchall()
        for eid, name, muscle, equip, contra in rows:
            cue = get_expert_cue(name, muscle, equip, contra)
            c.execute("UPDATE exercises SET description = ? WHERE id = ?", (cue, eid))
        conn.commit()
        conn.close()
        print(f"Refined descriptions in: {path}")

if __name__ == '__main__':
    apply_all()
