import os
import re
import time
import hmac
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote

import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from db import DatabaseManager, to_shamsi
from s3_storage import ArvanS3Storage
from templates_renderer import (
    LANDING_HTML,
    render_login_page,
    render_dashboard_page,
    render_video_player,
    render_image_viewer,
    render_not_found_page,
    resolve_exercise_title,
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

PRIMARY_SECRET_API_KEY = os.environ.get("NEMOV_API_KEY", "nemov_cloud_security")
LEGACY_SECRET_API_KEY = os.environ.get("YALDA_API_KEY", "yalda_cloud_sec_2006_gym")
VALID_API_KEYS = {PRIMARY_SECRET_API_KEY, LEGACY_SECRET_API_KEY, "nemov_cloud_security", "yalda_cloud_sec_2006_gym"}

ADMIN_USER = os.environ.get("ADMIN_USER", "Abolfazl")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "Abolfazl2006")
AUTH_COOKIE_NAME = "nemov_admin_session"
LEGACY_AUTH_COOKIE_NAME = "yalda_admin_session"
AUTH_SECRET_TOKEN = os.environ.get("SESSION_SECRET", "nemov_auth_token_secret_2006_gym")
LEGACY_AUTH_SECRET_TOKEN = "yalda_auth_token_secret_2006_gym"

SMS_API_KEY = os.environ.get("SMS_API_KEY", "").strip()
SMS_LINE_NUMBER = os.environ.get("SMS_LINE_NUMBER", "").strip()

db = DatabaseManager()
s3 = ArvanS3Storage()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print(f"[STARTUP] Initializing Nemov Cloud Server (PG={db.use_pg}, S3={s3.is_configured()})", flush=True)
    db.safe_init_and_seed()
    yield


app = FastAPI(title="Nemov Cloud Server", version="3.4.4", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_persian_digits(val) -> str:
    if val is None:
        return ""
    s = str(val)
    return s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def clean_phone(val) -> str:
    return re.sub(r"\D", "", normalize_persian_digits(val))


def timing_safe_equal(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def check_api_key(api_key: str | None) -> bool:
    if not api_key:
        return False
    return any(timing_safe_equal(api_key, k) for k in VALID_API_KEYS)


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME) or request.cookies.get(LEGACY_AUTH_COOKIE_NAME)
    return timing_safe_equal(token, AUTH_SECRET_TOKEN) or timing_safe_equal(token, LEGACY_AUTH_SECRET_TOKEN)


def is_admin_subdomain(hostname: str) -> bool:
    h = (hostname or "").lower()
    prefixes = ("admin.", "panel.", "dashboard.", "cloud.", "backup.", "backups.", "storage.", "messages.", "sms.", "gym.")
    return any(h.startswith(p) for p in prefixes)


def get_origin(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme or "https")
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "nemovapp.ir"))
    return f"{proto}://{host}"


# ------------------------------------------------------------------
# Health & Static Assets
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "db_mode": "postgresql" if db.use_pg else "sqlite_fallback",
        "db_error": db.last_error or None,
        "s3_configured": s3.is_configured(),
        "s3_bucket": s3.bucket,
    }


