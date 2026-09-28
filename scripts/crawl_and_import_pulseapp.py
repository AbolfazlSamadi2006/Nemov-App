import os
import sys
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

# Setup paths
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import config
from yalda.database.connection import get_session, mark_data_changed
from yalda.models.database_models import Exercise
import cv2

# Taxonomy Mappings
TOOL_MAP = {
    16: "bodyweight",  # بدون تجهیزات
    17: "machine",     # نیمکت
    18: "dumbbell",    # دمبل
    19: "machine",     # توپ
    20: "cable",       # کش
}

# Muscle Term IDs mapped to (primary_muscle_en, sub_muscle_fa)
MUSCLE_MAP = {
    24: ("legs", "پا"),
    28: ("legs", "جلو ران"),
    27: ("legs", "پشت ران"),
    29: ("legs", "داخل ران"),
    30: ("legs", "خارج ران"),
    25: ("legs", "ساق پا"),
    26: ("legs", "سرینی"),
    34: ("back", "پشت"),
    36: ("back", "فوقانی پشت"),
    37: ("back", "فیله کمر"),
    35: ("back", "لت"),
    21: ("arms", "دست"),
    23: ("arms", "جلو بازو"),
    22: ("arms", "پشت بازو"),
    47: ("arms", "ساعد"),
    38: ("chest", "سینه"),
    40: ("shoulders", "سرشانه"),
    39: ("shoulders", "شانه"),
    31: ("abs", "شکم"),
    33: ("abs", "راست شکمی"),
    32: ("abs", "مورب شکمی"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_html(raw_html: str) -> str:
    """Strips HTML tags and extra whitespaces."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def crop_video_and_extract_thumb(input_video_path: str, output_cropped_path: str, output_thumb_path: str, crop_top_px: int = 120) -> bool:
    """Crops crop_top_px from the top of the video and saves frame 0 as a thumbnail."""
    try:
        cap = cv2.VideoCapture(str(input_video_path))
        if not cap.isOpened():
            return False

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        new_height = height - crop_top_px
        if new_height <= 100:
            cap.release()
            return False

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_cropped_path), fourcc, fps, (width, new_height))

        first_frame_saved = False
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            cropped_frame = frame[crop_top_px:height, 0:width]

            if not first_frame_saved:
                cv2.imwrite(str(output_thumb_path), cropped_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                first_frame_saved = True

            out.write(cropped_frame)

        cap.release()
        out.release()
        return os.path.exists(output_cropped_path) and os.path.getsize(output_cropped_path) > 1000
    except Exception as e:
        print(f"Error cropping {input_video_path}: {e}")
        return False

def run_crawler():
    print("=" * 60)
    print("🚀 آغاز خزش و استخراج ۱۵۷ حرکت اصلاحی از PulseApp.ir")
    print("=" * 60)

    config.EXERCISE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    session = get_session()

    all_items = []
    # WordPress REST API pagination (100 per page, total 157)
    for page in [1, 2]:
        api_url = f"https://pulseapp.ir/wp-json/wp/v2/movement?per_page=100&page={page}"
        print(f"📥 دریافت فهرست صفحه {page}...")
        req = urllib.request.Request(api_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                all_items.extend(data)
                print(f"   تعداد حرکات این صفحه: {len(data)}")
        except Exception as e:
            print(f"   خطا در صفحه {page}: {e}")

    total_items = len(all_items)
    print(f"✅ مجموعاً {total_items} حرکت شناسایی شد.")
    print("=" * 60)

    imported_count = 0
    skipped_count = 0

    for idx, item in enumerate(all_items, start=1):
        wp_id = item.get("id")
        title = item.get("title", {}).get("rendered", "").strip()
        page_link = item.get("link", "")
        tools = item.get("tool", [])
        muscles = item.get("muscle", [])

        # Check if already in DB with media
        has_media = False
        cropped_video_name = f"exercise_pulse_{wp_id}.mp4"
        thumb_image_name = f"thumb_pulse_{wp_id}.jpg"
        cropped_video_path = config.EXERCISE_MEDIA_DIR / cropped_video_name
        thumb_image_path = config.EXERCISE_MEDIA_DIR / thumb_image_name
        if cropped_video_path.exists() and thumb_image_path.exists():
            has_media = True

        existing = session.query(Exercise).filter(Exercise.name_fa == title).first()
        if existing and existing.media_path and os.path.exists(existing.media_path) and existing.thumbnail_path and has_media:
            # Quickly sync taxonomy
            SPECIFIC_MUSCLE_PRIORITY = [28, 27, 29, 30, 25, 26, 36, 37, 35, 23, 22, 47, 38, 40, 39, 33, 32, 24, 34, 21, 31]
            pm, sm = "legs", ""
            for pref_id in SPECIFIC_MUSCLE_PRIORITY:
                if pref_id in muscles and pref_id in MUSCLE_MAP:
                    pm, sm = MUSCLE_MAP[pref_id]
                    break
            eq = "bodyweight"
            for t_id in tools:
                if t_id in TOOL_MAP:
                    eq = TOOL_MAP[t_id]
                    break
            existing.primary_muscle = pm
            existing.secondary_muscles = sm
            existing.equipment = eq
            existing.is_corrective = True
            session.commit()
            print(f"[{idx}/{total_items}] ⏭️ حرکت «{title}» قبلاً پردازش شده، اطلاعات به‌روزرسانی شد.")
            skipped_count += 1
            continue

        print(f"\n[{idx}/{total_items}] 🔄 در حال پردازش «{title}» (شناسه {wp_id})...")

        # Determine primary muscle and sub-muscle
        # Priority: Specific sub-muscles first, then general muscles
        SPECIFIC_MUSCLE_PRIORITY = [28, 27, 29, 30, 25, 26, 36, 37, 35, 23, 22, 47, 38, 40, 39, 33, 32, 24, 34, 21, 31]
        primary_muscle = "legs"
        sub_muscle = ""
        matched_m = False
        for pref_id in SPECIFIC_MUSCLE_PRIORITY:
            if pref_id in muscles and pref_id in MUSCLE_MAP:
                primary_muscle, sub_muscle = MUSCLE_MAP[pref_id]
                matched_m = True
                break

        if not matched_m:
            for m_id, (pm, sm) in MUSCLE_MAP.items():
                if sm and sm in title:
                    primary_muscle, sub_muscle = pm, sm
                    break

        # Determine equipment
        equipment = "bodyweight"
        for t_id in tools:
            if t_id in TOOL_MAP:
                equipment = TOOL_MAP[t_id]
                break

        # Fetch page HTML to extract direct MP4 URL
        video_url = None
        desc_text = ""
        try:
            req_page = urllib.request.Request(page_link, headers=HEADERS)
            with urllib.request.urlopen(req_page, timeout=30) as p_resp:
                page_html = p_resp.read().decode('utf-8', errors='ignore')
                mp4_match = re.search(r'https?://[^\s"\'<>]+\.mp4', page_html)
                if mp4_match:
                    video_url = mp4_match.group(0)

                # Extract description paragraphs
                desc_matches = re.findall(r'<p[^>]*>([\s\S]*?)</p>', page_html)
                clean_paragraphs = [clean_html(p) for p in desc_matches if len(clean_html(p)) > 15]
                if clean_paragraphs:
                    desc_text = "\n".join(clean_paragraphs[:3])
        except Exception as e:
            print(f"   ⚠️ خطا در دریافت صفحه وب: {e}")

        if not video_url:
            print(f"   ❌ لینک ویدیوی MP4 یافت نشد، رد شد.")
            continue

        # Safe URLs and file paths
        safe_video_url = urllib.parse.quote(video_url, safe='/:')
        raw_video_name = f"pulse_raw_{wp_id}.mp4"
        cropped_video_name = f"exercise_pulse_{wp_id}.mp4"
        thumb_image_name = f"thumb_pulse_{wp_id}.jpg"

        raw_video_path = config.EXERCISE_MEDIA_DIR / raw_video_name
        cropped_video_path = config.EXERCISE_MEDIA_DIR / cropped_video_name
        thumb_image_path = config.EXERCISE_MEDIA_DIR / thumb_image_name

        # Download raw video if not already present
        if not raw_video_path.exists():
            print(f"   ⬇️ در حال دانلود ویدیو...")
            try:
                req_vid = urllib.request.Request(safe_video_url, headers=HEADERS)
                with urllib.request.urlopen(req_vid, timeout=60) as v_resp, open(raw_video_path, 'wb') as f_out:
                    f_out.write(v_resp.read())
            except Exception as e:
                print(f"   ❌ خطا در دانلود ویدیو: {e}")
                continue

        # Crop 120px off the top and extract frame 0
        if not cropped_video_path.exists() or not thumb_image_path.exists():
            print(f"   ✂️ در حال کراپ ۱۲۰ پیکسل بالایی و استخراج فریم اول...")
            ok = crop_video_and_extract_thumb(str(raw_video_path), str(cropped_video_path), str(thumb_image_path), crop_top_px=120)
            if not ok:
                print(f"   ❌ خطا در عملیات کراپ!")
                continue

        # Clean up raw download to save disk space
        if raw_video_path.exists() and cropped_video_path.exists():
            try:
                raw_video_path.unlink()
            except Exception:
                pass

        # Save or update Exercise in database
        if not existing:
            ex = Exercise(
                name_fa=title,
                name_en="",
                primary_muscle=primary_muscle,
                secondary_muscles=sub_muscle,
                equipment=equipment,
                media_path=str(cropped_video_path),
                media_type="video",
                video_url="",
                is_corrective=True,
                thumbnail_path=str(thumb_image_path),
                video_cloud_url=None,
                contraindications="",
                description=desc_text or f"حرکت اصلاحی {sub_muscle} - {title}"
            )
            session.add(ex)
        else:
            existing.primary_muscle = primary_muscle
            existing.secondary_muscles = sub_muscle
            existing.equipment = equipment
            existing.media_path = str(cropped_video_path)
            existing.media_type = "video"
            existing.thumbnail_path = str(thumb_image_path)
            existing.is_corrective = True
            if desc_text:
                existing.description = desc_text

        session.commit()
        mark_data_changed()
        imported_count += 1
        print(f"   ✅ ثبت شد: عضله={primary_muscle} ({sub_muscle}) | ابزار={equipment}")

    session.close()

    # Mirror to candidate locations
    print("\n📦 در حال همگام‌سازی دیتابیس و رسانه‌ها در پوشه AppData...")
    config.sync_data_directories()

    print("=" * 60)
    print(f"🎉 عملیات با موفقیت پایان یافت!")
    print(f"   تعداد کل حرکات پردازش و وارد شده: {imported_count}")
    print(f"   تعداد حرکات بدون تغییر (قبلی): {skipped_count}")
    print("=" * 60)

if __name__ == "__main__":
    run_crawler()
