"""
Comprehensive unit & QA tests for:
1. SQLite WAL mode, atomic sqlite3.Connection.backup(), and rolling local backups.
2. Dual AutoSave (3m hidden local vs 5m optional Runflare cloud) & independent dirty tracking.
3. Silent local flush on MainWindow logout() and closeEvent() without ExitBackupDialog.
4. Universal 3-second debounced DraftService + Notification Bar integration across all 7 forms.
5. Same-section conflict resolution prompt ("finish current vs discard current & open past draft").
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton

_APP = QApplication.instance() or QApplication(sys.argv)

import config
from nemov.auth.authentication import CurrentUser
from nemov.database.connection import (
    init_db,
    engine,
    checkpoint_wal,
    mark_data_changed,
    reset_data_changed,
    has_data_changed,
    has_local_data_changed,
    reset_local_data_changed,
)
from nemov.services import backup_service
from nemov.services.autosave_service import (
    AutoSaveManager,
    DEFAULT_AUTOSAVE_INTERVAL_MS,
    LOCAL_AUTOSAVE_INTERVAL_MS,
    set_autosave_enabled,
)
from nemov.services.draft_service import DraftService, DebouncedDraftBinder, DEFAULT_DRAFT_DEBOUNCE_MS
from nemov.services.member_service import MemberService


class TestSqliteWalAndAtomicBackups(unittest.TestCase):
    def setUp(self):
        init_db()
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="nemov_wal_qa_"))
        self.orig_backups = config.BACKUPS_DIR
        self.orig_appdata = config.APPDATA_DATA_DIR
        config.BACKUPS_DIR = self.tmp_dir / "backups"
        config.APPDATA_DATA_DIR = self.tmp_dir / "appdata"
        config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        config.APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        config.BACKUPS_DIR = self.orig_backups
        config.APPDATA_DATA_DIR = self.orig_appdata
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_wal_mode_and_checkpoint_enabled(self):
        with engine.connect() as conn:
            mode = conn.exec_driver_sql("PRAGMA journal_mode;").scalar()
        self.assertEqual(str(mode).lower(), "wal")
        self.assertTrue(checkpoint_wal("PASSIVE"))

    def test_create_local_backup_atomic_rolling_and_integrity(self):
        # First backup creates latest_backup.db + AppData mirrors
        p1 = backup_service.create_local_backup()
        self.assertIsNotNone(p1)
        self.assertTrue((config.BACKUPS_DIR / "latest_backup.db").exists())
        self.assertTrue((config.APPDATA_DATA_DIR / "nemov.db").exists())
        self.assertTrue((config.APPDATA_DATA_DIR / "yalda.db").exists())

        # Second & third backups rotate into prev1 and prev2 cleanly
        backup_service.create_local_backup()
        self.assertTrue((config.BACKUPS_DIR / "latest_backup_prev1.db").exists())
        backup_service.create_local_backup()
        self.assertTrue((config.BACKUPS_DIR / "latest_backup_prev2.db").exists())

        for db_file in (
            config.BACKUPS_DIR / "latest_backup.db",
            config.BACKUPS_DIR / "latest_backup_prev1.db",
            config.BACKUPS_DIR / "latest_backup_prev2.db",
            config.APPDATA_DATA_DIR / "nemov.db",
        ):
            con = sqlite3.connect(str(db_file))
            try:
                chk = con.execute("PRAGMA integrity_check;").fetchone()
            finally:
                con.close()
            self.assertEqual(chk, ("ok",))


class TestDualAutoSaveAndSilentExit(unittest.TestCase):
    def setUp(self):
        init_db()
        reset_data_changed()
        reset_local_data_changed()

    def test_intervals_and_cloud_toggle_keeps_local_active(self):
        self.assertEqual(LOCAL_AUTOSAVE_INTERVAL_MS, 3 * 60 * 1000)
        self.assertEqual(DEFAULT_AUTOSAVE_INTERVAL_MS, 5 * 60 * 1000)
        mgr = AutoSaveManager.get_instance()
        try:
            set_autosave_enabled(True)
            mgr.start()
            self.assertTrue(mgr.local_timer.isActive())
            self.assertTrue(mgr.timer.isActive())

            # Turning off cloud autosave stops cloud timer ONLY; local 3-min stays active
            mgr.stop_cloud()
            self.assertFalse(mgr.timer.isActive())
            self.assertTrue(mgr.local_timer.isActive())
        finally:
            set_autosave_enabled(False)
            mgr.stop()

    def test_local_flush_preserves_cloud_dirty_flag(self):
        mark_data_changed()
        self.assertTrue(has_local_data_changed())
        self.assertTrue(has_data_changed())
        mgr = AutoSaveManager.get_instance()
        ok = mgr.flush_local_sync()
        self.assertTrue(ok)
        self.assertFalse(has_local_data_changed())
        self.assertTrue(has_data_changed())
        reset_data_changed()

    def test_main_window_close_and_logout_silent_without_exit_dialog(self):
        from nemov.views.main_window import MainWindow
        fake_user = SimpleNamespace(id=99, username="coach_qa", full_name="مربی تست", phone="09120009988", role="trainer")
        mark_data_changed()
        with patch("nemov.views.main_window.ExitBackupDialog") as mock_exit_dlg, \
             patch.object(CurrentUser, "get", return_value=fake_user), \
             patch.object(CurrentUser, "logout") as mock_logout:
            mw = MainWindow()
            mw.show()
            _APP.processEvents()

            # Simulate dirty workout draft open in memory
            mw.view_workouts.txt_title.setText("برنامه خروج سریع")
            mw.view_workouts._snapshot_change()

            mw.logout()
            mock_exit_dlg.assert_not_called()
            mock_logout.assert_called()

            # Verify draft was silently flushed on logout!
            drafts = DraftService.list_drafts(trainer_scope="09120009988")
            self.assertTrue(any("برنامه خروج سریع" in d.get("title", "") for d in drafts))
            DraftService.clear_all_for_trainer("09120009988")

            # Also verify closeEvent never opens ExitBackupDialog when visible & dirty
            mark_data_changed()
            mw.show()
            ev = QCloseEvent()
            mw.closeEvent(ev)
            self.assertTrue(ev.isAccepted())
            mock_exit_dlg.assert_not_called()
            mw.close()


class TestUniversalDraftsAndNotificationConflict(unittest.TestCase):
    def setUp(self):
        init_db()
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="nemov_draft_qa_"))
        self.orig_data = config.DATA_DIR
        self.orig_appdata = config.APPDATA_DATA_DIR
        config.DATA_DIR = self.tmp_dir / "data"
        config.APPDATA_DATA_DIR = self.tmp_dir / "appdata"
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.trainer_a = SimpleNamespace(id=101, username="coachA", full_name="مربی الف", phone="09121111111", role="trainer")
        self.trainer_b = SimpleNamespace(id=102, username="coachB", full_name="مربی ب", phone="09122222222", role="trainer")

    def tearDown(self):
        DraftService.clear_all_for_trainer("09121111111")
        DraftService.clear_all_for_trainer("09122222222")
        config.DATA_DIR = self.orig_data
        config.APPDATA_DATA_DIR = self.orig_appdata
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_debounce_is_3_seconds_and_trainer_isolated(self):
        self.assertEqual(DEFAULT_DRAFT_DEBOUNCE_MS, 3000)
        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            DraftService.save_draft(
                draft_id="d_a1",
                section="workout_editor",
                section_title="برنامه‌ریزی تمرینی",
                title="برنامه اختصاصی مربی الف",
                summary="۴ حرکت",
                payload={"title": "برنامه اختصاصی مربی الف"},
            )
            a_drafts = DraftService.list_drafts()
            self.assertEqual(len(a_drafts), 1)

        with patch.object(CurrentUser, "get", return_value=self.trainer_b):
            b_drafts = DraftService.list_drafts()
            self.assertEqual(len(b_drafts), 0)

    def test_sidebar_renders_draft_notifications_with_dismiss_and_mark_read_preserves(self):
        from nemov.views.components.sidebar import Sidebar
        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            DraftService.save_draft(
                draft_id="d_notif_1",
                section="workout_editor",
                section_title="برنامه‌ریزی تمرینی",
                title="برنامه حجم سارا",
                summary="۳ حرکت",
                payload={"title": "برنامه حجم سارا"},
            )
            sb = Sidebar()
            sb.resize(230, 820)
            sb.show()
            _APP.processEvents()

            self.assertTrue(sb.unified_notif_card.isVisible())
            buttons_list = sb.notif_items_container.findChildren(QPushButton)
            self.assertTrue(any("📝" in b.text() and "ناتمام" in b.toolTip() for b in buttons_list))
            self.assertTrue(any(b.text() == "✕" for b in buttons_list))

            # Verify "Mark all daily reminders read" does NOT wipe unsaved work drafts!
            sb.on_mark_all_notifications_read()
            _APP.processEvents()
            self.assertEqual(len(DraftService.list_drafts()), 1)

            # Clicking ✕ dismisses the draft cleanly
            del_btn = next(b for b in sb.notif_items_container.findChildren(QPushButton) if b.text() == "✕")
            del_btn.click()
            _APP.processEvents()
            self.assertEqual(len(DraftService.list_drafts()), 0)
            sb.close()

    def test_all_seven_sections_draft_save_restore_and_clear(self):
        from nemov.views.member_form_dialog import MemberFormDialog
        from nemov.views.food_library_dialog import FoodFormDialog
        from nemov.views.workout_library_view import ExerciseFormDialog
        from nemov.views.health_record_view import HealthRecordView
        from nemov.views.assessment_view import AssessmentView
        from nemov.views.workout_editor_view import WorkoutEditorView
        from nemov.views.nutrition_editor_view import NutritionEditorView

        members = MemberService.get_all_members()
        if not members:
            m = MemberService.create_member({
                "first_name": "تست", "last_name": "پیش‌نویس", "phone": "09129998877",
                "gender": "male", "status": "active",
            })
            member_id = m.id
        else:
            member_id = members[0].id

        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            # 1. WorkoutEditorView
            we = WorkoutEditorView()
            we.txt_title.setText("پیش‌نویس تمرینی تست")
            we._snapshot_change()
            self.assertTrue(we.has_unfinished_work())
            we._draft_binder.flush_now()
            w_draft = DraftService.get_draft(we.get_active_draft_id())
            self.assertIsNotNone(w_draft)
            we2 = WorkoutEditorView()
            we2.restore_draft(w_draft)
            self.assertEqual(we2.txt_title.text(), "پیش‌نویس تمرینی تست")
            we2.reset_to_new_plan()
            self.assertIsNone(DraftService.get_draft(w_draft["draft_id"]))
            we.close(); we2.close()

            # 2. NutritionEditorView
            ne = NutritionEditorView()
            ne.txt_title.setText("پیش‌نویس غذایی تست")
            ne._snapshot_change()
            self.assertTrue(ne.has_unfinished_work())
            ne._draft_binder.flush_now()
            n_draft = DraftService.get_draft(ne.get_active_draft_id())
            self.assertIsNotNone(n_draft)
            ne2 = NutritionEditorView()
            ne2.restore_draft(n_draft)
            self.assertEqual(ne2.txt_title.text(), "پیش‌نویس غذایی تست")
            ne2.reset_form()
            self.assertIsNone(DraftService.get_draft(n_draft["draft_id"]))
            ne.close(); ne2.close()

            # 3. HealthRecordView
            hv = HealthRecordView(member_id)
            hv.txt_limitations.setText("پرهیز از اسکوات سنگین")
            self.assertTrue(hv.has_unfinished_work())
            hv._draft_binder.flush_now()
            h_draft = DraftService.get_draft(hv.get_active_draft_id())
            self.assertIsNotNone(h_draft)
            hv2 = HealthRecordView(member_id)
            hv2.restore_draft(h_draft)
            self.assertEqual(hv2.txt_limitations.toPlainText(), "پرهیز از اسکوات سنگین")
            hv2.revert_changes()
            self.assertIsNone(DraftService.get_draft(h_draft["draft_id"]))
            hv.close(); hv2.close()

            # 4. AssessmentView
            av = AssessmentView(member_id)
            av.spin_waist.setValue(84.5)
            self.assertTrue(av.has_unfinished_work())
            av._draft_binder.flush_now()
            a_draft = DraftService.get_draft(av.get_active_draft_id())
            self.assertIsNotNone(a_draft)
            av2 = AssessmentView(member_id)
            av2.restore_draft(a_draft)
            self.assertAlmostEqual(av2.spin_waist.value(), 84.5)
            av2.reset_form()
            self.assertIsNone(DraftService.get_draft(a_draft["draft_id"]))
            av.close(); av2.close()

            # 5. MemberFormDialog (Cancel clears, [X] close preserves)
            mf = MemberFormDialog()
            mf.txt_first_name.setText("ورزشکار")
            mf.txt_last_name.setText("پیش‌نویس")
            mf.closeEvent(QCloseEvent())
            mf_draft = DraftService.get_draft(mf._draft_binder.draft_id)
            self.assertIsNotNone(mf_draft)
            mf2 = MemberFormDialog(draft_data=mf_draft)
            self.assertEqual(mf2.txt_first_name.text(), "ورزشکار")
            mf2._on_explicit_cancel()
            self.assertIsNone(DraftService.get_draft(mf_draft["draft_id"]))
            mf.close(); mf2.close()

            # 6. ExerciseFormDialog
            ef = ExerciseFormDialog()
            ef.txt_name.setText("حرکت ناتمام")
            ef.closeEvent(QCloseEvent())
            ef_draft = DraftService.get_draft(ef._draft_binder.draft_id)
            self.assertIsNotNone(ef_draft)
            ef2 = ExerciseFormDialog(draft_data=ef_draft)
            self.assertEqual(ef2.txt_name.text(), "حرکت ناتمام")
            ef2._draft_binder.clear_draft(rotate_id=False)
            ef.close(); ef2.close()

            # 7. FoodFormDialog
            ff = FoodFormDialog()
            ff.txt_name.setText("غذا ناتمام")
            ff.closeEvent(QCloseEvent())
            ff_draft = DraftService.get_draft(ff._draft_binder.draft_id)
            self.assertIsNotNone(ff_draft)
            ff2 = FoodFormDialog(draft_data=ff_draft)
            self.assertEqual(ff2.txt_name.text(), "غذا ناتمام")
            ff2._draft_binder.clear_draft(rotate_id=False)
            ff.close(); ff2.close()

    def test_same_section_conflict_prompt_finish_current_vs_open_past(self):
        from nemov.views.main_window import MainWindow
        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            past_draft = DraftService.save_draft(
                draft_id="workout_past_sara",
                section="workout_editor",
                section_title="برنامه‌ریزی تمرینی",
                title="برنامه تمرینی «کات سارا»",
                summary="۴ حرکت",
                payload={"title": "کات سارا", "goal": "fat_loss", "days_per_week": 3, "level": "beginner", "days": []},
            )
            mw = MainWindow()
            mw.show()
            mw.sidebar.navigate("workouts")
            # Simulate coach opening empty form and starting a NEW workout for another athlete
            mw.view_workouts.txt_title.setText("برنامه فعلی علی")
            mw.view_workouts._snapshot_change()
            current_draft_id = mw.view_workouts.get_active_draft_id()
            mw.view_workouts._draft_binder.flush_now()
            _APP.processEvents()

            # Choice 1: Keep current form ("ابتدا فرم جاری را تمام می‌کنم")
            class FakeKeepMsg:
                Icon = QMessageBox.Icon
                ButtonRole = QMessageBox.ButtonRole
                instances = []
                def __init__(self, *a, **kw):
                    self.btns = []
                    FakeKeepMsg.instances.append(self)
                def setWindowTitle(self, *a): pass
                def setIcon(self, *a): pass
                def setLayoutDirection(self, *a): pass
                def setText(self, *a): pass
                def addButton(self, text, role):
                    b = QPushButton(text)
                    self.btns.append((b, role))
                    return b
                def setDefaultButton(self, b): pass
                def exec(self):
                    self._clicked = self.btns[0][0]  # Keep current
                def clickedButton(self):
                    return self._clicked

            with patch("nemov.views.main_window.QMessageBox", FakeKeepMsg):
                mw.open_unfinished_draft(past_draft["draft_id"])
            self.assertEqual(mw.view_workouts.txt_title.text(), "برنامه فعلی علی")
            self.assertIsNotNone(DraftService.get_draft("workout_past_sara"))

            # Choice 2: Replace current form and open past draft ("باز کردن مورد ناتمام قبلی (حذف فرم جاری)")
            class FakeSwitchMsg(FakeKeepMsg):
                def exec(self):
                    self._clicked = self.btns[1][0]  # Open past, discard current

            with patch("nemov.views.main_window.QMessageBox", FakeSwitchMsg):
                mw.open_unfinished_draft(past_draft["draft_id"])

            self.assertEqual(mw.view_workouts.txt_title.text(), "کات سارا")
            self.assertIsNone(DraftService.get_draft(current_draft_id))
            mw.view_workouts.reset_to_new_plan()
            mw.close()

    def test_live_debounce_timer_and_revert_to_baseline_cleanup(self):
        from PyQt6.QtTest import QTest
        state = {"val": ""}
        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            binder = DebouncedDraftBinder(
                parent=_APP,
                section="workout_editor",
                section_title="تست زنده",
                get_payload_fn=lambda: {"val": state["val"]},
                is_dirty_fn=lambda: bool(state["val"]),
                get_meta_fn=lambda: {"title": f"برنامه «{state['val']}»", "summary": "تایمر ۳ ثانیه"},
                draft_id="live_debounce_test",
                debounce_ms=120,
            )
            state["val"] = "حرکت نیم‌فاصله ۱۴۰۵"
            binder.schedule()
            self.assertTrue(binder.timer.isActive())
            QTest.qWait(220)
            saved = DraftService.get_draft("live_debounce_test")
            self.assertIsNotNone(saved)
            self.assertEqual(saved["payload"]["val"], "حرکت نیم‌فاصله ۱۴۰۵")

            # Reverting back to clean baseline deletes persisted draft cleanly
            state["val"] = ""
            binder.schedule()
            QTest.qWait(220)
            self.assertIsNone(DraftService.get_draft("live_debounce_test"))

    def test_empty_tab_switch_not_dirty_and_corrupt_json_safe(self):
        from nemov.views.workout_editor_view import WorkoutEditorView
        from nemov.views.nutrition_editor_view import NutritionEditorView
        with patch.object(CurrentUser, "get", return_value=self.trainer_a):
            we = WorkoutEditorView()
            we.tabs.setCurrentIndex(1)
            we._snapshot_change()
            self.assertFalse(we.has_unfinished_work())
            we.close()

            ne = NutritionEditorView()
            ne.tabs.setCurrentIndex(1)
            ne._snapshot_change()
            self.assertFalse(ne.has_unfinished_work())
            ne.close()

            # Write corrupt & non-dict JSON files into drafts directory
            d_dir = config.DATA_DIR / "drafts"
            d_dir.mkdir(parents=True, exist_ok=True)
            (d_dir / "corrupt_1.json").write_text("{bad json", encoding="utf-8")
            (d_dir / "bad_shape.json").write_text("[1, 2, 3]", encoding="utf-8")
            self.assertIsNone(DraftService.get_draft("corrupt_1"))
            self.assertEqual(DraftService.list_drafts(), [])

    def test_open_unfinished_draft_all_sections_and_member_detail_conflict(self):
        from nemov.views.main_window import MainWindow
        members = MemberService.get_all_members()
        if not members:
            m = MemberService.create_member({
                "first_name": "سهراب", "last_name": "نیکو", "phone": "09128887766",
                "gender": "male", "status": "active",
            })
            member_id = m.id
        else:
            member_id = members[0].id

        m_second = MemberService.create_member({
            "first_name": "بهرام", "last_name": "تستدوم", "phone": "09127776655",
            "gender": "male", "status": "active",
        })

        try:
            with patch.object(CurrentUser, "get", return_value=self.trainer_a):
                mw = MainWindow()
                mw.show()

                # 1) Sidebar hides active workout draft while on workouts, reveals when switching to dashboard
                mw.sidebar.navigate("workouts")
                mw.view_workouts.txt_title.setText("برنامه فعال در پس‌زمینه")
                mw.view_workouts._snapshot_change()
                w_id = mw.view_workouts.get_active_draft_id()
                mw.view_workouts._draft_binder.flush_now()
                _APP.processEvents()
                self.assertIn(w_id, mw.sidebar._excluded_draft_ids)

                mw.sidebar.navigate("dashboard")
                _APP.processEvents()
                self.assertNotIn(w_id, mw.sidebar._excluded_draft_ids)

                # 2) Opening new workout for a member preserves the earlier draft instead of overwriting it!
                mw.open_new_workout_for_member(member_id)
                self.assertIsNotNone(DraftService.get_draft(w_id))
                self.assertNotEqual(mw.view_workouts.get_active_draft_id(), w_id)
                DraftService.delete_draft(w_id)
                mw.view_workouts.reset_to_new_plan()

                # 3) Nutrition conflict prompt test
                past_n = DraftService.save_draft(
                    draft_id="nut_past",
                    section="nutrition_editor",
                    section_title="برنامه‌ریزی تغذیه",
                    title="رژیم قبلی",
                    summary="۲ ماده",
                    payload={"title": "رژیم قبلی", "goal": "weight_loss", "days_pattern": "7_days", "meals": []},
                )
                mw.sidebar.navigate("nutrition")
                mw.view_nutrition.txt_title.setText("رژیم جاری")
                mw.view_nutrition._snapshot_change()
                cur_n_id = mw.view_nutrition.get_active_draft_id()
                mw.view_nutrition._draft_binder.flush_now()

                class FakeAcceptPastMsg:
                    Icon = QMessageBox.Icon
                    ButtonRole = QMessageBox.ButtonRole
                    def __init__(self, *a, **kw): self.btns = []
                    def setWindowTitle(self, *a): pass
                    def setIcon(self, *a): pass
                    def setLayoutDirection(self, *a): pass
                    def setText(self, *a): pass
                    def addButton(self, text, role):
                        b = QPushButton(text); self.btns.append(b); return b
                    def setDefaultButton(self, b): pass
                    def exec(self): self._clicked = self.btns[1]
                    def clickedButton(self): return self._clicked

                with patch("nemov.views.main_window.QMessageBox", FakeAcceptPastMsg):
                    mw.open_unfinished_draft(past_n["draft_id"])
                self.assertEqual(mw.view_nutrition.txt_title.text(), "رژیم قبلی")
                self.assertIsNone(DraftService.get_draft(cur_n_id))
                mw.view_nutrition.reset_form()

                # 4) HealthRecord & Assessment open + conflict resolution inside MemberDetailView
                DraftService.save_draft(
                    draft_id=f"health_record_m{m_second.id}",
                    section="health_record",
                    section_title="پرونده سلامت و پزشکی",
                    title="پرونده سلامت بهرام",
                    summary="",
                    payload={"exercise_limitations": "محدودیت ددلیفت", "has_hypertension": True},
                    member_id=m_second.id,
                    entity_id=m_second.id,
                )
                DraftService.save_draft(
                    draft_id=f"assessment_m{m_second.id}",
                    section="assessment",
                    section_title="ارزیابی فیزیکی و سایز",
                    title="ارزیابی فیزیکی بهرام",
                    summary="",
                    payload={"waist_circ": 79.0, "weight_kg": 72.5},
                    member_id=m_second.id,
                    entity_id=m_second.id,
                )

                # Open Member 1 with dirty HealthRecord, then click Member 2's HealthRecord draft -> conflict prompt fires!
                mw.open_member_detail(member_id)
                detail_w = mw.stack.currentWidget()
                detail_w.tabs.setCurrentIndex(0)
                detail_w.view_health.txt_limitations.setText("آسیب مچ موقت")
                with patch("nemov.views.main_window.QMessageBox", FakeAcceptPastMsg):
                    mw.open_unfinished_draft(f"health_record_m{m_second.id}")
                detail_w2 = mw.stack.currentWidget()
                self.assertEqual(detail_w2.member_id, m_second.id)
                self.assertEqual(detail_w2.tabs.currentIndex(), 0)
                self.assertEqual(detail_w2.view_health.txt_limitations.toPlainText(), "محدودیت ددلیفت")
                detail_w2.view_health.revert_changes()

                # Now click Member 2's Assessment draft directly (no dirty conflict)
                mw.open_unfinished_draft(f"assessment_m{m_second.id}")
                self.assertEqual(detail_w2.tabs.currentIndex(), 1)
                self.assertAlmostEqual(detail_w2.view_assessment.spin_waist.value(), 79.0)
                detail_w2.view_assessment.reset_form()

                # 5) Modal draft open hooks (member_form, exercise_form, food_form) via MainWindow
                for sec, did, dlg_cls in (
                    ("member_form", "mf_open_test", "nemov.views.main_window.MemberFormDialog"),
                    ("exercise_form", "ef_open_test", "nemov.views.workout_library_view.ExerciseFormDialog"),
                    ("food_form", "ff_open_test", "nemov.views.food_library_dialog.FoodFormDialog"),
                ):
                    DraftService.save_draft(
                        draft_id=did,
                        section=sec,
                        section_title=sec,
                        title=sec,
                        summary="",
                        payload={"first_name": "تست", "name_fa": "تست"},
                    )
                    with patch(dlg_cls) as mock_dlg:
                        mock_dlg.return_value.exec.return_value = 0
                        mw.open_unfinished_draft(did)
                        mock_dlg.assert_called_once()
                    DraftService.delete_draft(did)

                mw.close()
        finally:
            try:
                MemberService.delete_member(m_second.id)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
