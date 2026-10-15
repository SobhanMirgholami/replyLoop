"""Everything the app saves. Each Instagram account has its own rules, posts, settings and inbox."""
import json
from datetime import datetime, timedelta, timezone

import db
from db import ID

DEFAULT_SETTINGS = {
    "ai_fallback": True,
    "brand_voice": "خودمونی و کوتاه (حداکثر 2 جمله). به همون زبونی که کامنت نوشته شده جواب بده. حداکثر یه ایموجی.",
    "ignore_keywords": ["follow me", "check my page", "dm me for promo", "فالو کن", "پیج منو ببین", "فالو = فالو"],
    # Followers-only DMs (each rule can override these). Edit them in Settings for English-speaking audiences.
    "gate_message": "برای گرفتن لینک، اول پیج ما رو فالو کن 👇 بعد دکمه رو بزن.",
    "gate_button": "فالو کردم ✅",
    "not_following_message": "هنوز فالومون نکردی 🙈 اول پیج رو فالو کن، بعد دوباره دکمه رو بزن.",
    "check_failed_message": "تقریباً تمومه! یه پیام، هرچی خواستی، همین‌جا بفرست تا دوباره چک کنم 🙏",
}
BUTTON_MAX = 20      # Instagram's button title limit
HEADLINE_MAX = 640   # Instagram's button-template text limit
DM_EXPIRY_DAYS = 7

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS pending_logins (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,"
    " remember INTEGER DEFAULT 1, attempts INTEGER DEFAULT 0, expires_at TEXT NOT NULL)",
    f"CREATE TABLE IF NOT EXISTS users (id {ID}, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,"
    " is_owner INTEGER DEFAULT 0, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,"
    " expires_at TEXT NOT NULL, created_at TEXT)",
    f"CREATE TABLE IF NOT EXISTS accounts (id {ID}, ig_user_id TEXT UNIQUE NOT NULL, username TEXT,"
    " token_enc TEXT, token_refreshed_at TEXT, live INTEGER DEFAULT 0, is_demo INTEGER DEFAULT 0,"
    " last_error TEXT, created_at TEXT, live_since TEXT)",
    "CREATE TABLE IF NOT EXISTS settings (account_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT,"
    " PRIMARY KEY (account_id, key))",
    f"CREATE TABLE IF NOT EXISTS rules (id {ID}, account_id INTEGER NOT NULL, media_id TEXT,"
    " position INTEGER DEFAULT 0, name TEXT, keywords TEXT, reply TEXT DEFAULT '', dm TEXT DEFAULT '',"
    " followers_only INTEGER DEFAULT 0, gate_text TEXT DEFAULT '', gate_button TEXT DEFAULT '',"
    " not_following_text TEXT DEFAULT '', enabled INTEGER DEFAULT 1, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS posts (account_id INTEGER NOT NULL, media_id TEXT NOT NULL,"
    " context TEXT DEFAULT '', ai_enabled INTEGER DEFAULT 1, autoreply_enabled INTEGER DEFAULT 1,"
    " PRIMARY KEY (account_id, media_id))",
    "CREATE TABLE IF NOT EXISTS comments (comment_id TEXT PRIMARY KEY, account_id INTEGER NOT NULL,"
    " media_id TEXT, username TEXT, text TEXT, source TEXT, reply TEXT, status TEXT, dm_status TEXT,"
    " created_at TEXT)",
    f"CREATE TABLE IF NOT EXISTS events (id {ID}, account_id INTEGER NOT NULL, comment_id TEXT NOT NULL,"
    " kind TEXT, text TEXT, button TEXT, created_at TEXT)",
    f"CREATE TABLE IF NOT EXISTS dm_requests (id {ID}, account_id INTEGER NOT NULL, igsid TEXT,"
    " comment_id TEXT, media_id TEXT, text TEXT, button TEXT, not_following_text TEXT, status TEXT,"
    " created_at TEXT, updated_at TEXT)",
    "CREATE TABLE IF NOT EXISTS seen_messages (mid TEXT PRIMARY KEY, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS follower_history (account_id INTEGER NOT NULL, day TEXT NOT NULL, followers INTEGER,"
    " PRIMARY KEY (account_id, day))",
    "CREATE TABLE IF NOT EXISTS insight_cache (account_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT, fetched_at TEXT,"
    " PRIMARY KEY (account_id, key))",
    "CREATE TABLE IF NOT EXISTS stories (story_id TEXT PRIMARY KEY, account_id INTEGER NOT NULL, media_type TEXT,"
    " thumb TEXT, permalink TEXT, posted_at TEXT, metrics TEXT, captured_at TEXT)",
    "CREATE INDEX IF NOT EXISTS idx_stories_account ON stories (account_id, posted_at)",
    "CREATE INDEX IF NOT EXISTS idx_comments_account ON comments (account_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_events_comment ON events (comment_id)",
    "CREATE INDEX IF NOT EXISTS idx_dm_person ON dm_requests (account_id, igsid)",
    "CREATE INDEX IF NOT EXISTS idx_rules_account ON rules (account_id, media_id, position)",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ago(**kw) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kw)).isoformat()


