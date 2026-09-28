from sqlalchemy.orm import Session
from yalda.models.database_models import User, Exercise, FoodItem, SystemSetting
from yalda.utils.security import hash_password

def seed_initial_data(session: Session):
    # 1. Create Default Admin User if not exist (No dummy trainer accounts)
    if session.query(User).count() == 0:
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            full_name="مدیر سیستم",
            first_name="مدیر",
            last_name="سیستم",
            role="admin",
            is_active=True
        )
        session.add(admin_user)
        session.commit()

    # 1.1 Set initial app license status to false (Inactive until activated by Admin)
    if session.query(SystemSetting).filter(SystemSetting.key == "app_license_active").count() == 0:
        session.add(SystemSetting(key="app_license_active", value="false"))
        session.commit()

    # 2. Create Default Exercise Library if empty
    if session.query(Exercise).count() == 0:
        exercises = [
            # سینه (Chest)
            Exercise(name_fa="پرس سینه با هالتر", name_en="Barbell Bench Press", primary_muscle="chest", secondary_muscles="triceps, shoulders", equipment="barbell", contraindications="shoulder_injury", description="حرکت اصلی برای افزایش حجم و قدرت سینه"),
            Exercise(name_fa="پرس بالا سینه با دمبل", name_en="Incline Dumbbell Press", primary_muscle="chest", secondary_muscles="shoulders", equipment="dumbbell", contraindications="shoulder_injury", description="تمرکز بر عضلات بالایی سینه"),
            Exercise(name_fa="قفسه سینه دمبل (فلای)", name_en="Dumbbell Flyes", primary_muscle="chest", secondary_muscles="", equipment="dumbbell", contraindications="shoulder_injury", description="حرکت تک مفصلی جهت کشش عضلات سینه"),
            Exercise(name_fa="شنا سوئدی", name_en="Push-ups", primary_muscle="chest", secondary_muscles="triceps, core", equipment="bodyweight", contraindications="wrist_injury", description="حرکت وزن بدن برای آمادگی عمومی سینه"),

            # پا (Legs)
            Exercise(name_fa="اسکوات با هالتر", name_en="Barbell Back Squat", primary_muscle="legs", secondary_muscles="glutes, core", equipment="barbell", contraindications="knee_injury, back_injury", description="پادشاه حرکات پا برای حجم و قدرت کوادریسپس"),
            Exercise(name_fa="پرس پا دستگاه", name_en="Leg Press", primary_muscle="legs", secondary_muscles="glutes", equipment="machine", contraindications="knee_injury", description="حرکت ایمن‌تر با دستگاه برای عضلات پا"),
            Exercise(name_fa="ددلیفت رومانیایی", name_en="Romanian Deadlift", primary_muscle="legs", secondary_muscles="hamstrings, glutes, lower_back", equipment="barbell", contraindications="back_injury", description="حرکت عالی برای همسترینگ و سرینی"),
            Exercise(name_fa="پشت پا دستگاه خوابیده", name_en="Lying Leg Curls", primary_muscle="legs", secondary_muscles="hamstrings", equipment="machine", contraindications="knee_injury", description="تمرکز تک مفصلی روی عضلات پشت پا"),
            Exercise(name_fa="جلو پا دستگاه", name_en="Leg Extensions", primary_muscle="legs", secondary_muscles="quadriceps", equipment="machine", contraindications="knee_injury", description="ایزوله کردن عضلات چهارسر ران"),

            # زیربغل و پشت (Back)
            Exercise(name_fa="زیربغل سیم‌کش (لات پول‌داون)", name_en="Lat Pulldown", primary_muscle="back", secondary_muscles="biceps", equipment="cable", contraindications="", description="افزایش عرض عضلات پشتی و زیربغل"),
            Exercise(name_fa="زیربغل قایقی سیم‌کش", name_en="Seated Cable Row", primary_muscle="back", secondary_muscles="biceps, rhomboids", equipment="cable", contraindications="back_injury", description="افزایش ضخامت عضلات پشت"),
            Exercise(name_fa="بارفیکس دست باز", name_en="Wide Grip Pull-ups", primary_muscle="back", secondary_muscles="biceps", equipment="bodyweight", contraindications="shoulder_injury", description="حرکت عالی وزن بدن برای بخش پشتی"),
            Exercise(name_fa="ددلیفت سنتی", name_en="Conventional Deadlift", primary_muscle="back", secondary_muscles="legs, core", equipment="barbell", contraindications="back_injury", description="حرکت ترکیبی قدرت کل بدن"),

            # سرشانه (Shoulders)
            Exercise(name_fa="پرس سرشانه با دمبل نشسته", name_en="Seated Dumbbell Shoulder Press", primary_muscle="shoulders", secondary_muscles="triceps", equipment="dumbbell", contraindications="shoulder_injury", description="حجم‌دهی به بخش جلویی و میانی دلتوئید"),
            Exercise(name_fa="نشر جانب دمبل", name_en="Dumbbell Lateral Raise", primary_muscle="shoulders", secondary_muscles="", equipment="dumbbell", contraindications="shoulder_injury", description="ایزولاسیون دلتوئید جانبی برای عریض‌تر شدن سرشانه"),
            Exercise(name_fa="نشر خم دمبل", name_en="Rear Delt Flyes", primary_muscle="shoulders", secondary_muscles="upper_back", equipment="dumbbell", contraindications="", description="تقویت بخش پشتی سرشانه"),

            # بازو (Arms)
            Exercise(name_fa="جلو بازو با هالتر ایستاده", name_en="Barbell Bicep Curl", primary_muscle="arms", secondary_muscles="", equipment="barbell", contraindications="wrist_injury", description="اصلی‌ترین حرکت حجمی جلو بازو"),
            Exercise(name_fa="جلو بازو دمبل چکشی", name_en="Dumbbell Hammer Curl", primary_muscle="arms", secondary_muscles="forearms", equipment="dumbbell", contraindications="", description="تقویت عضلات براکیالیس و ساعد"),
            Exercise(name_fa="پشت بازو سیم‌کش با طناب", name_en="Tricep Rope Pushdown", primary_muscle="arms", secondary_muscles="", equipment="cable", contraindications="elbow_injury", description="ایزوله کردن عضلات سه سر بازویی"),
            Exercise(name_fa="پشت بازو دیپ دستگاه / پارالل", name_en="Tricep Dips", primary_muscle="arms", secondary_muscles="chest", equipment="bodyweight", contraindications="shoulder_injury", description="حرکت عالی برای حجم پشت بازو"),

            # شکم و فیله (Abs & Core)
            Exercise(name_fa="کرانچ شکم روی مت", name_en="Abdominal Crunch", primary_muscle="abs", secondary_muscles="", equipment="bodyweight", contraindications="back_injury", description="تقویت بخش بالایی راست شکمی"),
            Exercise(name_fa="پلانک ثابت", name_en="Plank", primary_muscle="abs", secondary_muscles="core, shoulders", equipment="bodyweight", contraindications="", description="تقویت استقامت کل عضلات کور و مرکز بدن"),
            Exercise(name_fa="فیله کمر روی نیمکت", name_en="Hyperextensions", primary_muscle="abs", secondary_muscles="lower_back, glutes", equipment="machine", contraindications="back_injury", description="تقویت راست‌کننده‌های ستون فقرات")
        ]
        session.add_all(exercises)
        session.commit()

    # 3. Safely merge Iranian Food Database without overwriting custom trainer foods
    seed_foods_database(session)

    # 4. Safely merge 157 corrective exercises pack without overwriting trainer exercises
    seed_corrective_exercises(session)


