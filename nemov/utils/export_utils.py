import os
import re
import json
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog
import config

SETTINGS_FILE = config.DATA_DIR / "export_settings.json"

def get_last_base_export_dir() -> str:
    """Returns the last used parent directory for athlete exports."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                p = data.get("last_base_export_dir")
                if p and os.path.exists(p):
                    return p
    except Exception:
        pass
    docs = Path.home() / "Documents"
    if docs.exists():
        return str(docs)
    return str(config.PDF_EXPORTS_DIR)

def set_last_base_export_dir(path: str):
    """Persists the last used parent directory."""
    try:
        data = {}
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["last_base_export_dir"] = path
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def resolve_athlete_export_path(
    member,
    default_filename: str,
    parent_widget,
    dialog_title: str,
    file_filter: str = "PDF Files (*.pdf)"
):
    """
    Resolves or creates a dedicated directory for the given athlete when exporting workout/nutrition plans.
    1. Looks for the athlete's existing dedicated folder in the path chosen by the trainer.
    2. If it does not exist, creates a folder named after the athlete.
    3. Saves all future workout/nutrition files for this athlete directly in that folder.

    Returns:
        (final_filepath, athlete_name) or (None, None) if cancelled.
    """
    # 1. Clean athlete name
    raw_name = ""
    if member:
        raw_name = (getattr(member, 'full_name', None) or f"{getattr(member, 'first_name', '')} {getattr(member, 'last_name', '')}").strip()
    if not raw_name:
        raw_name = "ورزشکار"
    athlete_name = re.sub(r'[\\/*?:"<>|]', '', raw_name).strip() or "ورزشکار"

    # 2. Determine initial directory for file dialog
    initial_dir = None
    saved_folder = getattr(member, 'export_folder_path', None) if member else None
    
    # If not loaded on member object, check database
    if not saved_folder and member and getattr(member, 'id', None):
        try:
            from nemov.database.connection import SessionLocal
            from nemov.models.database_models import Member as DBMember
            with SessionLocal() as db:
                db_m = db.query(DBMember).filter(DBMember.id == member.id).first()
                if db_m and db_m.export_folder_path:
                    saved_folder = db_m.export_folder_path
                    member.export_folder_path = saved_folder
        except Exception:
            pass

    if saved_folder and os.path.exists(saved_folder):
        initial_dir = saved_folder
    else:
        base_dir = get_last_base_export_dir()
        candidate = os.path.join(base_dir, athlete_name)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            initial_dir = candidate
        else:
            initial_dir = base_dir

    initial_filepath = os.path.join(initial_dir, default_filename)

    # 3. Prompt trainer with Save File Dialog
    chosen_path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        dialog_title,
        initial_filepath,
        file_filter
    )

    if not chosen_path:
        return None, None

    # 4. Check if chosen_path is already inside athlete folder or needs folder resolution
    chosen_dir = os.path.dirname(chosen_path)
    chosen_filename = os.path.basename(chosen_path)

    norm_chosen_dir = os.path.normpath(chosen_dir)
    dir_name = os.path.basename(norm_chosen_dir)

    target_folder = None
    if dir_name.strip() == athlete_name:
        # The trainer saved directly inside the athlete's folder
        target_folder = norm_chosen_dir
    else:
        # Check if a folder named after the athlete exists inside chosen_dir
        candidate_subfolder = os.path.join(norm_chosen_dir, athlete_name)
        if os.path.exists(candidate_subfolder) and os.path.isdir(candidate_subfolder):
            target_folder = candidate_subfolder
        else:
            # Create the athlete's folder inside the chosen directory
            os.makedirs(candidate_subfolder, exist_ok=True)
            target_folder = candidate_subfolder

    final_filepath = os.path.join(target_folder, chosen_filename)

    # 5. Remember this folder for this athlete from now on
    if member:
        member.export_folder_path = target_folder
        if getattr(member, 'id', None):
            try:
                from nemov.database.connection import SessionLocal
                from nemov.models.database_models import Member as DBMember
                with SessionLocal() as db:
                    db_m = db.query(DBMember).filter(DBMember.id == member.id).first()
                    if db_m:
                        db_m.export_folder_path = target_folder
                        db.commit()
            except Exception:
                pass

    # 6. Remember the parent directory as the base export directory for future athletes
    parent_base = os.path.dirname(target_folder)
    if parent_base and os.path.exists(parent_base):
        set_last_base_export_dir(parent_base)

    return final_filepath, athlete_name


GYM_FOLDER_NAME = "باشگاه یلدا"


def get_saved_gym_export_folder() -> str:
    """Returns the persisted dedicated gym export folder path if it exists on disk."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                p = data.get("gym_export_folder_path")
                if p and os.path.exists(p) and os.path.isdir(p):
                    return p
    except Exception:
        pass
    return None


def set_saved_gym_export_folder(path: str):
    """Persists the dedicated gym export folder path."""
    try:
        data = {}
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["gym_export_folder_path"] = path
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_gym_export_path(
    default_filename: str,
    parent_widget,
    dialog_title: str,
    file_filter: str = "PDF Files (*.pdf)"
):
    """
    Resolves or creates a dedicated 'باشگاه یلدا' directory for gym-wide exports
    (Financial Excel, Financial PDF, Workout/Nutrition Templates, Local Backups).
    1. Checks if 'باشگاه یلدا' already exists in the path selected by the trainer (or uses the remembered gym folder).
    2. If it exists, saves directly inside that folder.
    3. If it does not exist, creates 'باشگاه یلدا' in the chosen directory and remembers it for all future exports.

    Returns:
        (final_filepath, GYM_FOLDER_NAME) or (None, None) if cancelled.
    """
    saved_gym_folder = get_saved_gym_export_folder()
    if saved_gym_folder and os.path.exists(saved_gym_folder):
        initial_dir = saved_gym_folder
    else:
        base_dir = get_last_base_export_dir()
        candidate = os.path.join(base_dir, GYM_FOLDER_NAME)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            initial_dir = candidate
        else:
            initial_dir = base_dir

    initial_filepath = os.path.join(initial_dir, default_filename)

    chosen_path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        dialog_title,
        initial_filepath,
        file_filter
    )

    if not chosen_path:
        return None, None

    chosen_dir = os.path.dirname(chosen_path)
    chosen_filename = os.path.basename(chosen_path)

    norm_chosen_dir = os.path.normpath(chosen_dir)
    dir_name = os.path.basename(norm_chosen_dir)

    if dir_name.strip() == GYM_FOLDER_NAME:
        target_folder = norm_chosen_dir
    else:
        candidate_subfolder = os.path.join(norm_chosen_dir, GYM_FOLDER_NAME)
        if os.path.exists(candidate_subfolder) and os.path.isdir(candidate_subfolder):
            target_folder = candidate_subfolder
        else:
            os.makedirs(candidate_subfolder, exist_ok=True)
            target_folder = candidate_subfolder

    final_filepath = os.path.join(target_folder, chosen_filename)

    set_saved_gym_export_folder(target_folder)
    parent_base = os.path.dirname(target_folder)
    if parent_base and os.path.exists(parent_base):
        set_last_base_export_dir(parent_base)

    return final_filepath, GYM_FOLDER_NAME

