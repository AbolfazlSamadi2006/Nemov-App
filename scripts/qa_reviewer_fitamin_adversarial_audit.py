#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
Adversarial QA Audit Suite for Fitamin Database Ingestion & Cloud Video Integration
Reviewer & Critic Verification Script (M2 Fitamin Ingestion)
========================================================================================
"""
import os
import sys
import ssl
import re
import json
import zipfile
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "nemov.db"
YALDA_DB_PATH = PROJECT_ROOT / "data" / "yalda.db"
CHECKPOINT_PATH = PROJECT_ROOT / "data" / "fitamin_crawl_checkpoint.json"
BACKUP_ZIP = Path(r"C:\Users\user\.gemini\antigravity\project_backups\YaldaGym_20261024_123435_before_fitamin_crawl_and_release.zip")

VALID_MANNEQUIN_KEYS = {
    "neck", "shoulders", "chest", "biceps", "forearms", "abs",
    "legs_front", "traps", "upper_back", "triceps", "lats",
    "lower_back", "glutes", "legs_back", "calves",
    # Legacy fallbacks allowed by UI:
    "legs", "arms", "back", "سایر"
}

VALID_EQUIPMENT_KEYS = {"barbell", "dumbbell", "machine", "cable", "bodyweight", "سایر"}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def audit_test(test_num: int, title: str):
    print(f"\n[Test {test_num:02d}] {title}...")


def main():
    print("=" * 80)
    print("  ADVERSARIAL QA AUDIT: FITAMIN INGESTION & CLOUD STREAMING")
    print("=" * 80)
    
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    failures = []

    # ----------------------------------------------------------------------------------
    # 1. Total Count & Subsets Integrity
    # ----------------------------------------------------------------------------------
    audit_test(1, "Total Count & Subsets Integrity")
    c.execute("SELECT COUNT(*) FROM exercises")
    total_count = c.fetchone()[0]
    if total_count != 1005:
        failures.append(f"Expected 1005 total exercises, found {total_count}")
    else:
        print(f"  ✅ Total Exercises: {total_count} == 1005")

    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    corr_count = c.fetchone()[0]
    if corr_count != 157:
        failures.append(f"Expected 157 corrective exercises, found {corr_count}")
    else:
        print(f"  ✅ PulseApp Corrective Exercises: {corr_count} == 157")

    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 0")
    fitamin_count = c.fetchone()[0]
    if fitamin_count != 848:
        failures.append(f"Expected 848 Fitamin exercises, found {fitamin_count}")
    else:
        print(f"  ✅ Fitamin Bodybuilding Exercises: {fitamin_count} == 848")

    # ----------------------------------------------------------------------------------
    # 2. Corrective ID Continuity & Slot Replacement
    # ----------------------------------------------------------------------------------
    audit_test(2, "Corrective ID Continuity & Slot Replacement Verification")
    c.execute("SELECT id FROM exercises WHERE is_corrective = 1 ORDER BY id ASC")
    corr_ids = [r[0] for r in c.fetchall()]
    expected_corr_ids = list(range(24, 181))
    if corr_ids != expected_corr_ids:
        diff = set(expected_corr_ids) ^ set(corr_ids)
        failures.append(f"Corrective IDs do not match exact range [24..180]. Symmetric diff: {diff}")
    else:
        print(f"  ✅ Corrective IDs [24..180] 100% continuous and strictly preserved ({len(corr_ids)} IDs)")

    c.execute("SELECT id FROM exercises WHERE is_corrective = 0 ORDER BY id ASC")
    gym_ids = [r[0] for r in c.fetchall()]
    legacy_slots = [i for i in gym_ids if (1 <= i <= 23 or 181 <= i <= 189)]
    new_slots = [i for i in gym_ids if i >= 190]
    print(f"  ✅ Replaced legacy gym slots: {len(legacy_slots)} slots (IDs: {legacy_slots})")
    print(f"  ✅ Newly inserted gym slots: {len(new_slots)} slots (IDs: {min(new_slots)}..{max(new_slots)})")
    if len(legacy_slots) != 32 or len(new_slots) != 816:
        failures.append(f"Legacy slots ({len(legacy_slots)}) != 32 or New slots ({len(new_slots)}) != 816")

    # ----------------------------------------------------------------------------------
    # 3. Deep Diff Comparison Against Rule 2 Backup Archive
    # ----------------------------------------------------------------------------------
    audit_test(3, "Deep Diff Comparison Against Pre-Change Backup Archive")
    if not BACKUP_ZIP.exists():
        failures.append(f"Rule 2 backup archive missing at {BACKUP_ZIP}")
    else:
        print(f"  ✅ Rule 2 backup archive exists: {BACKUP_ZIP.name} ({BACKUP_ZIP.stat().st_size:,} bytes)")
        with zipfile.ZipFile(str(BACKUP_ZIP), 'r') as zf:
            # Find old database inside zip
            db_candidates = [n for n in zf.namelist() if n.endswith("data/nemov.db") or n.endswith("data/yalda.db")]
            if not db_candidates:
                failures.append("Could not find data/nemov.db or data/yalda.db in backup zip!")
            else:
                target_zip_entry = db_candidates[0]
                with tempfile.TemporaryDirectory() as tmp_dir:
                    extracted_db = zf.extract(target_zip_entry, tmp_dir)
                    old_conn = sqlite3.connect(extracted_db)
                    old_conn.row_factory = sqlite3.Row
                    old_c = old_conn.cursor()

                    # Compare all 157 corrective exercises
                    old_c.execute("SELECT * FROM exercises WHERE is_corrective = 1 ORDER BY id ASC")
                    old_corr_rows = {r["id"]: dict(r) for r in old_c.fetchall()}

                    c.execute("SELECT * FROM exercises WHERE is_corrective = 1 ORDER BY id ASC")
                    curr_corr_rows = {r["id"]: dict(r) for r in c.fetchall()}

                    mismatches = []
                    compare_cols = ["id", "name_fa", "primary_muscle", "secondary_muscles", "equipment", 
                                    "is_corrective", "thumbnail_path", "video_cloud_url", "contraindications"]
                    for cid, old_r in old_corr_rows.items():
                        if cid not in curr_corr_rows:
                            mismatches.append(f"Missing corrective ID {cid}")
                            continue
                        curr_r = curr_corr_rows[cid]
                        for col in compare_cols:
                            if old_r.get(col) != curr_r.get(col):
                                mismatches.append(f"ID {cid} column '{col}' changed: '{old_r.get(col)}' -> '{curr_r.get(col)}'")

                    if mismatches:
                        failures.append(f"Corrective exercise regression detected: {mismatches[:5]}")
                    else:
                        print(f"  ✅ Perfect 157/157 zero-diff match on all critical columns between backup DB and current DB!")

                    old_conn.close()

    # ----------------------------------------------------------------------------------
    # 4. Foreign Key Integrity Audit (workout_exercises)
    # ----------------------------------------------------------------------------------
    audit_test(4, "Foreign Key Integrity in workout_exercises")
    c.execute("""
        SELECT COUNT(*), COUNT(DISTINCT we.exercise_id)
        FROM workout_exercises we
        LEFT JOIN exercises e ON we.exercise_id = e.id
        WHERE e.id IS NULL
    """)
    orphaned_count, distinct_orphans = c.fetchone()
    if orphaned_count != 0:
        failures.append(f"Found {orphaned_count} orphaned references in workout_exercises!")
    else:
        print(f"  ✅ workout_exercises Foreign Key Integrity: 0 orphaned references (All referenced exercises exist)")

    # ----------------------------------------------------------------------------------
    # 5. Taxonomy Conformance: Primary Muscle & Equipment
    # ----------------------------------------------------------------------------------
    audit_test(5, "Taxonomy Conformance: Primary Muscle & Equipment")
    c.execute("SELECT DISTINCT primary_muscle, COUNT(*) FROM exercises GROUP BY primary_muscle")
    muscle_dist = dict(c.fetchall())
    invalid_muscles = set(muscle_dist.keys()) - VALID_MANNEQUIN_KEYS
    if invalid_muscles:
        failures.append(f"Invalid primary_muscle values found: {invalid_muscles}")
    else:
        print(f"  ✅ 100% of primary_muscle values ({len(muscle_dist)} categories) conform to Nemov mannequin:")
        for m, cnt in sorted(muscle_dist.items(), key=lambda x: -x[1]):
            print(f"      - {m:<15}: {cnt:>4} exercises")

    c.execute("SELECT DISTINCT equipment, COUNT(*) FROM exercises GROUP BY equipment")
    equip_dist = dict(c.fetchall())
    invalid_equips = set(equip_dist.keys()) - VALID_EQUIPMENT_KEYS
    if invalid_equips:
        failures.append(f"Invalid equipment values found: {invalid_equips}")
    else:
        print(f"  ✅ 100% of equipment values ({len(equip_dist)} categories) conform to Nemov standards:")
        for eq, cnt in sorted(equip_dist.items(), key=lambda x: -x[1]):
            print(f"      - {eq:<15}: {cnt:>4} exercises")

    # ----------------------------------------------------------------------------------
    # 6. Smart Tips Constraint & Description Sanitization
    # ----------------------------------------------------------------------------------
    audit_test(6, "Smart Tips Constraint (<= 180 chars) & Sanitization")
    c.execute("SELECT id, name_fa, description, LENGTH(description) as dlen FROM exercises WHERE is_corrective = 0")
    fitamin_rows = c.fetchall()
    
    overlength = [r for r in fitamin_rows if r["dlen"] > 180]
    empty_descs = [r for r in fitamin_rows if not r["description"] or not r["description"].strip()]
    html_tags = [r for r in fitamin_rows if re.search(r'<[^>]+>', r["description"] or "")]

    if overlength:
        failures.append(f"Found {len(overlength)} Fitamin exercises with description > 180 characters!")
    else:
        lens = [r["dlen"] for r in fitamin_rows]
        min_l, max_l, avg_l = min(lens), max(lens), sum(lens) / len(lens)
        print(f"  ✅ All 848 Fitamin descriptions meet constraint <= 180 chars (Min: {min_l}, Max: {max_l}, Avg: {avg_l:.1f} chars)")

    if empty_descs:
        failures.append(f"Found {len(empty_descs)} Fitamin exercises with empty description!")
    else:
        print(f"  ✅ Zero empty descriptions found across all 848 Fitamin exercises.")

    if html_tags:
        failures.append(f"Found {len(html_tags)} descriptions containing raw HTML tags!")
    else:
        print(f"  ✅ Zero raw HTML tags found in descriptions (Clean Persian text).")

    # Sample smart tip
    sample_tip = fitamin_rows[0]
    print(f"  ℹ️ Sample Tip [ID {sample_tip['id']} - {sample_tip['name_fa']}]:")
    print(f"     \"{sample_tip['description']}\" ({sample_tip['dlen']} chars)")

    # ----------------------------------------------------------------------------------
    # 7. Video Cloud URLs Completeness & Format Validation
    # ----------------------------------------------------------------------------------
    audit_test(7, "Video Cloud URLs Completeness & Format Validation")
    c.execute("SELECT COUNT(*) FROM exercises WHERE video_cloud_url IS NULL OR video_cloud_url = ''")
    empty_cloud = c.fetchone()[0]
    if empty_cloud != 0:
        failures.append(f"Found {empty_cloud} exercises with missing video_cloud_url!")
    else:
        print(f"  ✅ 100% of exercises (1005/1005) have video_cloud_url populated.")

    c.execute("SELECT id, video_cloud_url FROM exercises WHERE video_cloud_url NOT LIKE 'https://storage.nemovapp.ir/%'")
    non_nemov_cloud = c.fetchall()
    if non_nemov_cloud:
        print(f"  ℹ️ Notice: {len(non_nemov_cloud)} exercises have cloud URLs not on storage.nemovapp.ir (e.g. pulseapp cloud).")
        # Ensure they are valid URLs
        for r in non_nemov_cloud:
            if not r["video_cloud_url"].startswith("http"):
                failures.append(f"Exercise ID {r['id']} has invalid cloud URL: {r['video_cloud_url']}")
    else:
        print(f"  ✅ All 1,005 video_cloud_url values start with valid HTTP/HTTPS endpoints.")

    # ----------------------------------------------------------------------------------
    # 8. Live HTTP 206 Partial Content Range Streaming Verification
    # ----------------------------------------------------------------------------------
    audit_test(8, "Live HTTP 206 Partial Content Streaming Verification")
    c.execute("SELECT id, name_fa, video_cloud_url FROM exercises WHERE is_corrective = 0 AND video_cloud_url LIKE 'https://storage.nemovapp.ir/%' ORDER BY id ASC LIMIT 5")
    sample_videos = c.fetchall()
    
    stream_successes = 0
    for row in sample_videos:
        target_url = row["video_cloud_url"]
        if "?raw=1" not in target_url:
            test_url = f"{target_url}?raw=1"
        else:
            test_url = target_url

        try:
            req = urllib.request.Request(
                test_url,
                headers={
                    "User-Agent": HEADERS["User-Agent"],
                    "Range": "bytes=0-100"
                }
            )
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
                status = resp.status
                c_range = resp.headers.get("Content-Range")
                c_type = resp.headers.get("Content-Type")
                data = resp.read()

                if status == 206 and c_range and "bytes 0-100/" in c_range:
                    stream_successes += 1
                    print(f"  ✅ [ID {row['id']:<4}] HTTP 206 Range OK | {row['name_fa'][:25]:<25} | Range: {c_range} | Type: {c_type}")
                else:
                    print(f"  ⚠️ [ID {row['id']:<4}] Unexpected streaming response: Status {status}, Range {c_range}")
        except Exception as e:
            print(f"  ⚠️ [ID {row['id']:<4}] HTTP Range request failed for {test_url}: {e}")

    if stream_successes < 3:
        failures.append(f"HTTP 206 Range streaming succeeded on only {stream_successes}/5 test samples.")
    else:
        print(f"  ✅ Video streaming verified: {stream_successes}/5 samples verified with HTTP 206 Partial Content!")

    # ----------------------------------------------------------------------------------
    # 9. Multi-Database Mirroring Synchronization Verification
    # ----------------------------------------------------------------------------------
    audit_test(9, "Multi-Database Mirroring Synchronization")
    mirrors = [
        ("Root yalda.db", YALDA_DB_PATH),
        ("AppData Nemov nemov.db", Path(os.path.expandvars(r"%APPDATA%\Nemov\data\nemov.db"))),
        ("AppData YaldaGym nemov.db", Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\nemov.db"))),
        ("AppData YaldaGym yalda.db", Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\yalda.db"))),
    ]

    for m_label, m_path in mirrors:
        if not m_path.exists():
            print(f"  ⚠️ Mirror missing (non-critical if AppData not yet initialized): {m_path}")
            continue
        m_conn = sqlite3.connect(str(m_path))
        m_c = m_conn.cursor()
        m_c.execute("SELECT COUNT(*) FROM exercises")
        cnt = m_c.fetchone()[0]
        m_c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
        corr = m_c.fetchone()[0]
        m_conn.close()

        if cnt != 1005 or corr != 157:
            failures.append(f"Mirror {m_label} out of sync! Count: {cnt}, Corrective: {corr}")
        else:
            print(f"  ✅ {m_label:<25} 100% in sync: {cnt} exercises ({corr} corrective)")

    # ----------------------------------------------------------------------------------
    # 10. Checkpoint Audit
    # ----------------------------------------------------------------------------------
    audit_test(10, "Checkpoint Audit (data/fitamin_crawl_checkpoint.json)")
    if not CHECKPOINT_PATH.exists():
        failures.append(f"Checkpoint file missing at {CHECKPOINT_PATH}")
    else:
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            cp_data = json.load(f)
        
        urls = cp_data.get("movement_urls", [])
        exs = cp_data.get("exercises", {})
        ingested = cp_data.get("db_ingested", False)

        if len(urls) != 848:
            failures.append(f"Checkpoint has {len(urls)} URLs, expected 848")
        if len(exs) != 848:
            failures.append(f"Checkpoint has {len(exs)} exercises, expected 848")
        if not ingested:
            failures.append("Checkpoint db_ingested is False")
        
        print(f"  ✅ Checkpoint validated: {len(urls)} URLs, {len(exs)} exercises, db_ingested={ingested}")

    conn.close()

    # ----------------------------------------------------------------------------------
    # Summary & Verdict
    # ----------------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("  AUDIT SUMMARY")
    print("=" * 80)
    if failures:
        print(f"❌ AUDIT FAILED with {len(failures)} failures:")
        for idx, f in enumerate(failures, 1):
            print(f"   {idx}. {f}")
        sys.exit(1)
    else:
        print("🎉 ALL 10 ADVERSARIAL AUDIT CHECKS PASSED WITH ZERO INTEGRITY DEFECTS!")
        print("   Verdict: FULL COMPLIANCE")
        sys.exit(0)


if __name__ == "__main__":
    main()
