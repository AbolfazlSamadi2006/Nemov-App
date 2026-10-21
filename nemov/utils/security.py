import hashlib
import secrets

def normalize_digits(s: str) -> str:
    """Convert Persian and Arabic numerals to ASCII English numerals."""
    if not s:
        return s
    persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return s.translate(persian_to_eng)

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 with a random salt."""
    salt = secrets.token_hex(16)
    pwd_bytes = (password + salt).encode('utf-8')
    h = hashlib.sha256(pwd_bytes).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, hashed_str: str) -> bool:
    """Verifies a password against a stored salt:hash string."""
    if not hashed_str or ":" not in hashed_str:
        return False
    try:
        salt, stored_hash = hashed_str.split(":", 1)
        pwd_bytes = (password + salt).encode('utf-8')
        computed_hash = hashlib.sha256(pwd_bytes).hexdigest()
        if secrets.compare_digest(stored_hash, computed_hash):
            return True
        # Check with normalized digits if digits are present
        normalized = normalize_digits(password)
        if normalized != password:
            norm_bytes = (normalized + salt).encode('utf-8')
            norm_hash = hashlib.sha256(norm_bytes).hexdigest()
            return secrets.compare_digest(stored_hash, norm_hash)
        return False
    except Exception:
        return False
