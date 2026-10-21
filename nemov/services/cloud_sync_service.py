import os
import uuid
import json
import ssl
import time
import socket
import errno
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image
import config
from nemov.database.connection import get_session, mark_data_changed
from nemov.models.database_models import Exercise

VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.webm', '.mov']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']


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
    return f"خطای ارتباط با سرور ابری: {err_str}"


def upload_exercise_video_to_cloud(video_path: str, custom_filename: str = None) -> tuple[bool, str, str]:
    """
    Uploads a local exercise video file to the Cloudflare Worker R2 video endpoint.
    Automatically ensures web-standard H.264 format with faststart before upload.
    Returns: (success: bool, url_or_error: str, filename: str)
    """
    if not video_path or not os.path.exists(video_path):
        return False, "فایل ویدیویی روی دیسک یافت نشد.", ""

    base_url = config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/")
    upload_endpoint = f"{base_url}/api/video/upload"

    p = Path(video_path)
    filename = custom_filename or p.name

    upload_path = video_path
    temp_h264_path = None

    # Automatically ensure web-standard H.264 format, 720p HD scaling, and high-efficiency compression before upload
    try:
        import subprocess
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_dir = tempfile.gettempdir()
        temp_h264_path = os.path.join(temp_dir, f"h264_{uuid.uuid4().hex[:8]}.mp4")

        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(video_path),
            "-vf", "scale=-2:min(720\\,ih)",
            "-c:v", "libx264",
            "-r", "25",
            "-preset", "fast",
            "-crf", "26",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-an",
            temp_h264_path
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, capture_output=True, creationflags=flags)
        if res.returncode == 0 and os.path.exists(temp_h264_path) and os.path.getsize(temp_h264_path) > 0:
            upload_path = temp_h264_path
            if not filename.lower().endswith(".mp4"):
                filename = f"{p.stem}.mp4"
    except Exception:
        pass

    try:
        with open(upload_path, "rb") as f:
            video_bytes = f.read()

        file_size_mb = len(video_bytes) / (1024 * 1024)
        adaptive_timeout = max(180, int(file_size_mb * 45))

        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        body = bytearray()

        # Field: filename
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="filename"\r\n\r\n')
        body.extend(f"{filename}\r\n".encode("utf-8"))

        # Field: file
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(b"Content-Type: video/mp4\r\n\r\n")
        body.extend(video_bytes)
        body.extend(b"\r\n")

        # Closing boundary
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

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
                        video_url = resp_data.get("url", f"{base_url}/video/{filename}")
                        return True, video_url, filename
                    else:
                        return False, resp_data.get("detail", resp_data.get("message", "خطا در آپلود ویدیو")), filename
            except urllib.error.HTTPError as e:
                if e.code in (502, 503, 504) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                try:
                    err_data = json.loads(e.read().decode("utf-8"))
                    msg = err_data.get("detail", err_data.get("message", f"خطای سرور: {e.code}"))
                except Exception:
                    msg = f"خطای سرور ابری (کد {e.code})"
                return False, msg, filename
            except Exception as e:
                last_exc = e
                if _is_transient_network_error(e) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                break

        if last_exc:
            return False, _format_network_error_message(last_exc), filename
        return False, "خطا در ارسال ویدیو به سرور ابری", filename
    finally:
        if temp_h264_path and os.path.exists(temp_h264_path):
            try:
                os.remove(temp_h264_path)
            except Exception:
                pass


