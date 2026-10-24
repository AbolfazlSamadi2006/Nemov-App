#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
Adversarial Verification Suite: Fitamin Checkpointing, AppData Sync & Desktop View Performance
========================================================================================
Empirical Challenger Test Harness for Milestone 2:
1. Checkpoint JSON structure, completeness, syntax, and taxonomy validation.
2. Idempotent execution of crawl_fitamin_database.py --db-only without duplication or loss.
3. AppData and fallback database mirror consistency and cryptographic row checksum comparison.
4. Desktop WorkoutLibraryView instantiation, filter responsiveness (<50ms), and stress testing.
========================================================================================
"""

import os
import sys
import time
import json
import ssl
import shutil
import hashlib
import sqlite3
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Dict, List, Any, Tuple

def get_process_memory_mb() -> float:
    try:
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        hProcess = kernel32.GetCurrentProcess()
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t),
            ]
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0

# Force UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CHECKPOINT_PATH = PROJECT_ROOT / "data" / "fitamin_crawl_checkpoint.json"
ROOT_DB_PATH = PROJECT_ROOT / "data" / "nemov.db"
YALDA_DB_PATH = PROJECT_ROOT / "data" / "yalda.db"
APPDATA_NEMOV_DB = Path(os.path.expandvars(r"%APPDATA%\Nemov\data\nemov.db"))
APPDATA_YALDA_NEMOV_DB = Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\nemov.db"))
APPDATA_YALDA_YALDA_DB = Path(os.path.expandvars(r"%APPDATA%\YaldaGym\data\yalda.db"))

SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

VALID_MUSCLES = {
    "neck", "shoulders", "chest", "biceps", "forearms", "abs",
    "legs_front", "traps", "upper_back", "triceps", "lats",
    "lower_back", "glutes", "legs_back", "calves", "legs", "arms", "back", "سایر"
}
VALID_EQUIPMENT = {"barbell", "dumbbell", "machine", "cable", "bodyweight", "سایر"}

passed_assertions = 0
failed_assertions = 0

def check(assertion: bool, message: str):
    global passed_assertions, failed_assertions
    if assertion:
        passed_assertions += 1
        print(f"  [PASS] {message}")
    else:
        failed_assertions += 1
        print(f"  [FAIL] {message}")

# ======================================================================================
# Target 1: Checkpoint Structure & Completeness Stress
# ======================================================================================

def test_checkpoint_structure():
    print("\n" + "=" * 70)
    print("TARGET 1: CHECKPOINT JSON STRUCTURE & COMPLETENESS")
    print("=" * 70)

    check(CHECKPOINT_PATH.exists(), f"Checkpoint file exists at {CHECKPOINT_PATH}")
    file_size = CHECKPOINT_PATH.stat().st_size
    check(file_size > 1_000_000, f"Checkpoint file size is realistic: {file_size:,} bytes (>1MB)")

    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    check(isinstance(data, dict), "Checkpoint root is valid JSON dictionary")
    check("movement_urls" in data and "exercises" in data, "Required root keys present in checkpoint")
    check(data.get("listing_crawled") is True, "Checkpoint listing_crawled flag is True")
    check(data.get("db_ingested") is True, "Checkpoint db_ingested flag is True")

    urls = data.get("movement_urls", [])
    check(len(urls) == 848, f"movement_urls length is exactly 848 (got {len(urls)})")
    check(len(set(urls)) == 848, f"movement_urls contains 848 unique URLs (zero duplicates)")

    exercises = data.get("exercises", {})
    check(len(exercises) == 848, f"exercises map contains exactly 848 entries (got {len(exercises)})")
    check(set(exercises.keys()) == set(urls), "100% key match between movement_urls and exercises dictionary")

    # Detailed field validation
    missing_title = 0
    missing_video = 0
    missing_muscle = 0
    missing_equip = 0
    missing_tips = 0
    overlength_tips = []
    invalid_muscles = set()
    invalid_equips = set()
    missing_cloud = 0

    for url, ex in exercises.items():
        if not ex.get("title") or not str(ex.get("title")).strip():
            missing_title += 1
        if not ex.get("video_url"):
            missing_video += 1
        if not ex.get("primary_muscle"):
            missing_muscle += 1
        else:
            if ex.get("primary_muscle") not in VALID_MUSCLES:
                invalid_muscles.add(ex.get("primary_muscle"))
        if not ex.get("equipment"):
            missing_equip += 1
        else:
            if ex.get("equipment") not in VALID_EQUIPMENT:
                invalid_equips.add(ex.get("equipment"))
        tips = ex.get("smart_tips", "")
        if not tips:
            missing_tips += 1
        elif len(tips) > 180:
            overlength_tips.append((ex.get("title"), len(tips)))
        if not ex.get("cloud_url"):
            missing_cloud += 1

    check(missing_title == 0, f"All 848 exercises have non-empty Persian titles (missing: {missing_title})")
    check(missing_video == 0, f"All 848 exercises have non-empty video URLs (missing: {missing_video})")
    check(missing_muscle == 0, f"All 848 exercises have primary muscle assigned (missing: {missing_muscle})")
    check(len(invalid_muscles) == 0, f"All primary muscles conform to Nemov schema (invalid: {invalid_muscles})")
    check(missing_equip == 0, f"All 848 exercises have equipment assigned (missing: {missing_equip})")
    check(len(invalid_equips) == 0, f"All equipment values conform to Nemov schema (invalid: {invalid_equips})")
    check(missing_tips == 0, f"All 848 exercises have smart safety tips (missing: {missing_tips})")
    check(len(overlength_tips) == 0, f"100% of smart tips are <= 180 chars (violations: {len(overlength_tips)})")
    check(missing_cloud == 0, f"All 848 exercises have cloud URL format assigned (missing: {missing_cloud})")


# ======================================================================================
# Target 1 (Part B): Idempotent Database Ingestion Stress
# ======================================================================================

def test_idempotent_ingestion():
    print("\n" + "=" * 70)
    print("TARGET 1 (PART B): IDEMPOTENT DB INGESTION STRESS (--db-only)")
    print("=" * 70)

    # 1. Snapshot database state before running
    conn = sqlite3.connect(str(ROOT_DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM exercises")
    before_total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    before_corr = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 0")
    before_fitamin = c.fetchone()[0]
    c.execute("SELECT id, name_fa, primary_muscle, equipment, is_corrective, video_cloud_url FROM exercises ORDER BY id ASC")
    before_rows = c.fetchall()
    before_hash = hashlib.sha256(repr(before_rows).encode('utf-8')).hexdigest()
    conn.close()

    print(f"  Pre-run Snapshot: Total={before_total}, Corr={before_corr}, Fitamin={before_fitamin}, SHA256={before_hash[:16]}")
    check(before_total == 1005, f"Pre-run total exercises is exactly 1,005 (got {before_total})")
    check(before_corr == 157, f"Pre-run corrective exercises is exactly 157 (got {before_corr})")
    check(before_fitamin == 848, f"Pre-run Fitamin exercises is exactly 848 (got {before_fitamin})")

    # 2. Execute crawl_fitamin_database.py --db-only via subprocess
    script_path = PROJECT_ROOT / "scripts" / "crawl_fitamin_database.py"
    py_exe = sys.executable
    print(f"  Executing: {py_exe} {script_path} --db-only")
    t0 = time.time()
    res = subprocess.run([py_exe, str(script_path), "--db-only"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    duration = time.time() - t0
    print(f"  Execution completed in {duration:.2f}s with returncode {res.returncode}")

    check(res.returncode == 0, f"crawl_fitamin_database.py --db-only exited with code 0 (got {res.returncode})")
    check("DATABASE INGESTION VERIFICATION REPORT" in res.stdout, "Ingestion report displayed in stdout")

    # 3. Verify database state post-execution
    conn = sqlite3.connect(str(ROOT_DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM exercises")
    after_total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    after_corr = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 0")
    after_fitamin = c.fetchone()[0]
    c.execute("SELECT id, name_fa, primary_muscle, equipment, is_corrective, video_cloud_url FROM exercises ORDER BY id ASC")
    after_rows = c.fetchall()
    after_hash = hashlib.sha256(repr(after_rows).encode('utf-8')).hexdigest()

    # Check for duplicate IDs
    c.execute("SELECT id, COUNT(*) FROM exercises GROUP BY id HAVING COUNT(*) > 1")
    dupe_ids = c.fetchall()
    check(len(dupe_ids) == 0, f"Zero duplicate primary keys found post-ingestion (dupes: {len(dupe_ids)})")

    # Check corrective exercises range [24..180]
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1 AND id >= 24 AND id <= 180")
    intact_corr_ids = c.fetchone()[0]
    check(intact_corr_ids == 157, f"All 157 corrective exercises retain exact IDs 24..180 (got {intact_corr_ids})")

    # Check foreign keys
    c.execute("SELECT COUNT(*) FROM workout_exercises we LEFT JOIN exercises e ON we.exercise_id = e.id WHERE e.id IS NULL")
    orphans = c.fetchone()[0]
    check(orphans == 0, f"Workout foreign key integrity preserved with 0 orphaned references (got {orphans})")

    conn.close()

    check(after_total == 1005, f"Post-run total exercises remains exactly 1,005 (no duplicate rows, got {after_total})")
    check(after_corr == 157, f"Post-run corrective exercises remains exactly 157 (no corruption, got {after_corr})")
    check(after_fitamin == 848, f"Post-run Fitamin exercises remains exactly 848 (got {after_fitamin})")
    check(after_hash == before_hash, f"Row checksum is 100% identical post-execution: {after_hash[:16]} == {before_hash[:16]}")


# ======================================================================================
# Target 2: AppData Mirror Consistency
# ======================================================================================

def compute_db_table_hash(db_path: Path, table_name: str) -> Tuple[int, str]:
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in c.fetchall()]
    cols_str = ", ".join(cols)
    c.execute(f"SELECT {cols_str} FROM {table_name} ORDER BY id ASC")
    rows = c.fetchall()
    row_count = len(rows)
    h = hashlib.sha256(repr(rows).encode('utf-8')).hexdigest()
    conn.close()
    return row_count, h

def test_appdata_mirror_consistency():
    print("\n" + "=" * 70)
    print("TARGET 2: APPDATA & LOCAL MIRROR DATABASE CONSISTENCY")
    print("=" * 70)

    mirrors = {
        "root_nemov": ROOT_DB_PATH,
        "root_yalda": YALDA_DB_PATH,
        "appdata_nemov": APPDATA_NEMOV_DB,
        "appdata_yalda_nemov": APPDATA_YALDA_NEMOV_DB,
        "appdata_yalda_yalda": APPDATA_YALDA_YALDA_DB
    }

    # Reference metrics from root_nemov
    ref_count, ref_hash = compute_db_table_hash(ROOT_DB_PATH, "exercises")
    print(f"  Reference 'exercises' (data/nemov.db): {ref_count} rows, SHA256={ref_hash[:16]}")

    for name, p in mirrors.items():
        if name == "root_nemov":
            continue
        exists = p.exists()
        check(exists, f"Mirror '{name}' exists at: {p}")
        if not exists:
            continue

        count, row_hash = compute_db_table_hash(p, "exercises")
        check(count == 1005, f"Mirror '{name}' exercises row count == 1,005 (got {count})")
        check(row_hash == ref_hash, f"Mirror '{name}' row checksum matches reference exactly: {row_hash[:16]} == {ref_hash[:16]}")

        # Check schemas
        conn_ref = sqlite3.connect(str(ROOT_DB_PATH))
        c_ref = conn_ref.cursor()
        c_ref.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exercises'")
        ref_sql = c_ref.fetchone()[0]
        conn_ref.close()

        conn_m = sqlite3.connect(str(p))
        c_m = conn_m.cursor()
        c_m.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exercises'")
        m_sql = c_m.fetchone()[0]
        conn_m.close()

        check(m_sql.strip() == ref_sql.strip(), f"Mirror '{name}' table schema for 'exercises' is identical")


# ======================================================================================
# Target 3: Desktop View Compatibility & Performance (< 50ms requirement)
# ======================================================================================

def test_desktop_view_compatibility():
    print("\n" + "=" * 70)
    print("TARGET 3: DESKTOP WORKOUT LIBRARY VIEW COMPATIBILITY & LATENCY")
    print("=" * 70)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from nemov.views.workout_library_view import WorkoutLibraryView
    from nemov.services.workout_service import WorkoutService

    # 1. Instantiation time
    t0 = time.time()
    view = WorkoutLibraryView()
    inst_time_ms = (time.time() - t0) * 1000
    print(f"  WorkoutLibraryView instantiation time: {inst_time_ms:.1f}ms")
    check(inst_time_ms < 500, f"WorkoutLibraryView instantiates within reasonable time (<500ms, took {inst_time_ms:.1f}ms)")

    # 2. Initial exercise count
    initial_rows = view.table.rowCount()
    check(initial_rows == 1005, f"Initial table rowCount is exactly 1,005 (got {initial_rows})")

    # 3. Muscle Filter Latency Benchmark (<50ms)
    test_muscles = [
        "chest", "legs_front", "legs_back", "glutes", "calves",
        "biceps", "triceps", "forearms", "abs", "shoulders",
        "lats", "traps", "upper_back", "lower_back", "neck",
        "legs", "back", "arms", "corrective", "all"
    ]

    muscle_latencies = []
    for m in test_muscles:
        idx = view.combo_muscle.findData(m)
        if idx >= 0:
            t_start = time.perf_counter()
            view.combo_muscle.setCurrentIndex(idx)
            view.load_exercises()
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            muscle_latencies.append((m, elapsed_ms, view.table.rowCount()))

    max_muscle_lat = max(lat for _, lat, _ in muscle_latencies)
    avg_muscle_lat = sum(lat for _, lat, _ in muscle_latencies) / len(muscle_latencies)
    print(f"  Muscle Filter Latencies: avg={avg_muscle_lat:.2f}ms, max={max_muscle_lat:.2f}ms across {len(muscle_latencies)} filters")
    for m, lat, count in muscle_latencies[:5]:
        print(f"    - Muscle '{m}': {lat:.2f}ms ({count} rows)")
    check(max_muscle_lat < 50.0, f"All muscle filters execute within < 50ms (max was {max_muscle_lat:.2f}ms)")

    # 4. Search Filter Latency Benchmark (<50ms)
    test_searches = [
        "پرس", "اسکوات", "شنا", "دمبل", "هالتر", "سیم کش", "پلانک", "ددلیفت", "a", "حرکت_ناموجود_تست"
    ]

    search_latencies = []
    # Reset muscle to all
    view.combo_muscle.setCurrentIndex(0)

    for q in test_searches:
        t_start = time.perf_counter()
        view.txt_search.setText(q)
        view.load_exercises()
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        search_latencies.append((q, elapsed_ms, view.table.rowCount()))

    # Reset search
    view.txt_search.setText("")
    view.load_exercises()

    max_search_lat = max(lat for _, lat, _ in search_latencies)
    avg_search_lat = sum(lat for _, lat, _ in search_latencies) / len(search_latencies)
    print(f"  Search Filter Latencies: avg={avg_search_lat:.2f}ms, max={max_search_lat:.2f}ms across {len(search_latencies)} queries")
    for q, lat, count in search_latencies[:5]:
        print(f"    - Query '{q}': {lat:.2f}ms ({count} rows)")
    check(max_search_lat < 50.0, f"All text search filters execute within < 50ms (max was {max_search_lat:.2f}ms)")

    # 5. Equipment Query Benchmark (<50ms)
    test_equips = ["barbell", "dumbbell", "machine", "cable", "bodyweight"]
    equip_latencies = []
    for eq in test_equips:
        t_start = time.perf_counter()
        exs = WorkoutService.get_all_exercises(equipment=eq)
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        equip_latencies.append((eq, elapsed_ms, len(exs)))

    max_equip_lat = max(lat for _, lat, _ in equip_latencies)
    print(f"  Equipment Query Latencies: max={max_equip_lat:.2f}ms across {len(equip_latencies)} categories")
    for eq, lat, count in equip_latencies:
        print(f"    - Equipment '{eq}': {lat:.2f}ms ({count} exercises)")
    check(max_equip_lat < 50.0, f"All equipment queries execute within < 50ms (max was {max_equip_lat:.2f}ms)")

    # 6. Rapid Stress Test & Memory Leak Check (100 rapid cycles)
    mem_before_mb = get_process_memory_mb()
    print(f"  Memory before stress test: {mem_before_mb:.2f} MB")

    t_stress_start = time.perf_counter()
    cycles = 100
    for i in range(cycles):
        if i % 3 == 0:
            view.txt_search.setText("پرس")
        elif i % 3 == 1:
            view.combo_muscle.setCurrentIndex(1) # corrective
        else:
            view.txt_search.setText("")
            view.combo_muscle.setCurrentIndex(0) # all
        app.processEvents()

    stress_elapsed = (time.perf_counter() - t_stress_start)
    mem_after_mb = get_process_memory_mb()
    mem_delta_mb = mem_after_mb - mem_before_mb
    print(f"  100 Rapid Filter Cycles completed in {stress_elapsed:.2f}s ({stress_elapsed/cycles*1000:.2f}ms/op)")
    print(f"  Memory after stress test: {mem_after_mb:.2f} MB (Delta: {mem_delta_mb:+.2f} MB)")
    check(mem_delta_mb < 20.0, f"Memory delta is bounded under 20MB after 100 rapid operations (delta was {mem_delta_mb:+.2f}MB)")

    # 7. Offscreen Screenshot Capture & Layout Geometry Check
    view.resize(1366, 768)
    view.show()
    app.processEvents()

    screenshot_path = SCRATCH_DIR / "qa_challenger_m2_workout_library_1366x768.png"
    pixmap = view.grab()
    pixmap.save(str(screenshot_path))
    check(screenshot_path.exists() and screenshot_path.stat().st_size > 10_000, f"Offscreen screenshot captured successfully: {screenshot_path} ({screenshot_path.stat().st_size:,} bytes)")


# ======================================================================================
# Main Execution Summary
# ======================================================================================

def main():
    print("=" * 70)
    print("EMPIRICAL CHALLENGER: M2 FITAMIN INGESTION & UI INTEGRATION QA")
    print("=" * 70)

    test_checkpoint_structure()
    test_idempotent_ingestion()
    test_appdata_mirror_consistency()
    test_desktop_view_compatibility()

    print("\n" + "=" * 70)
    print(f"ADVERSARIAL VERIFICATION SUMMARY: {passed_assertions} PASSED, {failed_assertions} FAILED")
    print("=" * 70)

    if failed_assertions > 0:
        print(f"❌ TEST SUITE FAILED with {failed_assertions} failures.")
        sys.exit(1)
    else:
        print("🎉 ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    main()
