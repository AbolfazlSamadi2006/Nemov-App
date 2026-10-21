import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import config

LOGS_DIR = config.DATA_DIR / "logs"

# Ensure logs directory exists
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

APP_LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "error.log"

_is_configured = False


def setup_logging():
    """Initializes rotating file handlers and console stream logging."""
    global _is_configured
    if _is_configured:
        return

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Standard formatter
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # 1. App Log Handler (INFO and above - captures general flow and errors)
    try:
        app_handler = RotatingFileHandler(
            filename=str(APP_LOG_FILE),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(formatter)
        root_logger.addHandler(app_handler)
    except Exception as e:
        print(f"[Logging] Failed to initialize app.log handler: {e}", file=sys.stderr)

    # 2. Dedicated Error Log Handler (ERROR and CRITICAL only)
    try:
        error_handler = RotatingFileHandler(
            filename=str(ERROR_LOG_FILE),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    except Exception as e:
        print(f"[Logging] Failed to initialize error.log handler: {e}", file=sys.stderr)

    # 3. Console Handler (for dev/debugging)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _is_configured = True
    logging.info(f"=== Yalda Gym Application Started ({config.APP_VERSION}) ===")


def get_logger(name: str = "yalda"):
    """Returns a named logger."""
    if not _is_configured:
        setup_logging()
    return logging.getLogger(name)


def log_info(msg: str, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)


def log_warning(msg: str, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)


def log_error(msg: str, exc_info=True, *args, **kwargs):
    get_logger().error(msg, exc_info=exc_info, *args, **kwargs)


def log_critical(msg: str, exc_info=True, *args, **kwargs):
    get_logger().critical(msg, exc_info=exc_info, *args, **kwargs)


def get_logs_dir() -> Path:
    """Returns the path to the logs directory."""
    return LOGS_DIR


def get_log_content(which: str = "error", max_lines: int = 300) -> str:
    """Returns the last max_lines from error.log or app.log."""
    target_file = ERROR_LOG_FILE if which == "error" else APP_LOG_FILE
    if not target_file.exists():
        return f"فایل {target_file.name} هنوز ایجاد نشده است یا خالی است."
    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            recent = lines[-max_lines:] if len(lines) > max_lines else lines
            return "".join(recent)
    except Exception as e:
        return f"خطا در خواندن فایل لاگ: {e}"


def get_parsed_log_entries(max_lines: int = 600) -> list[dict]:
    """Parses app.log into structured numbered log entry dictionaries."""
    import re
    log_pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\[([A-Z]+)\]\s*(.*)$")
    target_file = APP_LOG_FILE
    if not target_file.exists() or target_file.stat().st_size == 0:
        if ERROR_LOG_FILE.exists() and ERROR_LOG_FILE.stat().st_size > 0:
            target_file = ERROR_LOG_FILE
        else:
            return []

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            recent = lines[-max_lines:] if len(lines) > max_lines else lines
    except Exception as e:
        return [{
            "num": 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "ERROR",
            "message": f"خطا در بارگذاری فایل لاگ: {e}",
            "body": []
        }]

    entries = []
    current = None
    counter = 1

    for line in recent:
        line_clean = line.rstrip("\r\n")
        m = log_pattern.match(line_clean)
        if m:
            if current:
                entries.append(current)
            ts, level, rest = m.groups()
            current = {
                "num": counter,
                "timestamp": ts,
                "level": level.upper(),
                "message": rest,
                "body": []
            }
            counter += 1
        else:
            if current:
                current["body"].append(line_clean)
            elif line_clean.strip():
                current = {
                    "num": counter,
                    "timestamp": "",
                    "level": "INFO",
                    "message": line_clean,
                    "body": []
                }
                counter += 1

    if current:
        entries.append(current)

    return entries


def get_last_error_snippet() -> str:
    """Extracts the latest traceback/error snippet from error.log."""
    if not ERROR_LOG_FILE.exists():
        return "هیچ خطایی ثبت نشده است."
    try:
        with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
            if not content:
                return "فایل لاگ خالی است."
            # Grab last 2500 characters
            return content[-2500:]
    except Exception as e:
        return f"خطا در بازیابی آخرین خطا: {e}"


def clear_logs() -> bool:
    """Safely clears content of current log files."""
    success = True
    for fpath in [APP_LOG_FILE, ERROR_LOG_FILE]:
        if fpath.exists():
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] لاگ‌ها توسط کاربر پاک‌سازی شدند.\n")
            except Exception:
                success = False
    return success


def open_logs_folder():
    """Opens the logs directory in Windows File Explorer."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(LOGS_DIR))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(LOGS_DIR)])
    except Exception as e:
        log_error(f"Failed to open logs folder: {e}")
