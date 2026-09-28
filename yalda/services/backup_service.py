import os
import shutil
import zipfile
import socket
import json
import urllib.request
import urllib.error
import ssl
import time
import errno
from pathlib import Path
from datetime import datetime
import config
from yalda.database.connection import SessionLocal
from yalda.models.database_models import BackupRecord
from yalda.utils.jalali_date import gregorian_to_shamsi


def create_local_backup() -> Path:
    """Always updates and overwrites the single local backup in data/backups/latest_backup.db and AppData."""
    if not config.DB_PATH.exists():
        return None
        
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    local_backup_file = config.BACKUPS_DIR / "latest_backup.db"
    
    try:
        shutil.copy2(config.DB_PATH, local_backup_file)
    except Exception as e:
        print(f"Error saving local backup: {e}")
        
    # Sync to persistent AppData
    try:
        config.APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        appdata_db = config.APPDATA_DATA_DIR / "yalda.db"
        shutil.copy2(config.DB_PATH, appdata_db)
    except Exception as e:
        print(f"Error syncing to AppData: {e}")
        
    return local_backup_file


def export_offline_backup(target_file_path: str) -> bool:
    """Exports a copy of the database to the specified custom path and refreshes local backup."""
    if not config.DB_PATH.exists():
        return False
    try:
        target_p = Path(target_file_path)
        target_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config.DB_PATH, target_p)
        create_local_backup()
        return True
    except Exception as e:
        print(f"Error exporting offline backup: {e}")
        return False


def _is_transient_network_error(exc: Exception) -> bool:
    """Checks if the exception is caused by transient network drops, TCP RST (10054), or timeouts."""
    if isinstance(exc, (TimeoutError, socket.timeout, ConnectionResetError)):
        return True
    err_str = str(exc).lower()
    if any(k in err_str for k in ("10054", "forcibly closed", "connection reset", "timed out", "remote end closed", "remotedisconnected")):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout, ConnectionResetError)):
            return True
        if isinstance(reason, OSError):
            if getattr(reason, "errno", None) in (errno.ECONNRESET, 10054, errno.ETIMEDOUT, 10060):
                return True
        reason_str = str(reason).lower()
        if any(k in reason_str for k in ("10054", "forcibly closed", "connection reset", "timed out", "remote disconnected")):
            return True
    return False


def _format_network_error_message(exc: Exception) -> str:
    """Converts raw socket / network exceptions into user-friendly Persian guidance."""
    err_str = str(exc)
    if "10054" in err_str or "forcibly closed" in err_str.lower() or "connection reset" in err_str.lower():
        return "ارتباط با سرور ابری به دلیل اختلال لحظه‌ای شبکه یا فایروال اینترنت قطع شد (WinError 10054). لطفاً چند لحظه بعد مجدداً تلاش نمایید."
    if "timed out" in err_str.lower() or isinstance(exc, (TimeoutError, socket.timeout)):
        return "مهلت زمانی اتصال به سرور ابری به پایان رسید (Timeout). لطفاً سرعت اینترنت را بررسی نموده و دوباره تلاش کنید."
    return f"خطا در ارتباط با سرور ابری: {err_str}"