@app.get("/fonts/bkoodak.woff2")
@app.get("/fonts/BKoodak.woff2")
def serve_font():
    return FileResponse(
        ASSETS_DIR / "bkoodak.woff2",
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/images/nemov_logo.png")
@app.get("/nemov_logo.png")
@app.get("/images/logo.png")
@app.get("/favicon.ico")
def serve_nemov_logo():
    return FileResponse(
        ASSETS_DIR / "nemov_logo.png",
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/images/yalda_logo.jpg")
@app.get("/yalda_logo.jpg")
@app.get("/logo.jpg")
def serve_yalda_logo():
    return FileResponse(
        ASSETS_DIR / "yalda_logo.jpg",
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/images/developer_photo.jpg")
@app.get("/developer_photo.jpg")
@app.get("/images/developer.jpg")
@app.get("/developer.jpg")
def serve_dev_photo():
    return FileResponse(
        ASSETS_DIR / "developer_photo.jpg",
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/robots.txt")
def robots():
    body = "User-agent: *\nAllow: /\nDisallow: /dashboard\nDisallow: /login\nDisallow: /api/\n\nSitemap: https://nemovapp.ir/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")


@app.get("/sitemap.xml")
def sitemap():
    body = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://nemovapp.ir/</loc>
    <lastmod>2026-11-25</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return Response(content=body, media_type="application/xml")


# ------------------------------------------------------------------
# Authentication & Landing / Dashboard Pages
# ------------------------------------------------------------------
@app.get("/landing", response_class=HTMLResponse)
def landing_page():
    return HTMLResponse(content=LANDING_HTML)


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if is_authenticated(request):
        dest = "/" if is_admin_subdomain(request.url.hostname) else "/dashboard"
        return RedirectResponse(url=dest, status_code=302)
    return HTMLResponse(content=render_login_page())


@app.post("/login")
async def login_post(request: Request, username: str = Form(""), password: str = Form("")):
    if timing_safe_equal(username, ADMIN_USER) and timing_safe_equal(password, ADMIN_PASS):
        dest = "/" if is_admin_subdomain(request.url.hostname) else "/dashboard"
        resp = RedirectResponse(url=dest, status_code=303)
        resp.set_cookie(AUTH_COOKIE_NAME, AUTH_SECRET_TOKEN, httponly=True, max_age=86400 * 7, path="/", samesite="lax")
        return resp
    return HTMLResponse(content=render_login_page("نام کاربری یا رمز عبور اشتباه است."), status_code=401)


@app.get("/logout")
def logout(request: Request):
    dest = "/" if is_admin_subdomain(request.url.hostname) else "/login"
    resp = RedirectResponse(url=dest, status_code=302)
    resp.delete_cookie(AUTH_COOKIE_NAME, path="/")
    resp.delete_cookie(LEGACY_AUTH_COOKIE_NAME, path="/")
    return resp


def _render_dashboard_response(request: Request) -> HTMLResponse:
    trainers = db.get_all_backups()
    total_size = sum(float(t.get("file_size_mb", 0) or 0) for t in trainers)
    last_activity = trainers[0].get("last_backup_shamsi", "-") if trainers else "هنوز ثبتی انجام نشده"

    origin_url = get_origin(request)
    media_list, total_media_mb = s3.list_media(origin_url=origin_url)

    sms_list = db.get_all_sms_accounts()
    total_sms_rem = sum(int(s.get("remaining", 0) or 0) for s in sms_list)
    total_sms_sent = sum(int(s.get("total_used", 0) or 0) for s in sms_list)
    sms_logs = db.get_sms_logs(limit=50)

    host = (request.url.hostname or "").lower()
    tab_param = request.query_params.get("tab", "")
    default_tab = "backups"
    if host.startswith(("messages.", "sms.")) or tab_param == "messages":
        default_tab = "messages"
    elif host.startswith("storage.") or tab_param == "media":
        default_tab = "media"

    html_content = render_dashboard_page(
        trainers=trainers,
        total_size_mb=f"{total_size:.2f}",
        last_activity=last_activity,
        media_list=media_list,
        total_media_size_mb=total_media_mb,
        default_tab=default_tab,
        origin_url=origin_url,
        sms_list=sms_list,
        total_sms_remaining=total_sms_rem,
        total_sms_sent=total_sms_sent,
        sms_logs=sms_logs,
    )
    return HTMLResponse(content=html_content)


@app.get("/")
def root(request: Request):
    host = (request.url.hostname or "").lower()
    if not is_admin_subdomain(host) and not request.query_params.get("tab"):
        return HTMLResponse(content=LANDING_HTML)
    if not is_authenticated(request):
        return HTMLResponse(content=render_login_page())
    return _render_dashboard_response(request)


@app.get("/dashboard")
@app.get("/dashboard/")
def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return _render_dashboard_response(request)


# ------------------------------------------------------------------
# Backup API Endpoints
# ------------------------------------------------------------------
@app.post("/api/backup/upload")
async def api_backup_upload(
    request: Request,
    phone: str = Form(""),
    trainer_name: str = Form("مربی"),
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    if not check_api_key(x_api_key):
        return JSONResponse({"success": False, "detail": "کلید امنیتی سرور نامعتبر است."}, status_code=401)
    p = clean_phone(phone)
    if not p:
        return JSONResponse({"success": False, "detail": "شماره مربی نامعتبر است."}, status_code=400)

    data = await file.read()
    size_mb = round(len(data) / (1024 * 1024), 2)
    now_iso = datetime.now(timezone.utc).isoformat()
    shamsi_dt = to_shamsi()

    try:
        s3.upload_backup(p, data)
        db.upsert_backup(p, trainer_name or "مربی", now_iso, shamsi_dt, size_mb)
        return JSONResponse({
            "success": True,
            "message": f"نسخه پشتیبان با موفقیت در سرور ابری ذخیره شد (حجم: {size_mb:.2f} MB)",
            "timestamp": shamsi_dt,
        })
    except Exception as e:
        return JSONResponse({"success": False, "detail": f"خطا در ذخیره فایل: {e}"}, status_code=500)


@app.get("/api/backup/download/{phone_raw}")
def api_backup_download(phone_raw: str, request: Request, x_api_key: str | None = Header(default=None)):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return Response("دسترسی غیرمجاز", status_code=401)
    p = clean_phone(phone_raw)
    data = s3.download_backup(p)
    if data is None:
        return Response("فایل پشتیبان برای این مربی در مخزن ابری یافت نشد.", status_code=404)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="nemov_{p}.db"'},
    )


@app.post("/api/backup/delete/{phone_raw}")
@app.delete("/api/backup/delete/{phone_raw}")
def api_backup_delete(phone_raw: str, request: Request, x_api_key: str | None = Header(default=None)):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return JSONResponse({"success": False, "detail": "دسترسی غیرمجاز"}, status_code=401)
    p = clean_phone(phone_raw)
    s3.delete_backup(p)
    db.delete_backup(p)
    if request.method == "DELETE" or x_api_key or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True, "message": "حساب پشتیبان با موفقیت حذف شد."})
    return RedirectResponse(url="/dashboard?tab=backups", status_code=303)


# ------------------------------------------------------------------
# Media Endpoints (ArvanCloud Object Storage)
# ------------------------------------------------------------------
@app.post("/api/video/upload")
@app.post("/api/image/upload")
@app.post("/api/media/upload")
async def api_media_upload(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(""),
    x_api_key: str | None = Header(default=None),
):
    if not check_api_key(x_api_key):
        return JSONResponse({"success": False, "detail": "کلید امنیتی سرور نامعتبر است."}, status_code=401)

    fn = (filename or file.filename or "media.mp4").strip()
    ext = fn.split(".")[-1].lower() if "." in fn else "mp4"
    is_image = ext in ("jpg", "jpeg", "png", "webp", "bmp", "gif") or "/image/" in str(request.url.path)
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "webp": "image/webp", "bmp": "image/bmp", "gif": "image/gif",
        "mp4": "video/mp4", "webm": "video/webm", "ogg": "video/ogg", "mov": "video/quicktime", "m4v": "video/mp4",
    }
    ctype = mime_map.get(ext, "image/jpeg" if is_image else "video/mp4")

    data = await file.read()
    size_mb = round(len(data) / (1024 * 1024), 2)
    s3.upload_media(fn, data, ctype, is_image=is_image)

    origin = get_origin(request)
    media_url = f"{origin}/{'image' if is_image else 'video'}/{fn}"
    return JSONResponse({
        "success": True,
        "message": "فایل با موفقیت در ابر آروان ذخیره شد.",
        "url": media_url,
        "filename": fn,
        "size_mb": size_mb,
    })


