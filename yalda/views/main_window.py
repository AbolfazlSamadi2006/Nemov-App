from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
import config
from yalda.views.components.sidebar import Sidebar
from yalda.views.dashboard_view import DashboardView
from yalda.views.member_detail_view import MemberDetailView
from yalda.views.member_form_dialog import MemberFormDialog
from yalda.views.components.exit_backup_dialog import ExitBackupDialog
from yalda.auth.authentication import CurrentUser

class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_TITLE} (نسخه {config.APP_VERSION})")

        # Explicitly set window icon to multi-resolution nemov.ico
        from yalda.utils.image_utils import get_app_icon, apply_windows_taskbar_icon
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        apply_windows_taskbar_icon(self)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            min_w = min(960, max(800, avail.width() - 40))
            min_h = min(560, max(480, avail.height() - 50))
            self.setMinimumSize(min_w, min_h)
            init_w = min(1280, max(min_w, avail.width() - 20))
            init_h = min(800, max(min_h, avail.height() - 40))
            self.resize(init_w, init_h)
        else:
            self.resize(1280, 800)
            self.setMinimumSize(960, 560)

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

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        from yalda.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self)

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
        self.sidebar.notifications_marked_read.connect(self._on_sidebar_notifications_marked_read)
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

    @property
    def view_members(self):
        if self._view_members is None:
            from yalda.views.member_list_view import MemberListView
            self._view_members = MemberListView()
            self._view_members.open_member_detail.connect(self.open_member_detail)
            self.stack.addWidget(self._view_members)
        return self._view_members

    @property
    def view_workouts(self):
        if self._view_workouts is None:
            from yalda.views.workout_editor_view import WorkoutEditorView
            self._view_workouts = WorkoutEditorView()
            self._view_workouts.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
            self._view_workouts.open_exercise_bank_requested.connect(lambda: self.sidebar.navigate("exercises"))
            self._view_workouts.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_workouts)
        return self._view_workouts

    @property
    def view_nutrition(self):
        if self._view_nutrition is None:
            from yalda.views.nutrition_editor_view import NutritionEditorView
            self._view_nutrition = NutritionEditorView()
            self._view_nutrition.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
            self._view_nutrition.open_food_bank_requested.connect(lambda: self.sidebar.navigate("foods"))
            self._view_nutrition.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_nutrition)
        return self._view_nutrition

    @property
    def view_templates(self):
        if self._view_templates is None:
            from yalda.views.templates_manager_view import TemplatesManagerView
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
            from yalda.views.workout_library_view import WorkoutLibraryView
            self._view_exercises = WorkoutLibraryView()
            self._view_exercises.back_requested.connect(self.go_back)
            self._view_exercises.cloud_sync_progress.connect(self.sidebar.show_cloud_sync_progress)
            self._view_exercises.cloud_sync_finished.connect(self.sidebar.finish_cloud_sync_progress)
            self.stack.addWidget(self._view_exercises)
        return self._view_exercises

    @property
    def view_foods(self):
        if self._view_foods is None:
            from yalda.views.food_library_view import FoodLibraryView
            self._view_foods = FoodLibraryView()
            self._view_foods.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_foods)
        return self._view_foods

    @property
    def view_developer(self):
        if self._view_developer is None:
            from yalda.views.developer_view import DeveloperView
            self._view_developer = DeveloperView()
            self._view_developer.back_requested.connect(self.go_back)
            self.stack.addWidget(self._view_developer)
        return self._view_developer

    @property
    def view_backup(self):
        if self._view_backup is None:
            from yalda.views.backup_view import BackupView
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
            from yalda.views.accounting_view import AccountingView
            self._view_accounting = AccountingView()
            self._view_accounting.member_clicked.connect(self.open_member_detail)
            self.stack.addWidget(self._view_accounting)
        return self._view_accounting

    @property
    def view_sms(self):
        if self._view_sms is None:
            from yalda.views.sms_view import SmsView
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

    def open_workout_editor_with_plan(self, plan_id: int, member_id: int = None):
        self.sidebar.navigate("workouts")
        self.view_workouts.load_plan_for_edit(plan_id)
        if member_id:
            self.view_workouts.set_selected_member(member_id)

    def open_nutrition_editor_with_plan(self, plan_id: int, member_id: int = None):
        self.sidebar.navigate("nutrition")
        self.view_nutrition.load_plan_for_edit(plan_id)
        if member_id:
            self.view_nutrition.set_selected_member(member_id)

    def open_new_workout_editor(self):
        self.sidebar.navigate("workouts")
        self.view_workouts.reset_to_new_plan()

    def open_new_workout_for_member(self, member_id: int):
        self.sidebar.navigate("workouts")
        self.view_workouts.reset_to_new_plan()
        self.view_workouts.set_selected_member(member_id)

    def open_new_nutrition_editor(self):
        self.sidebar.navigate("nutrition")
        self.view_nutrition.reset_form()

    def open_new_nutrition_for_member(self, member_id: int):
        self.sidebar.navigate("nutrition")
        self.view_nutrition.reset_form()
        self.view_nutrition.set_selected_member(member_id)

    def refresh_on_login(self):
        """Refreshes sidebar, resets active index to Dashboard, and loads dashboard data instantly."""
        from yalda.database.connection import reset_data_changed
        reset_data_changed()
        self._nav_history = []
        self._current_page_state = ("page", "dashboard")

        if hasattr(self, 'sidebar'):
            self.sidebar.navigate("dashboard")

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
                from yalda.views.components.tuition_payment_dialog import TuitionPaymentDialog
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
        idx = self.stack.addWidget(detail_view)
        self.stack.setCurrentIndex(idx)

    def logout(self):
        from yalda.database.connection import has_data_changed, reset_data_changed
        if has_data_changed():
            dialog = ExitBackupDialog(self, is_logout=True)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                reset_data_changed()
                CurrentUser.logout()
                self.logout_signal.emit()
                self.hide()
        else:
            CurrentUser.logout()
            self.logout_signal.emit()
            self.hide()

    def on_account_deleted(self):
        from yalda.database.connection import reset_data_changed
        reset_data_changed()
        CurrentUser.logout()
        self.logout_signal.emit()
        self.hide()

    def closeEvent(self, event):
        # If window is hidden or user already logged out, accept immediately
        if not self.isVisible() or CurrentUser.get() is None:
            event.accept()
            return

        from yalda.database.connection import has_data_changed, reset_data_changed
        if has_data_changed():
            dialog = ExitBackupDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                reset_data_changed()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
