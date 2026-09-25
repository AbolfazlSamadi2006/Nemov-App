import jdatetime

PAL_LEVELS = {
    "sedentary": {
        "pal": 1.2,
        "title": "بی‌تحرک",
        "desc": "بدون ورزش، کار نشسته، کم‌تحرک",
        "combo_text": "بی‌تحرک (بدون ورزش)",
        "color": "#64748B",
    },
    "lightly_active": {
        "pal": 1.375,
        "title": "کم‌فعالیت",
        "desc": "ورزش سبک ۱-۲ روز در هفته",
        "combo_text": "کم‌فعالیت (۱ تا ۲ روز)",
        "color": "#3B82F6",
    },
    "semi_active": {
        "pal": 1.46,
        "title": "نیمه‌فعال",
        "desc": "ورزش متوسط ۲-۳ روز در هفته",
        "combo_text": "نیمه‌فعال (۲ تا ۳ روز)",
        "color": "#06B6D4",
    },
    "moderately_active": {
        "pal": 1.55,
        "title": "فعالیت متوسط",
        "desc": "ورزش منظم ۳-۵ روز در هفته",
        "combo_text": "فعالیت متوسط (۳ تا ۵ روز)",
        "color": "#10B981",
    },
    "very_active": {
        "pal": 1.725,
        "title": "فعالیت سنگین",
        "desc": "ورزش سنگین ۶-۷ روز در هفته",
        "combo_text": "فعالیت سنگین (۶ تا ۷ روز)",
        "color": "#F59E0B",
    },
    "extra_active": {
        "pal": 1.9,
        "title": "فعالیت حرفه‌ای",
        "desc": "دو جلسه تمرین در روز یا کار فیزیکی شدید",
        "combo_text": "فعالیت حرفه‌ای (تمرین شدید)",
        "color": "#EF4444",
    },
}


def calculate_age_from_shamsi(birth_date_shamsi: str, default_age: int = 25) -> int:
    """
    محاسبه سن دقیق ورزشکار به سال بر اساس تاریخ تولد شمسی (YYYY/MM/DD)
    """
    if not birth_date_shamsi:
        return default_age
    try:
        persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        clean = str(birth_date_shamsi).translate(persian_to_eng).strip()
        parts = clean.replace("-", "/").split("/")
        if len(parts) < 1:
            return default_age
        byear = int(parts[0])
        bmonth = int(parts[1]) if len(parts) > 1 else 1
        bday = int(parts[2]) if len(parts) > 2 else 1

        today = jdatetime.date.today()
        age = today.year - byear - ((today.month, today.day) < (bmonth, bday))
        if 1 <= age <= 120:
            return age
    except Exception:
        pass
    return default_age


def calculate_bmr_tdee(
    height_cm: float,
    weight_kg: float,
    age: int = 25,
    gender: str = "male",
    activity_level: str = "moderately_active",
):
    """
    محاسبه متابولیسم پایه (BMR) و کالری مورد نیاز روزانه (TDEE = BMR * PAL)
    فرمول Mifflin-St Jeor:
      مردان: BMR = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
      زنان:  BMR = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    """
    try:
        height_cm = float(height_cm or 0.0)
        weight_kg = float(weight_kg or 0.0)
        age = int(age or 25)
    except (ValueError, TypeError):
        return 0, 0, 1.55, "نامشخص", "#888888"

    if height_cm <= 0 or weight_kg <= 0:
        return 0, 0, 1.55, "نامشخص", "#888888"

    if age <= 0 or age > 120:
        age = 25

    gender_norm = str(gender or "male").strip().lower()
    if gender_norm in ("female", "زن", "خانم"):
        bmr_raw = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) - 161.0
    else:
        bmr_raw = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) + 5.0

    pal_info = PAL_LEVELS.get(activity_level or "moderately_active", PAL_LEVELS["moderately_active"])
    pal = pal_info["pal"]
    tdee_raw = bmr_raw * pal

    bmr = max(0, int(round(bmr_raw)))
    tdee = max(0, int(round(tdee_raw)))

    return bmr, tdee, pal, pal_info["title"], pal_info["color"]
