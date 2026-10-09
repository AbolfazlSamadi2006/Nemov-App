import os
from pathlib import Path

import sys
import shutil

# Base directories
BASE_DIR = Path(__file__).resolve().parent

# AppData persistent path
APPDATA_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "YaldaGym" / "data"
APPDATA_DATA_DIR.mkdir(parents=True, exist_ok=True)

if getattr(sys, 'frozen', False):
    # Running as compiled PyInstaller EXE: place data folder right next to Yalda.exe
    EXE_DIR = Path(sys.executable).resolve().parent
    DATA_DIR = EXE_DIR / "data"
else:
    # Running as source python
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def sync_data_directories():
    """Finds the latest yalda.db across runtime data folder, backups folder, and persistent AppData folder to guarantee zero data loss."""
    candidate_locations = [
        DATA_DIR,
        APPDATA_DATA_DIR
    ]
    
    db_candidates = []
    for loc in candidate_locations:
        db_p = loc / "yalda.db"
        if db_p.exists() and db_p.stat().st_size > 0:
            db_candidates.append((db_p.stat().st_mtime, db_p, loc))
        # Also check latest_backup.db inside backups/
        backup_p = loc / "backups" / "latest_backup.db"
        if backup_p.exists() and backup_p.stat().st_size > 0:
            db_candidates.append((backup_p.stat().st_mtime, backup_p, loc))
            
    if db_candidates:
        db_candidates.sort(key=lambda x: x[0], reverse=True)
        latest_mtime, latest_db, latest_loc = db_candidates[0]
        
        # Mirror latest DB to all candidate locations
        for target_loc in candidate_locations:
            target_loc.mkdir(parents=True, exist_ok=True)
            target_db = target_loc / "yalda.db"
            if not target_db.exists() or target_db.stat().st_mtime < latest_mtime:
                try:
                    shutil.copy2(latest_db, target_db)
                except Exception:
                    pass
            
            # Mirror uploads folder
            src_uploads = latest_loc / "uploads"
            tgt_uploads = target_loc / "uploads"
            if src_uploads.exists():
                for item in src_uploads.rglob("*"):
                    if item.is_file():
                        try:
                            rel_p = item.relative_to(src_uploads)
                            dest_p = tgt_uploads / rel_p
                            dest_p.parent.mkdir(parents=True, exist_ok=True)
                            if not dest_p.exists() or dest_p.stat().st_mtime < item.stat().st_mtime:
                                shutil.copy2(item, dest_p)
                        except Exception:
                            pass

# Execute initial sync
sync_data_directories()

# Sub-directories for uploads and data
UPLOADS_DIR = DATA_DIR / "uploads"
PROFILE_PHOTOS_DIR = UPLOADS_DIR / "profile-photos"
PROGRESS_PHOTOS_DIR = UPLOADS_DIR / "progress-photos"
EXERCISE_MEDIA_DIR = UPLOADS_DIR / "exercise-media"
PDF_EXPORTS_DIR = DATA_DIR / "pdf"
BACKUPS_DIR = DATA_DIR / "backups"

for folder in [UPLOADS_DIR, PROFILE_PHOTOS_DIR, PROGRESS_PHOTOS_DIR, EXERCISE_MEDIA_DIR, PDF_EXPORTS_DIR, BACKUPS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database URI
DB_PATH = DATA_DIR / "yalda.db"
DATABASE_URI = f"sqlite:///{DB_PATH}"



# App Details
APP_NAME = "یلدا"
APP_ENGLISH_NAME = "Yalda Gym"
APP_VERSION = "v3.2.1"
GYM_ADDRESS = "باشگاه بدنسازی یلدا | مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳"




# Styling & Colors (Dark Red & Black Theme)
COLOR_BACKGROUND = "#121212"
COLOR_SURFACE = "#1E1E1E"
COLOR_SURFACE_LIGHT = "#2D2D2D"
COLOR_PRIMARY_ACCENT = "#8B0000"      # Dark Red
COLOR_PRIMARY_ACCENT_HOVER = "#A91D22" # Lighter Dark Red
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#B0B0B0"
COLOR_SUCCESS = "#2E7D32"
COLOR_WARNING = "#F57C00"
COLOR_ERROR = "#D32F2F"
COLOR_BORDER = "#333333"

# Fonts
FONT_FAMILY = "Vazirmatn"

# Cloud Backup Server Settings
DEFAULT_CLOUD_BACKUP_URL = os.environ.get("YALDA_CLOUD_URL", "https://storage.gymassistantapp.ir")
CLOUD_BACKUP_SECRET_KEY = "yalda_cloud_sec_2006_gym"

# Support Email Settings (Gmail SMTP)
SUPPORT_EMAIL_ADDRESS = "gymassistantapp.support@gmail.com"
SUPPORT_EMAIL_APP_PASSWORD = "xngruboohbruxqwk"
SUPPORT_EMAIL_SENDER_NAME = "پشتیبانی نرم افزار همیار باشگاه یلدا"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT_SSL = 465
SMTP_PORT_TLS = 587

