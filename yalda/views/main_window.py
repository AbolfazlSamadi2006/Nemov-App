from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
import config
from yalda.views.components.sidebar import Sidebar
from yalda.views.dashboard_view import DashboardView
from yalda.views.member_list_view import MemberListView
from yalda.views.member_detail_view import MemberDetailView
from yalda.views.member_form_dialog import MemberFormDialog
from yalda.views.workout_editor_view import WorkoutEditorView
from yalda.views.nutrition_editor_view import NutritionEditorView
from yalda.views.templates_manager_view import TemplatesManagerView
from yalda.views.workout_library_view import WorkoutLibraryView
from yalda.views.food_library_view import FoodLibraryView
from yalda.views.backup_view import BackupView
from yalda.views.accounting_view import AccountingView
from yalda.views.developer_view import DeveloperView
from yalda.views.components.exit_backup_dialog import ExitBackupDialog
from yalda.auth.authentication import CurrentUser

class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} - نرم‌افزار مدیریت باشگاه بدنسازی (نسخه {config.APP_VERSION})")

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

        self.init_ui()

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
        main_layout.addWidget(self.sidebar)

        # Stacked Container for Views
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Instantiate Views
        self.view_dashboard = DashboardView()
        self.view_dashboard.navigate_to.connect(self.handle_dashboard_navigation)

        self.view_members = MemberListView()
        self.view_members.open_member_detail.connect(self.open_member_detail)

        self.view_workouts = WorkoutEditorView()
        self.view_workouts.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
        self.view_workouts.open_exercise_bank_requested.connect(lambda: self.sidebar.navigate("exercises"))
        self.view_workouts.back_requested.connect(self.go_back)

        self.view_nutrition = NutritionEditorView()
        self.view_nutrition.manage_templates_requested.connect(lambda: self.sidebar.navigate("templates"))
        self.view_nutrition.open_food_bank_requested.connect(lambda: self.sidebar.navigate("foods"))
        self.view_nutrition.back_requested.connect(self.go_back)

        self.view_templates = TemplatesManagerView()
        self.view_templates.edit_workout_requested.connect(self.open_workout_editor_with_plan)
        self.view_templates.edit_nutrition_requested.connect(self.open_nutrition_editor_with_plan)
        self.view_templates.new_workout_requested.connect(self.open_new_workout_editor)
        self.view_templates.new_nutrition_requested.connect(self.open_new_nutrition_editor)
        self.view_templates.back_requested.connect(self.go_back)

        self.view_exercises = WorkoutLibraryView()
        self.view_exercises.back_requested.connect(self.go_back)
        self.view_exercises.cloud_sync_progress.connect(self.sidebar.show_cloud_sync_progress)
        self.view_exercises.cloud_sync_finished.connect(self.sidebar.finish_cloud_sync_progress)

        self.view_foods = FoodLibraryView()
        self.view_foods.back_requested.connect(self.go_back)

        self.view_developer = DeveloperView()
        self.view_developer.back_requested.connect(self.go_back)

        self.view_backup = BackupView()
        self.view_backup.account_deleted_signal.connect(self.on_account_deleted)
        self.view_backup.back_requested.connect(self.go_back)
        self.view_backup.notifications_changed_signal.connect(self.sidebar.refresh_notifications)
        self.sidebar.notifications_marked_read.connect(self.view_backup.load_notification_history)

        self.view_accounting = AccountingView()
        self.view_accounting.member_clicked.connect(self.open_member_detail)

        self._nav_history = []
        self._is_navigating_back = False
        self._current_page_state = ("page", "dashboard")

        self.stack.addWidget(self.view_dashboard)  # Index 0
        self.stack.addWidget(self.view_members)    # Index 1
        self.stack.addWidget(self.view_workouts)   # Index 2
        self.stack.addWidget(self.view_nutrition)  # Index 3
        self.stack.addWidget(self.view_templates)  # Index 4
        self.stack.addWidget(self.view_exercises)  # Index 5
        self.stack.addWidget(self.view_foods)      # Index 6
        self.stack.addWidget(self.view_developer)  # Index 7
        self.stack.addWidget(self.view_backup)     # Index 8
        self.stack.addWidget(self.view_accounting) # Index 9

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
        page_map = {
            "dashboard": 0,
            "members": 1,
            "workouts": 2,
            "nutrition": 3,
            "templates": 4,
            "exercises": 5,
            "foods": 6,
            "developer": 7,
            "backup": 8,
            "accounting": 9
        }
        if page_id in page_map:
            if not self._is_navigating_back and hasattr(self, '_current_page_state'):
                if self._current_page_state != ("page", page_id):
                    self._nav_history.append(self._current_page_state)
            self._current_page_state = ("page", page_id)

            if page_id == "dashboard":
                self.view_dashboard.refresh_dashboard()
            elif page_id == "members":
                self.view_members.load_members()
            elif page_id == "workouts":
                self.view_workouts.refresh_editor()
            elif page_id == "nutrition":
                self.view_nutrition.refresh_editor()
            elif page_id == "templates":
                self.view_templates.load_all_templates()
            elif page_id == "exercises":
                self.view_exercises.load_exercises()
            elif page_id == "foods":
                self.view_foods.load_foods()
            elif page_id == "developer":
                self.view_developer.load_data()
            elif page_id == "backup":
                self.view_backup.load_backups()
            elif page_id == "accounting":
                self.view_accounting.load_data()
            self.stack.setCurrentIndex(page_map[page_id])

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
