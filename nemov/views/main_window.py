from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
import config
from nemov.views.components.sidebar import Sidebar
from nemov.views.dashboard_view import DashboardView
from nemov.views.member_detail_view import MemberDetailView
from nemov.views.member_form_dialog import MemberFormDialog
from nemov.views.components.exit_backup_dialog import ExitBackupDialog
from nemov.auth.authentication import CurrentUser

class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()
    SIDEBAR_COLLAPSE_THRESHOLD = 1050
    SIDEBAR_EXPAND_THRESHOLD = 1100

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_TITLE} (نسخه {config.APP_VERSION})")

        # Explicitly set window icon to multi-resolution nemov.ico
        from nemov.utils.image_utils import get_app_icon, apply_windows_taskbar_icon
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        apply_windows_taskbar_icon(self)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        from nemov.utils.ui_scaling import get_available_screen_size, clamp_minimum_size
        avail_w, avail_h = get_available_screen_size(self)
        min_w, min_h = clamp_minimum_size(960, 560, widget=self, floor_w=640, floor_h=380, margin_w=24, margin_h=36)
        self.setMinimumSize(min_w, min_h)
        init_w = min(max(1280, avail_w if avail_w <= 1280 else 1280), max(min_w, avail_w - 20))
        init_h = min(max(800, avail_h if avail_h <= 800 else 800), max(min_h, avail_h - 40))
        self.resize(init_w, init_h)

        self._view_members = None
        self._view_workouts = None
        self._view_nutrition = None
        self._view_templates = None
        self._view_exercises = None
        self._view_foods = None
        self._view_developer = None
        self._view_backup = None
        self._view_accounting = None
        self._view_sms = None
        self._user_sidebar_override = None
        self._auto_collapsed_by_resize = False

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        from nemov.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self)
        self._sync_sidebar_to_window_width(animate=False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_sidebar_to_window_width(animate=True)

    def _on_sidebar_user_toggled(self, collapsed: bool):
        self._user_sidebar_override = bool(collapsed)
        self._auto_collapsed_by_resize = False

    def _sync_sidebar_to_window_width(self, animate: bool = True):
        if not hasattr(self, "sidebar") or not self.sidebar:
            return
        w = self.width()
        if w <= 0:
            return
        if w < self.SIDEBAR_COLLAPSE_THRESHOLD:
            if not self.sidebar.is_collapsed() and self._user_sidebar_override is not False:
                self._auto_collapsed_by_resize = True
                self.sidebar.set_collapsed(True, animate=animate, user_initiated=False)
        elif w >= self.SIDEBAR_EXPAND_THRESHOLD:
            if self._auto_collapsed_by_resize and self._user_sidebar_override is None and self.sidebar.is_collapsed():
                self._auto_collapsed_by_resize = False
                self.sidebar.set_collapsed(False, animate=animate, user_initiated=False)
            elif not self.sidebar.is_collapsed() and self._user_sidebar_override is False:
                self._user_sidebar_override = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        self.sidebar.logout_requested.connect(self.logout)
        self.sidebar.member_birthday_clicked.connect(self.open_member_detail)
        self.sidebar.member_expiration_clicked.connect(self.open_member_detail)
        self.sidebar.draft_clicked.connect(self.open_unfinished_draft)
        self.sidebar.notifications_marked_read.connect(self._on_sidebar_notifications_marked_read)
        self.sidebar.collapse_toggled.connect(self._on_sidebar_user_toggled)
        main_layout.addWidget(self.sidebar)

        # Stacked Container for Views
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Dashboard View (Index 0) loaded immediately
        self.view_dashboard = DashboardView()
        self.view_dashboard.navigate_to.connect(self.handle_dashboard_navigation)
        self.stack.addWidget(self.view_dashboard)  # Index 0

        self._nav_history = []
        self._is_navigating_back = False
        self._current_page_state = ("page", "dashboard")

        # Initialize AutoSave engine
        try:
            from nemov.services.autosave_service import AutoSaveManager
            AutoSaveManager.get_instance().start()
        except Exception as e:
            print(f"Error starting AutoSaveManager: {e}")

        # Start non-blocking background update check
        QTimer.singleShot(3500, self._start_background_update_check)
        self._bg_update_timer = QTimer(self)
        self._bg_update_timer.setInterval(15 * 60 * 1000)  # 15 minutes
        self._bg_update_timer.timeout.connect(self._on_periodic_update_check)
        self._bg_update_timer.start()

    @property
    def view_members(self):
        if self._view_members is None:
            from nemov.views.member_list_view import MemberListView
            self._view_members = MemberListView()
            self._view_members.open_member_detail.connect(self.open_member_detail)
            self.stack.addWidget(self._view_members)
        return self._view_members

    @property
    def view_workouts(self):
        if self._view_workouts is None:
            from nemov.views.workout_editor_view import WorkoutEditorView
            self._view_workouts = WorkoutEditorView()
            self._view_workouts.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
            self._view_workouts.open_exercise_bank_requested.connect(lambda: self.sidebar.navigate("exercises"))
            self._view_workouts.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_workouts)
        return self._view_workouts

    @property
    def view_nutrition(self):
        if self._view_nutrition is None:
            from nemov.views.nutrition_editor_view import NutritionEditorView
            self._view_nutrition = NutritionEditorView()
            self._view_nutrition.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
            self._view_nutrition.open_food_bank_requested.connect(lambda: self.sidebar.navigate("foods"))
            self._view_nutrition.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_nutrition)
        return self._view_nutrition

    @property
    def view_templates(self):
        if self._view_templates is None:
            from nemov.views.templates_manager_view import TemplatesManagerView
            self._view_templates = TemplatesManagerView()
            self._view_templates.edit_workout_requested.connect(self.open_workout_editor_with_plan)
            self._view_templates.edit_nutrition_requested.connect(self.open_nutrition_editor_with_plan)
            self._view_templates.new_workout_requested.connect(self.open_new_workout_editor)
            self._view_templates.new_nutrition_requested.connect(self.open_new_nutrition_editor)
            self._view_templates.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_templates)
        return self._view_templates

    @property
    def view_exercises(self):
        if self._view_exercises is None:
            from nemov.views.workout_library_view import WorkoutLibraryView
            self._view_exercises = WorkoutLibraryView()
            self._view_exercises.back_requested.connect(self.go_back)
            self._view_exercises.cloud_sync_progress.connect(self.sidebar.show_cloud_sync_progress)
            self._view_exercises.cloud_sync_finished.connect(self.sidebar.finish_cloud_sync_progress)
            self.stack.addWidget(self._view_exercises)
        return self._view_exercises

    @property
    def view_foods(self):
        if self._view_foods is None:
            from nemov.views.food_library_view import FoodLibraryView
            self._view_foods = FoodLibraryView()
            self._view_foods.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_foods)
        return self._view_foods

    @property
    def view_developer(self):
        if self._view_developer is None:
            from nemov.views.developer_view import DeveloperView
            self._view_developer = DeveloperView()
            self._view_developer.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_developer)
        return self._view_developer

    @property
    def view_backup(self):
        if self._view_backup is None:
            from nemov.views.backup_view import BackupView
            self._view_backup = BackupView()
            self._view_backup.account_deleted_signal.connect(self.on_account_deleted)
            self._view_backup.back_requested.connect(self.go_back)
            self._view_backup.notifications_changed_signal.connect(self.sidebar.refresh_notifications)
            self._view_backup.branding_changed_signal.connect(self.sidebar.refresh_branding)
            self.stack.addWidget(self._view_backup)
        return self._view_backup

    def _on_sidebar_notifications_marked_read(self):
        if self._view_backup is not None:
            try:
                self._view_backup.load_notification_history()
            except Exception:
                pass

    @property
    def view_accounting(self):
        if self._view_accounting is None:
            from nemov.views.accounting_view import AccountingView
            self._view_accounting = AccountingView()
            self._view_accounting.member_clicked.connect(self.open_member_detail)
            self.stack.addWidget(self._view_accounting)
        return self._view_accounting

    @property
    def view_sms(self):
        if self._view_sms is None:
            from nemov.views.sms_view import SmsView
            self._view_sms = SmsView()
            self.stack.addWidget(self._view_sms)
        return self._view_sms

    def go_back(self):
        if self._nav_history:
            prev_state = self._nav_history.pop()
            self._is_navigating_back = True
            try:
                kind = prev_state[0]
                if kind == "page":
                    self.sidebar.navigate(prev_state[1])
                elif kind == "member_detail":
                    self.open_member_detail(prev_state[1])
                self._current_page_state = prev_state
            finally:
                self._is_navigating_back = False
        else:
            self.sidebar.navigate("dashboard")

    def switch_page(self, page_id: str):
        self.sidebar.refresh_notifications()
        page_dict = {
            "dashboard": lambda: self.view_dashboard,
            "members": lambda: self.view_members,
            "workouts": lambda: self.view_workouts,
            "nutrition": lambda: self.view_nutrition,
            "templates": lambda: self.view_templates,
            "exercises": lambda: self.view_exercises,
            "foods": lambda: self.view_foods,
            "developer": lambda: self.view_developer,
            "backup": lambda: self.view_backup,
            "accounting": lambda: self.view_accounting,
            "sms": lambda: self.view_sms,
        }
        if page_id in page_dict:
            if not self._is_navigating_back and hasattr(self, '_current_page_state'):
                if self._current_page_state != ("page", page_id):
                    self._nav_history.append(self._current_page_state)
            self._current_page_state = ("page", page_id)

            target_widget = page_dict[page_id]()

            if page_id == "dashboard":
                target_widget.refresh_dashboard()
            elif page_id == "members":
                target_widget.load_members()
            elif page_id == "workouts":
                target_widget.refresh_editor()
            elif page_id == "nutrition":
                target_widget.refresh_editor()
            elif page_id == "templates":
                target_widget.load_all_templates()
            elif page_id == "exercises":
                target_widget.load_exercises()
            elif page_id == "foods":
                target_widget.load_foods()
            elif page_id == "developer":
                target_widget.load_data()
            elif page_id == "backup":
                target_widget.load_backups()
            elif page_id == "accounting":
                target_widget.load_data()
            elif page_id == "sms":
                target_widget.refresh_balance()
                target_widget.load_members()

            self.stack.setCurrentWidget(target_widget)
            self._sync_excluded_draft_ids()

    def _sync_excluded_draft_ids(self):
        if not hasattr(self, "sidebar") or not self.sidebar:
            return
        excluded = set()
        try:
            curr = self.stack.currentWidget()
            if curr is not None:
                if curr is self._view_workouts and hasattr(curr, "get_active_draft_id"):
                    did = curr.get_active_draft_id()
                    if did:
                        excluded.add(did)
                elif curr is self._view_nutrition and hasattr(curr, "get_active_draft_id"):
                    did = curr.get_active_draft_id()
                    if did:
                        excluded.add(did)
                elif isinstance(curr, MemberDetailView) and hasattr(curr, "tabs"):
                    tab_idx = curr.tabs.currentIndex()
                    if tab_idx == 0 and hasattr(curr, "view_health"):
                        excluded.add(curr.view_health.get_active_draft_id())
                    elif tab_idx == 1 and hasattr(curr, "view_assessment"):
                        excluded.add(curr.view_assessment.get_active_draft_id())
            self.sidebar.set_excluded_draft_ids(excluded)
        except Exception:
            pass

    def _get_active_unfinished_widget(self, section: str):
        if section == "workout_editor" and self._view_workouts is not None:
            if self._view_workouts.has_unfinished_work():
                return self._view_workouts, "workouts"
        elif section == "nutrition_editor" and self._view_nutrition is not None:
            if self._view_nutrition.has_unfinished_work():
                return self._view_nutrition, "nutrition"
        elif section in ("health_record", "assessment"):
            curr = self.stack.currentWidget()
            if isinstance(curr, MemberDetailView):
                w = curr.view_health if section == "health_record" else curr.view_assessment
                if hasattr(w, "has_unfinished_work") and w.has_unfinished_work():
                    return w, "member_detail"
        return None, None

    def _confirm_replace_active_unfinished(self, section: str, target_draft: dict) -> bool:
        """
        If an unfinished draft/form is already open in the exact same section (different from target_draft),
        asks whether the coach wants to finish the current form first or discard it and resume the older one.
        """
        active_widget, _ctx = self._get_active_unfinished_widget(section)
        if active_widget is None:
            return True
        if active_widget.get_active_draft_id() == target_draft.get("draft_id"):
            return True

        sec_title = target_draft.get("section_title") or "این بخش"
        cur_desc = active_widget.get_unfinished_summary() if hasattr(active_widget, "get_unfinished_summary") else "فرم جاری"
        target_desc = target_draft.get("title") or sec_title

        msg = QMessageBox(self)
        msg.setWindowTitle("⚠️ فرم ناتمام دیگری در همین بخش باز است")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        msg.setText(
            f"در بخش «{sec_title}» هم‌اکنون یک فرم ناتمام دیگر ({cur_desc}) باز است.\n\n"
            f"مورد ناتمام انتخاب‌شده: {target_desc}\n\n"
            "آیا مایلید ابتدا همین فرم بازشده فعلی را تکمیل کنید یا از فرم جاری صرف‌نظر کرده و مورد ناتمام قبلی باز شود؟"
        )
        btn_keep_current = msg.addButton("↩️ ابتدا فرم جاری را تمام می‌کنم", QMessageBox.ButtonRole.RejectRole)
        btn_open_past = msg.addButton("📂 باز کردن مورد ناتمام قبلی (حذف فرم جاری)", QMessageBox.ButtonRole.AcceptRole)
        msg.setDefaultButton(btn_keep_current)
        msg.exec()

        if msg.clickedButton() == btn_open_past:
            binder = getattr(active_widget, "_draft_binder", None)
            if hasattr(active_widget, "reset_to_new_plan"):
                active_widget.reset_to_new_plan(clear_draft=True)
            elif hasattr(active_widget, "reset_form"):
                active_widget.reset_form(clear_draft=True)
            elif hasattr(active_widget, "revert_changes"):
                active_widget.revert_changes()
            elif binder:
                binder.clear_draft(rotate_id=True)
            return True
        return False

    def open_unfinished_draft(self, draft_id: str):
        from nemov.services.draft_service import DraftService
        draft = DraftService.get_draft(draft_id)
        if not draft:
            self.sidebar.refresh_notifications()
            return

        section = draft.get("section")
        if not self._confirm_replace_active_unfinished(section, draft):
            # Focus active section if user chose to finish the currently open form first
            if section == "workout_editor":
                self.sidebar.navigate("workouts")
            elif section == "nutrition_editor":
                self.sidebar.navigate("nutrition")
            self._sync_excluded_draft_ids()
            return

        entity_id = draft.get("entity_id")
        member_id = draft.get("member_id")

        if section == "workout_editor":
            self.sidebar.navigate("workouts")
            self.view_workouts.restore_draft(draft)
            self._sync_excluded_draft_ids()
        elif section == "nutrition_editor":
            self.sidebar.navigate("nutrition")
            self.view_nutrition.restore_draft(draft)
            self._sync_excluded_draft_ids()
        elif section in ("health_record", "assessment") and member_id:
            curr = self.stack.currentWidget()
            if not (isinstance(curr, MemberDetailView) and curr.member_id == member_id):
                self.open_member_detail(member_id)
                curr = self.stack.currentWidget()
            if isinstance(curr, MemberDetailView):
                if section == "health_record":
                    curr.tabs.setCurrentIndex(0)
                    curr.view_health.restore_draft(draft)
                else:
                    curr.tabs.setCurrentIndex(1)
                    curr.view_assessment.restore_draft(draft)
                self._sync_excluded_draft_ids()
        elif section == "member_form":
            from nemov.services.member_service import MemberService
            member_obj = MemberService.get_member_by_id(entity_id) if entity_id else None
            dlg = MemberFormDialog(self, member_data=member_obj, draft_data=draft)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.view_dashboard.refresh_dashboard()
                if self._view_members is not None:
                    self._view_members.load_members()
                curr = self.stack.currentWidget()
                if isinstance(curr, MemberDetailView) and member_obj and curr.member_id == member_obj.id:
                    curr.load_member_info()
            self.sidebar.refresh_notifications()
        elif section == "exercise_form":
            from nemov.services.workout_service import WorkoutService
            from nemov.views.workout_library_view import ExerciseFormDialog
            ex_obj = None
            if entity_id:
                ex_obj = next((e for e in WorkoutService.get_all_exercises(include_unlisted=True) if e.id == entity_id), None)
            dlg = ExerciseFormDialog(self, exercise_data=ex_obj, draft_data=draft)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                if ex_obj:
                    WorkoutService.update_exercise(ex_obj.id, data)
                    QMessageBox.information(self, "موفقیت", "حرکت ورزشی با موفقیت ویرایش شد.")
                else:
                    WorkoutService.create_exercise(data)
                    QMessageBox.information(self, "موفقیت", "حرکت جدید به بانک افزوده شد.")
                if self._view_exercises is not None:
                    self._view_exercises.reload_exercises()
            self.sidebar.refresh_notifications()
        elif section == "food_form":
            from nemov.services.nutrition_service import NutritionService
            from nemov.views.food_library_dialog import FoodFormDialog
            food_obj = None
            if entity_id:
                food_obj = next((f for f in NutritionService.get_all_foods(include_unlisted=True) if f.id == entity_id), None)
            dlg = FoodFormDialog(self, food_data=food_obj, draft_data=draft)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                if food_obj:
                    NutritionService.update_food(food_obj.id, data)
                    QMessageBox.information(self, "موفقیت", "ماده غذایی با موفقیت ویرایش شد.")
                else:
                    NutritionService.create_food(data)
                    QMessageBox.information(self, "موفقیت", "ماده غذایی جدید با موفقیت اضافه شد.")
                if self._view_foods is not None:
                    self._view_foods.load_foods()
            self.sidebar.refresh_notifications()

    def open_workout_editor_with_plan(self, plan_id: int, member_id: int = None):
        if self._view_workouts is not None and self._view_workouts.has_unfinished_work():
            self._view_workouts._draft_binder.flush_now()
        self.sidebar.navigate("workouts")
        self.view_workouts.load_plan_for_edit(plan_id)
        if member_id:
            self.view_workouts.set_selected_member(member_id)
        self._sync_excluded_draft_ids()

    def open_nutrition_editor_with_plan(self, plan_id: int, member_id: int = None):
        if self._view_nutrition is not None and self._view_nutrition.has_unfinished_work():
            self._view_nutrition._draft_binder.flush_now()
        self.sidebar.navigate("nutrition")
        self.view_nutrition.load_plan_for_edit(plan_id)
        if member_id:
            self.view_nutrition.set_selected_member(member_id)
        self._sync_excluded_draft_ids()

    def open_new_workout_editor(self):
        preserve = self._view_workouts is not None and self._view_workouts.has_unfinished_work()
        if preserve:
            self._view_workouts._draft_binder.flush_now()
            self._view_workouts.reset_to_new_plan(clear_draft=False)
            self._view_workouts._draft_binder.new_draft_id()
        else:
            self.view_workouts.reset_to_new_plan()
        self.sidebar.navigate("workouts")
        self._sync_excluded_draft_ids()

    def open_new_workout_for_member(self, member_id: int):
        preserve = self._view_workouts is not None and self._view_workouts.has_unfinished_work()
        if preserve:
            self._view_workouts._draft_binder.flush_now()
            self._view_workouts.reset_to_new_plan(clear_draft=False)
            self._view_workouts._draft_binder.new_draft_id()
        else:
            self.view_workouts.reset_to_new_plan()
        self.sidebar.navigate("workouts")
        self.view_workouts.set_selected_member(member_id)
        self._sync_excluded_draft_ids()

    def open_new_nutrition_editor(self):
        preserve = self._view_nutrition is not None and self._view_nutrition.has_unfinished_work()
        if preserve:
            self._view_nutrition._draft_binder.flush_now()
            self._view_nutrition.reset_form(clear_draft=False)
            self._view_nutrition._draft_binder.new_draft_id()
        else:
            self.view_nutrition.reset_form()
        self.sidebar.navigate("nutrition")
        self._sync_excluded_draft_ids()

    def open_new_nutrition_for_member(self, member_id: int):
        preserve = self._view_nutrition is not None and self._view_nutrition.has_unfinished_work()
        if preserve:
            self._view_nutrition._draft_binder.flush_now()
            self._view_nutrition.reset_form(clear_draft=False)
            self._view_nutrition._draft_binder.new_draft_id()
        else:
            self.view_nutrition.reset_form()
        self.sidebar.navigate("nutrition")
        self.view_nutrition.set_selected_member(member_id)
        self._sync_excluded_draft_ids()

    def refresh_on_login(self):
        """Refreshes sidebar, resets active index to Dashboard, and loads dashboard data instantly."""
        from nemov.database.connection import reset_data_changed
        reset_data_changed()
        self._nav_history = []
        self._current_page_state = ("page", "dashboard")

        if hasattr(self, 'sidebar'):
            self.sidebar.refresh_branding()
            self.sidebar._apply_theme_style()
            self.sidebar.navigate("dashboard")
            self.sidebar.refresh_notifications()
            self._sync_excluded_draft_ids()

        try:
            self.view_dashboard.refresh_dashboard()
        except Exception:
            pass

        self.stack.setCurrentIndex(0)

    def handle_dashboard_navigation(self, target: str):
        if target == "add_member":
            try:
                dialog = MemberFormDialog(self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.view_dashboard.refresh_dashboard()
                    self.view_members.load_members()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطایی رخ داد: {str(e)}")
        elif target == "pay_tuition":
            try:
                from nemov.views.components.tuition_payment_dialog import TuitionPaymentDialog
                dialog = TuitionPaymentDialog(self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.view_dashboard.refresh_dashboard()
                    if hasattr(self, 'view_members') and self.view_members:
                        self.view_members.load_members()
                    if hasattr(self, 'view_accounting') and self.view_accounting:
                        self.view_accounting.load_data()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در باز کردن پنجره ثبت شهریه: {str(e)}")
        elif target == "new_workout":
            self.sidebar.navigate("workouts")
        elif target == "new_nutrition":
            self.sidebar.navigate("nutrition")

    def open_member_detail(self, member_id: int):
        if not self._is_navigating_back and hasattr(self, '_current_page_state'):
            if self._current_page_state != ("member_detail", member_id):
                self._nav_history.append(self._current_page_state)
        self._current_page_state = ("member_detail", member_id)

        detail_view = MemberDetailView(member_id)
        detail_view.back_requested.connect(self.go_back)
        detail_view.edit_workout_requested.connect(self.open_workout_editor_with_plan)
        detail_view.edit_nutrition_requested.connect(self.open_nutrition_editor_with_plan)
        detail_view.create_workout_requested.connect(self.open_new_workout_for_member)
        detail_view.create_nutrition_requested.connect(self.open_new_nutrition_for_member)
        detail_view.tabs.currentChanged.connect(lambda _idx: self._sync_excluded_draft_ids())
        idx = self.stack.addWidget(detail_view)
        self.stack.setCurrentIndex(idx)
        self._sync_excluded_draft_ids()

    def _persist_active_theme_locally(self):
        """Silently persists the active theme locally on exit/logout without triggering ExitBackupDialog."""
        try:
            from nemov.utils.theme_manager import ThemeManager
            from nemov.services.branding_service import BrandingService
            current_theme = ThemeManager.get_current_theme_key()
            if current_theme:
                BrandingService.save_selected_theme_id(current_theme)
        except Exception:
            pass

    def _flush_all_local_state_silently(self):
        """Flushes active theme, pending form drafts, SQLite WAL, and local/AppData atomic backup silently."""
        self._persist_active_theme_locally()
        try:
            from nemov.services.draft_service import DraftService
            DraftService.flush_all_binders()
        except Exception:
            pass
        try:
            from nemov.services.autosave_service import AutoSaveManager
            AutoSaveManager.get_instance().flush_local_sync()
        except Exception:
            pass

    def logout(self):
        self._flush_all_local_state_silently()
        try:
            from nemov.services.autosave_service import AutoSaveManager, is_autosave_enabled
            if is_autosave_enabled():
                AutoSaveManager.get_instance().trigger_autosave_if_eligible()
        except Exception:
            pass
        # Clear in-memory cached forms after flushing drafts so another trainer login starts clean
        if self._view_workouts is not None:
            self._view_workouts.reset_to_new_plan(clear_draft=False)
            self._view_workouts._draft_binder.new_draft_id()
        if self._view_nutrition is not None:
            self._view_nutrition.reset_form(clear_draft=False)
            self._view_nutrition._draft_binder.new_draft_id()
        CurrentUser.logout()
        self.logout_signal.emit()
        self.hide()

    def on_account_deleted(self):
        from nemov.database.connection import reset_data_changed
        reset_data_changed()
        CurrentUser.logout()
        self.logout_signal.emit()
        self.hide()

    def closeEvent(self, event):
        self._flush_all_local_state_silently()
        # If window is hidden or user already logged out, accept immediately
        if not self.isVisible() or CurrentUser.get() is None:
            event.accept()
            return

        from nemov.database.connection import reset_data_changed
        reset_data_changed()
        event.accept()

    def _start_background_update_check(self):
        try:
            from nemov.services.update_service import UpdateCheckWorker
            self._bg_update_worker = UpdateCheckWorker()
            self._bg_update_worker.finished_signal.connect(self._on_bg_update_check_finished)
            self._bg_update_worker.start()
        except Exception:
            pass

    def _on_bg_update_check_finished(self, has_update: bool, info: dict, error_msg: str):
        if not error_msg:
            try:
                from nemov.services.update_service import UpdateService
                UpdateService.set_check_result(has_update, info)
                if has_update and hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.refresh_notifications()
            except Exception:
                pass

    def _on_periodic_update_check(self):
        try:
            from nemov.services.update_service import UpdateService
            # If an update is already detected and known, skip checking to save network requests
            if UpdateService.has_update_available():
                return
            self._start_background_update_check()
        except Exception:
            pass
