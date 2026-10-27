import sys
import os
import sqlite3
import datetime
import traceback

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "details": []
}

def check(subsystem: str, feature: str, passed: bool, detail: str = "", is_warn: bool = False):
    status = "PASS" if passed else ("WARN" if is_warn else "FAIL")
    if passed:
        results["passed"] += 1
    elif is_warn:
        results["warnings"] += 1
    else:
        results["failed"] += 1
        
    results["details"].append({
        "subsystem": subsystem,
        "feature": feature,
        "status": status,
        "detail": detail
    })
    print(f"[{status}] [{subsystem}] {feature}: {detail}")

print("="*80)
print("STARTING COMPREHENSIVE END-TO-END TRACE OF ALL NEMOV SUBSYSTEMS")
print("="*80)

# ==============================================================================
# SECTION 1: AUTHENTICATION, PASSWORD RECOVERY & COACH CLOUD RESTORE
# ==============================================================================
print("\n--- 1. Auth, Password Recovery & Cloud Restore ---")
try:
    from nemov.database.connection import get_session
    from nemov.models.database_models import User
    from nemov.auth.authentication import (
        authenticate_user, check_username_exists, CurrentUser,
        verify_recovery_credentials
    )
    from nemov.views.login_view import LoginView
    from nemov.views.cloud_restore_dialog import CloudRestoreDialog
    from nemov.views.password_recovery_dialog import PasswordRecoveryDialog

    with get_session() as s:
        admin = s.query(User).filter(User.username == "admin").first()
        check("Auth", "Admin User Exists in Database", admin is not None, f"Admin found: {getattr(admin, 'display_name', None)}")
        
        # Test password check with master dynamic code
        if admin:
            user_auth = authenticate_user("admin", "2006")
            check("Auth", "Admin Authentication Logic", user_auth is not None, "Authenticated successfully as admin")

    # Test login view widget
    lv = LoginView()
    check("Auth", "LoginView UI Instantiation", lv is not None, "Login window rendered cleanly")

    # Test Cloud Restore Dialog logic
    crd = CloudRestoreDialog()
    check("Auth", "CloudRestoreDialog UI Instantiation", crd is not None, "Cloud restore dialog initialized")
    
    # Test phone number normalization
    from nemov.utils.jalali_date import normalize_digits
    test_phone = normalize_digits("۰۹۱۲۳۴۵۶۷۸۹")
    check("Auth", "Persian Phone Digits Normalization", test_phone == "09123456789", f"Normalized to: {test_phone}")

    # Test Password Recovery Dialog
    prd = PasswordRecoveryDialog()
    check("Auth", "PasswordRecoveryDialog UI Instantiation", prd is not None, "Password recovery initialized")

