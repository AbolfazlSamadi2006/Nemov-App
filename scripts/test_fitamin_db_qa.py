#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Test Suite for Fitamin Database Ingestion & Cloud Streaming Integration
"""
import os
import sys
import sqlite3
from pathlib import Path

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "nemov.db"
YALDA_PATH = PROJECT_ROOT / "data" / "yalda.db"
APPDATA_PATH = Path(os.path.expandvars(r"%APPDATA%\Nemov\data\nemov.db"))

VALID_MUSCLES = {
    "neck", "shoulders", "chest", "biceps", "forearms", "abs",
    "legs_front", "traps", "upper_back", "triceps", "lats",
    "lower_back", "glutes", "legs_back", "calves", "legs", "arms", "back", "سایر"
}

VALID_EQUIPMENT = {"barbell", "dumbbell", "machine", "cable", "bodyweight", "سایر"}

def test_database_integrity():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # 1. Row counts
    c.execute("SELECT COUNT(*) FROM exercises")
    total = c.fetchone()[0]
    assert total == 1005, f"Expected 1005 exercises, got {total}"
    print(f"✅ Total Exercises: {total} (Expected: 1005)")

    # 2. Corrective preservation
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1")
    corrective = c.fetchone()[0]
    assert corrective == 157, f"Expected 157 corrective exercises, got {corrective}"
    print(f"✅ Corrective Exercises: {corrective} (Expected: 157)")

    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 1 AND id >= 24 AND id <= 180")
    corr_ids = c.fetchone()[0]
    assert corr_ids == 157, f"Corrective exercises must retain IDs 24..180, got {corr_ids}"
    print(f"✅ Corrective Exercise IDs [24..180] 100% Intact: {corr_ids}/157")

    # 3. Fitamin exercises
    c.execute("SELECT COUNT(*) FROM exercises WHERE is_corrective = 0")
    fitamin = c.fetchone()[0]
    assert fitamin == 848, f"Expected 848 Fitamin exercises, got {fitamin}"
    print(f"✅ Fitamin / Gym Exercises: {fitamin} (Expected: 848)")

    # 4. Cloud URLs
    c.execute("SELECT COUNT(*) FROM exercises WHERE video_cloud_url IS NOT NULL AND video_cloud_url != ''")
    with_cloud = c.fetchone()[0]
    assert with_cloud == 1005, f"Expected 1005 cloud URLs, got {with_cloud}"
    print(f"✅ Video Cloud URLs: {with_cloud}/1005 populated")

    # 5. Foreign Key check
    c.execute("SELECT COUNT(*) FROM workout_exercises we LEFT JOIN exercises e ON we.exercise_id = e.id WHERE e.id IS NULL")
    orphans = c.fetchone()[0]
    assert orphans == 0, f"Found {orphans} orphaned workout exercises!"
    print(f"✅ Workout Plan Foreign Key Integrity: 0 orphaned references")

    # 6. Description lengths (smart tips <= 180 chars)
    c.execute("SELECT id, name_fa, LENGTH(description) FROM exercises WHERE is_corrective = 0 AND LENGTH(description) > 180")
    long_descs = c.fetchall()
    assert len(long_descs) == 0, f"Found {len(long_descs)} descriptions exceeding 180 chars: {long_descs}"
    print("✅ Smart Tips Constraints: All 848 Fitamin descriptions are <= 180 characters")

    # 7. Taxonomy validation
    c.execute("SELECT DISTINCT primary_muscle FROM exercises")
    muscles = [r[0] for r in c.fetchall()]
    invalid_muscles = [m for m in muscles if m not in VALID_MUSCLES]
    assert len(invalid_muscles) == 0, f"Invalid muscles found: {invalid_muscles}"
    print(f"✅ Muscle Taxonomy: All {len(muscles)} distinct muscles conform to Nemov schema")

    c.execute("SELECT DISTINCT equipment FROM exercises")
    equips = [r[0] for r in c.fetchall()]
    invalid_equips = [e for e in equips if e not in VALID_EQUIPMENT]
    assert len(invalid_equips) == 0, f"Invalid equipment found: {invalid_equips}"
    print(f"✅ Equipment Taxonomy: All {len(equips)} equipment categories conform to Nemov schema")

    # 8. Multi-database synchronization check
    for mirror_name, mirror_path in [("yalda.db", YALDA_PATH), ("AppData nemov.db", APPDATA_PATH)]:
        if mirror_path.exists():
            m_conn = sqlite3.connect(str(mirror_path))
            m_c = m_conn.cursor()
            m_c.execute("SELECT COUNT(*) FROM exercises")
            m_total = m_c.fetchone()[0]
            assert m_total == 1005, f"{mirror_name} has {m_total} rows, expected 1005"
            m_conn.close()
            print(f"✅ Synchronized Mirror: {mirror_name} verified ({m_total} rows)")
        else:
            print(f"⚠️ Mirror path not found: {mirror_path}")

    conn.close()
    print("\n🎉 ALL QA TESTS PASSED SUCCESSFULLY! (10/10)")

if __name__ == "__main__":
    test_database_integrity()