@app.post("/api/media/delete")
async def api_media_delete_form(
    request: Request,
    filename: str = Form(""),
    type: str = Form(""),
    x_api_key: str | None = Header(default=None),
):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return Response("دسترسی غیرمجاز", status_code=401)
    is_img = True if type == "image" else (False if type == "video" else None)
    if filename:
        s3.delete_media(filename, is_image=is_img)
    return RedirectResponse(url="/dashboard?tab=media", status_code=303)


@app.post("/api/media/delete/{filename_raw:path}")
@app.delete("/api/media/delete/{filename_raw:path}")
def api_media_delete_path(filename_raw: str, request: Request, x_api_key: str | None = Header(default=None)):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return JSONResponse({"success": False, "detail": "دسترسی غیرمجاز"}, status_code=401)
    fn = unquote(filename_raw)
    s3.delete_media(fn, is_image=None)
    return JSONResponse({"success": True, "message": "رسانه حذف شد."})


@app.api_route("/video/{filename_raw:path}", methods=["GET", "HEAD"])
def serve_video(filename_raw: str, request: Request):
    fn = unquote(filename_raw)
    ext = fn.split(".")[-1].lower() if "." in fn else ""
    if ext in ("jpg", "jpeg", "png", "webp", "bmp", "gif"):
        return RedirectResponse(url=f"/image/{fn}", status_code=302)

    accept = request.headers.get("accept", "")
    is_raw = (
        request.query_params.get("raw") == "1"
        or request.query_params.get("download") == "1"
        or request.method == "HEAD"
        or ("text/html" not in accept and len(accept) > 0 and "play" not in request.query_params)
    )
    arvan_url = s3.get_public_media_url(fn, is_image=False)
    if is_raw:
        return RedirectResponse(url=arvan_url, status_code=302)

    if not s3.head_media(fn, is_image=False):
        return HTMLResponse(
            content=render_not_found_page("ویدیو یافت نشد", "فایل ویدیویی درخواستی در فضای ابری آروان موجود نیست."),
            status_code=404,
        )
    title = resolve_exercise_title(fn, request.query_params.get("title"))
    return HTMLResponse(content=render_video_player(title=title, stream_url=arvan_url, filename=fn))


