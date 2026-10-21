import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure application path
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from nemov.views.components.unregistered_items_dialog import UnregisteredItemsDialog
from nemov.services.workout_service import WorkoutService
from nemov.services.nutrition_service import NutritionService
from nemov.services.member_service import MemberService
from nemov.database.connection import get_session, check_and_migrate_db
from nemov.models.database_models import Member, Exercise, FoodItem, WorkoutPlan, NutritionPlan
from nemov.pdf.pdf_generator import PDFGenerator


def test_visual_dialog():
    print("--- 1. Testing Visual QA for UnregisteredItemsDialog ---")
    import config
    from PyQt6.QtGui import QFontDatabase, QFont
    font_path = config.BASE_DIR / "resources" / "fonts" / "BKoodakBd.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QFont("B Koodak", 10))

    qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            content = f.read()
            arrow_down_path = (config.BASE_DIR / "resources" / "images" / "arrow_down.svg").as_posix()
            arrow_up_path = (config.BASE_DIR / "resources" / "images" / "arrow_up.svg").as_posix()
            check_path = (config.BASE_DIR / "resources" / "images" / "check.svg").as_posix()
            content = content.replace("resources/images/arrow_down.svg", arrow_down_path)
            content = content.replace("resources/images/arrow_up.svg", arrow_up_path)
            content = content.replace("resources/images/check.svg", check_path)
            app.setStyleSheet(content)

    items = [
        "شنا سوئدی روی پنجه پا با کش مقاومتی",
        "پرس سرشانه تک‌دست نشسته روی جعبه",
        "لانج تعادلی معکوس با بوسوبال",
        "دیپ پارالل مایل مچ برعکس",
        "پلانک چرخشی با دمبل سبک",
        "اسکوات زرچر انفجاری با طناب کشی"
    ]
    dlg = UnregisteredItemsDialog(item_type="exercise", unregistered_items=items, mode="assign")
    dlg.show()
    app.processEvents()

    # Capture collapsed screenshot
    collapsed_pix = dlg.grab()
    collapsed_path = "qa_unregistered_dialog_collapsed.png"
    collapsed_pix.save(collapsed_path)
    print(f"Captured collapsed dialog: {collapsed_path} ({collapsed_pix.width()}x{collapsed_pix.height()})")

    # Toggle to expanded
    dlg._toggle_items_list()
    app.processEvents()
    expanded_pix = dlg.grab()
    expanded_path = "qa_unregistered_dialog_expanded.png"
    expanded_pix.save(expanded_path)
    print(f"Captured expanded dialog: {expanded_path} ({expanded_pix.width()}x{expanded_pix.height()})")

    dlg.close()


def test_functional_workout_plan_unlisted():
    print("\n--- 2. Testing Functional QA: Workout Plan with Unlisted Exercise ---")
    check_and_migrate_db()
    session = get_session()
    try:
        # Find or create a test member
        member = session.query(Member).first()
        if not member:
            member = Member(
                national_id="9999999999",
                first_name="آرش",
                last_name="کمانگیر",
                gender="male",
                phone="09120000000"
            )
            session.add(member)
            session.commit()

        member_id = member.id
        custom_ex_name = "حرکت تستی کاملاً اختصاصی بدون ثبت در بانک"

        # Create unlisted exercise
        unlisted_ex = WorkoutService.create_exercise({
            "name_fa": custom_ex_name,
            "primary_muscle": "سایر",
            "equipment": "سایر",
            "is_custom": True,
            "is_unlisted": True
        })
        print(f"Created unlisted exercise ID: {unlisted_ex.id}, is_unlisted: {unlisted_ex.is_unlisted}")

        # Verify that get_all_exercises by default DOES NOT include it
        standard_exercises = WorkoutService.get_all_exercises(include_unlisted=False)
        assert not any(e.id == unlisted_ex.id for e in standard_exercises), "Unlisted exercise leaked into standard bank!"
        print("✓ Verified: Unlisted exercise does NOT appear in standard exercise bank dropdown!")

        # Create workout plan containing this exercise
        plan_info = {
            "title": "برنامه تست حرکات اختصاصی",
            "goal": "hypertrophy",
            "days_per_week": 1,
            "training_level": "beginner"
        }
        days_data = [
            {
                "day_number": 1,
                "day_title": "روز اول: اختصاصی",
                "exercises": [
                    {
                        "exercise_id": unlisted_ex.id,
                        "custom_exercise_name": custom_ex_name,
                        "sets": 4,
                        "reps": "12",
                        "weight_suggestion": "20kg",
                        "rest_seconds": 90,
                        "tempo": "3-0-1-0",
                        "trainer_notes": "با کنترل کامل وزنه"
                    }
                ]
            }
        ]

        created_plan = WorkoutService.create_workout_plan(plan_info, days_data)
        WorkoutService.assign_plan_to_member(member_id, created_plan.id)
        print(f"✓ Created workout plan ID: {created_plan.id} and assigned to member {member_id}")

        plan = WorkoutService.get_plan_by_id(created_plan.id)

        # Test PDF generation
        pdf_path = f"exports/test_workout_unlisted_{plan.id}.pdf"
        os.makedirs("exports", exist_ok=True)
        saved_pdf = PDFGenerator.generate_workout_pdf(member, plan, pdf_path)
        assert os.path.exists(saved_pdf), "PDF was not created!"
        assert os.path.getsize(saved_pdf) > 1000, "PDF file is too small or empty!"
        print(f"✓ Generated PDF successfully: {saved_pdf} ({os.path.getsize(saved_pdf)} bytes)")


    finally:
        session.close()