def is_internet_connected(timeout: float = 3.0) -> bool:
    """Checks if active internet connection is available."""
    # First check cloud backup server or HTTPS
    try:
        req = urllib.request.Request(config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/"), method="HEAD")
        req.add_header("User-Agent", f"YaldaGymNetCheck/{config.APP_VERSION}")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        pass

    hosts = [
        ("8.8.8.8", 53),
        ("1.1.1.1", 53),
        ("google.com", 80)
    ]
    for host, port in hosts:
        try:
            s = socket.create_connection((host, port), timeout=timeout)
            s.close()
            return True
        except (socket.timeout, OSError):
            continue
    return False


def upload_cloud_backup(trainer_phone: str, trainer_name: str = "", server_url: str = None) -> tuple[bool, str]:
    """Uploads the database to the Yalda Cloud Backup Server with automatic retry on transient drops."""
    if not config.DB_PATH.exists():
        return False, "فایل پایگاه‌داده یافت نشد."
        
    # 1. Verify Internet Connection
    if not is_internet_connected():
        return False, "اتصال اینترنت برقرار نیست. لطفاً سیستم خود را به اینترنت متصل کنید و دوباره تلاش نمایید."
        
    url = server_url or config.DEFAULT_CLOUD_BACKUP_URL
    if not url.endswith("/"):
        upload_endpoint = f"{url}/api/backup/upload"
    else:
        upload_endpoint = f"{url}api/backup/upload"
        
    # Always refresh local backup
    create_local_backup()
    
    # 2. Prepare Multipart Form Data
    try:
        boundary = "----WebKitFormBoundaryYaldaGym" + os.urandom(8).hex()
        
        with open(config.DB_PATH, "rb") as f:
            db_bytes = f.read()
            
        body = bytearray()
        
        # Field: phone
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="phone"\r\n\r\n')
        body.extend(f"{trainer_phone}\r\n".encode("utf-8"))
        
        # Field: trainer_name
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="trainer_name"\r\n\r\n')
        body.extend(f"{trainer_name}\r\n".encode("utf-8"))
        
        # Field: file
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="file"; filename="yalda.db"\r\n')
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        body.extend(db_bytes)
        body.extend(b"\r\n")
        
        # Closing boundary
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        
        db_size_mb = len(db_bytes) / (1024 * 1024)
        adaptive_timeout = max(90, int(db_size_mb * 40))
        
        req = urllib.request.Request(upload_endpoint, data=bytes(body), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("X-API-Key", config.CLOUD_BACKUP_SECRET_KEY)
        req.add_header("User-Agent", f"YaldaGymDesktop/{config.APP_VERSION}")
        req.add_header("Connection", "close")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        max_retries = 3
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=adaptive_timeout, context=ctx) as response:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    if response.status in (200, 201) and resp_data.get("success", True):
                        return True, "نسخه پشتیبان با موفقیت در سرور ابری و حافظه سیستم ذخیره شد."
                    else:
                        return False, resp_data.get("message", "خطا در ثبت بک‌آپ روی سرور.")
            except urllib.error.HTTPError as e:
                if e.code in (502, 503, 504) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                try:
                    err_body = json.loads(e.read().decode("utf-8"))
                    return False, err_body.get("detail", err_body.get("message", f"خطای سرور: {e.code}"))
                except Exception:
                    return False, f"خطای ارتباط با سرور (کد {e.code})"
            except Exception as e:
                last_exc = e
                if _is_transient_network_error(e) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                break
                
        if last_exc:
            return False, _format_network_error_message(last_exc)
        return False, "خطا در برقراری ارتباط با سرور ابری."
        
    except Exception as e:
        return False, f"خطا در آماده‌سازی نسخه پشتیبان: {str(e)}"


def download_and_restore_cloud_backup(trainer_phone: str, server_url: str = None) -> tuple[bool, str]:
    """Downloads the latest database backup for the given trainer phone from cloud server and restores it."""
    clean_phone = "".join(filter(str.isdigit, str(trainer_phone)))
    if not clean_phone:
        return False, "شماره موبایل مربی نامعتبر است."

    if not is_internet_connected():
        return False, "اتصال اینترنت برقرار نیست. لطفاً اتصال اینترنت خود را بررسی نمایید."

    url = server_url or config.DEFAULT_CLOUD_BACKUP_URL
    if not url.endswith("/"):
        download_endpoint = f"{url}/api/backup/download/{clean_phone}"
    else:
        download_endpoint = f"{url}api/backup/download/{clean_phone}"

    max_retries = 3
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(download_endpoint, method="GET")
            req.add_header("X-API-Key", config.CLOUD_BACKUP_SECRET_KEY)
            req.add_header("User-Agent", f"YaldaGymDesktop/{config.APP_VERSION}")
            req.add_header("Connection", "close")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=45, context=ctx) as response:
                if response.status == 200:
                    data_bytes = response.read()
                    if not data_bytes or len(data_bytes) < 100:
                        return False, "فایل دیتابیس دریافتی از سرور خالی یا نامعتبر است."

                    # Safety: Save current DB before overwriting
                    if config.DB_PATH.exists():
                        try:
                            create_local_backup()
                        except Exception:
                            pass

                    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
                    with open(config.DB_PATH, "wb") as f:
                        f.write(data_bytes)

                    # Sync to AppData
                    try:
                        config.APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(config.DB_PATH, config.APPDATA_DATA_DIR / "yalda.db")
                    except Exception:
                        pass

                    # Run database migrations in case schema needs updates
                    try:
                        from yalda.database.connection import check_and_migrate_db
                        check_and_migrate_db()
                    except Exception:
                        pass

                    return True, "اطلاعات و پایگاه‌داده با موفقیت از سرور ابری دریافت و بازیابی شد."
                else:
                    return False, f"سرور با وضعیت {response.status} پاسخ داد."

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "هیچ نسخه پشتیبانی برای این شماره موبایل در سرور ابری یافت نشد."
            elif e.code == 401:
                return False, "کلید احراز هویت سرور ابری نامعتبر است."
            elif e.code in (502, 503, 504) and attempt < max_retries:
                time.sleep(2 * attempt)
                continue
            else:
                return False, f"خطای ارتباط با سرور ابری (کد {e.code})"
        except Exception as e:
            last_exc = e
            if _is_transient_network_error(e) and attempt < max_retries:
                time.sleep(2 * attempt)
                continue
            break

    if last_exc:
        return False, _format_network_error_message(last_exc)
    return False, "خطا در دریافت اطلاعات از سرور ابری."


