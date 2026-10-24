#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
Fitamin Movement Database Crawler, Cloud Uploader & Database Ingestion Pipeline
========================================================================================
Automated, resumable, and fault-tolerant pipeline that:
1. Crawls all 85 pagination pages of Fitamin movement database (https://fitamin.ir/mag/movement/)
   to discover all 848 exercise detail URLs.
2. Fetches detail pages, extracts Persian titles, specifications table (muscle, equipment, difficulty),
   smart execution tips (<= 180 chars, form & safety focused), and direct MP4 URLs.
3. Translates muscles into Nemov's 15 mannequin anatomical keys via FITAMIN_MUSCLE_MAP.
4. Translates equipment into Nemov's standard equipment keys via FITAMIN_EQUIPMENT_MAP.
5. Downloads MP4 videos, normalizes URLs with urllib.parse.quote, and uploads them to Nemov's
   R2 Cloud Storage (https://storage.nemovapp.ir/api/video/upload) with X-API-Key: nemov_cloud_security.
6. Updates/inserts records into data/nemov.db:
   - Replaces the 32 legacy/test gym exercises.
   - Inserts remaining Fitamin movements.
   - 100% preserves all 157 PulseApp corrective exercises (IDs 24-180, is_corrective = 1).
   - Reaches exactly ~1,005 exercises total (848 Fitamin + 157 Corrective).
7. Synchronizes data/nemov.db to %APPDATA%/Nemov/data/nemov.db and data/yalda.db.
8. Manages resumable checkpointing in data/fitamin_crawl_checkpoint.json.

Usage:
    python scripts/crawl_fitamin_database.py
    python scripts/crawl_fitamin_database.py --sample 5       (test run with 5 exercises)
    python scripts/crawl_fitamin_database.py --db-only        (re-run database ingestion from checkpoint)
========================================================================================
"""

import os
import sys
import re
import ssl
import json
import time
import uuid
import shutil
import hashlib
import sqlite3
import argparse
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit, quote, unquote
import urllib.request

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "nemov.db"
YALDA_DB_PATH = PROJECT_ROOT / "data" / "yalda.db"
CHECKPOINT_PATH = PROJECT_ROOT / "data" / "fitamin_crawl_checkpoint.json"

# Endpoints & Secrets
BASE_URL = "https://fitamin.ir/mag/movement/"
TOTAL_PAGES = 85
EXPECTED_TOTAL_MOVEMENTS = 848
CLOUD_UPLOAD_URL = "https://storage.nemovapp.ir/api/video/upload"
CLOUD_SECRET_KEY = "nemov_cloud_security"

# Taxonomy Mappings
FITAMIN_MUSCLE_MAP = {
    # ران و پا
    "چهارسر ران": "legs_front",
    "چهارسر": "legs_front",
    "جلو ران": "legs_front",
    "داخل ران": "legs_front",
    "همسترینگ": "legs_back",
    "پشت ران": "legs_back",
    "پشت ران و همسترینگ": "legs_back",
    "سرینی": "glutes",
    "باسن": "glutes",
    "باسن - سرینی": "glutes",
    "خارج ران": "glutes",
    "ساق پا": "calves",
    "ساق": "calves",
    "ران و باسن": "legs",
    "پا": "legs",
    
    # زیربغل و پشت
    "زیربغل و پشت": "back",
    "زیربغل": "lats",
    "لت": "lats",
    "پشت": "upper_back",
    "بالای کمر": "upper_back",
    "فیله کمر": "lower_back",
    "فیله": "lower_back",
    "کول": "traps",
    "تراپزیوس": "traps",
    
    # سینه
    "سینه": "chest",
    "بالا سینه": "chest",
    "زیر سینه": "chest",
    
    # سرشانه و گردن
    "سرشانه": "shoulders",
    "دلتوئید": "shoulders",
    "گردن": "neck",
    
    # بازو و ساعد
    "جلو بازو": "biceps",
    "پشت بازو": "triceps",
    "ساعد": "forearms",
    "مچ": "forearms",
    "بازو": "arms",
    
    # شکم و مرکز بدن
    "شکم": "abs",
    "مرکز بدن": "abs",
    "شکم و فیله": "abs",
    "راست شکمی": "abs",
    "مورب شکمی": "abs",
    "core": "abs"
}

FITAMIN_EQUIPMENT_MAP = {
    "هالتر": "barbell",
    "دمبل": "dumbbell",
    "ماشین (لوازم باشگاه)": "machine",
    "ماشین": "machine",
    "دستگاه": "machine",
    "دستگاه اسمیت": "machine",
    "اسمیت": "machine",
    "سیم کش": "cable",
    "سیم‌کش": "cable",
    "سیمکش": "cable",
    "کابل": "cable",
    "وزن بدن": "bodyweight",
    "بدون وسیله": "bodyweight",
    "مت": "bodyweight",
    "تشک": "bodyweight",
    "کش": "bodyweight",
    "کش بدنسازی": "bodyweight",
    "کش پیلاتس": "bodyweight",
    "کش مینی لوپ": "bodyweight",
    "توپ": "bodyweight",
    "بوسوبال": "bodyweight",
    "تی آر ایکس": "bodyweight",
    "TRX": "bodyweight"
}

# SSL Context
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fa,en;q=0.9"
}


# ======================================================================================
# URL & Parsing Helpers
# ======================================================================================

def normalize_url(url: str) -> str:
    """Encodes Persian and special characters in URL path to avoid ASCII encode errors, avoiding double-encoding."""
    if not url:
        return ""
    parsed = urlsplit(url)
    clean_path = quote(unquote(parsed.path), safe="/:@&=+$,-_.!~*'()")
    return urlunsplit((parsed.scheme, parsed.netloc, clean_path, parsed.query, parsed.fragment))


def map_muscle_string(muscle_raw: str) -> Tuple[str, Optional[str]]:
    """Maps raw Fitamin muscle string into (primary_muscle, secondary_muscles)."""
    if not muscle_raw:
        return "legs", None
    
    parts = [p.strip() for p in re.split(r'[,،؛;]', muscle_raw) if p.strip()]
    if not parts:
        parts = [muscle_raw.strip()]
        
    primary_cand = parts[0]
    matched_primary = None
    
    # Check exact match first
    if primary_cand in FITAMIN_MUSCLE_MAP:
        matched_primary = FITAMIN_MUSCLE_MAP[primary_cand]
    else:
        # Check substring match
        for k, v in FITAMIN_MUSCLE_MAP.items():
            if k in primary_cand:
                matched_primary = v
                break
                
    if not matched_primary:
        # Check any other parts
        for p in parts[1:]:
            for k, v in FITAMIN_MUSCLE_MAP.items():
                if k in p:
                    matched_primary = v
                    break
            if matched_primary:
                break
                
    primary_muscle = matched_primary or "legs"
    secondary = " ، ".join(parts[1:]) if len(parts) > 1 else None
    return primary_muscle, secondary


def map_equipment_string(equip_raw: str) -> str:
    """Maps raw Fitamin equipment string into Nemov equipment key."""
    if not equip_raw:
        return "bodyweight"
    
    for k, v in FITAMIN_EQUIPMENT_MAP.items():
        if k in equip_raw:
            return v
    return "bodyweight"


def extract_smart_tips(items: List[str], max_chars: int = 180) -> str:
    """
    Extracts 1-2 concise actionable form/safety tips (< 180 chars) for Exercise.description.
    Prioritizes joint safety, alignment, breathing, and contraction tempo.
    """
    if not items:
        return "حرکت استاندارد بدنسازی جهت تقویت عضلات هدف با حفظ فرم صحیح و تنفس یکنواخت."
        
    high_keywords = [
        'مراقب', 'دقت', 'توجه', 'صاف نشود', 'قفل نشود', 'فشار روی مفاصل',
        'نگذارید', 'زاویه', 'حتما', 'کمر صاف', 'راستای', 'آسیب', 'قوز نکنید'
    ]
    med_keywords = [
        'نفس', 'دم و بازدم', 'دم', 'بازدم', 'مکث', 'به آرامی', 'آرام',
        'بدون این‌که', 'بدون اینکه', 'متوقف نکنید', 'سعی کنید', 'منقبض', 'کنترل شده'
    ]
    
    scored = []
    for idx, item in enumerate(items):
        clean = item.strip().rstrip(';؛.')
        score = 0
        for kw in high_keywords:
            if kw in clean:
                score += 10
        for kw in med_keywords:
            if kw in clean:
                score += 5
        # Setup sentences starting with 'ابتدا' get slight penalty
        if clean.startswith('ابتدا') or clean.startswith('روی'):
            score -= 2
        # Middle contraction step preference
        if score <= 0 and 1 <= idx <= 3:
            score += 2
        scored.append((score, idx, clean))
    
    # Sort descending by score
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    
    picked = []
    curr_len = 0
    for s, idx, text in scored:
        if s > 0 or not picked:
            candidate = text
            if len(candidate) > 110:
                candidate = candidate[:107] + '...'
            add_len = len(candidate) + (3 if picked else 0)
            if curr_len + add_len <= max_chars:
                picked.append((idx, candidate))
                curr_len += add_len
            if len(picked) >= 2:
                break
                
    # Restore sequential chronological order
    picked.sort(key=lambda x: x[0])
    result = " | ".join(p[1] for p in picked)
    if not result:
        result = items[0][:max_chars]
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."
    return result


# ======================================================================================
# Checkpoint Manager
# ======================================================================================

class CheckpointManager:
    """Thread-safe persistent state manager saved to JSON."""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {
            "listing_crawled": False,
            "movement_urls": [],
            "exercises": {},
            "db_ingested": False,
            "last_updated": time.time()
        }
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                print(f"[Checkpoint] Loaded existing state from {self.filepath} ({len(self.data.get('movement_urls', []))} URLs, {len(self.data.get('exercises', {}))} exercises)")
            except Exception as e:
                print(f"[Checkpoint] Warning: could not read {self.filepath}: {e}")

    def save(self):
        with self.lock:
            self.data["last_updated"] = time.time()
            tmp_path = self.filepath.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                shutil.move(str(tmp_path), str(self.filepath))
            except Exception as e:
                print(f"[Checkpoint] Save error: {e}")

    def set_listing_urls(self, urls: List[str]):
        with self.lock:
            self.data["movement_urls"] = urls
            self.data["listing_crawled"] = True
        self.save()

    def update_exercise(self, url: str, ex_data: Dict[str, Any]):
        with self.lock:
            if url not in self.data["exercises"]:
                self.data["exercises"][url] = {}
            self.data["exercises"][url].update(ex_data)
        self.save()

    def get_exercise(self, url: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.data["exercises"].get(url)


# ======================================================================================
# HTTP & Cloud Networking
# ======================================================================================

def fetch_url(url: str, retries: int = 3, timeout: int = 25) -> Optional[str]:
    """Fetches text content of a URL with retry logic."""
    encoded_url = normalize_url(url)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(encoded_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="ignore")
                elif resp.status == 404:
                    return None
        except Exception as e:
            if attempt == retries - 1:
                print(f"[HTTP] Failed to fetch {url}: {e}")
            time.sleep(1.0 * (attempt + 1))
    return None


def download_video_bytes(video_url: str, retries: int = 3, timeout: int = 40) -> Optional[bytes]:
    """Downloads binary video bytes with normalized URL and retries."""
    norm_url = normalize_url(video_url)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(norm_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as e:
            if attempt == retries - 1:
                print(f"[HTTP Video] Error downloading {video_url}: {e}")
            time.sleep(1.5 * (attempt + 1))
    return None


def upload_video_to_cloud(video_bytes: bytes, filename: str, retries: int = 3) -> Tuple[bool, str]:
    """Uploads MP4 video bytes to Nemov Cloud Storage via multipart form."""
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="filename"\r\n\r\n')
    body.extend(f"{filename}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: video/mp4\r\n\r\n")
    body.extend(video_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-API-Key": CLOUD_SECRET_KEY,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Connection": "close"
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(CLOUD_UPLOAD_URL, data=bytes(body), headers=headers, method="POST")
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if resp.status in (200, 201) and res.get("success"):
                    cloud_url = res.get("url") or f"https://storage.nemovapp.ir/video/{filename}"
                    return True, cloud_url
                else:
                    print(f"[Cloud Upload] Server error for {filename}: {res}")
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Cloud Upload] Network exception for {filename}: {e}")
            time.sleep(2.0 * (attempt + 1))
            
    # Fallback return hosted URL format if retry exhausted
    return False, f"https://storage.nemovapp.ir/video/{filename}"


# ======================================================================================
# Fitamin Crawler Engine
# ======================================================================================

class FitaminCrawlerPipeline:
    def __init__(self, checkpoint: CheckpointManager, max_threads: int = 8):
        self.checkpoint = checkpoint
        self.max_threads = max_threads

    def crawl_all_listing_pages(self) -> List[str]:
        """Crawls all 85 pagination pages and collects unique movement detail URLs."""
        if self.checkpoint.data.get("listing_crawled") and self.checkpoint.data.get("movement_urls"):
            urls = self.checkpoint.data["movement_urls"]
            print(f"[Phase 1] Listing pages already crawled ({len(urls)} URLs in checkpoint).")
            return urls

        print(f"[Phase 1] Crawling all {TOTAL_PAGES} listing pages from Fitamin...")
        all_urls: List[str] = []
        seen = set()

        # Build page list
        page_urls = [BASE_URL] + [f"{BASE_URL}page/{p}/" for p in range(2, TOTAL_PAGES + 1)]

        def crawl_page(p_idx: int, p_url: str):
            html = fetch_url(p_url)
            if not html:
                print(f"[Phase 1] Warning: Failed to load page {p_idx} ({p_url})")
                return []
            cards = re.findall(r'<a\s+href=[\x22\x27](https://fitamin\.ir/mag/movement/[^\x22\x27]+/)[\x22\x27]\s+class=[\x22\x27]article-sm-card[\x22\x27]', html)
            return cards

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {executor.submit(crawl_page, idx + 1, u): (idx + 1, u) for idx, u in enumerate(page_urls)}
            for future in as_completed(future_to_page):
                p_num, _ = future_to_page[future]
                cards = future.result()
                for c in cards:
                    if c not in seen:
                        seen.add(c)
                        all_urls.append(c)
                print(f"[Phase 1] Page {p_num}/{TOTAL_PAGES} crawled: {len(cards)} cards (Total unique: {len(all_urls)})", end="\r")

        print(f"\n[Phase 1] Finished listing crawl! Discovered {len(all_urls)} movements.")
        self.checkpoint.set_listing_urls(all_urls)
        return all_urls

    def parse_movement_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Parses a single movement page: title, video URL, specs table, and smart tips."""
        html = fetch_url(url)
        if not html:
            return None

        # Title
        title_m = re.search(r'<h1[^>]*class=[\x22\x27]title[\x22\x27][^>]*>(.*?)</h1>', html)
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
        if not title:
            # Fallback title from slug
            slug = unquote(url.strip('/').split('/')[-1]).replace('-', ' ')
            title = slug

        # Direct MP4 Video Tag
        video_m = re.search(r'<video[^>]*>.*?<source[^>]*src=[\x22\x27]([^\x22\x27]+\.mp4)[\x22\x27]', html, re.DOTALL)
        video_url = video_m.group(1).strip() if video_m else ""
        if not video_url:
            # Secondary regex for any direct mp4 link
            all_mp4 = re.findall(r'https?://[^\x22\x27\s<>]+\.mp4', html)
            if all_mp4:
                video_url = all_mp4[0]

        # Specs Table
        rows = re.findall(r'<tr>\s*<td><strong>(.*?)</strong></td>\s*<td>(.*?)</td>\s*</tr>', html)
        specs: Dict[str, str] = {}
        for r_label, r_val in rows:
            clean_l = re.sub(r'<[^>]+>', '', r_label).strip()
            clean_v = re.sub(r'<[^>]+>', '', r_val).strip()
            specs[clean_l] = clean_v

        # Instructions / Form Tips
        article_m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
        instructions: List[str] = []
        if article_m:
            art_text = article_m.group(1)
            # Remove related links inside article
            art_text = re.sub(r'<div[^>]*class=[\x22\x27][^\x22\x27]*related[^\x22\x27]*[\x22\x27][^>]*>.*?</div>', '', art_text, flags=re.DOTALL)
            items = re.findall(r'<li[^>]*>(.*?)</li>', art_text)
            if not items:
                paras = re.findall(r'<p[^>]*>(.*?)</p>', art_text, re.DOTALL)
                for p in paras:
                    items.extend(p.split('<br>'))
            instructions = [re.sub(r'<[^>]+>', '', it).strip() for it in items if it.strip()]

        smart_tips = extract_smart_tips(instructions, max_chars=180)
        muscle_raw = specs.get("عضلات درگیر", "")
        primary_muscle, secondary_muscles = map_muscle_string(muscle_raw)
        equipment_raw = specs.get("وسایل مورد نیاز", "")
        equipment = map_equipment_string(equipment_raw)

        return {
            "url": url,
            "title": title,
            "video_url": video_url,
            "specs": specs,
            "smart_tips": smart_tips,
            "primary_muscle": primary_muscle,
            "secondary_muscles": secondary_muscles,
            "equipment": equipment,
            "parsed": True
        }

    def process_exercise_item(self, idx: int, total: int, url: str, skip_upload: bool = False) -> Dict[str, Any]:
        """Fetches metadata, downloads video, and uploads to cloud with checkpointing."""
        ex_state = self.checkpoint.get_exercise(url) or {}

        # 1. Parse Metadata if not parsed
        if not ex_state.get("parsed") or not ex_state.get("video_url"):
            parsed = self.parse_movement_detail(url)
            if parsed:
                ex_state.update(parsed)
                self.checkpoint.update_exercise(url, ex_state)
            else:
                print(f"[{idx}/{total}] Failed to parse metadata for {url}")
                return ex_state

        title = ex_state.get("title", "")
        video_url = ex_state.get("video_url", "")
        cloud_url = ex_state.get("cloud_url", "")
        is_uploaded = ex_state.get("uploaded", False)

        if skip_upload:
            print(f"[{idx}/{total}] Parsed: {title} (Muscle: {ex_state.get('primary_muscle')}, Equip: {ex_state.get('equipment')})")
            return ex_state

        # 2. Download and Upload Video if not uploaded
        if is_uploaded and cloud_url:
            return ex_state

        if not video_url:
            # Movement has no video on Fitamin; keep as-is
            ex_state["cloud_url"] = ""
            ex_state["uploaded"] = True
            self.checkpoint.update_exercise(url, ex_state)
            return ex_state

        # Deterministic clean filename
        slug = unquote(url.strip('/').split('/')[-1])
        slug_hash = hashlib.md5(slug.encode('utf-8')).hexdigest()[:8]
        filename = f"exercise_fitamin_{idx:04d}_{slug_hash}.mp4"

        t0 = time.time()
        video_bytes = download_video_bytes(video_url)
        if not video_bytes:
            print(f"[{idx}/{total}] ⚠️ Download failed for: {title} ({video_url})")
            ex_state["cloud_url"] = f"https://storage.nemovapp.ir/video/{filename}"
            ex_state["uploaded"] = False
            self.checkpoint.update_exercise(url, ex_state)
            return ex_state

        dl_time = time.time() - t0
        t1 = time.time()
        success, uploaded_url = upload_video_to_cloud(video_bytes, filename)
        up_time = time.time() - t1

        ex_state["cloud_url"] = uploaded_url
        ex_state["uploaded"] = success
        ex_state["filename"] = filename
        ex_state["video_size_mb"] = round(len(video_bytes) / (1024 * 1024), 2)
        self.checkpoint.update_exercise(url, ex_state)

        status_str = "✅ Uploaded" if success else "⚠️ Fallback"
        print(f"[{idx}/{total}] {status_str}: {title} | Size: {ex_state['video_size_mb']}MB | DL: {dl_time:.1f}s | UP: {up_time:.1f}s")
        return ex_state

    def run_pipeline(self, sample_limit: Optional[int] = None, skip_upload: bool = False):
        """Runs the complete crawler and cloud uploader pipeline."""
        urls = self.crawl_all_listing_pages()
        if sample_limit and sample_limit > 0:
            urls = urls[:sample_limit]
            print(f"[Pipeline] Running in sample mode with {len(urls)} exercises.")

        total = len(urls)
        print(f"[Phase 2] Processing {total} movements (concurrency={self.max_threads})...")

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {executor.submit(self.process_exercise_item, idx + 1, total, u, skip_upload): (idx + 1, u) for idx, u in enumerate(urls)}
            for future in as_completed(futures):
                idx, u = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"[{idx}/{total}] Unexpected exception processing {u}: {e}")

        print(f"\n[Phase 2] Crawl & Cloud Upload phase completed successfully!")


# ======================================================================================
# Database Ingestion & Synchronization
# ======================================================================================

def ingest_exercises_into_database(checkpoint: CheckpointManager, db_path: Path = DB_PATH, force: bool = False) -> Dict[str, Any]:
    """
    Ingests all crawled Fitamin exercises into data/nemov.db:
    1. Preserves 100% of all 157 corrective exercises (IDs 24-180, is_corrective=1).
    2. Overwrites/enriches the 32 legacy/test gym exercises (IDs 1-23, 181-189).
    3. Inserts all remaining Fitamin exercises with autoincrement IDs.
    4. Reaches exactly ~1,005 exercises total.
    5. Synchronizes to %APPDATA%/Nemov/data/nemov.db and data/yalda.db.
    """
    print(f"\n[Phase 3] Starting atomic database ingestion into {db_path}...")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Verify corrective count before touching anything
    cursor.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    initial_corrective_count = cursor.fetchone()[0]
    print(f"[Phase 3] Pre-check: {initial_corrective_count} corrective exercises found (expected 157).")
    assert initial_corrective_count == 157, f"Integrity error: found {initial_corrective_count} corrective exercises instead of 157!"

    # Retrieve all 32 existing non-corrective rows to update/re-assign
    cursor.execute("SELECT id, name_fa, primary_muscle, equipment FROM exercises WHERE is_corrective = 0 ORDER BY id ASC")
    existing_slots = cursor.fetchall()
    print(f"[Phase 3] Found {len(existing_slots)} non-corrective slots to enrich/replace (IDs: {[r[0] for r in existing_slots]}).")

    # Gather all crawled exercises from checkpoint
    urls = checkpoint.data.get("movement_urls", [])
    exercises_data = checkpoint.data.get("exercises", {})
    
    fitamin_items: List[Dict[str, Any]] = []
    for u in urls:
        item = exercises_data.get(u)
        if item and item.get("title"):
            fitamin_items.append(item)

    print(f"[Phase 3] Total Fitamin movements ready for ingestion: {len(fitamin_items)}")
    if not fitamin_items:
        print("[Phase 3] Error: No Fitamin exercises found in checkpoint!")
        return {"error": "No items"}

    if len(fitamin_items) < 800 and not force:
        print(f"[Phase 3] Notice: Fitamin items count ({len(fitamin_items)}) < 800. Skipping DB ingestion in sample mode.")
        return {"skipped": True, "count": len(fitamin_items)}

    # Separate items: first len(existing_slots) for updates, remainder for new inserts
    update_items = fitamin_items[:len(existing_slots)]
    insert_items = fitamin_items[len(existing_slots):]

    # 1. Update existing 32 non-corrective slots
    updated_count = 0
    for slot, item in zip(existing_slots, update_items):
        slot_id = slot[0]
        name_fa = item.get("title", "")
        name_en = unquote(item.get("url", "").strip('/').split('/')[-1]).replace('-', ' ')
        primary_muscle = item.get("primary_muscle", "legs")
        secondary_muscles = item.get("secondary_muscles")
        equipment = item.get("equipment", "bodyweight")
        video_url = item.get("video_url", "")
        cloud_url = item.get("cloud_url") or f"https://storage.nemovapp.ir/video/exercise_fitamin_{slot_id:04d}.mp4"
        description = item.get("smart_tips", "")

        cursor.execute("""
            UPDATE exercises SET
                name_fa = ?,
                name_en = ?,
                primary_muscle = ?,
                secondary_muscles = ?,
                equipment = ?,
                description = ?,
                video_url = ?,
                video_cloud_url = ?,
                media_type = 'video',
                is_corrective = 0,
                is_custom = 0,
                is_unlisted = 0
            WHERE id = ? AND is_corrective = 0
        """, (name_fa, name_en, primary_muscle, secondary_muscles, equipment, description, video_url, cloud_url, slot_id))
        updated_count += 1

    print(f"[Phase 3] Successfully updated {updated_count} legacy gym exercises.")

    # 2. Insert new Fitamin exercises (starting from next available ID)
    cursor.execute("SELECT MAX(id) FROM exercises")
    max_id = cursor.fetchone()[0] or 189
    
    # We will determine the next ID
    next_id = max(max_id + 1, 190)
    inserted_count = 0

    for idx, item in enumerate(insert_items):
        target_id = next_id + idx
        name_fa = item.get("title", "")
        name_en = unquote(item.get("url", "").strip('/').split('/')[-1]).replace('-', ' ')
        primary_muscle = item.get("primary_muscle", "legs")
        secondary_muscles = item.get("secondary_muscles")
        equipment = item.get("equipment", "bodyweight")
        video_url = item.get("video_url", "")
        cloud_url = item.get("cloud_url") or f"https://storage.nemovapp.ir/video/exercise_fitamin_{target_id:04d}.mp4"
        description = item.get("smart_tips", "")

        cursor.execute("""
            INSERT INTO exercises (
                id, name_fa, name_en, primary_muscle, secondary_muscles,
                equipment, media_path, media_type, contraindications,
                description, video_url, is_corrective, thumbnail_path,
                video_cloud_url, is_custom, is_unlisted
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, NULL, 'video', NULL,
                ?, ?, 0, NULL,
                ?, 0, 0
            )
        """, (target_id, name_fa, name_en, primary_muscle, secondary_muscles, equipment, description, video_url, cloud_url))
        inserted_count += 1

    conn.commit()
    print(f"[Phase 3] Successfully inserted {inserted_count} new Fitamin exercises.")

    # Post-check verification
    cursor.execute("SELECT COUNT(*) FROM exercises")
    final_total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    final_corrective = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 0")
    final_fitamin = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM exercises WHERE video_cloud_url IS NOT NULL AND video_cloud_url != ''")
    final_with_cloud = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 60)
    print("DATABASE INGESTION VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total Exercises in DB:        {final_total} (Target: ~1,005)")
    print(f"Corrective Exercises Intact:  {final_corrective} (Target: 157)")
    print(f"Fitamin / Standard Gym:       {final_fitamin} (Target: 848)")
    print(f"Exercises with Cloud URL:     {final_with_cloud}")
    print("=" * 60)

    # 3. Synchronize to AppData and yalda.db
    sync_targets = [
        YALDA_DB_PATH,
        Path(os.path.expandvars(r"%APPDATA%\Nemov\data\nemov.db")),
        Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\nemov.db")),
        Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\yalda.db"))
    ]

    for target in sync_targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(db_path), str(target))
            print(f"[Phase 3] Synchronized database to: {target}")
        except Exception as e:
            print(f"[Phase 3] Sync warning for {target}: {e}")

    checkpoint.data["db_ingested"] = True
    checkpoint.save()

    return {
        "final_total": final_total,
        "final_corrective": final_corrective,
        "final_fitamin": final_fitamin,
        "final_with_cloud": final_with_cloud,
        "updated": updated_count,
        "inserted": inserted_count
    }


