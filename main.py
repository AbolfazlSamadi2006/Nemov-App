import sys
import traceback
import threading
from datetime import datetime
import config
from yalda.utils.logger import setup_logging, log_critical, log_error, log_info
from yalda.app import YaldaApplication

def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        sys.__excepthook__(exctype, value, tb)
    except Exception:
        pass
    try:
        log_critical(f"Unhandled GUI exception: {value}", exc_info=(exctype, value, tb))
    except Exception:
        pass
    try:
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance():
            from yalda.views.components.error_dialog import show_error_dialog
            show_error_dialog(
                message="متاسفانه خطای پیش‌بینی‌نشده‌ای در برنامه رخ داد. جهت پایداری نرم‌افزار، اجرای آن متوقف نشد و جزئیات در فایل لاگ خطاها ذخیره گردید.",
                technical_details=error_msg,
                title="خطای سیستم"
            )
    except Exception:
        pass

def thread_exception_hook(args):
    tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    thread_name = getattr(args.thread, "name", "UnknownThread")
    log_error(f"Unhandled exception in background thread '{thread_name}': {args.exc_value}\n{tb_str}")

def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(getattr(config, "APP_USER_MODEL_ID", "nemov.sports.management.desktop.v3"))
        except Exception:
            pass
    setup_logging()
    sys.excepthook = exception_hook
    threading.excepthook = thread_exception_hook
    log_info("Starting Nemov Application...")
    app = YaldaApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
