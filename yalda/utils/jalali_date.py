import jdatetime
from datetime import datetime

PERSIAN_TO_ENG = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')

def normalize_digits(s: str) -> str:
    if not s:
        return ""
    return str(s).translate(PERSIAN_TO_ENG).strip()

def get_today_shamsi() -> str:
    """Returns today's date in Shamsi format: YYYY/MM/DD"""
    try:
        now = jdatetime.date.today()
        return now.strftime("%Y/%m/%d")
    except Exception:
        return ""

def get_now_shamsi_for_filename() -> str:
    """Returns current Shamsi date and time formatted safely for Windows filenames: YYYY-MM-DD_HH-MM"""
    try:
        now = jdatetime.datetime.now()
        return now.strftime("%Y-%m-%d_%H-%M")
    except Exception:
        now = datetime.now()
        return now.strftime("%Y-%m-%d_%H-%M")

def format_shamsi(date_str: str) -> str:
    """Ensures YYYY/MM/DD format with leading zeros and normalized digits"""
    if not date_str:
        return ""
    try:
        clean = normalize_digits(date_str).replace("-", "/").strip()
        parts = [p.strip() for p in clean.split("/") if p.strip()]
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            y, m, d = parts
            return f"{int(y):04d}/{int(m):02d}/{int(d):02d}"
    except Exception:
        pass
    return normalize_digits(date_str)

def parse_shamsi(shamsi_str: str) -> jdatetime.date:
    """Parses YYYY/MM/DD into a jdatetime.date object. Raises ValueError if invalid/incomplete."""
    if not shamsi_str:
        raise ValueError("Empty date string")
    clean = normalize_digits(shamsi_str).replace("-", "/").strip()
    parts = [p.strip() for p in clean.split("/") if p.strip()]
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid Shamsi date format: '{shamsi_str}'")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    return jdatetime.date(y, m, d)

def is_valid_shamsi(shamsi_str: str) -> bool:
    """Checks whether the given string is a complete and valid Shamsi date"""
    try:
        parse_shamsi(shamsi_str)
        return True
    except Exception:
        return False

def shamsi_to_gregorian(shamsi_str: str) -> datetime:
    """Converts a Shamsi date string (YYYY/MM/DD) to Python datetime safely"""
    if not shamsi_str:
        return None
    try:
        j_date = parse_shamsi(shamsi_str)
        g_date = j_date.togregorian()
        return datetime.combine(g_date, datetime.min.time())
    except Exception:
        return None

def gregorian_to_shamsi(dt) -> str:
    """Converts Python datetime or date to Shamsi date string safely"""
    if not dt:
        return ""
    try:
        if isinstance(dt, datetime):
            g_date = dt.date()
        else:
            g_date = dt
        j_date = jdatetime.date.fromgregorian(date=g_date)
        return j_date.strftime("%Y/%m/%d")
    except Exception:
        return ""

def add_days_shamsi(shamsi_str: str, days: int) -> str:
    """Adds N days to a Shamsi date string safely"""
    if not shamsi_str:
        return ""
    try:
        j_date = parse_shamsi(shamsi_str)
        new_date = j_date + jdatetime.timedelta(days=days)
        return new_date.strftime("%Y/%m/%d")
    except Exception:
        return ""

def add_months_shamsi(shamsi_str: str, months: int) -> str:
    """Adds N months to a Shamsi date string safely"""
    if not shamsi_str:
        return ""
    try:
        j_date = parse_shamsi(shamsi_str)
        month = j_date.month + months
        year = j_date.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(j_date.day, 29 if month == 12 else 30 if month > 6 else 31)
        new_date = jdatetime.date(year, month, day)
        return new_date.strftime("%Y/%m/%d")
    except Exception:
        return ""

def calculate_age_from_shamsi(birth_shamsi_str: str) -> int:
    """Calculates age in years from Shamsi birth date safely"""
    if not birth_shamsi_str:
        return 0
    try:
        b_date = parse_shamsi(birth_shamsi_str)
        today = jdatetime.date.today()
        age = today.year - b_date.year
        if (today.month, today.day) < (b_date.month, b_date.day):
            age -= 1
        return max(0, age)
    except Exception:
        return 0

def days_until_expire(expire_shamsi_str: str) -> int:
    """Returns number of days remaining until expiration safely"""
    if not expire_shamsi_str:
        return -999
    try:
        exp_date = parse_shamsi(expire_shamsi_str)
        today = jdatetime.date.today()
        delta = (exp_date - today).days
        return delta
    except Exception:
        return -999

def is_membership_active(expire_shamsi_str: str) -> bool:
    """Checks whether membership is active today safely"""
    try:
        days = days_until_expire(expire_shamsi_str)
        return days >= 0
    except Exception:
        return False
