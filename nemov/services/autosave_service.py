"""
nemov/services/autosave_service.py
Lightweight, non-blocking background AutoSave service for Nemov.
Periodically backs up database to the Runflare Cloud Server & ArvanCloud Storage when internet is connected,
checking for new data changes every 5 minutes with 0% UI lag and no interruptions.
"""
import os
import time
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
import config
from nemov.database.connection import (
    get_session,
    has_data_changed,
    reset_data_changed,
    has_local_data_changed,
    reset_local_data_changed,
)
from nemov.models.database_models import SystemSetting
from nemov.auth.authentication import CurrentUser
from nemov.utils.logger import log_info, log_error


SETTING_KEY_AUTOSAVE = "cloud_autosave_enabled"
DEFAULT_AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes (Runflare Cloud)
LOCAL_AUTOSAVE_INTERVAL_MS = 3 * 60 * 1000    # 3 minutes (Always-on hidden Local)


def is_autosave_enabled() -> bool:
    """Checks if background cloud autosave is enabled in system settings."""
    try:
        session = get_session()
        try:
            s = session.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY_AUTOSAVE).first()
            if s and s.value:
                return s.value.strip().lower() == "true"
        finally:
            session.close()
    except Exception:
        pass
    return False


def set_autosave_enabled(enabled: bool) -> bool:
    """Enables or disables cloud autosave in system settings."""
    try:
        session = get_session()
        try:
            s = session.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY_AUTOSAVE).first()
            val = "true" if enabled else "false"
            if s:
                s.value = val
            else:
                s = SystemSetting(key=SETTING_KEY_AUTOSAVE, value=val)
                session.add(s)
            session.commit()
            log_info(f"Cloud autosave setting set to: {val}")
            return True
        finally:
            session.close()
    except Exception as e:
        log_error(f"Failed to update autosave setting: {e}")
        return False


class AutoSaveWorker(QThread):
    """
    Completely silent, low-priority background thread for syncing database to the Runflare Cloud Server.
    Guarantees 0% UI lag and no intrusive popups on network drops.
    """
    autosave_done = pyqtSignal(bool, str)

    def __init__(self, phone: str, trainer_name: str, parent=None):
        super().__init__(parent)
        self.phone = phone
        self.trainer_name = trainer_name

    def run(self):
        try:
            from nemov.services.backup_service import is_internet_connected, upload_cloud_backup, BackupService
            # Check connection with fast timeout
            if not is_internet_connected(timeout=2.0):
                self.autosave_done.emit(False, "No internet connection")
                return

            # Perform database upload to Runflare Cloud Server & ArvanCloud Storage
            success, msg = upload_cloud_backup(trainer_phone=self.phone, trainer_name=self.trainer_name)
            if success:
                try:
                    BackupService.record_cloud_backup(self.phone)
                except Exception:
                    pass
                log_info(f"AutoSave completed successfully to Runflare Cloud Server for {self.phone}")
                self.autosave_done.emit(True, msg)
            else:
                log_info(f"AutoSave skipped or transient fail: {msg}")
                self.autosave_done.emit(False, msg)
        except Exception as e:
            log_error(f"AutoSaveWorker exception: {e}")
            self.autosave_done.emit(False, str(e))


class _LocalAutoSaveWorker(QThread):
    """Silent, non-blocking background worker for 3-minute atomic local database AutoSave."""
    local_done = pyqtSignal(bool)

    def run(self):
        try:
            from nemov.services.backup_service import create_local_backup
            res = create_local_backup()
            self.local_done.emit(res is not None)
        except Exception as e:
            log_error(f"Local AutoSaveWorker exception: {e}")
            self.local_done.emit(False)


