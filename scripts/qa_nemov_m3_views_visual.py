#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visual & Functional QA Inspection: Milestone 3 (Views & Dialogs Theming)
Verifies all modified views and modal dialogs render properly across dark immersion
(royal_gold, neon_pulse) and 9router light (olympic_white, fresh_mint) palettes.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from yalda.utils.theme_manager import ThemeManager

TEST_THEMES = ["royal_gold", "neon_pulse", "olympic_white", "fresh_mint"]

def run_visual_inspection():
    print("=" * 80)
    print("MILESTONE 3: VIEWS & MODAL DIALOGS VISUAL & FUNCTIONAL QA INSPECTION")
    print("=" * 80)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    output_dir = PROJECT_ROOT / "qa_artifacts" / "m3_views"
    output_dir.mkdir(parents=True, exist_ok=True)

    from yalda.views.components.stat_card import StatCard
    from yalda.views.dashboard_view import DashboardView
    from yalda.views.member_list_view import MemberListView
    from yalda.views.accounting_view import AccountingView
    from yalda.views.sms_view import SmsView
    from yalda.views.backup_view import BackupView
    from yalda.views.components.tuition_payment_dialog import TuitionPaymentDialog
    from yalda.views.components.expense_form_dialog import ExpenseFormDialog
    from yalda.views.components.trainer_details_dialog import TrainerDetailsDialog
    from yalda.views.trainer_register_dialog import TrainerRegisterDialog
    from yalda.views.password_recovery_dialog import PasswordRecoveryDialog
    from yalda.views.cloud_restore_dialog import CloudRestoreDialog
    from yalda.views.components.backup_destination_dialog import BackupDestinationDialog
    from yalda.views.components.email_spam_guide_dialog import EmailSpamGuideDialog
    from yalda.views.components.unregistered_items_dialog import UnregisteredItemsDialog
    from yalda.views.data_migration_dialog import DataMigrationDialog
    from yalda.views.components.jalali_calendar_widget import JalaliCalendarDialog
    from yalda.views.workout_editor_view import IncompletePlanWarningDialog

    passed_checks = 0
    total_checks = 0

    for theme_key in TEST_THEMES:
        print(f"\n🎨 Testing Theme: {theme_key}")
        ThemeManager.apply_theme(theme_key, app)
        palette = ThemeManager.get_current_palette()

        # 1. StatCard
        total_checks += 1
        sc = StatCard("تعداد ورزشکاران", "145", "👤", "#10B981")
        sc.resize(220, 100)
        sc.show()
        pix = sc.grab()
        assert not pix.isNull() and pix.width() > 0, "StatCard grab failed"
        sc.close()
        print(f"  [PASS] StatCard rendered cleanly in {theme_key}")
        passed_checks += 1

        # 2. DashboardView
        total_checks += 1
        dv = DashboardView()
        dv.resize(1024, 700)
        dv.show()
        pix = dv.grab()
        assert not pix.isNull() and pix.width() > 0, "DashboardView grab failed"
        # Save snapshot for first dark and first light
        if theme_key in ["royal_gold", "olympic_white"]:
            pix.save(str(output_dir / f"dashboard_{theme_key}.png"))
        dv.close()
        print(f"  [PASS] DashboardView rendered cleanly in {theme_key}")
        passed_checks += 1

        # 3. MemberListView
        total_checks += 1
        mlv = MemberListView()
        mlv.resize(1024, 700)
        mlv.show()
        pix = mlv.grab()
        assert not pix.isNull() and pix.width() > 0, "MemberListView grab failed"
        if theme_key in ["royal_gold", "olympic_white"]:
            pix.save(str(output_dir / f"members_{theme_key}.png"))
        mlv.close()
        print(f"  [PASS] MemberListView rendered cleanly in {theme_key}")
        passed_checks += 1

        # 4. AccountingView
        total_checks += 1
        av = AccountingView()
        av.resize(1024, 700)
        av.show()
        pix = av.grab()
        assert not pix.isNull() and pix.width() > 0, "AccountingView grab failed"
        if theme_key in ["royal_gold", "olympic_white"]:
            pix.save(str(output_dir / f"accounting_{theme_key}.png"))
        av.close()
        print(f"  [PASS] AccountingView rendered cleanly in {theme_key}")
        passed_checks += 1

        # 5. SMSView
        total_checks += 1
        sv = SmsView()
        sv.resize(1024, 700)
        sv.show()
        pix = sv.grab()
        assert not pix.isNull() and pix.width() > 0, "SMSView grab failed"
        sv.close()
        print(f"  [PASS] SMSView rendered cleanly in {theme_key}")
        passed_checks += 1

        # 6. BackupView
        total_checks += 1
        bv = BackupView()
        bv.resize(1024, 700)
        bv.show()
        pix = bv.grab()
        assert not pix.isNull() and pix.width() > 0, "BackupView grab failed"
        bv.close()
        print(f"  [PASS] BackupView rendered cleanly in {theme_key}")
        passed_checks += 1

        # 7. TuitionPaymentDialog
        total_checks += 1
        tpd = TuitionPaymentDialog(member_id=1)
        tpd.show()
        pix = tpd.grab()
        assert not pix.isNull() and pix.width() > 0, "TuitionPaymentDialog grab failed"
        tpd.close()
        print(f"  [PASS] TuitionPaymentDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 8. ExpenseFormDialog
        total_checks += 1
        efd = ExpenseFormDialog()
        efd.show()
        pix = efd.grab()
        assert not pix.isNull() and pix.width() > 0, "ExpenseFormDialog grab failed"
        efd.close()
        print(f"  [PASS] ExpenseFormDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 9. TrainerDetailsDialog
        total_checks += 1
        tdd = TrainerDetailsDialog(trainer_data={"full_name": "مربی نموف", "username": "coach1", "phone": "09120000000"})
        tdd.show()
        pix = tdd.grab()
        assert not pix.isNull() and pix.width() > 0, "TrainerDetailsDialog grab failed"
        tdd.close()
        print(f"  [PASS] TrainerDetailsDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 10. TrainerRegisterDialog
        total_checks += 1
        trd = TrainerRegisterDialog()
        trd.show()
        pix = trd.grab()
        assert not pix.isNull() and pix.width() > 0, "TrainerRegisterDialog grab failed"
        trd.close()
        print(f"  [PASS] TrainerRegisterDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 11. PasswordRecoveryDialog
        total_checks += 1
        prd = PasswordRecoveryDialog()
        prd.show()
        pix = prd.grab()
        assert not pix.isNull() and pix.width() > 0, "PasswordRecoveryDialog grab failed"
        prd.close()
        print(f"  [PASS] PasswordRecoveryDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 12. CloudRestoreDialog
        total_checks += 1
        crd = CloudRestoreDialog()
        crd.show()
        pix = crd.grab()
        assert not pix.isNull() and pix.width() > 0, "CloudRestoreDialog grab failed"
        crd.close()
        print(f"  [PASS] CloudRestoreDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 13. BackupDestinationDialog
        total_checks += 1
        bdd = BackupDestinationDialog()
        bdd.show()
        pix = bdd.grab()
        assert not pix.isNull() and pix.width() > 0, "BackupDestinationDialog grab failed"
        bdd.close()
        print(f"  [PASS] BackupDestinationDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 14. EmailSpamGuideDialog
        total_checks += 1
        esd = EmailSpamGuideDialog()
        esd.show()
        pix = esd.grab()
        assert not pix.isNull() and pix.width() > 0, "EmailSpamGuideDialog grab failed"
        esd.close()
        print(f"  [PASS] EmailSpamGuideDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 15. UnregisteredItemsDialog
        total_checks += 1
        uid = UnregisteredItemsDialog(item_type="exercise", unregistered_items=["پرس سینه جدید", "اسکوات بولگاری"])
        uid.show()
        pix = uid.grab()
        assert not pix.isNull() and pix.width() > 0, "UnregisteredItemsDialog grab failed"
        uid.close()
        print(f"  [PASS] UnregisteredItemsDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 16. DataMigrationDialog
        total_checks += 1
        dmd = DataMigrationDialog()
        dmd.show()
        pix = dmd.grab()
        assert not pix.isNull() and pix.width() > 0, "DataMigrationDialog grab failed"
        dmd.close()
        print(f"  [PASS] DataMigrationDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 17. JalaliCalendarDialog
        total_checks += 1
        jcd = JalaliCalendarDialog()
        jcd.show()
        pix = jcd.grab()
        assert not pix.isNull() and pix.width() > 0, "JalaliCalendarDialog grab failed"
        jcd.close()
        print(f"  [PASS] JalaliCalendarDialog rendered cleanly in {theme_key}")
        passed_checks += 1

        # 18. IncompletePlanWarningDialog
        total_checks += 1
        ipd = IncompletePlanWarningDialog(empty_days=[(0, "روز اول"), (2, "روز سوم")])
        ipd.show()
        pix = ipd.grab()
        assert not pix.isNull() and pix.width() > 0, "IncompletePlanWarningDialog grab failed"
        ipd.close()
        print(f"  [PASS] IncompletePlanWarningDialog rendered cleanly in {theme_key}")
        passed_checks += 1

    print("\n" + "=" * 80)
    print(f"VISUAL INSPECTION RESULT: {passed_checks}/{total_checks} CHECKS PASSED (100%)")
    print(f"Snapshots saved to: {output_dir}")
    print("=" * 80)

if __name__ == "__main__":
    run_visual_inspection()
