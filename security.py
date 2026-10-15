"""Passwords, login sessions, brute-force protection, and encryption of Instagram tokens."""
import base64
import hashlib
import hmac
import secrets
import threading
import time

from cryptography.fernet import Fernet, InvalidToken

import store
from config import SECRET_KEY

SESSION_COOKIE = "rl_session"
PENDING_COOKIE = "rl_2fa"          # short-lived: password/Google was right, waiting for the 6-digit code
PENDING_MINUTES = 5
REMEMBER_DAYS = 30
SHORT_SESSION_DAYS = 1
MIN_PASSWORD = 10

# ---------------- passwords (scrypt, from Python's standard library) ----------------
_N, _R, _P = 2 ** 14, 8, 1


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        h = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(h.hex(), digest)
    except Exception:
        return False


_DUMMY_HASH = hash_password(secrets.token_hex(8))   # so unknown emails take as long as wrong passwords


def password_problem(pw: str) -> str | None:
    if len(pw) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    return None


# ---------------- sessions ----------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(user_id: int, remember: bool, user_agent: str = "", ip: str = "") -> tuple[str, int | None]:
    """Returns (cookie value, cookie max-age or None for a browser-session cookie)."""
    token = secrets.token_urlsafe(32)
    days = REMEMBER_DAYS if remember else SHORT_SESSION_DAYS
    store.create_session(_hash_token(token), user_id, days, user_agent, ip)
    return token, (days * 86400 if remember else None)


def session_id(token: str | None) -> str:
    """A public id for a session (first 16 characters of its stored hash; the cookie itself is never shown)."""
    return _hash_token(token)[:16] if token else ""


def start_pending(user_id: int, remember: bool) -> str:
    token = secrets.token_urlsafe(32)
    store.create_pending_login(_hash_token(token), user_id, remember, PENDING_MINUTES)
    return token


def pending(token: str | None):
    return store.pending_login(_hash_token(token)) if token else None


def pending_failed(token: str) -> int:
    return store.pending_login_failed(_hash_token(token))


def end_pending(token: str | None):
    if token:
        store.delete_pending_login(_hash_token(token))


def session_user(token: str | None):
    return store.session_user(_hash_token(token)) if token else None


def end_session(token: str | None):
    if token:
        store.delete_session(_hash_token(token))


def end_other_sessions(user_id: int, keep_token: str | None):
    store.delete_user_sessions(user_id, _hash_token(keep_token) if keep_token else None)


# ---------------- brute-force protection ----------------
_fails: dict[str, list[float]] = {}
_fails_lock = threading.Lock()
MAX_FAILS, WINDOW = 5, 15 * 60


def too_many_attempts(*keys: str) -> bool:
    cutoff = time.time() - WINDOW
    with _fails_lock:
        return any(len([t for t in _fails.get(k, []) if t > cutoff]) >= MAX_FAILS for k in keys)


def record_failure(*keys: str):
    now = time.time()
    with _fails_lock:
        for k in keys:
            _fails[k] = [t for t in _fails.get(k, []) if t > now - WINDOW] + [now]


def clear_failures(*keys: str):
    with _fails_lock:
        for k in keys:
            _fails.pop(k, None)


def login(email: str, password: str):
    """Returns the user, or None. Takes the same time whether or not the email exists."""
    user = store.user_by_email(email.strip().lower())
    ok = check_password(password, user["pw_hash"] if user else _DUMMY_HASH)
    return user if (user and ok) else None


# ---------------- encrypting Instagram tokens at rest ----------------
_key = SECRET_KEY or secrets.token_hex(32)   # without SECRET_KEY, tokens only survive until restart
EPHEMERAL_KEY = not SECRET_KEY
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(_key.encode()).digest()))


def encrypt(text: str) -> str:
    return _fernet.encrypt(text.encode()).decode()


def decrypt(blob: str | None) -> str | None:
    if not blob:
        return None
    try:
        return _fernet.decrypt(blob.encode()).decode()
    except InvalidToken:
        return None
