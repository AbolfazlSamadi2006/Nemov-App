import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, Qt
import config
from yalda.database.connection import init_db
from yalda.views.login_view import LoginView

class YaldaApplication:
    def __init__(self):
        # Set Windows AppUserModelID so Windows Taskbar pins and displays the custom logo
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(getattr(config, "APP_USER_MODEL_ID", "nemov.sports.management.desktop.v3"))
        except Exception:
            pass

        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass

        self.app = QApplication(sys.argv)
        self.app.setApplicationName(config.APP_NAME)

        # Set Global Application & Taskbar Icon with multi-resolution .ico support
        from yalda.utils.image_utils import get_app_icon, apply_windows_taskbar_icon
        self.app_icon = get_app_icon()
        if not self.app_icon.isNull():
            self.app.setWindowIcon(self.app_icon)

        # Check for Database presence (Portable mode check)
        db_file = config.DATA_DIR / "yalda.db"
        if not db_file.exists():
            from yalda.views.data_migration_dialog import DataMigrationDialog
            dlg = DataMigrationDialog()
            dlg.exec()

        # Initialize Database
        init_db()

        # Load Dark Red & Black QSS Theme
        self.load_stylesheet()

        # Windows setup
        self.login_view = LoginView()
        if not self.app_icon.isNull():
            self.login_view.setWindowIcon(self.app_icon)
        apply_windows_taskbar_icon(self.login_view)
        self.main_window = None

        self.login_view.login_success.connect(self.on_login_success)
        self.app.aboutToQuit.connect(config.sync_data_directories)

    def load_stylesheet(self):
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
                self.app.setStyleSheet(content)

    def run(self):
        self.login_view.showMaximized()
        from yalda.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self.login_view)
        # Pre-warm OpenCV C++ DLLs silently in background thread so camera opens instantly
        try:
            import threading
            threading.Thread(target=self._preload_opencv, daemon=True).start()
        except Exception:
            pass
        return self.app.exec()

    def _preload_opencv(self):
        """Warm up OpenCV C++ codecs and drivers in background."""
        try:
            import cv2
            _ = cv2.__version__
        except Exception:
            pass

    def on_login_success(self):
        from yalda.auth.authentication import CurrentUser
        from yalda.utils.logger import log_info
        user = CurrentUser.get()
        username = user.username if user else "مربی"
        user_id = user.id if user else "-"
        log_info(f"Trainer logged in: {username} (ID: {user_id})")
        self.login_view.hide()
        if not self.main_window:
            from yalda.views.main_window import MainWindow
            self.main_window = MainWindow()
            self.main_window.logout_signal.connect(self.on_logout)

        # Force refresh all views and reset to Dashboard for the newly logged-in trainer
        self.main_window.refresh_on_login()
        self.main_window.showMaximized()
        from yalda.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self.main_window)

    def on_logout(self):
        from yalda.auth.authentication import CurrentUser
        from yalda.utils.logger import log_info
        user = CurrentUser.get()
        username = user.username if user else "مربی"
        log_info(f"Trainer logged out: {username}")
        CurrentUser.logout()
        if self.main_window:
            self.main_window.hide()
        self.login_view.txt_username.clear()
        self.login_view.txt_password.clear()
        self.login_view.showMaximized()
        from yalda.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self.login_view)