def test_functional_nutrition_plan_unlisted():
    print("\n--- 3. Testing Functional QA: Nutrition Plan with Unlisted Food ---")
    session = get_session()
    try:
        member = session.query(Member).first()
        member_id = member.id
        custom_food_name = "اسموتی دست‌ساز پروتئینی موز و جو دوسر"

        unlisted_food = NutritionService.add_custom_food({
            "name_fa": custom_food_name,
            "category": "other",
            "unit": "1 لیوان",
            "calories": 280,
            "protein_g": 25,
            "carbs_g": 35,
            "fat_g": 5,
            "is_custom": True,
            "is_unlisted": True
        })
        print(f"Created unlisted food ID: {unlisted_food.id}, is_unlisted: {unlisted_food.is_unlisted}")

        # Verify that get_all_foods by default DOES NOT include it
        standard_foods = NutritionService.get_all_foods(include_unlisted=False)
        assert not any(f.id == unlisted_food.id for f in standard_foods), "Unlisted food leaked into standard food bank!"
        print("✓ Verified: Unlisted food does NOT appear in standard food bank dropdown!")

        plan_info = {
            "title": "رژیم تست مواد اختصاصی",
            "goal": "muscle_gain",
            "target_calories": 2500,
            "target_protein": 160,
            "target_carbs": 280,
            "target_fat": 65
        }
        meals_data = [
            {
                "meal_name": "صبحانه",
                "order_index": 1,
                "items": [
                    {
                        "food_id": unlisted_food.id,
                        "custom_food_name": custom_food_name,
                        "amount": 2.0,
                        "unit": "لیوان",
                        "notes": "همراه با پودر دارچین"
                    }
                ]
            }
        ]

        created_nut_plan = NutritionService.create_nutrition_plan(plan_info, meals_data)
        NutritionService.assign_nutrition_plan(member_id, created_nut_plan.id)
        print(f"✓ Created nutrition plan ID: {created_nut_plan.id} and assigned to member {member_id}")

        nut_plan = NutritionService.get_plan_by_id(created_nut_plan.id)

        # Test PDF generation
        pdf_path = f"exports/test_nutrition_unlisted_{nut_plan.id}.pdf"
        saved_nut_pdf = PDFGenerator.generate_nutrition_pdf(member, nut_plan, pdf_path)
        assert os.path.exists(saved_nut_pdf), "Nutrition PDF was not created!"
        assert os.path.getsize(saved_nut_pdf) > 1000, "Nutrition PDF file is too small!"
        print(f"✓ Generated Nutrition PDF successfully: {saved_nut_pdf} ({os.path.getsize(saved_nut_pdf)} bytes)")

    finally:
        session.close()


if __name__ == "__main__":
    test_visual_dialog()
    test_functional_workout_plan_unlisted()
    test_functional_nutrition_plan_unlisted()
    print("\n==========================================")
    print("ALL VISUAL & FUNCTIONAL QA CHECKS PASSED 100%!")
    print("==========================================")