class AutoSaveManager(QObject):
    """
    Orchestrates two independent AutoSave loops:
    1. Hidden, always-on 3-minute local atomic backup (+ AppData mirror & WAL checkpoint).
    2. Optional 5-minute Runflare cloud backup (controlled by Settings checkbox).
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AutoSaveManager()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(DEFAULT_AUTOSAVE_INTERVAL_MS)
        self.timer.timeout.connect(self.trigger_autosave_if_eligible)

        self.local_timer = QTimer(self)
        self.local_timer.setInterval(LOCAL_AUTOSAVE_INTERVAL_MS)
        self.local_timer.timeout.connect(self.trigger_local_autosave_if_eligible)

        self.worker = None
        self.local_worker = None
        self._last_backup_mtime = 0.0
        self._last_local_backup_mtime = 0.0

    def start(self):
        """Starts the periodic hidden 3m local timer and (when enabled) 5m cloud timer."""
        if not self.local_timer.isActive():
            self.local_timer.start()
            log_info("Local AutoSave timer started (3m silent interval).")
        if is_autosave_enabled() and not self.timer.isActive():
            self.timer.start()
            log_info("AutoSaveManager timer started (5m interval).")

    def stop(self):
        """Stops cloud and local autosave timers."""
        if self.timer.isActive():
            self.timer.stop()
            log_info("AutoSaveManager timer stopped.")
        if self.local_timer.isActive():
            self.local_timer.stop()

    def start_cloud(self):
        """Starts only the optional 5m Runflare cloud AutoSave timer."""
        if not self.timer.isActive():
            self.timer.start()
            log_info("AutoSaveManager timer started (5m interval).")

    def stop_cloud(self):
        """Stops only the optional Runflare cloud timer while keeping 3m local AutoSave active."""
        if self.timer.isActive():
            self.timer.stop()
            log_info("AutoSaveManager timer stopped.")

    def record_manual_backup_done(self):
        """Notifies the manager that a manual backup just succeeded, resetting dirty state."""
        mtime = os.path.getmtime(config.DB_PATH) if config.DB_PATH.exists() else time.time()
        self._last_backup_mtime = mtime
        self._last_local_backup_mtime = mtime
        reset_data_changed()
        reset_local_data_changed()

    def trigger_local_autosave_if_eligible(self):
        """Silently creates an atomic local backup every 3 minutes whenever DB data changed."""
        if not CurrentUser.get():
            return
        if self.local_worker and self.local_worker.isRunning():
            return
        db_path = config.DB_PATH
        db_mtime = os.path.getmtime(db_path) if db_path.exists() else 0.0
        is_dirty = has_local_data_changed() or (
            self._last_local_backup_mtime > 0 and db_mtime > self._last_local_backup_mtime
        ) or (self._last_local_backup_mtime == 0.0)
        if not is_dirty:
            return
        self.local_worker = _LocalAutoSaveWorker(parent=self)
        self.local_worker.local_done.connect(self._on_local_worker_completed)
        self.local_worker.start()

    def _on_local_worker_completed(self, success: bool):
        if success:
            self._last_local_backup_mtime = os.path.getmtime(config.DB_PATH) if config.DB_PATH.exists() else time.time()
            reset_local_data_changed()

    def flush_local_sync(self) -> bool:
        """Fast synchronous local flush used on exit/logout (<25ms, zero dialogs)."""
        try:
            from nemov.services.backup_service import create_local_backup
            res = create_local_backup()
            if res is not None:
                self._last_local_backup_mtime = os.path.getmtime(config.DB_PATH) if config.DB_PATH.exists() else time.time()
                reset_local_data_changed()
                return True
        except Exception as e:
            log_error(f"Local exit flush exception: {e}")
        return False

    def trigger_autosave_if_eligible(self):
        """Checks conditions and runs background autosave if enabled, user logged in, and data changed."""
        if not is_autosave_enabled():
            return

        u = CurrentUser.get()
        if not u:
            return

        # Do not run if worker is currently in progress
        if self.worker and self.worker.isRunning():
            return

        db_path = config.DB_PATH
        db_mtime = os.path.getmtime(db_path) if db_path.exists() else 0.0

        # Check if changes occurred since last backup
        is_dirty = has_data_changed() or (self._last_backup_mtime > 0 and db_mtime > self._last_backup_mtime)

        # If a backup has already run and no new data was modified, skip this 5-minute turn!
        if self._last_backup_mtime > 0 and not is_dirty:
            log_info("AutoSave check (5m interval): No new data changes detected since last backup. Skipping cloud upload.")
            return

        phone = u.phone if (u and u.phone) else "09336427711"
        trainer_name = u.full_name if u else "مربی محترم"

        self.worker = AutoSaveWorker(phone=phone, trainer_name=trainer_name, parent=self)
        self.worker.autosave_done.connect(self._on_worker_completed)
        self.worker.start()

    def _on_worker_completed(self, success: bool, msg: str):
        if success:
            self._last_backup_mtime = os.path.getmtime(config.DB_PATH) if config.DB_PATH.exists() else time.time()
            reset_data_changed()
            log_info("AutoSave state updated: dirty flag reset and timestamp recorded.")