def upload_exercise_image_to_cloud(image_path: str, custom_filename: str = None) -> tuple[bool, str, str]:
    """
    Uploads a local exercise image file to the Cloudflare Worker image endpoint.
    Automatically ensures web-optimized format (JPEG quality 92) before upload.
    Returns: (success: bool, url_or_error: str, filename: str)
    """
    if not image_path or not os.path.exists(image_path):
        return False, "فایل تصویری روی دیسک یافت نشد.", ""

    base_url = config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/")
    upload_endpoint = f"{base_url}/api/image/upload"

    p = Path(image_path)
    filename = custom_filename or p.name

    upload_path = image_path
    temp_img_path = None

    # Optimize image for web delivery
    try:
        loaded = Image.open(image_path)
        if loaded.mode != "RGB":
            loaded = loaded.convert("RGB")
        temp_dir = tempfile.gettempdir()
        temp_img_path = os.path.join(temp_dir, f"opt_{uuid.uuid4().hex[:8]}.jpg")
        loaded.save(temp_img_path, format="JPEG", quality=92, optimize=True)
        if os.path.exists(temp_img_path) and os.path.getsize(temp_img_path) > 0:
            upload_path = temp_img_path
            if not filename.lower().endswith(('.jpg', '.jpeg')):
                filename = f"{p.stem}.jpg"
    except Exception:
        pass

    try:
        with open(upload_path, "rb") as f:
            img_bytes = f.read()

        img_size_mb = len(img_bytes) / (1024 * 1024)
        adaptive_timeout = max(90, int(img_size_mb * 30))

        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        body = bytearray()

        # Field: filename
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="filename"\r\n\r\n')
        body.extend(f"{filename}\r\n".encode("utf-8"))

        # Field: file
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(img_bytes)
        body.extend(b"\r\n")

        # Closing boundary
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

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
                try:
                    with urllib.request.urlopen(req, timeout=adaptive_timeout, context=ctx) as response:
                        resp_data = json.loads(response.read().decode("utf-8"))
                        if response.status in (200, 201) and resp_data.get("success", True):
                            image_url = resp_data.get("url", f"{base_url}/image/{filename}")
                            return True, image_url, filename
                        else:
                            return False, resp_data.get("detail", resp_data.get("message", "خطا در آپلود تصویر")), filename
                except urllib.error.HTTPError as http_err:
                    # Fallback to /api/video/upload which also handles images
                    if http_err.code == 404:
                        fallback_endpoint = f"{base_url}/api/video/upload"
                        fallback_req = urllib.request.Request(fallback_endpoint, data=bytes(body), method="POST")
                        fallback_req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
                        fallback_req.add_header("X-API-Key", config.CLOUD_BACKUP_SECRET_KEY)
                        fallback_req.add_header("User-Agent", f"YaldaGymDesktop/{config.APP_VERSION}")
                        fallback_req.add_header("Connection", "close")
                        with urllib.request.urlopen(fallback_req, timeout=adaptive_timeout, context=ctx) as response:
                            resp_data = json.loads(response.read().decode("utf-8"))
                            if response.status in (200, 201) and resp_data.get("success", True):
                                image_url = resp_data.get("url", f"{base_url}/image/{filename}")
                                return True, image_url, filename
                    raise http_err

            except urllib.error.HTTPError as e:
                if e.code in (502, 503, 504) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                try:
                    err_data = json.loads(e.read().decode("utf-8"))
                    msg = err_data.get("detail", err_data.get("message", f"خطای سرور: {e.code}"))
                except Exception:
                    msg = f"خطای سرور ابری (کد {e.code})"
                return False, msg, filename
            except Exception as e:
                last_exc = e
                if _is_transient_network_error(e) and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                break

        if last_exc:
            return False, _format_network_error_message(last_exc), filename
        return False, "خطا در ارسال تصویر به سرور ابری", filename
    finally:
        if temp_img_path and os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception:
                pass