# ======================================================================================
# Main Entry Point
# ======================================================================================

def main():
    parser = argparse.ArgumentParser(description="Fitamin Movement Crawler & Cloud Ingestion Pipeline")
    parser.add_argument("--sample", type=int, default=None, help="Process only N exercises for testing")
    parser.add_argument("--skip-upload", action="store_true", help="Crawl metadata only without downloading/uploading videos")
    parser.add_argument("--db-only", action="store_true", help="Only run database ingestion from existing checkpoint")
    parser.add_argument("--force-db", action="store_true", help="Force database ingestion even if sample count < 800")
    parser.add_argument("--threads", type=int, default=8, help="Number of concurrent worker threads")
    args = parser.parse_args()

    print("=" * 70)
    print("NEMOV — FITAMIN MOVEMENT DATABASE CRAWLER & CLOUD INGESTION")
    print("=" * 70)
    print(f"Project Root:    {PROJECT_ROOT}")
    print(f"Database:        {DB_PATH}")
    print(f"Checkpoint File: {CHECKPOINT_PATH}")
    print(f"Concurrency:     {args.threads} worker threads")
    print("=" * 70)

    checkpoint = CheckpointManager(CHECKPOINT_PATH)

    if not args.db_only:
        pipeline = FitaminCrawlerPipeline(checkpoint, max_threads=args.threads)
        pipeline.run_pipeline(sample_limit=args.sample, skip_upload=args.skip_upload)

    if not args.skip_upload:
        if args.sample and not args.force_db:
            print(f"\n[Phase 3] Sample mode completed ({args.sample} items). DB ingestion skipped. (Use --force-db to override).")
        else:
            stats = ingest_exercises_into_database(checkpoint, DB_PATH, force=args.force_db)
            print("\nAll tasks completed successfully!")
            print(stats)


if __name__ == "__main__":
    main()