# Columns added after the first release. Existing databases get them on startup; nothing is lost.
MIGRATIONS = [
    ("users", "role", "TEXT DEFAULT 'editor'"),          # owner is is_owner=1; others: editor or viewer
    ("users", "totp_secret_enc", "TEXT"),               # two-step login secret (encrypted)
    ("users", "totp_pending_enc", "TEXT"),              # secret being set up, not active yet
    ("users", "totp_last_step", "INTEGER DEFAULT 0"),   # last code used, so it can't be replayed
    ("users", "backup_codes", "TEXT"),                  # JSON list of sha256 hashes
    ("sessions", "last_seen_at", "TEXT"),
    ("sessions", "user_agent", "TEXT"),
    ("sessions", "ip", "TEXT"),
]
ROLES = ("editor", "viewer")


def init():
    db.run_many(SCHEMA)
    for table, col, decl in MIGRATIONS:
        if db.IS_PG:
            db.run(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {decl}")
        elif col not in {r["name"] for r in db.rows(f"PRAGMA table_info({table})")}:
            db.run(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


# ---------------- users & sessions ----------------
def user_count() -> int:
    return db.row("SELECT COUNT(*) AS n FROM users")["n"]


def create_user(email: str, pw_hash: str, is_owner=False, role="editor") -> dict:
    return db.row("INSERT INTO users (email, pw_hash, is_owner, role, created_at) VALUES (?,?,?,?,?) RETURNING *",
                  (email, pw_hash, int(is_owner), role, now()))


def user_by_email(email: str):
    return db.row("SELECT * FROM users WHERE email=?", (email,))


def user_by_id(uid: int):
    return db.row("SELECT * FROM users WHERE id=?", (uid,))


def list_users() -> list[dict]:
    return [{"id": r["id"], "email": r["email"], "is_owner": bool(r["is_owner"]), "role": role_of(r),
             "two_factor": bool(r["totp_secret_enc"]), "created_at": r["created_at"]}
            for r in db.rows("SELECT * FROM users ORDER BY id")]


def role_of(user) -> str:
    return "owner" if user.get("is_owner") else (user.get("role") if user.get("role") in ROLES else "editor")


def set_role(uid: int, role: str) -> bool:
    return db.run("UPDATE users SET role=? WHERE id=? AND is_owner=0", (role, uid)) > 0


def set_totp_pending(uid: int, secret_enc: str | None):
    db.run("UPDATE users SET totp_pending_enc=? WHERE id=?", (secret_enc, uid))


def enable_totp(uid: int, secret_enc: str, step: int, backup_json: str):
    db.run("UPDATE users SET totp_secret_enc=?, totp_pending_enc=NULL, totp_last_step=?, backup_codes=? WHERE id=?",
           (secret_enc, step, backup_json, uid))


def disable_totp(uid: int):
    db.run("UPDATE users SET totp_secret_enc=NULL, totp_pending_enc=NULL, totp_last_step=0, backup_codes=NULL WHERE id=?",
           (uid,))


def set_totp_step(uid: int, step: int) -> bool:
    """Records a used code; returns False if a newer/same code was already used (replay)."""
    return db.run("UPDATE users SET totp_last_step=? WHERE id=? AND COALESCE(totp_last_step, 0) < ?",
                  (step, uid, step)) > 0


def set_backup_codes(uid: int, backup_json: str):
    db.run("UPDATE users SET backup_codes=? WHERE id=?", (backup_json, uid))


def replace_backup_codes(uid: int, old_json: str | None, new_json: str) -> bool:
    """Uses up a backup code; fails if another request changed the list first (no double use)."""
    return db.run("UPDATE users SET backup_codes=? WHERE id=? AND backup_codes=?", (new_json, uid, old_json or "")) > 0


# ---------------- sign-in waiting for the two-step code ----------------
def create_pending_login(token_hash: str, uid: int, remember: bool, minutes: int = 5):
    db.run("DELETE FROM pending_logins WHERE expires_at < ?", (now(),))
    db.run("INSERT INTO pending_logins (token_hash, user_id, remember, expires_at) VALUES (?,?,?,?)",
           (token_hash, uid, int(remember), (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()))


def pending_login(token_hash: str):
    return db.row("SELECT * FROM pending_logins WHERE token_hash=? AND expires_at > ?", (token_hash, now()))


def pending_login_failed(token_hash: str) -> int:
    db.run("UPDATE pending_logins SET attempts = attempts + 1 WHERE token_hash=?", (token_hash,))
    r = db.row("SELECT attempts FROM pending_logins WHERE token_hash=?", (token_hash,))
    return r["attempts"] if r else 99


def delete_pending_login(token_hash: str):
    db.run("DELETE FROM pending_logins WHERE token_hash=?", (token_hash,))


def set_password(uid: int, pw_hash: str):
    db.run("UPDATE users SET pw_hash=? WHERE id=?", (pw_hash, uid))


def delete_user(uid: int) -> bool:
    db.run("DELETE FROM sessions WHERE user_id=?", (uid,))
    return db.run("DELETE FROM users WHERE id=? AND is_owner=0", (uid,)) > 0


def create_session(token_hash: str, uid: int, days: int, user_agent: str = "", ip: str = ""):
    db.run("INSERT INTO sessions (token_hash, user_id, expires_at, created_at, last_seen_at, user_agent, ip)"
           " VALUES (?,?,?,?,?,?,?)",
           (token_hash, uid, (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(), now(), now(),
            (user_agent or "")[:300], (ip or "")[:64]))


def session_user(token_hash: str):
    r = db.row("SELECT u.id, u.email, u.is_owner, u.role, u.totp_secret_enc, s.last_seen_at FROM sessions s"
               " JOIN users u ON u.id = s.user_id WHERE s.token_hash=? AND s.expires_at > ?", (token_hash, now()))
    if not r:
        return None
    if not r["last_seen_at"] or r["last_seen_at"] < ago(minutes=5):    # don't write on every request
        db.run("UPDATE sessions SET last_seen_at=? WHERE token_hash=?", (now(), token_hash))
    return {"id": r["id"], "email": r["email"], "is_owner": r["is_owner"], "role": role_of(r),
            "two_factor": bool(r["totp_secret_enc"])}


def list_sessions(uid: int) -> list[dict]:
    return db.rows("SELECT token_hash, created_at, last_seen_at, user_agent, ip FROM sessions"
                   " WHERE user_id=? AND expires_at > ? ORDER BY COALESCE(last_seen_at, created_at) DESC", (uid, now()))


def delete_session_by_prefix(uid: int, prefix: str) -> bool:
    if len(prefix) < 16:
        return False
    return db.run("DELETE FROM sessions WHERE user_id=? AND token_hash LIKE ?", (uid, prefix + "%")) > 0


def delete_session(token_hash: str):
    db.run("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def delete_user_sessions(uid: int, keep_hash: str | None = None):
    db.run("DELETE FROM sessions WHERE user_id=? AND token_hash != ?", (uid, keep_hash or ""))


def purge_old():
    db.run("DELETE FROM sessions WHERE expires_at < ?", (now(),))
    db.run("DELETE FROM pending_logins WHERE expires_at < ?", (now(),))
    db.run("DELETE FROM seen_messages WHERE created_at < ?", (ago(days=3),))


# ---------------- Instagram accounts ----------------
def _account(r):
    if not r:
        return None
    r = dict(r)
    r["live"] = bool(r["live"])
    r["is_demo"] = bool(r["is_demo"])
    return r


def list_accounts() -> list[dict]:
    return [_account(r) for r in db.rows("SELECT * FROM accounts ORDER BY id")]


def get_account(aid: int):
    return _account(db.row("SELECT * FROM accounts WHERE id=?", (aid,)))


def account_by_ig_id(ig_user_id: str):
    return _account(db.row("SELECT * FROM accounts WHERE ig_user_id=?", (str(ig_user_id),)))


def upsert_account(ig_user_id: str, username: str, token_enc: str | None, is_demo=False) -> dict:
    return _account(db.row(
        "INSERT INTO accounts (ig_user_id, username, token_enc, token_refreshed_at, is_demo, created_at)"
        " VALUES (?,?,?,?,?,?) ON CONFLICT (ig_user_id) DO UPDATE SET username=excluded.username,"
        " token_enc=excluded.token_enc, token_refreshed_at=excluded.token_refreshed_at, last_error=NULL"
        " RETURNING *", (str(ig_user_id), username, token_enc, now(), int(is_demo), now())))


def update_account(aid: int, **fields):
    allowed = {"live", "token_enc", "token_refreshed_at", "last_error", "username", "live_since"}
    sets = [(k, int(v) if isinstance(v, bool) else v) for k, v in fields.items() if k in allowed]
    if sets:
        db.run(f"UPDATE accounts SET {', '.join(k + '=?' for k, _ in sets)} WHERE id=?",
               [v for _, v in sets] + [aid])


def delete_account(aid: int):
    for table in ("rules", "posts", "settings", "comments", "events", "dm_requests", "follower_history", "insight_cache", "stories"):
        db.run(f"DELETE FROM {table} WHERE account_id=?", (aid,))
    db.run("DELETE FROM accounts WHERE id=?", (aid,))


# ---------------- settings ----------------
def get_settings(aid: int) -> dict:
    saved = {r["key"]: json.loads(r["value"]) for r in db.rows("SELECT key, value FROM settings WHERE account_id=?", (aid,))}
    return {**DEFAULT_SETTINGS, **saved}


def save_settings(aid: int, values: dict):
    for key in DEFAULT_SETTINGS:
        if key in values:
            db.run("INSERT INTO settings (account_id, key, value) VALUES (?,?,?)"
                   " ON CONFLICT (account_id, key) DO UPDATE SET value=excluded.value",
                   (aid, key, json.dumps(values[key], ensure_ascii=False)))


# ---------------- rules ----------------
RULE_FIELDS = ("name", "keywords", "reply", "dm", "followers_only", "gate_text", "gate_button",
               "not_following_text", "enabled")


def _rule(r):
    if not r:
        return None
    r = dict(r)
    r["keywords"] = json.loads(r["keywords"] or "[]")
    for k in ("followers_only", "enabled"):
        r[k] = bool(r[k])
    for k in ("reply", "dm", "gate_text", "gate_button", "not_following_text", "name"):
        r[k] = r[k] or ""
    return r


def list_rules(aid: int, media_id: str | None) -> list[dict]:
    """media_id=None: the account's global rules. Ordered: the first match wins."""
    if media_id is None:
        rs = db.rows("SELECT * FROM rules WHERE account_id=? AND media_id IS NULL ORDER BY position, id", (aid,))
    else:
        rs = db.rows("SELECT * FROM rules WHERE account_id=? AND media_id=? ORDER BY position, id", (aid, media_id))
    return [_rule(r) for r in rs]


def rules_for(aid: int, media_id: str | None) -> list[tuple[dict, str]]:
    post = [(r, "post") for r in list_rules(aid, media_id) if r["enabled"]] if media_id else []
    glob = [(r, "global") for r in list_rules(aid, None) if r["enabled"]]
    return post + glob


def get_rule(aid: int, rid: int):
    return _rule(db.row("SELECT * FROM rules WHERE id=? AND account_id=?", (rid, aid)))


def _params(fields: dict) -> list:
    return [json.dumps(v, ensure_ascii=False) if k == "keywords" else int(v) if isinstance(v, bool) else v
            for k, v in ((k, fields[k]) for k in RULE_FIELDS)]


def create_rule(aid: int, media_id: str | None, fields: dict) -> dict:
    scope = "media_id IS NULL" if media_id is None else "media_id=?"
    scope_params = (aid,) if media_id is None else (aid, media_id)
    pos = db.row(f"SELECT COALESCE(MAX(position), -1) + 1 AS p FROM rules WHERE account_id=? AND {scope}", scope_params)["p"]
    cols = ", ".join(RULE_FIELDS)
    marks = ", ".join("?" * len(RULE_FIELDS))
    return _rule(db.row(f"INSERT INTO rules (account_id, media_id, position, created_at, {cols})"
                        f" VALUES (?,?,?,?, {marks}) RETURNING *", [aid, media_id, pos, now()] + _params(fields)))


def update_rule(aid: int, rid: int, fields: dict):
    sets = ", ".join(f"{k}=?" for k in RULE_FIELDS)
    if db.run(f"UPDATE rules SET {sets} WHERE id=? AND account_id=?", _params(fields) + [rid, aid]) == 0:
        return None
    return get_rule(aid, rid)


def delete_rule(aid: int, rid: int) -> bool:
    return db.run("DELETE FROM rules WHERE id=? AND account_id=?", (rid, aid)) > 0


def reorder_rules(aid: int, ids: list[int]):
    for pos, rid in enumerate(ids):
        db.run("UPDATE rules SET position=? WHERE id=? AND account_id=?", (pos, int(rid), aid))


def rule_counts(aid: int) -> dict:
    rs = db.rows("SELECT media_id, COUNT(*) AS n, MAX(followers_only) AS gated FROM rules"
                 " WHERE account_id=? AND media_id IS NOT NULL GROUP BY media_id", (aid,))
    return {r["media_id"]: {"n": r["n"], "gated": bool(r["gated"])} for r in rs}


# ---------------- per-post settings ----------------
DEFAULT_POST = {"context": "", "ai_enabled": True, "autoreply_enabled": True}


def _post(r):
    return {"context": r["context"] or "", "ai_enabled": bool(r["ai_enabled"]), "autoreply_enabled": bool(r["autoreply_enabled"])}


def get_post(aid: int, media_id: str | None) -> dict:
    if not media_id:
        return dict(DEFAULT_POST)
    r = db.row("SELECT * FROM posts WHERE account_id=? AND media_id=?", (aid, media_id))
    return _post(r) if r else dict(DEFAULT_POST)


def all_posts(aid: int) -> dict:
    return {r["media_id"]: _post(r) for r in db.rows("SELECT * FROM posts WHERE account_id=?", (aid,))}


def save_post(aid: int, media_id: str, context: str, ai_enabled: bool, autoreply_enabled: bool):
    db.run("INSERT INTO posts (account_id, media_id, context, ai_enabled, autoreply_enabled) VALUES (?,?,?,?,?)"
           " ON CONFLICT (account_id, media_id) DO UPDATE SET context=excluded.context,"
           " ai_enabled=excluded.ai_enabled, autoreply_enabled=excluded.autoreply_enabled",
           (aid, media_id, context, int(ai_enabled), int(autoreply_enabled)))


# ---------------- comments (inbox) & their timeline ----------------
def claim_comment(aid, comment_id, media_id, username, text) -> bool:
    """Atomically records a new comment. False if it was already seen (duplicate webhook)."""
    return db.row("INSERT INTO comments (comment_id, account_id, media_id, username, text, status, created_at)"
                  " VALUES (?,?,?,?,?, 'processing', ?) ON CONFLICT (comment_id) DO NOTHING RETURNING comment_id",
                  (comment_id, aid, media_id, username, text, now())) is not None


def save_comment(aid, comment_id, media_id, username, text, source, reply, status, dm_status):
    db.run("INSERT INTO comments (comment_id, account_id, media_id, username, text, source, reply, status, dm_status, created_at)"
           " VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT (comment_id) DO UPDATE SET source=excluded.source,"
           " reply=excluded.reply, status=excluded.status, dm_status=excluded.dm_status",
           (comment_id, aid, media_id, username, text, source, reply, status, dm_status, now()))


def add_event(aid: int, comment_id: str, kind: str, text: str | None = None, button: str | None = None):
    db.run("INSERT INTO events (account_id, comment_id, kind, text, button, created_at) VALUES (?,?,?,?,?,?)",
           (aid, comment_id, kind, text, button, now()))


INBOX_FILTERS = {
    "all": "",
    "waiting": " AND dm_status LIKE 'waiting%'",
    "delivered": " AND dm_status IN ('sent', 'delivered')",
    "replied": " AND reply IS NOT NULL AND status NOT LIKE 'error%'",
    "skipped": " AND status = 'skipped'",
    "errors": " AND (status LIKE 'error%' OR dm_status LIKE 'error%')",
}


def inbox(aid: int, kind="all", media_id=None, limit=100) -> list[dict]:
    sql = "SELECT * FROM comments WHERE account_id=?" + INBOX_FILTERS.get(kind, "")
    params = [aid]
    if media_id:
        sql += " AND media_id=?"
        params.append(media_id)
    return db.rows(sql + " ORDER BY created_at DESC LIMIT ?", params + [min(int(limit), 500)])


def inbox_counts(aid: int) -> dict:
    return {k: db.row("SELECT COUNT(*) AS n FROM comments WHERE account_id=?" + f, (aid,))["n"]
            for k, f in INBOX_FILTERS.items()}


def comment(aid: int, comment_id: str):
    c = db.row("SELECT * FROM comments WHERE comment_id=? AND account_id=?", (comment_id, aid))
    if c:
        c["events"] = db.rows("SELECT kind, text, button, created_at FROM events WHERE comment_id=? ORDER BY id", (comment_id,))
        c["pending_dm"] = db.row("SELECT status FROM dm_requests WHERE comment_id=? AND status != 'delivered'", (comment_id,)) is not None
    return c


def stats(aid: int) -> dict:
    since = ago(hours=24)
    q = lambda extra: db.row("SELECT COUNT(*) AS n FROM comments WHERE account_id=? AND created_at > ?" + extra, (aid, since))["n"]
    return {
        "handled": q(" AND status != 'skipped'"),
        "replies": q(" AND reply IS NOT NULL AND status NOT LIKE 'error%'"),
        "dms": q(" AND dm_status IN ('sent', 'delivered')"),
        "skipped": q(" AND status = 'skipped'"),
        "waiting": db.row("SELECT COUNT(*) AS n FROM dm_requests WHERE account_id=? AND status LIKE 'waiting%' AND created_at > ?",
                          (aid, ago(days=DM_EXPIRY_DAYS)))["n"],
    }


# ---------------- followers-only DMs in progress ----------------
def add_dm_request(aid, igsid, comment_id, media_id, text, button, not_following_text):
    db.run("INSERT INTO dm_requests (account_id, igsid, comment_id, media_id, text, button, not_following_text,"
           " status, created_at, updated_at) VALUES (?,?,?,?,?,?,?, 'waiting_tap', ?, ?)",
           (aid, igsid, comment_id, media_id, text, button, not_following_text, now(), now()))


def pending_dms(aid: int, igsid: str) -> list[dict]:
    return db.rows("SELECT * FROM dm_requests WHERE account_id=? AND igsid=? AND status != 'delivered' AND created_at > ?"
                   " ORDER BY id", (aid, igsid, ago(days=DM_EXPIRY_DAYS)))


def dm_request_for_comment(aid: int, comment_id: str):
    return db.row("SELECT * FROM dm_requests WHERE account_id=? AND comment_id=? AND status != 'delivered'", (aid, comment_id))


def set_dm_status(requests: list[dict], status: str):
    for r in requests:
        db.run("UPDATE dm_requests SET status=?, updated_at=? WHERE id=?", (status, now(), r["id"]))
        db.run("UPDATE comments SET dm_status=? WHERE comment_id=?", (status, r["comment_id"]))


# ---------------- insights ----------------
def save_followers(aid: int, day: str, followers: int):
    db.run("INSERT INTO follower_history (account_id, day, followers) VALUES (?,?,?)"
           " ON CONFLICT (account_id, day) DO UPDATE SET followers=excluded.followers", (aid, day, followers))


def follower_history(aid: int, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    return db.rows("SELECT day, followers FROM follower_history WHERE account_id=? AND day >= ? ORDER BY day", (aid, since))


def cache_get(aid: int, key: str, max_age_seconds: int):
    r = db.row("SELECT value FROM insight_cache WHERE account_id=? AND key=? AND fetched_at > ?",
               (aid, key, ago(seconds=max_age_seconds)))
    return json.loads(r["value"]) if r else None


def cache_put(aid: int, key: str, value):
    db.run("INSERT INTO insight_cache (account_id, key, value, fetched_at) VALUES (?,?,?,?)"
           " ON CONFLICT (account_id, key) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at",
           (aid, key, json.dumps(value, ensure_ascii=False), now()))


def save_story(aid: int, s: dict, metrics: dict):
    db.run("INSERT INTO stories (story_id, account_id, media_type, thumb, permalink, posted_at, metrics, captured_at)"
           " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT (story_id) DO UPDATE SET metrics=excluded.metrics,"
           " captured_at=excluded.captured_at, thumb=excluded.thumb",
           (s["id"], aid, s.get("media_type"), s.get("thumbnail_url") or s.get("media_url"), s.get("permalink"),
            s.get("timestamp"), json.dumps(metrics), now()))


def list_stories(aid: int, days: int) -> list[dict]:
    rs = db.rows("SELECT * FROM stories WHERE account_id=? AND captured_at > ? ORDER BY posted_at DESC", (aid, ago(days=days)))
    for r in rs:
        r["metrics"] = json.loads(r["metrics"] or "{}")
    return rs


def impact(aid: int, days: int, include_test=False) -> dict:
    """What the bot achieved, from our own records (no Instagram call needed).
    Test-mode comments are left out for real accounts (nothing was actually sent)."""
    since = ago(days=days)
    t = "" if include_test else " AND status != 'test'"
    c = lambda extra: db.row("SELECT COUNT(*) AS n FROM comments WHERE account_id=? AND created_at > ?" + t
                             + extra, (aid, since))["n"]
    reqs = db.rows("SELECT d.comment_id, d.status FROM dm_requests d JOIN comments c ON c.comment_id = d.comment_id"
                   " WHERE d.account_id=? AND d.created_at > ?" + t.replace("status", "c.status"), (aid, since))
    kinds: dict[str, set] = {}
    if reqs:
        for e in db.rows("SELECT e.comment_id, e.kind FROM events e JOIN dm_requests d ON d.comment_id = e.comment_id"
                         " WHERE d.account_id=? AND d.created_at > ?", (aid, since)):
            kinds.setdefault(e["comment_id"], set()).add(e["kind"])
    tapped = [r for r in reqs if kinds.get(r["comment_id"], set()) & {"tap", "message"}]
    not_following = [r for r in reqs if "not_following" in kinds.get(r["comment_id"], set())]
    converted = [r for r in not_following if r["status"] == "delivered"]
    by_rule = db.rows("SELECT source, COUNT(*) AS comments,"
                      " SUM(CASE WHEN reply IS NOT NULL AND status NOT LIKE 'error%' THEN 1 ELSE 0 END) AS replies,"
                      " SUM(CASE WHEN dm_status IN ('sent', 'delivered') THEN 1 ELSE 0 END) AS dms"
                      " FROM comments WHERE account_id=? AND created_at > ?" + t + " AND source IS NOT NULL"
                      " GROUP BY source ORDER BY comments DESC", (aid, since))
    conv_by_comment = {r["comment_id"] for r in converted}
    gated_by_source = db.rows("SELECT c.source, c.comment_id FROM comments c JOIN dm_requests d ON d.comment_id = c.comment_id"
                              " WHERE c.account_id=? AND d.created_at > ?" + t.replace("status", "c.status"), (aid, since))
    for r in by_rule:
        mine = [g for g in gated_by_source if g["source"] == r["source"]]
        r["gated"] = len(mine)
        r["converted"] = len([g for g in mine if g["comment_id"] in conv_by_comment])
    return {
        "comments": c(""), "answered": c(" AND status != 'skipped'"),
        "replies": c(" AND reply IS NOT NULL AND status NOT LIKE 'error%'"),
        "dms": c(" AND dm_status IN ('sent', 'delivered')"),
        "funnel": {"buttons": len(reqs), "tapped": len(tapped), "not_following": len(not_following),
                   "converted": len(converted), "already_following": len([r for r in reqs if r["status"] == "delivered"]) - len(converted)},
        "by_rule": [r for r in by_rule if r["source"] not in ("ignored", "paused", "no-match", "ai-skip")],
    }


def message_seen(mid: str) -> bool:
    """True if this DM/tap was already processed (Meta can deliver a webhook twice)."""
    return db.row("INSERT INTO seen_messages (mid, created_at) VALUES (?,?) ON CONFLICT (mid) DO NOTHING RETURNING mid",
                  (mid, now())) is None