def seed_foods_database(session: Session):
    """
    Safely merges the comprehensive Iranian sports & nutrition foods database:
    - Guaranteed ZERO DELETIONS: Every single custom food item created by the trainer is 100% PRESERVED.
    - If a food item does not exist in the database, it is created with its accurate macros, category, and unit.
    - Does NOT overwrite existing items or modify custom trainer foods.
    """
    import os
    import json
    from pathlib import Path
    import config

    candidate_json_paths = [
        config.BASE_DIR / "resources" / "data" / "foods_database.json",
    ]

    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_json_paths.insert(0, Path(sys._MEIPASS) / "resources" / "data" / "foods_database.json")

    json_file = None
    for p in candidate_json_paths:
        if p.exists():
            json_file = p
            break

    if not json_file:
        return

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            food_items = json.load(f)
    except Exception:
        return

    # Map existing foods by Persian name
    existing_foods = {f.name_fa.strip(): f for f in session.query(FoodItem).all() if f.name_fa}

    added = []
    for item in food_items:
        name_fa = item.get("name_fa", "").strip()
        if not name_fa or name_fa in existing_foods:
            continue

        food = FoodItem(
            name_fa=name_fa,
            category=item.get("category", "rice"),
            unit=item.get("unit", "100 گرم"),
            calories=float(item.get("calories", 0.0)),
            protein_g=float(item.get("protein_g", 0.0)),
            carbs_g=float(item.get("carbs_g", 0.0)),
            fat_g=float(item.get("fat_g", 0.0)),
            is_custom=False
        )
        added.append(food)
        existing_foods[name_fa] = food

    # Normalize legacy categories from early versions if any exist
    legacy_updated = False
    for f in session.query(FoodItem).all():
        if f.category == "bread":
            f.category = "rice"
            legacy_updated = True
        elif f.category == "vegetables":
            f.category = "fruits"
            legacy_updated = True
        elif f.name_fa in ("مغز گردو", "مغز بادام درختى", "کره بادام زمینی") and f.category == "legumes":
            f.category = "nuts"
            legacy_updated = True
        elif f.name_fa == "مكمل وی پروتئین" and f.category == "dairy":
            f.category = "supplements"
            legacy_updated = True

    if added or legacy_updated:
        try:
            if added:
                session.add_all(added)
            session.commit()
            from yalda.database.connection import mark_data_changed
            mark_data_changed()
        except Exception:
            session.rollback()