def upload_exercise_media_to_cloud(media_path: str, custom_filename: str = None) -> tuple[bool, str, str]:
    """
    Automatically detects if media_path is video or image and uploads to cloud.
    """
    if not media_path:
        return False, "مسیر رسانه نامعتبر است.", ""
    ext = os.path.splitext(media_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return upload_exercise_video_to_cloud(media_path, custom_filename)
    else:
        return upload_exercise_image_to_cloud(media_path, custom_filename)


def resolve_exercise_media_path(media_path: str) -> str | None:
    """
    Finds and resolves an exercise media file across candidate directories.
    """
    if not media_path:
        return None
    p = Path(media_path)
    if p.exists() and p.is_file():
        return str(p.resolve())

    filename = p.name
    candidate_dirs = [
        config.EXERCISE_MEDIA_DIR,
        config.DATA_DIR / "uploads" / "exercise-media",
        config.APPDATA_DATA_DIR / "uploads" / "exercise-media",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate_dirs.append(Path(local_app_data) / "Programs" / "YaldaGym" / "data" / "uploads" / "exercise-media")

    for d in candidate_dirs:
        try:
            cand = d / filename
            if cand.exists() and cand.is_file():
                return str(cand.resolve())
        except Exception:
            pass
    return None


def is_exercise_media_pending(ex: Exercise) -> bool:
    """
    Determines whether an exercise has a local media file (video or image)
    that needs to be synced/uploaded to the cloud.
    """
    if not ex or not ex.media_path or not str(ex.media_path).strip():
        return False

    actual_path = resolve_exercise_media_path(ex.media_path)
    if not actual_path or not os.path.exists(actual_path):
        return False

    cloud_url = (getattr(ex, "video_cloud_url", "") or "").strip()
    if not cloud_url:
        return True

    from urllib.parse import unquote
    decoded_url = unquote(cloud_url).lower()
    local_stem = Path(actual_path).stem.lower()

    # If the cloud URL doesn't contain the local media stem, it is outdated
    if local_stem not in decoded_url:
        return True

    return False


def is_exercise_video_pending(ex: Exercise) -> bool:
    """Backward compatibility alias for is_exercise_media_pending."""
    return is_exercise_media_pending(ex)


def sync_all_pending_exercise_media(progress_callback=None) -> tuple[int, int, list]:
    """
    Scans all exercises in the database with a local media file (video or image)
    that need cloud synchronization, and uploads them to Cloudflare Worker R2.
    
    progress_callback(current, total, exercise_name) can be provided.
    Returns: (success_count, fail_count, list_of_errors)
    """
    session = get_session()
    try:
        all_exercises = session.query(Exercise).filter(
            Exercise.media_path.isnot(None),
            Exercise.media_path != ""
        ).all()

        pending_exercises = [ex for ex in all_exercises if is_exercise_media_pending(ex)]
        total = len(pending_exercises)
        if total == 0:
            return 0, 0, []

        success_count = 0
        fail_count = 0
        errors = []

        for idx, ex in enumerate(pending_exercises, start=1):
            if progress_callback:
                progress_callback(idx, total, ex.name_fa)

            actual_path = resolve_exercise_media_path(ex.media_path)
            if not actual_path or not os.path.exists(actual_path):
                fail_count += 1
                errors.append(f"فایل رسانه برای حرکت «{ex.name_fa}» یافت نشد.")
                continue

            success, res_url, fname = upload_exercise_media_to_cloud(actual_path)
            if success:
                ex.video_cloud_url = res_url
                if not ex.video_url or "workers.dev" in ex.video_url:
                    ex.video_url = res_url
                session.commit()
                mark_data_changed()
                success_count += 1
            else:
                fail_count += 1
                errors.append(f"خطا در آپلود حرکت «{ex.name_fa}»: {res_url}")

        return success_count, fail_count, errors
    finally:
        session.close()


def sync_all_pending_exercise_videos(progress_callback=None) -> tuple[int, int, list]:
    """Backward compatibility alias for sync_all_pending_exercise_media."""
    return sync_all_pending_exercise_media(progress_callback=progress_callback)


def get_pending_sync_count() -> int:
    """
    Returns the count of exercises that have a local media file (video or image) needing cloud sync.
    """
    session = get_session()
    try:
        exercises = session.query(Exercise).filter(
            Exercise.media_path.isnot(None),
            Exercise.media_path != ""
        ).all()
        return sum(1 for ex in exercises if is_exercise_media_pending(ex))
    except Exception:
        return 0
    finally:
        session.close()


def check_internet_connection(timeout: float = 3.0) -> bool:
    """
    Reliably verifies active internet connectivity by probing cloud server or DNS HTTPS endpoints.
    Safe against local proxy/DNS spoofing and never raises uncaught exceptions.
    """
    import urllib.request
    import urllib.error
    import ssl

    test_urls = [
        config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/"),
        "https://1.1.1.1",
        "https://www.google.com"
    ]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url in test_urls:
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", f"YaldaGymNetCheck/{config.APP_VERSION}")
            with urllib.request.urlopen(req, timeout=timeout, context=ctx):
                return True
        except urllib.error.HTTPError:
            # Reached the remote web server (status 200..499 proves internet is alive)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        except Exception:
            continue

    return False
