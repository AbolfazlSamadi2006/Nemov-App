import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Base Setup
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "server_data" / "backups"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SECRET_API_KEY = os.environ.get("YALDA_API_KEY", "yalda_cloud_sec_2006_gym")
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "2006")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "super_secret_session_key_yalda_2006")

app = FastAPI(title="Yalda Gym Cloud Backup Server", version="v3.0.0")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Simple Gregorian to Shamsi converter for server
def to_shamsi(dt: datetime) -> str:
    # Approximate or accurate conversion
    g_y, g_m, g_d = dt.year, dt.month, dt.day
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (g_y % 4 == 0 and g_y % 100 != 0) or (g_y % 400 == 0):
        g_days_in_month[1] = 29
    gy = g_y - 1600
    gm = g_m - 1
    gd = g_d - 1
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    g_day_no += gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    for i in range(11):
        days_in_j_month = 31 if i < 6 else 30
        if j_day_no < days_in_j_month:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= days_in_j_month
    else:
        jm = 12
        jd = j_day_no + 1
    return f"{jy:04d}/{jm:02d}/{jd:02d} {dt.strftime('%H:%M')}"


# ==============================================================================
# API Endpoints (For Desktop App)
# ==============================================================================

@app.post("/api/backup/upload")
async def upload_backup(
    phone: str = Form(...),
    trainer_name: str = Form(""),
    file: UploadFile = File(...),
    x_api_key: str = Header(None)
):
    if x_api_key != SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="کلید امنیتی سرور نامعتبر است.")

    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone:
        raise HTTPException(status_code=400, detail="شماره موبایل مربی نامعتبر است.")

    trainer_dir = STORAGE_DIR / clean_phone
    trainer_dir.mkdir(parents=True, exist_ok=True)
    db_file_path = trainer_dir / "yalda.db"

    # Save and overwrite previous database file
    with open(db_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_mb = round(os.path.getsize(db_file_path) / (1024 * 1024), 2)
    now = datetime.now()

    meta = {
        "phone": clean_phone,
        "trainer_name": trainer_name or "مربی",
        "last_backup_iso": now.isoformat(),
        "last_backup_shamsi": to_shamsi(now),
        "file_size_mb": file_size_mb,
        "filename": "yalda.db"
    }

    with open(trainer_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "message": f"نسخه پشتیبان مربی با موفقیت در سرور ذخیره شد (حجم: {file_size_mb} MB)",
        "timestamp": meta["last_backup_shamsi"]
    }


@app.get("/api/backup/download/{phone}")
async def download_backup(phone: str, x_api_key: str = Header(None), req: Request = None):
    # Allow either API key header or logged in admin session
    is_admin = req and req.session.get("is_admin")
    if not is_admin and x_api_key != SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="دسترسی غیرمجاز")

    clean_phone = "".join(filter(str.isdigit, phone))
    db_file_path = STORAGE_DIR / clean_phone / "yalda.db"

    if not db_file_path.exists():
        raise HTTPException(status_code=404, detail="نسخه پشتیبان برای این مربی یافت نشد.")

    return FileResponse(
        path=str(db_file_path),
        filename=f"yalda_{clean_phone}.db",
        media_type="application/octet-stream"
    )


# ==============================================================================
# Web Admin Dashboard (For Master Admin)
# ==============================================================================

def get_all_trainers_metadata():
    trainers = []
    total_size = 0.0
    for folder in STORAGE_DIR.iterdir():
        if folder.is_dir():
            meta_path = folder / "metadata.json"
            db_path = folder / "yalda.db"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    trainers.append(data)
                    total_size += data.get("file_size_mb", 0.0)
                except Exception:
                    pass
            elif db_path.exists():
                size = round(os.path.getsize(db_path) / (1024 * 1024), 2)
                trainers.append({
                    "phone": folder.name,
                    "trainer_name": "نامشخص",
                    "last_backup_shamsi": "-",
                    "file_size_mb": size
                })
                total_size += size

    trainers.sort(key=lambda x: x.get("last_backup_iso", ""), reverse=True)
    return trainers, round(total_size, 2)


@app.get("/", response_class=HTMLResponse)
async def home_dashboard(request: Request):
    if not request.session.get("is_admin"):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

    trainers, total_size = get_all_trainers_metadata()
    last_activity = trainers[0]["last_backup_shamsi"] if trainers else "هنوز ثبتی انجام نشده"

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "trainers": trainers,
            "total_trainers": len(trainers),
            "total_size_mb": total_size,
            "last_activity": last_activity
        }
    )


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "نام کاربری یا رمز عبور اشتباه است."}
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/backup/delete/{phone}")
async def delete_trainer_backup(phone: str, request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="دسترسی غیرمجاز")
    clean_phone = "".join(filter(str.isdigit, phone))
    trainer_dir = STORAGE_DIR / clean_phone
    if trainer_dir.exists():
        shutil.rmtree(trainer_dir)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)