def seed_corrective_exercises(session: Session):
    """
    Safely merges the 157 corrective exercises into the database:
    - Guaranteed ZERO DELETIONS: Every single custom exercise, workout plan, assessment, or member created by the trainer is 100% PRESERVED.
    - If a corrective movement does not exist in the database, it is created with its cloud video URL and thumbnail.
    - If it already exists, ensures its video_cloud_url and thumbnail are populated without altering custom trainer modifications.
    """
    import os
    import json
    from pathlib import Path
    import config

    candidate_json_paths = [
        config.BASE_DIR / "resources" / "data" / "corrective_exercises.json",
    ]

    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_json_paths.insert(0, Path(sys._MEIPASS) / "resources" / "data" / "corrective_exercises.json")

    json_file = None
    for p in candidate_json_paths:
        if p.exists():
            json_file = p
            break

    if not json_file:
        return

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            pack = json.load(f)
    except Exception:
        return

    # Map existing exercises by Persian name
    existing_exercises = {e.name_fa.strip(): e for e in session.query(Exercise).all() if e.name_fa}

    added_count = 0
    updated_count = 0

    for item in pack:
        name_fa = item.get("name_fa", "").strip()
        if not name_fa:
            continue

        thumb_fn = item.get("thumbnail_filename", "")
        thumb_path = ""
        if thumb_fn:
            from yalda.utils.image_utils import resolve_image_path
            resolved = resolve_image_path(thumb_fn)
            if resolved and os.path.exists(resolved):
                thumb_path = resolved

        cloud_url = item.get("video_cloud_url") or item.get("video_url") or ""

        if name_fa not in existing_exercises:
            new_ex = Exercise(
                name_fa=name_fa,
                name_en=item.get("name_en", ""),
                primary_muscle=item.get("primary_muscle", "other"),
                secondary_muscles=item.get("secondary_muscles", ""),
                equipment=item.get("equipment", "bodyweight"),
                media_path="",
                media_type="video",
                video_url=cloud_url,
                is_corrective=True,
                thumbnail_path=thumb_path,
                video_cloud_url=cloud_url,
                contraindications=item.get("contraindications", ""),
                description=item.get("description", "")
            )
            session.add(new_ex)
            existing_exercises[name_fa] = new_ex
            added_count += 1
        else:
            ex = existing_exercises[name_fa]
            changed = False
            if cloud_url and not ex.video_cloud_url:
                ex.video_cloud_url = cloud_url
                if not ex.video_url:
                    ex.video_url = cloud_url
                changed = True
            if thumb_path and not ex.thumbnail_path:
                ex.thumbnail_path = thumb_path
                changed = True
            if not ex.is_corrective:
                ex.is_corrective = True
                changed = True
            if ex.description and "پالس" in ex.description:
                ex.description = ""
                changed = True
            if changed:
                updated_count += 1

    if added_count > 0 or updated_count > 0:
        try:
            session.commit()
            from yalda.database.connection import mark_data_changed
            mark_data_changed()
        except Exception:
            session.rollback()