@app.api_route("/image/{filename_raw:path}", methods=["GET", "HEAD"])
def serve_image(filename_raw: str, request: Request):
    fn = unquote(filename_raw)
    accept = request.headers.get("accept", "")
    is_raw = (
        request.query_params.get("raw") == "1"
        or request.query_params.get("download") == "1"
        or request.method == "HEAD"
        or ("text/html" not in accept and len(accept) > 0 and "play" not in request.query_params)
    )
    arvan_url = s3.get_public_media_url(fn, is_image=True)
    if is_raw:
        return RedirectResponse(url=arvan_url, status_code=302)

    if not s3.head_media(fn, is_image=True):
        return HTMLResponse(
            content=render_not_found_page("تصویر یافت نشد", "تصویر درخواستی در فضای ابری آروان موجود نیست."),
            status_code=404,
        )
    title = resolve_exercise_title(fn, request.query_params.get("title"))
    return HTMLResponse(content=render_image_viewer(title=title, image_url=arvan_url))


# ------------------------------------------------------------------
# SMS Management Endpoints (PostgreSQL + SMS.ir)
# ------------------------------------------------------------------
@app.post("/api/admin/sms/recharge")
async def api_admin_sms_recharge(request: Request, x_api_key: str | None = Header(default=None)):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return JSONResponse({"success": False, "detail": "دسترسی غیرمجاز"}, status_code=401)

    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        body = await request.json()
        phone_raw = body.get("phone", "")
        trainer_name = body.get("trainer_name", "مربی")
        amount_raw = body.get("amount", 0)
    else:
        form = await request.form()
        phone_raw = form.get("phone", "")
        trainer_name = form.get("trainer_name", "مربی")
        amount_raw = form.get("amount", 0)

    p = clean_phone(phone_raw)
    try:
        amount = int(normalize_persian_digits(amount_raw or "0"))
    except ValueError:
        amount = 0

    if not p or amount <= 0 or amount > 1000000:
        return JSONResponse({"success": False, "detail": "اطلاعات مربی یا تعداد پیامک نامعتبر است."}, status_code=400)

    acc = db.get_sms_account(p) or {
        "phone": p,
        "trainer_name": trainer_name or "مربی",
        "remaining": 0,
        "total_credited": 0,
        "total_used": 0,
        "status": "active",
        "registered_at_shamsi": to_shamsi(),
    }
    if trainer_name and trainer_name != "مربی":
        acc["trainer_name"] = trainer_name
    acc["remaining"] = int(acc.get("remaining", 0)) + amount
    acc["total_credited"] = int(acc.get("total_credited", 0)) + amount
    acc["last_recharge_shamsi"] = to_shamsi()
    acc["status"] = "active"
    db.upsert_sms_account(acc)

    if x_api_key or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True, "message": "شارژ پیامک با موفقیت انجام شد.", "remaining": acc["remaining"]})
    return RedirectResponse(url="/dashboard?tab=messages&recharged=1", status_code=303)


