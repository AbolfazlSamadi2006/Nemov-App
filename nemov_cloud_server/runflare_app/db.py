import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

BASE_DIR = Path(__file__).resolve().parent
SEED_FILE = BASE_DIR / "assets" / "seed_data.json"
LOCAL_SQLITE = BASE_DIR / "local_fallback.db"


def to_shamsi(dt: datetime = None) -> str:
    if dt is None:
        # Iran time UTC+3:30
        from datetime import timedelta
        dt = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
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
    jm, jd = 0, 0
    for i in range(11):
        days = 31 if i < 6 else 30
        if j_day_no < days:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= days
    if jm == 0:
        jm = 12
        jd = j_day_no + 1
    return f"{jy}/{jm:02d}/{jd:02d} {dt.hour:02d}:{dt.minute:02d}"


class DatabaseManager:
    """Manages PostgreSQL (primary) or SQLite (local fallback) for SMS and backup metadata."""

    def __init__(self):
        self.db_url = os.environ.get("DATABASE_URL", "").strip()
        self.use_pg = bool(self.db_url and HAS_PSYCOPG and self.db_url.startswith("postgres"))
        self.last_error = ""

    def _connect(self):
        if self.use_pg:
            return psycopg.connect(self.db_url, row_factory=dict_row, autocommit=True, connect_timeout=10)
        conn = sqlite3.connect(str(LOCAL_SQLITE))
        conn.row_factory = sqlite3.Row
        return conn

    def safe_init_and_seed(self):
        import time
        if self.use_pg:
            for attempt in range(3):
                try:
                    self.init_and_seed()
                    print("[DB] PostgreSQL connected, initialized and seeded successfully.", flush=True)
                    return
                except Exception as exc:
                    self.last_error = f"Attempt {attempt+1}: {exc}"
                    print(f"[DB WARNING] PostgreSQL init attempt {attempt+1} failed: {exc}", flush=True)
                    time.sleep(2)
            print("[DB FALLBACK] Switching to local SQLite fallback due to PostgreSQL error.", flush=True)
            self.use_pg = False
        self.init_and_seed()
        print("[DB] SQLite fallback initialized successfully.", flush=True)

    def init_and_seed(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_accounts (
                    phone VARCHAR(32) PRIMARY KEY,
                    trainer_name VARCHAR(255) NOT NULL DEFAULT 'مربی',
                    gym_name VARCHAR(255) NOT NULL DEFAULT 'نرم‌افزار مدیریت ورزشی نِمُو',
                    remaining INTEGER NOT NULL DEFAULT 0,
                    total_credited INTEGER NOT NULL DEFAULT 0,
                    total_used INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    registered_at_shamsi VARCHAR(64) DEFAULT '-',
                    last_recharge_shamsi VARCHAR(64) DEFAULT '-',
                    updated_at VARCHAR(64) DEFAULT ''
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_logs (
                    id VARCHAR(64) PRIMARY KEY,
                    date_shamsi VARCHAR(64) NOT NULL,
                    trainer_name VARCHAR(255) DEFAULT 'مربی',
                    trainer_phone VARCHAR(32) NOT NULL,
                    recipient VARCHAR(32) NOT NULL,
                    member_name VARCHAR(255) DEFAULT 'ورزشکار',
                    msg_type VARCHAR(64) DEFAULT 'custom',
                    detail TEXT DEFAULT '',
                    created_at VARCHAR(64) DEFAULT ''
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS backup_metadata (
                    phone VARCHAR(32) PRIMARY KEY,
                    trainer_name VARCHAR(255) NOT NULL DEFAULT 'مربی',
                    last_backup_iso VARCHAR(64) DEFAULT '',
                    last_backup_shamsi VARCHAR(64) DEFAULT '-',
                    file_size_mb DOUBLE PRECISION DEFAULT 0,
                    filename VARCHAR(128) DEFAULT 'nemov.db'
                );
            """)
            if not self.use_pg:
                conn.commit()

            # Check if seeding is needed
            cur.execute("SELECT COUNT(*) AS cnt FROM sms_accounts")
            row = cur.fetchone()
            sms_cnt = row["cnt"] if isinstance(row, dict) else row[0]

            cur.execute("SELECT COUNT(*) AS cnt FROM backup_metadata")
            row_b = cur.fetchone()
            bkp_cnt = row_b["cnt"] if isinstance(row_b, dict) else row_b[0]

            if SEED_FILE.exists() and (sms_cnt == 0 or bkp_cnt == 0):
                with open(SEED_FILE, "r", encoding="utf-8") as sf:
                    seed = json.load(sf)

                ph = "%s" if self.use_pg else "?"
                if sms_cnt == 0:
                    for acc in seed.get("sms_accounts", []):
                        cur.execute(
                            f"""
                            INSERT INTO sms_accounts (phone, trainer_name, remaining, total_credited, total_used, status, last_recharge_shamsi, registered_at_shamsi)
                            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                            ON CONFLICT (phone) DO NOTHING
                            """,
                            (
                                acc["phone"],
                                acc.get("trainer_name", "مربی"),
                                int(acc.get("remaining", 0)),
                                int(acc.get("total_credited", 0)),
                                int(acc.get("total_used", 0)),
                                acc.get("status", "pending"),
                                acc.get("last_recharge_shamsi", "-"),
                                acc.get("last_recharge_shamsi", "-"),
                            ),
                        )
                    for idx, log in enumerate(seed.get("sms_logs", [])):
                        cur.execute(
                            f"""
                            INSERT INTO sms_logs (id, date_shamsi, trainer_name, trainer_phone, recipient, member_name, msg_type, detail, created_at)
                            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                log["id"],
                                log.get("date_shamsi", "-"),
                                log.get("trainer_name", "مربی"),
                                log.get("trainer_phone", ""),
                                log.get("recipient", ""),
                                log.get("member_name", "ورزشکار"),
                                log.get("type", "custom"),
                                log.get("detail", ""),
                                f"2026-11-01T00:00:{59-min(idx,59):02d}Z",
                            ),
                        )

                if bkp_cnt == 0:
                    for idx, b in enumerate(seed.get("backups", [])):
                        cur.execute(
                            f"""
                            INSERT INTO backup_metadata (phone, trainer_name, last_backup_iso, last_backup_shamsi, file_size_mb, filename)
                            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                            ON CONFLICT (phone) DO NOTHING
                            """,
                            (
                                b["phone"],
                                b.get("trainer_name", "مربی"),
                                f"2026-11-01T00:00:{50-min(idx,49):02d}Z",
                                b.get("last_backup_shamsi", "-"),
                                float(b.get("file_size_mb", 0)),
                                b.get("filename", "nemov.db"),
                            ),
                        )
                if not self.use_pg:
                    conn.commit()

    def _ph(self):
        return "%s" if self.use_pg else "?"

    def get_all_backups(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM backup_metadata ORDER BY last_backup_iso DESC")
            return [dict(r) for r in cur.fetchall()]

    def upsert_backup(self, phone: str, trainer_name: str, iso_dt: str, shamsi_dt: str, size_mb: float):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO backup_metadata (phone, trainer_name, last_backup_iso, last_backup_shamsi, file_size_mb, filename)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'nemov.db')
                ON CONFLICT (phone) DO UPDATE SET
                    trainer_name = EXCLUDED.trainer_name,
                    last_backup_iso = EXCLUDED.last_backup_iso,
                    last_backup_shamsi = EXCLUDED.last_backup_shamsi,
                    file_size_mb = EXCLUDED.file_size_mb
                """,
                (phone, trainer_name, iso_dt, shamsi_dt, size_mb),
            )
            if not self.use_pg:
                conn.commit()

    def delete_backup(self, phone: str):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM backup_metadata WHERE phone = {ph}", (phone,))
            if not self.use_pg:
                conn.commit()

    def get_all_sms_accounts(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sms_accounts")
            rows = [dict(r) for r in cur.fetchall()]
            rows.sort(
                key=lambda a: (
                    0 if (a.get("remaining", 0) == 0 and a.get("total_credited", 0) == 0) else 1,
                    a.get("last_recharge_shamsi") or "",
                ),
                reverse=True,
            )
            return rows

    def get_sms_account(self, phone: str):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM sms_accounts WHERE phone = {ph}", (phone,))
            r = cur.fetchone()
            return dict(r) if r else None

    def upsert_sms_account(self, account: dict):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO sms_accounts (phone, trainer_name, gym_name, remaining, total_credited, total_used, status, registered_at_shamsi, last_recharge_shamsi, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT (phone) DO UPDATE SET
                    trainer_name = EXCLUDED.trainer_name,
                    gym_name = EXCLUDED.gym_name,
                    remaining = EXCLUDED.remaining,
                    total_credited = EXCLUDED.total_credited,
                    total_used = EXCLUDED.total_used,
                    status = EXCLUDED.status,
                    last_recharge_shamsi = EXCLUDED.last_recharge_shamsi,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    account["phone"],
                    account.get("trainer_name", "مربی"),
                    account.get("gym_name", "نرم‌افزار مدیریت ورزشی نِمُو"),
                    int(account.get("remaining", 0)),
                    int(account.get("total_credited", 0)),
                    int(account.get("total_used", 0)),
                    account.get("status", "pending"),
                    account.get("registered_at_shamsi", "-"),
                    account.get("last_recharge_shamsi", "-"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            if not self.use_pg:
                conn.commit()

    def delete_sms_account(self, phone: str):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM sms_accounts WHERE phone = {ph}", (phone,))
            if not self.use_pg:
                conn.commit()

    def add_sms_log(self, log: dict):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO sms_logs (id, date_shamsi, trainer_name, trainer_phone, recipient, member_name, msg_type, detail, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    log["id"],
                    log["date_shamsi"],
                    log.get("trainer_name", "مربی"),
                    log["trainer_phone"],
                    log["recipient"],
                    log.get("member_name", "ورزشکار"),
                    log.get("type", "custom"),
                    log.get("detail", ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            if not self.use_pg:
                conn.commit()

    def get_sms_logs(self, phone: str = None, limit: int = 100):
        ph = self._ph()
        with self._connect() as conn:
            cur = conn.cursor()
            if phone:
                cur.execute(
                    f"SELECT id, date_shamsi, trainer_name, trainer_phone, recipient, member_name, msg_type AS type, detail FROM sms_logs WHERE trainer_phone = {ph} ORDER BY created_at DESC LIMIT {ph}",
                    (phone, limit),
                )
            else:
                cur.execute(
                    f"SELECT id, date_shamsi, trainer_name, trainer_phone, recipient, member_name, msg_type AS type, detail FROM sms_logs ORDER BY created_at DESC LIMIT {ph}",
                    (limit,),
                )
            return [dict(r) for r in cur.fetchall()]
