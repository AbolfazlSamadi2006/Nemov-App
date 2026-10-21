import sys
import os
import sqlite3
from pathlib import Path

# Add project root
sys.path.insert(0, os.getcwd())

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import config

db_paths = [
    config.DB_PATH,
    config.DATA_DIR / "nemov.db",
    config.DATA_DIR / "yalda.db",
    config.APPDATA_DATA_DIR / "nemov.db",
    config.APPDATA_DATA_DIR / "yalda.db",
    config.LEGACY_APPDATA_DATA_DIR / "yalda.db",
]

# Also check dist if exists
for dist_candidate in [
    Path("dist/Nemov/data/nemov.db"),
    Path("dist/Nemov/data/yalda.db"),
    Path("dist/Yalda/data/yalda.db"),
]:
    if dist_candidate.exists():
        db_paths.append(dist_candidate)

# Deduplicate paths preserving priority order
seen_paths = set()
unique_db_paths = []
for p in db_paths:
    res = p.resolve() if p.exists() else p
    if res not in seen_paths:
        seen_paths.add(res)
        unique_db_paths.append(p)
db_paths = unique_db_paths

print("Starting clean up of test trainers (علی محمدی و مینا احمدی)...")

for db_p in db_paths:
    if not db_p.exists():
        print(f"Skipping non-existent db: {db_p}")
        continue
    print(f"\nProcessing database: {db_p}")
    conn = sqlite3.connect(db_p)
    cur = conn.cursor()

    # Find test user IDs
    cur.execute("""
        SELECT id, username, first_name, last_name, phone 
        FROM users 
        WHERE (first_name = 'علی' AND last_name = 'محمدی')
           OR (first_name = 'مینا' AND last_name = 'احمدی')
           OR username LIKE 'tr_ali_%'
           OR username LIKE 'tr_mina_%'
    """)
    test_users = cur.fetchall()
    print(f"Found {len(test_users)} test users:")
    user_ids = []
    for u in test_users:
        print(f"  ID={u[0]}, Username={u[1]}, Name={u[2]} {u[3]}, Phone={u[4]}")
        user_ids.append(u[0])

    # Find test members
    cur.execute("""
        SELECT id, first_name, last_name, phone 
        FROM members 
        WHERE first_name LIKE 'عضو_علی_%' 
           OR first_name LIKE 'عضو_مینا_%'
           OR phone LIKE '0912b7f2%'
           OR phone LIKE '09123831%'
           OR phone LIKE '0912437c%'
           OR phone LIKE '09129333%'
           OR phone LIKE '0912ec49%'
    """)
    test_members = cur.fetchall()
    print(f"Found {len(test_members)} test members:")
    member_ids = []
    for m in test_members:
        print(f"  ID={m[0]}, Name={m[1]} {m[2]}, Phone={m[3]}")
        member_ids.append(m[0])

    if member_ids:
        m_str = ",".join(str(x) for x in member_ids)
        # Check all child tables
        for child_tbl in ["workouts", "nutrition_plans", "payments", "attendance", "body_assessments", "member_notes", "progress_photos"]:
            try:
                cur.execute(f"DELETE FROM {child_tbl} WHERE member_id IN ({m_str})")
            except Exception:
                pass
        cur.execute(f"DELETE FROM members WHERE id IN ({m_str})")
        print(f"Deleted {len(member_ids)} test members.")

    if user_ids:
        u_str = ",".join(str(x) for x in user_ids)
        for child_tbl in ["workouts", "nutrition_plans", "payments", "attendance", "body_assessments", "system_settings"]:
            try:
                cur.execute(f"DELETE FROM {child_tbl} WHERE user_id IN ({u_str})")
            except Exception:
                pass
        cur.execute(f"DELETE FROM users WHERE id IN ({u_str})")
        print(f"Deleted {len(user_ids)} test users.")

    conn.commit()

    # Verify remaining users and members
    cur.execute("SELECT id, username, first_name, last_name, role FROM users")
    rem_users = cur.fetchall()
    print("Remaining users:")
    for u in rem_users:
        print(f"  ID={u[0]}, Username={u[1]}, Name={u[2]} {u[3]}, Role={u[4]}")

    cur.execute("SELECT id, first_name, last_name, phone FROM members")
    rem_members = cur.fetchall()
    print(f"Remaining members count: {len(rem_members)}")
    for m in rem_members:
        print(f"  ID={m[0]}, Name={m[1]} {m[2]}, Phone={m[3]}")

    conn.close()

print("\nCleanup completed successfully!")