@app.post("/api/admin/sms/delete/{phone_raw}")
def api_admin_sms_delete(phone_raw: str, request: Request, x_api_key: str | None = Header(default=None)):
    if not (is_authenticated(request) or check_api_key(x_api_key)):
        return JSONResponse({"success": False, "detail": "دسترسی غیرمجاز"}, status_code=401)
    p = clean_phone(phone_raw)
    if p:
        db.delete_sms_account(p)
    if x_api_key or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True, "message": "حساب پیامکی مربی با موفقیت حذف شد."})
    return RedirectResponse(url="/dashboard?tab=messages", status_code=303)


@app.get("/api/sms/balance")
def api_sms_balance(phone: str = "", trainer_name: str = "", gym_name: str = ""):
    p = clean_phone(phone)
    if not p:
        return JSONResponse({"success": False, "detail": "شماره موبایل مربی ارسال نشده است."}, status_code=400)

    acc = db.get_sms_account(p)
    if not acc:
        acc = {
            "phone": p,
            "trainer_name": trainer_name or "مربی باشگاه",
            "gym_name": gym_name or "نرم‌افزار مدیریت ورزشی نِمُو",
            "remaining": 0,
            "total_credited": 0,
            "total_used": 0,
            "status": "pending",
            "registered_at_shamsi": to_shamsi(),
            "last_recharge_shamsi": "-",
        }
        db.upsert_sms_account(acc)
    elif trainer_name and trainer_name not in ("مربی", "مدیر سیستم") and acc.get("trainer_name") != trainer_name:
        acc["trainer_name"] = trainer_name
        db.upsert_sms_account(acc)

    rem = int(acc.get("remaining", 0) or 0)
    tot = int(acc.get("total_credited", 0) or 0)
    status = "active" if rem > 0 else ("pending" if tot == 0 else "depleted")
    return JSONResponse({
        "success": True,
        "phone": acc["phone"],
        "trainer_name": acc.get("trainer_name", ""),
        "remaining": rem,
        "total_credited": tot,
        "total_used": int(acc.get("total_used", 0) or 0),
        "status": status,
        "last_recharge_shamsi": acc.get("last_recharge_shamsi", "-"),
    })


@app.post("/api/sms/register")
async def api_sms_register(request: Request):
    body = await request.json()
    p = clean_phone(body.get("phone", ""))
    if not p:
        return JSONResponse({"success": False, "detail": "شماره موبایل نامعتبر است."}, status_code=400)
    tname = body.get("trainer_name") or "مربی باشگاه"
    gname = body.get("gym_name") or "نرم‌افزار مدیریت ورزشی نِمُو"
    acc = db.get_sms_account(p)
    if not acc:
        acc = {
            "phone": p, "trainer_name": tname, "gym_name": gname,
            "remaining": 0, "total_credited": 0, "total_used": 0,
            "status": "pending", "registered_at_shamsi": to_shamsi(), "last_recharge_shamsi": "-",
        }
        db.upsert_sms_account(acc)
    elif tname and acc.get("trainer_name") != tname:
        acc["trainer_name"] = tname
        db.upsert_sms_account(acc)

    return JSONResponse({
        "success": True,
        "phone": p,
        "trainer_name": acc.get("trainer_name", tname),
        "remaining": acc.get("remaining", 0),
        "status": "active" if (acc.get("remaining", 0) or 0) > 0 else "pending",
        "message": "مشخصات شما با موفقیت در سامانه پیامکی ثبت شد.",
    })


