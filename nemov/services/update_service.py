import os
import re
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal, QObject
import config
from nemov.utils.jalali_date import get_today_shamsi

GITHUB_REPO = "AbolfazlSamadi2006/Nemov-App"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v_str: str) -> tuple:
    """
    Parses semantic version strings like 'v3.4.1', '3.4.2', 'v3.4.10' into comparable integer tuples.
    """
    if not v_str:
        return (0,)
    v_clean = re.sub(r'^[vV]', '', str(v_str).strip())
    parts = []
    for segment in re.split(r'[\.\-\_]', v_clean):
        nums = re.findall(r'\d+', segment)
        if nums:
            parts.append(int(nums[0]))
    return tuple(parts) if parts else (0,)


def format_bytes(num_bytes: int) -> str:
    """Formats bytes into Persian human-readable format (e.g. ۱۰۴.۸ مگابایت)."""
    if not num_bytes or num_bytes <= 0:
        return "۰ مگابایت"
    mb = num_bytes / (1024 * 1024)
    fa_mb = f"{mb:.1f}".translate(str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹."))
    return f"{fa_mb} مگابایت"


class UpdateCheckWorker(QThread):
    finished_signal = pyqtSignal(bool, dict, str)  # has_update, info, error_msg

    def __init__(self, current_version: str = config.APP_VERSION, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"Nemov-Desktop-App/{self.current_version}"
                }
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                if response.status != 200:
                    self.finished_signal.emit(False, {}, f"خطای سرور گیت‌هاب (کد {response.status})")
                    return
                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)

            tag_name = data.get("tag_name", "")
            cur_tuple = parse_version(self.current_version)
            latest_tuple = parse_version(tag_name)
            has_update = latest_tuple > cur_tuple

            # Search assets for direct setup executable
            assets = data.get("assets", [])
            download_url = ""
            asset_name = ""
            asset_size = 0
            for asset in assets:
                name = asset.get("name", "")
                if name.lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    asset_name = name
                    asset_size = asset.get("size", 0)
                    if "setup" in name.lower():
                        break

            if not download_url:
                download_url = data.get("html_url", "")

            info = {
                "tag_name": tag_name,
                "name": data.get("name", tag_name),
                "body": data.get("body", ""),
                "html_url": data.get("html_url", ""),
                "download_url": download_url,
                "asset_name": asset_name or f"Nemov_Setup_{tag_name}.exe",
                "asset_size": asset_size,
                "published_at": data.get("published_at", "")
            }
            self.finished_signal.emit(has_update, info, "")
        except urllib.error.URLError:
            self.finished_signal.emit(False, {}, "عدم دسترسی به اینترنت یا قطع ارتباط با سرور گیت‌هاب")
        except Exception as e:
            self.finished_signal.emit(False, {}, f"خطا در بررسی به‌روزرسانی: {str(e)}")


class UpdateDownloadWorker(QThread):
    progress_signal = pyqtSignal(int, int, int)  # percent, downloaded_bytes, total_bytes
    finished_signal = pyqtSignal(bool, str, str)  # success, file_path, error_msg

    def __init__(self, download_url: str, asset_name: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.asset_name = asset_name or "Nemov_Setup.exe"
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        part_file = None
        try:
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)

            target_file = downloads_dir / self.asset_name
            part_file = downloads_dir / f"{self.asset_name}.part"

            req = urllib.request.Request(
                self.download_url,
                headers={
                    "User-Agent": f"Nemov-Desktop-App/{config.APP_VERSION}"
                }
            )

            with urllib.request.urlopen(req, timeout=20) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536  # 64 KB

                with open(part_file, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            f.close()
                            if part_file.exists():
                                part_file.unlink(missing_ok=True)
                            self.finished_signal.emit(False, "", "دانلود توسط کاربر لغو شد.")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.progress_signal.emit(pct, downloaded, total_size)

            if target_file.exists():
                try:
                    target_file.unlink()
                except Exception:
                    pass
            part_file.rename(target_file)

            self.finished_signal.emit(True, str(target_file), "")
        except Exception as e:
            if part_file and part_file.exists():
                try:
                    part_file.unlink(missing_ok=True)
                except Exception:
                    pass
            self.finished_signal.emit(False, "", f"خطا در دانلود فایل: {str(e)}")


class UpdateService:
    """
    Session-level singleton service managing update state, background checking,
    notification suppression, and installer execution.
    """
    _latest_info: dict = None
    _has_update: bool = False
    _last_check_time: str = ""
    _notification_seen: bool = False
    _downloaded_installer_path: str = None
    _active_check_worker: UpdateCheckWorker = None
    _active_download_worker: UpdateDownloadWorker = None

    @classmethod
    def set_check_result(cls, has_update: bool, info: dict):
        cls._has_update = has_update
        cls._latest_info = info or {}
        now = datetime.now()
        shamsi_today = get_today_shamsi()
        time_str = now.strftime("%H:%M")
        cls._last_check_time = f"{shamsi_today} ساعت {time_str}"

    @classmethod
    def get_latest_info(cls) -> dict:
        return cls._latest_info or {}

    @classmethod
    def has_update_available(cls) -> bool:
        return cls._has_update

    @classmethod
    def get_last_check_time(cls) -> str:
        return cls._last_check_time

    @classmethod
    def is_notification_pending(cls) -> bool:
        """Returns True only if an update exists and user has NOT seen it in this session yet."""
        return cls._has_update and not cls._notification_seen

    @classmethod
    def mark_notification_seen(cls):
        """Marks the update as seen so sidebar reminders do not repeat during this session."""
        cls._notification_seen = True

    @classmethod
    def set_downloaded_installer(cls, path: str):
        if path and os.path.exists(path):
            cls._downloaded_installer_path = str(path)
        else:
            cls._downloaded_installer_path = None

    @classmethod
    def get_downloaded_installer(cls) -> str:
        if cls._downloaded_installer_path and os.path.exists(cls._downloaded_installer_path):
            return cls._downloaded_installer_path
        return None

    @classmethod
    def apply_update_and_exit(cls, installer_path: str = None) -> bool:
        """
        Launches the downloaded installer executable and terminates the running Nemov app.
        """
        path_to_run = installer_path or cls.get_downloaded_installer()
        if not path_to_run or not os.path.exists(path_to_run):
            return False

        try:
            os.startfile(path_to_run)
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            return True
        except Exception as e:
            print(f"Error launching installer: {e}")
            return False
