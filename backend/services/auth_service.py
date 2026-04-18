import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "weatherwise-super-secret-key-change-in-prod-2026")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7


# ── Password Hashing (Python built-in hashlib — no bcrypt dependency) ────────

def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 ile şifrele (Python stdlib)."""
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}${key.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Saklanan hash ile karşılaştır."""
    try:
        salt, key_hex = stored.split("$", 1)
        key = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