@app.post("/api/sms/send")
async def api_sms_send(request: Request, x_api_key: str | None = Header(default=None)):
    if not check_api_key(x_api_key):
        return JSONResponse({"success": False, "detail": "کلید امنیتی سرور نامعتبر است."}, status_code=401)

    body = await request.json()
    p = clean_phone(body.get("phone", ""))
    recipient = clean_phone(body.get("recipient", ""))
    if recipient.startswith("0098"):
        recipient = "0" + recipient[4:]
    elif recipient.startswith("98") and len(recipient) == 12:
        recipient = "0" + recipient[2:]
    elif recipient.startswith("9") and len(recipient) == 10:
        recipient = "0" + recipient

    if not p or not recipient:
        return JSONResponse({"success": False, "detail": "شماره فرستنده یا گیرنده نامعتبر است."}, status_code=400)

    acc = db.get_sms_account(p)
    if not acc or int(acc.get("remaining", 0) or 0) <= 0:
        return JSONResponse({
            "success": False,
            "remaining": 0,
            "detail": "اعتبار بسته پیامک شما به پایان رسیده است. جهت خرید یا شارژ مجدد با مدیریت تماس بگیرید.",
        }, status_code=402)

    template_id = body.get("template_id")
    parameters = body.get("parameters") or []
    message_text = body.get("message_text") or ""
    trainer_name = body.get("trainer_name") or "مربی"
    member_name = body.get("member_name") or "ورزشکار"
    msg_type = body.get("type") or "custom"

    sms_success = False
    sms_detail = ""

    if SMS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if template_id:
                    sanitized_params = [
                        {
                            "name": str(param.get("name", "")).strip(),
                            "value": str(param.get("value") if param.get("value") not in (None, "") else "-").strip(),
                        }
                        for param in parameters
                        if isinstance(param, dict)
                    ]
                    res = await client.post(
                        "https://api.sms.ir/v1/send/verify",
                        headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-KEY": SMS_API_KEY},
                        json={"mobile": recipient, "templateId": int(template_id), "parameters": sanitized_params},
                    )
                    rj = res.json()
                    if res.status_code == 200 and rj.get("status") in (1, 200):
                        sms_success = True
                        sms_detail = "ارسال موفق از طریق الگوی خدماتی SMS.ir"
                    else:
                        sms_detail = rj.get("message") or f"خطای درگاه پیامک: {res.status_code}"
                else:
                    res = await client.post(
                        "https://api.sms.ir/v1/send/bulk",
                        headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-KEY": SMS_API_KEY},
                        json={"lineNumber": SMS_LINE_NUMBER, "messageText": message_text, "mobiles": [recipient]},
                    )
                    rj = res.json()
                    if res.status_code == 200 and rj.get("status") in (1, 200):
                        sms_success = True
                        sms_detail = "ارسال موفق پیامک متنی"
                    else:
                        sms_detail = rj.get("message") or f"خطای خط پیامک: {res.status_code}"
        except Exception as exc:
            sms_detail = f"خطا در اتصال به درگاه پیامک: {exc}"
    else:
        sms_success = True
        sms_detail = "ارسال آزمایشی موفق (شبیه‌ساز پیامک فعال است - SMS_API_KEY تنظیم نشده)"

    if sms_success:
        acc["remaining"] = max(0, int(acc.get("remaining", 0)) - 1)
        acc["total_used"] = int(acc.get("total_used", 0)) + 1
        db.upsert_sms_account(acc)
        db.add_sms_log({
            "id": f"sms_{int(time.time() * 1000)}",
            "date_shamsi": to_shamsi(),
            "trainer_name": trainer_name,
            "trainer_phone": p,
            "recipient": recipient,
            "member_name": member_name,
            "type": msg_type,
            "detail": sms_detail,
        })
        return JSONResponse({
            "success": True,
            "remaining": acc["remaining"],
            "message": "پیامک با موفقیت ارسال شد.",
            "detail": sms_detail,
        })

    return JSONResponse({
        "success": False,
        "remaining": acc.get("remaining", 0),
        "detail": sms_detail or "ارسال پیامک با خطا مواجه شد.",
    }, status_code=502)


@app.get("/api/sms/history")
def api_sms_history(phone: str = ""):
    p = clean_phone(phone)
    logs = db.get_sms_logs(phone=p if p else None, limit=100)
    return JSONResponse({"success": True, "logs": logs})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