except Exception as e:
    check("Auth", "Auth Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 2: MEMBER MANAGEMENT & ENROLLMENT
# ==============================================================================
print("\n--- 2. Member Management & Enrollment ---")
created_m = None
try:
    from nemov.services.member_service import MemberService
    from nemov.models.database_models import Member, HealthRecord
    from nemov.views.member_list_view import MemberListView
    from nemov.views.member_form_dialog import MemberFormDialog
    from nemov.utils.jalali_date import get_today_shamsi, add_months_shamsi

    today_sh = get_today_shamsi()
    all_members = MemberService.get_all_members()
    check("Members", "Fetch All Members", True, f"Found {len(all_members)} members in DB")

    # Clean existing test member if any
    with get_session() as s:
        existing = s.query(Member).filter(Member.phone == "09999999999").all()
        for em in existing:
            s.delete(em)
        s.commit()

    test_member_data = {
        "first_name": "ورزشکار",
        "last_name": "تستی_سیستم",
        "phone": "09999999999",
        "gender": "male",
        "membership_start_shamsi": today_sh,
        "membership_expire_shamsi": add_months_shamsi(today_sh, 1),
        "tuition_fee": 1500000.0,
        "status": "active"
    }

    created_m = MemberService.create_member(test_member_data)
    check("Members", "Create Member with HealthRecord", created_m is not None and created_m.id is not None, f"Created ID: {getattr(created_m, 'id', None)}")

    # Verify associated health record exists
    if created_m:
        with get_session() as s:
            hr = s.query(HealthRecord).filter(HealthRecord.member_id == created_m.id).first()
            check("Members", "Auto HealthRecord Creation", hr is not None, f"HealthRecord ID: {getattr(hr, 'id', None)}")

        # Test member update
        updated_m = MemberService.update_member(created_m.id, {"height_cm": 182.0, "initial_weight_kg": 78.5})
        check("Members", "Update Member Specs", updated_m.height_cm == 182.0 and updated_m.initial_weight_kg == 78.5, f"Updated: {updated_m.height_cm}cm, {updated_m.initial_weight_kg}kg")

    # Test MemberListView
    mlv = MemberListView()
    check("Members", "MemberListView UI Instantiation", mlv is not None, f"Member list table rows: {mlv.table.rowCount()}")

except Exception as e:
    check("Members", "Member Management Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 3: TUITION PAYMENT & AUTO-RENEWAL OF MEMBERSHIP
# ==============================================================================
print("\n--- 3. Tuition Payment & Membership Expiration Renewal ---")
try:
    from nemov.services.accounting_service import AccountingService
    from nemov.models.database_models import TuitionPayment

    if created_m:
        # Deliberately expire member to test auto-renewal extension
        with get_session() as s:
            m_db = s.query(Member).filter(Member.id == created_m.id).first()
            m_db.membership_expire_shamsi = "1402/01/01"  # in past
            m_db.status = "expired"
            s.commit()

        # Test adding monthly tuition payment
        payment_amount = 1800000.0
        tp = AccountingService.add_tuition_payment(
            member_id=created_m.id,
            amount=payment_amount,
            payment_date_shamsi=today_sh,
            payment_type="شهریه دوره ماهانه",
            notes="تست خودکار تمدید شهریه"
        )
        check("Tuition", "Record Tuition Payment", tp is not None and tp.id is not None, f"Payment ID: {tp.id}, Amount: {tp.amount}")

        # Check member in DB after payment: did expiry extend and status activate?
        with get_session() as s:
            m_refreshed = s.query(Member).filter(Member.id == created_m.id).first()
            check("Tuition", "Member Tuition Fee Updated", m_refreshed.tuition_fee == payment_amount, f"Fee: {m_refreshed.tuition_fee}")
            check("Tuition", "Member Auto-Activated", m_refreshed.status == "active", f"Status: {m_refreshed.status}")
            
            # Verify expiry was renewed from today to +1 month!
            expected_new_expiry = add_months_shamsi(today_sh, 1)
            check("Tuition", "Membership Expiry Auto-Renewed (+1 Month)", m_refreshed.membership_expire_shamsi == expected_new_expiry, 
                  f"Actual: {m_refreshed.membership_expire_shamsi}, Expected: {expected_new_expiry}")

except Exception as e:
    check("Tuition", "Tuition Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 4: WORKOUT & NUTRITION PLANNING ENGINES
# ==============================================================================
print("\n--- 4. Workout & Nutrition Planning Engines ---")
try:
    from nemov.services.workout_service import WorkoutService
    from nemov.services.nutrition_service import NutritionService
    from nemov.views.workout_editor_view import WorkoutEditorView
    from nemov.views.nutrition_editor_view import NutritionEditorView
    from nemov.models.database_models import WorkoutPlan, WorkoutDay, WorkoutExercise, Exercise, FoodItem
    from nemov.utils.bmr_calculator import calculate_bmr_tdee

    # 1. Workout Editor View
    we_view = WorkoutEditorView()
    check("WorkoutPlan", "WorkoutEditorView Instantiation", we_view is not None, "Workout editor initialized")

    # 2. Nutrition Editor View
    ne_view = NutritionEditorView()
    check("NutritionPlan", "NutritionEditorView Instantiation", ne_view is not None, "Nutrition editor initialized")

    # Test BMR and TDEE calculation (Mifflin-St Jeor formula)
    bmr_m, tdee_m, pal_m, pal_title_m, _ = calculate_bmr_tdee(180.0, 85.0, 26, "male", "moderately_active")
    bmr_f, tdee_f, pal_f, pal_title_f, _ = calculate_bmr_tdee(165.0, 60.0, 24, "female", "lightly_active")
    check("NutritionPlan", "BMR & TDEE Calculation (Mifflin-St Jeor)", tdee_m > 2000 and tdee_f > 1400, 
          f"Male BMR: {bmr_m}, TDEE: {tdee_m} kcal ({pal_title_m}) | Female BMR: {bmr_f}, TDEE: {tdee_f} kcal")

    # Check exercise library count & muscle groups
    exs = WorkoutService.get_all_exercises()
    check("WorkoutPlan", "Exercise Bank Total Items", len(exs) >= 1000, f"Total exercises: {len(exs)}")

    # Check food library
    foods = NutritionService.get_all_foods()
    check("NutritionPlan", "Food Items Database", len(foods) > 0, f"Total food items: {len(foods)}")

except Exception as e:
    check("Planning", "Planning Engines Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 5: EXERCISE LIBRARY CLOUD VIDEO STREAMING
# ==============================================================================
print("\n--- 5. Exercise Library & Video Cloud URLs ---")
try:
    with get_session() as s:
        ex_cloud = s.query(Exercise).filter(Exercise.video_cloud_url.isnot(None), Exercise.video_cloud_url != "").all()
        check("CloudMedia", "Cloud Video URLs Availability", len(ex_cloud) >= 1000, f"Count with cloud video URL: {len(ex_cloud)}")
        
        # Verify URL domain structure
        sample_urls = [e.video_cloud_url for e in ex_cloud[:5]]
        all_valid_domains = all("storage.nemovapp.ir" in u or "nemovapp.ir" in u for u in sample_urls)
        check("CloudMedia", "Cloud Storage Domain Integrity", all_valid_domains, f"Sample URLs: {sample_urls[:2]}")

    # Test WorkoutLibraryView after our QWidget deletion fix
    from nemov.views.workout_library_view import WorkoutLibraryView
    wlv = WorkoutLibraryView()
    check("CloudMedia", "WorkoutLibraryView (Post-Fix)", wlv is not None and wlv.table.rowCount() == 1005, f"Workout library rows: {wlv.table.rowCount()}")

except Exception as e:
    check("CloudMedia", "Cloud Media Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 6: SMS NOTIFICATION ENGINE & DYNAMIC #GYM#
# ==============================================================================
print("\n--- 6. SMS Notification Engine ---")
try:
    from nemov.services.sms_service import SmsService
    from nemov.services.branding_service import BrandingService
    from nemov.views.sms_view import SmsView

    sms_v = SmsView()
    check("SMS", "SmsView UI Instantiation", sms_v is not None, "SMS control center initialized")

    # Test template replacement
    club_name = BrandingService.get_club_name()
    tmpl = "ورزشکار گرامی #NAME#، شهریه شما در تاریخ #EXPIRY# منقضی می‌شود. مدیریت باشگاه #GYM#"
    rendered = SmsService.render_template(
        tmpl,
        name="سامان اکبری",
        expiry="1403/09/01",
        gym=club_name
    )
    check("SMS", "Dynamic Tag Substitution (#NAME#, #EXPIRY#, #GYM#)", ("سامان اکبری" in rendered and "1403/09/01" in rendered and club_name in rendered), f"Rendered: '{rendered}'")

    # Verify templates exist
    templates = SmsService.get_templates()
    check("SMS", "Built-in SMS Templates", len(templates) > 0, f"Total templates: {len(templates)}")

except Exception as e:
    check("SMS", "SMS Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 7: ACCOUNTING, FINANCE & EXCEL EXPORTS
# ==============================================================================
print("\n--- 7. Accounting, Finance & Excel Exports ---")
try:
    from nemov.services.accounting_service import AccountingService
    from nemov.views.accounting_view import AccountingView
    from nemov.utils.excel_generator import ExcelGenerator
    from nemov.models.database_models import ClubExpense

    acc_v = AccountingView()
    check("Accounting", "AccountingView UI Instantiation", acc_v is not None, "Accounting dashboard loaded")

    # Test recording an expense
    exp = AccountingService.add_expense(
        title="خرید تجهیزات تست سیستم",
        amount=250000.0,
        expense_date_shamsi=today_sh,
        category="تجهیزات",
        description="تست خودکار پایش عملکرد"
    )
    check("Accounting", "Record Club Expense", exp is not None and exp.id is not None, f"Expense ID: {exp.id}, Amount: {exp.amount}")

    # Test financial summary calculation
    summary = AccountingService.get_financial_summary()
    check("Accounting", "Financial Summary Calculation", "net_profit" in summary and "total_income" in summary and "total_expense" in summary, 
          f"Income: {summary.get('total_income'):,}, Expense: {summary.get('total_expense'):,}, Net: {summary.get('net_profit'):,}")

    # Test Excel Export
    os.makedirs("exports", exist_ok=True)
    excel_path = "exports/test_audit_accounting.xlsx"
    txs = AccountingService.get_transactions()
    res_path = ExcelGenerator.generate_financial_excel(
        output_filepath=excel_path,
        summary=summary,
        transactions=txs,
        filter_info={"time_label": "کل دوره", "trainer_label": "همه مربیان"}
    )
    check("Accounting", "Excel (.xlsx) Report Generation", os.path.exists(excel_path) and os.path.getsize(excel_path) > 1000, 
          f"File created: {excel_path} ({os.path.getsize(excel_path)} bytes)")

except Exception as e:
    check("Accounting", "Accounting Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 8: PDF GENERATION & DYNAMIC BRANDING / LOGO INJECTION
# ==============================================================================
print("\n--- 8. PDF Generation & Dynamic Branding ---")
try:
    from nemov.pdf.pdf_generator import PDFGenerator
    from nemov.services.branding_service import BrandingService
    from nemov.models.database_models import (
        WorkoutPlan, WorkoutDay, WorkoutExercise, Exercise,
        NutritionPlan, MealPlan, FoodItem, MealItem
    )

    # 1. Test Workout PDF Generation
    with get_session() as s:
        first_m = s.query(Member).first()
        sample_ex = s.query(Exercise).first()

        if first_m and sample_ex:
            wp = WorkoutPlan(
                title="برنامه تمرینی اختصاصی",
                goal="hypertrophy",
                days_per_week=3
            )
            day1 = WorkoutDay(day_number=1, day_title="روز اول (سینه و پشت بازو)")
            we1 = WorkoutExercise(
                exercise_id=sample_ex.id,
                sets=4,
                reps="10-12",
                rest_seconds=60,
                tempo="2-0-2",
                trainer_notes="انقباض کامل در انتهای دامنه حرکت"
            )
            we1.exercise = sample_ex
            day1.workout_exercises = [we1]
            wp.days = [day1]

            w_pdf_out = "exports/test_audit_workout_plan.pdf"
            PDFGenerator.generate_workout_pdf(first_m, wp, w_pdf_out)
            check("PDF", "Workout PDF Generation with Logo", os.path.exists(w_pdf_out) and os.path.getsize(w_pdf_out) > 5000,
                  f"Workout PDF: {w_pdf_out} ({os.path.getsize(w_pdf_out)} bytes)")

            # 2. Test Nutrition PDF Generation
            np = NutritionPlan(
                title="برنامه غذایی اختصاصی",
                goal="muscle_gain",
                target_calories=2500,
                target_protein=160,
                target_carbs=300,
                target_fat=70
            )
            sample_food = s.query(FoodItem).first()
            mp1 = MealPlan(meal_name="صبحانه", order_index=1)
            if sample_food:
                mi1 = MealItem(food_id=sample_food.id, amount=150.0, unit="گرم", notes="همراه با آبمیوه")
                mi1.food = sample_food
                mp1.items = [mi1]
            np.meals = [mp1]

            n_pdf_out = "exports/test_audit_nutrition_plan.pdf"
            PDFGenerator.generate_nutrition_pdf(np, first_m, n_pdf_out)
            check("PDF", "Nutrition PDF Generation with Logo", os.path.exists(n_pdf_out) and os.path.getsize(n_pdf_out) > 5000,
                  f"Nutrition PDF: {n_pdf_out} ({os.path.getsize(n_pdf_out)} bytes)")

            # 3. Test Financial PDF Generation
            f_pdf_out = "exports/test_audit_financial_report.pdf"
            PDFGenerator.generate_financial_pdf(
                summary=AccountingService.get_financial_summary(),
                transactions=AccountingService.get_transactions(),
                filter_info={"time_label": "کل دوره", "trainer_label": "همه مربیان"},
                output_path=f_pdf_out
            )
            check("PDF", "Financial PDF Generation with Logo", os.path.exists(f_pdf_out) and os.path.getsize(f_pdf_out) > 5000,
                  f"Financial PDF: {f_pdf_out} ({os.path.getsize(f_pdf_out)} bytes)")

except Exception as e:
    check("PDF", "PDF Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")


# ==============================================================================
# SECTION 9: SETTINGS, THEME MANAGER & BACKUP SYSTEM
# ==============================================================================
print("\n--- 9. Settings, Theme Manager & Backup Engine ---")
try:
    from nemov.utils.theme_manager import ThemeManager
    from nemov.services.backup_service import BackupService
    from nemov.views.backup_view import BackupView

    # Theme Manager 17 palettes
    themes = ThemeManager.PALETTES
    check("Settings", "Theme Palettes Engine", len(themes) == 17, f"Total palettes registered: {len(themes)}")

    # Backup View UI
    bv = BackupView()
    check("Settings", "BackupView UI Instantiation", bv is not None, "Backup management dashboard initialized")

    # Database connection test
    with get_session() as s:
        check("Settings", "Direct SQLite Session Connection", s.is_active, "Session open and healthy")

except Exception as e:
    check("Settings", "Settings Subsystem Execution", False, f"Exception: {e}\n{traceback.format_exc()}")

# Clean up temporary created member and expense to leave DB 100% clean
try:
    with get_session() as s:
        if created_m:
            m_del = s.query(Member).filter(Member.id == created_m.id).first()
            if m_del:
                s.delete(m_del)
        if 'exp' in locals() and exp:
            exp_del = s.query(ClubExpense).filter(ClubExpense.id == exp.id).first()
            if exp_del:
                s.delete(exp_del)
        s.commit()
    print("\n[INFO] Cleaned up temporary test member and records.")
except Exception:
    pass

print("\n" + "="*80)
print(f"FINAL AUDIT EXECUTION SUMMARY:")
print(f"  TOTAL CHECKS: {results['passed'] + results['failed'] + results['warnings']}")
print(f"  PASSED:       {results['passed']}")
print(f"  FAILED:       {results['failed']}")
print(f"  WARNINGS:     {results['warnings']}")
print("="*80)
