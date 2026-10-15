"""Two-step login: 6-digit codes from an authenticator app (TOTP, RFC 6238) plus one-time backup codes."""
import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from urllib.parse import quote

ISSUER = "replyloop"
PERIOD = 30
BACKUP_COUNT = 10
_BACKUP_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"     # no 0/o, 1/l/i to avoid mix-ups
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")   # Persian/Arabic keyboards


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def pretty_secret(secret: str) -> str:
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


def otpauth_uri(secret: str, email: str) -> str:
    label = quote(f"{ISSUER}:{email}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&algorithm=SHA1&digits=6&period={PERIOD}"


def _code(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    h = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def clean(code: str) -> str:
    return "".join(ch for ch in str(code or "").translate(_DIGITS) if ch.isalnum()).lower()


def verify(secret: str, code: str, last_step: int = 0, now: float | None = None) -> int | None:
    """Returns the time step that matched (store it, so the same code can't be used twice), or None.
    Accepts the previous and next 30-second code too, for phones whose clock is slightly off."""
    code = clean(code)
    if len(code) != 6 or not code.isdigit():
        return None
    current = int((time.time() if now is None else now) // PERIOD)
    for step in (current - 1, current, current + 1):
        if step > (last_step or 0) and hmac.compare_digest(_code(secret, step), code):
            return step
    return None


# ---------------- backup codes ----------------
def _hash(code: str) -> str:
    return hashlib.sha256(clean(code).encode()).hexdigest()


def new_backup_codes() -> tuple[list[str], str]:
    """Returns (codes to show once, JSON of their hashes to store)."""
    codes = []
    for _ in range(BACKUP_COUNT):
        raw = "".join(secrets.choice(_BACKUP_ALPHABET) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes, json.dumps([_hash(c) for c in codes])


def use_backup_code(stored_json: str | None, code: str) -> str | None:
    """If `code` is an unused backup code, returns the updated JSON (with it removed); else None."""
    try:
        hashes = json.loads(stored_json or "[]")
    except ValueError:
        return None
    want = _hash(code)
    for h in hashes:
        if hmac.compare_digest(h, want):
            hashes.remove(h)
            return json.dumps(hashes)
    return None


def backup_left(stored_json: str | None) -> int:
    try:
        return len(json.loads(stored_json or "[]"))
    except ValueError:
        return 0