class BackupService:
    @staticmethod
    def restore_from_cloud(trainer_phone: str) -> tuple[bool, str]:
        return download_and_restore_cloud_backup(trainer_phone)
    @staticmethod
    def get_all_backups():
        with SessionLocal() as db:
            return db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()

    @staticmethod
    def create_backup(target_filepath: str = None) -> str:
        config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
        time_str = now.strftime("%H-%M-%S")
        default_filename = f"yalda_backup_{shamsi_date}_{time_str}.zip"

        if target_filepath:
            p = Path(target_filepath)
            if p.is_dir() or not p.suffix:
                p.mkdir(parents=True, exist_ok=True)
                filepath = p / default_filename
                filename = default_filename
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                filepath = p
                filename = p.name
        else:
            filepath = config.BACKUPS_DIR / default_filename
            filename = default_filename

        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            if config.DB_PATH.exists():
                zipf.write(config.DB_PATH, arcname="yalda.db")
            if config.UPLOADS_DIR.exists():
                for root, _, files in os.walk(config.UPLOADS_DIR):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(config.DATA_DIR)
                        zipf.write(full_p, arcname=str(rel_p))

        file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
        shamsi_display = f"{gregorian_to_shamsi(now.date())} {now.strftime('%H:%M:%S')}"

        with SessionLocal() as db:
            record = BackupRecord(
                file_name=filename,
                file_path=str(filepath),
                backup_size_mb=file_size_mb,
                backup_date_shamsi=shamsi_display,
                created_at=now
            )
            db.add(record)
            db.commit()

        create_local_backup()
        return str(filepath)

    @staticmethod
    def record_cloud_backup(trainer_phone: str = "") -> None:
        """Records a successful cloud backup in the database history."""
        now = datetime.now()
        shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
        time_str = now.strftime("%H-%M-%S")
        filename = f"yalda_cloud_backup_{shamsi_date}_{time_str}.db"
        shamsi_display = f"{gregorian_to_shamsi(now.date())} {now.strftime('%H:%M:%S')}"
        size_mb = 0.0
        if config.DB_PATH.exists():
            size_mb = round(os.path.getsize(config.DB_PATH) / (1024 * 1024), 2)

        with SessionLocal() as db:
            record = BackupRecord(
                file_name=filename,
                file_path="☁️ سرور ابری یلدا (Cloud Server)",
                backup_size_mb=size_mb,
                backup_date_shamsi=shamsi_display,
                created_at=now
            )
            db.add(record)
            db.commit()

    @staticmethod
    def record_email_backup(trainer_email: str, filename: str = "", size_mb: float = 0.0) -> None:
        """Records a successful email backup in the database history."""
        now = datetime.now()
        shamsi_date = gregorian_to_shamsi(now.date()).replace("/", "-")
        time_str = now.strftime("%H-%M-%S")
        if not filename:
            filename = f"yalda_backup_{shamsi_date}_{time_str}.db"
        shamsi_display = f"{gregorian_to_shamsi(now.date())} {now.strftime('%H:%M:%S')}"
        if size_mb <= 0.0 and config.DB_PATH.exists():
            size_mb = round(os.path.getsize(config.DB_PATH) / (1024 * 1024), 2)

        with SessionLocal() as db:
            record = BackupRecord(
                file_name=filename,
                file_path=f"📧 ایمیل مربی ({trainer_email})",
                backup_size_mb=round(size_mb, 2),
                backup_date_shamsi=shamsi_display,
                created_at=now
            )
            db.add(record)
            db.commit()

    @staticmethod
    def delete_backup(backup_id: int) -> bool:
        with SessionLocal() as db:
            record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
            if record:
                if record.file_path and os.path.exists(record.file_path):
                    try:
                        os.remove(record.file_path)
                    except Exception as e:
                        print(f"Error removing physical backup file: {e}")
                db.delete(record)
                db.commit()
                return True
            return False

    @staticmethod
    def restore_backup(filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError("فایل بک‌آپ یافت نشد.")

        if filepath.endswith(".zip"):
            with zipfile.ZipFile(filepath, "r") as zipf:
                zipf.extractall(config.DATA_DIR)
        elif filepath.endswith(".db"):
            shutil.copy2(filepath, config.DB_PATH)
            try:
                config.APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filepath, config.APPDATA_DATA_DIR / "yalda.db")
            except Exception:
                pass

        create_local_backup()