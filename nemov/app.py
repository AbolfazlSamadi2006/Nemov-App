import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, Qt
import config
from nemov.database.connection import init_db
from nemov.views.login_view import LoginView

class NemovApplication:
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

        # Load and register embedded fonts to guarantee crisp Persian rendering across all systems
        try:
            from PyQt6.QtGui import QFontDatabase, QFont
            fonts_dir = config.BASE_DIR / "resources" / "fonts"
            if fonts_dir.exists():
                for font_name in ["Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf", "BKoodakBd.ttf", "BTitrBd.ttf", "segoeui.ttf"]:
                    f_p = fonts_dir / font_name
                    if f_p.exists():
                        QFontDatabase.addApplicationFont(str(f_p))
            self.app.setFont(QFont("Vazirmatn", 11))
        except Exception:
            pass

        # Set Global Application & Taskbar Icon with multi-resolution .ico support
        from nemov.utils.image_utils import get_app_icon, apply_windows_taskbar_icon
        self.app_icon = get_app_icon()
        if not self.app_icon.isNull():
            self.app.setWindowIcon(self.app_icon)

        # Check for Database presence (Portable mode check)
        db_file = config.DATA_DIR / "nemov.db"
        legacy_db_file = config.DATA_DIR / "yalda.db"
        if not db_file.exists() and not legacy_db_file.exists():
            from nemov.views.data_migration_dialog import DataMigrationDialog
            dlg = DataMigrationDialog()
            dlg.exec()

        # Initialize Database
        init_db()

        # Load Saved Theme dynamically via ThemeManager with safe fallback
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
        """
        Loads and applies the saved theme dynamically via ThemeManager with safe fallback.
        Ensures application startup is 100% resilient against database or theme errors.
        """
        try:
            from nemov.utils.theme_manager import ThemeManager
            ThemeManager.apply_saved_theme(self.app)
        except Exception:
            try:
                from nemov.utils.theme_manager import ThemeManager
                ThemeManager.apply_theme("crimson_fury", self.app)
            except Exception:
                pass

    def run(self):
        self.login_view.showMaximized()
        from nemov.utils.image_utils import apply_windows_taskbar_icon
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
        from nemov.auth.authentication import CurrentUser
        from nemov.utils.logger import log_info
        user = CurrentUser.get()
        username = user.username if user else "مربی"
        user_id = user.id if user else "-"
        log_info(f"Trainer logged in: {username} (ID: {user_id})")
        self.login_view.hide()
        if not self.main_window:
            from nemov.views.main_window import MainWindow
            self.main_window = MainWindow()
            self.main_window.logout_signal.connect(self.on_logout)

        # Force refresh all views and reset to Dashboard for the newly logged-in trainer
        self.main_window.refresh_on_login()
        self.main_window.showMaximized()
        from nemov.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self.main_window)

    def on_logout(self):
        from nemov.auth.authentication import CurrentUser
        from nemov.utils.logger import log_info
        user = CurrentUser.get()
        username = user.username if user else "مربی"
        log_info(f"Trainer logged out: {username}")
        CurrentUser.logout()
        if self.main_window:
            self.main_window.hide()
        self.login_view.txt_username.clear()
        self.login_view.txt_password.clear()
        self.login_view.showMaximized()
        from nemov.utils.image_utils import apply_windows_taskbar_icon
        apply_windows_taskbar_icon(self.login_view)


# Backward-compatibility alias
YaldaApplication = NemovApplication
