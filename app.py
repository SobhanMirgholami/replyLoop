"""replyloop web server (Starlette).

  /            the dashboard (an installable web app)
  /api/...     JSON API used by the dashboard (login required)
  /webhook     Meta sends comments, DMs and button taps here
  /health      for the keep-alive pinger

Run locally:  uvicorn app:app --reload
"""
import contextlib
import json
import os
import secrets
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.background import BackgroundTasks
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import ai
import bot
import db
import google_auth
import qr
import twofa
import i18n
import insights
import instagram
import security
import store
from config import ADMIN_EMAIL, ADMIN_PASSWORD, APP_SECRET, VERIFY_TOKEN

STATIC = Path(__file__).parent / "static"
# Render's free plan wipes local files on every restart, so SQLite there loses everything.
ON_RENDER_WITHOUT_DB = bool(os.getenv("RENDER")) and not db.IS_PG


class HTTPError(Exception):
    def __init__(self, code: int, detail: str):
        self.code, self.detail = code, detail


# ======================= helpers =======================
def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


LEVEL = {"viewer": 1, "editor": 2, "owner": 3}


def api(fn, auth=True, owner=False, owner_write=False, need=None):
    """Wraps an API handler: reads JSON, checks login and role, runs the (blocking) work in a thread.

    Who may call it: `owner` = only the owner; `owner_write` = anyone may read, only the owner may change;
    `need` = a fixed minimum role. By default viewers can read (GET) and editors can change things."""
    async def endpoint(request: Request):
        lang = request.headers.get("x-lang")
        i18n.set_from_header(lang)
        body = {}
        if request.method != "GET":
            # Browsers can't send this header cross-site without our permission -> blocks CSRF
            if request.headers.get("x-requested-with") != "replyloop":
                return JSONResponse({"detail": i18n.tr("Bad request")}, 400)
            raw = await request.body()
            try:
                body = json.loads(raw) if raw else {}
            except ValueError:
                return JSONResponse({"detail": i18n.tr("Invalid JSON")}, 400)
            if not isinstance(body, dict):
                return JSONResponse({"detail": i18n.tr("Invalid JSON")}, 400)

        def work():
            i18n.set_from_header(lang)
            user = None
            if auth:
                user = security.session_user(request.cookies.get(security.SESSION_COOKIE))
                if not user:
                    raise HTTPError(401, "Please sign in.")
                reading = request.method == "GET"
                required = ("owner" if owner else need or
                            ("viewer" if reading else "owner" if owner_write else "editor"))
                if LEVEL[user["role"]] < LEVEL[required]:
                    raise HTTPError(403, "Only the owner can do this." if required == "owner"
                                    else "You have view-only access.")
            return fn(request, body, user)

        try:
            result = await run_in_threadpool(work)
        except HTTPError as e:
            return JSONResponse({"detail": i18n.tr(e.detail)}, e.code)
        except instagram.InstagramError as e:
            return JSONResponse({"detail": i18n.tr(f"Instagram: {e}")}, 502)
        return result if isinstance(result, Response) else JSONResponse(result)
    return endpoint


def text_field(body, key, max_len=2000, required=False, label=None) -> str:
    v = body.get(key, "")
    if not isinstance(v, str):
        raise HTTPError(422, f"{label or key} must be text.")
    v = v.strip()
    if required and not v:
        raise HTTPError(422, f"{label or key} is required.")
    if len(v) > max_len:
        raise HTTPError(422, f"{label or key} is too long (max {max_len} characters).")
    return v


def bool_field(body, key, default=False) -> bool:
    v = body.get(key, default)
    if not isinstance(v, bool):
        raise HTTPError(422, f"{key} must be true or false.")
    return v


def list_field(body, key, max_items=50, item_len=100) -> list[str]:
    v = body.get(key, [])
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise HTTPError(422, f"{key} must be a list of text.")
    v = [x.strip() for x in v if x.strip()]
    if len(v) > max_items or any(len(x) > item_len for x in v):
        raise HTTPError(422, f"Too many or too long items in {key}.")
    return v


def account_of(request) -> dict:
    try:
        aid = int(request.path_params["aid"])
    except ValueError:
        raise HTTPError(404, "Account not found.")
    acc = store.get_account(aid)
    if not acc:
        raise HTTPError(404, "Account not found.")
    return acc


def public_account(acc: dict) -> dict:
    return {"id": acc["id"], "username": acc["username"], "live": acc["live"], "is_demo": acc["is_demo"],
            "last_error": i18n.tr(acc["last_error"]), "token_refreshed_at": acc["token_refreshed_at"],
            "token_ok": acc["is_demo"] or bool(security.decrypt(acc["token_enc"])),
            "waiting": store.stats(acc["id"])["waiting"]}


# ======================= auth =======================
def h_login(request, body, _):
    email = text_field(body, "email", 200, True, "Email").lower()
    password = body.get("password") if isinstance(body.get("password"), str) else ""
    keys = (f"ip:{client_ip(request)}", f"email:{email}")
    if security.too_many_attempts(*keys):
        raise HTTPError(429, "Too many attempts. Wait 15 minutes and try again.")
    user = security.login(email, password)
    if not user:
        security.record_failure(*keys)
        raise HTTPError(401, "Wrong email or password.")
    security.clear_failures(*keys)
    remember = bool(body.get("remember", True))
    if user.get("totp_secret_enc"):          # two-step login is on: ask for the code before signing in
        return ask_for_code(request, user["id"], remember, JSONResponse({"two_factor": True}))
    return signed_in(request, user["id"], remember, JSONResponse({"ok": True}))


def signed_in(request, uid: int, remember: bool, resp):
    """Starts a session and puts its cookie on `resp`."""
    token, max_age = security.start_session(uid, remember, request.headers.get("user-agent", ""), client_ip(request))
    resp.set_cookie(security.SESSION_COOKIE, token, max_age=max_age, httponly=True, samesite="lax",
                    secure=is_https(request), path="/")
    if request.cookies.get(security.PENDING_COOKIE):
        resp.delete_cookie(security.PENDING_COOKIE, path="/api/")
    return resp


def ask_for_code(request, uid: int, remember: bool, resp):
    ticket = security.start_pending(uid, remember)
    resp.set_cookie(security.PENDING_COOKIE, ticket, max_age=security.PENDING_MINUTES * 60, httponly=True,
                    samesite="lax", secure=is_https(request), path="/api/")
    return resp


def second_factor_ok(user: dict, code: str) -> bool:
    """Checks a 6-digit app code (each one works once) or a one-time backup code."""
    secret = security.decrypt(user.get("totp_secret_enc"))
    if secret:
        step = twofa.verify(secret, code, user.get("totp_last_step") or 0)
        if step is not None and store.set_totp_step(user["id"], step):
            return True
    remaining = twofa.use_backup_code(user.get("backup_codes"), code)
    return remaining is not None and store.replace_backup_codes(user["id"], user.get("backup_codes"), remaining)


def h_login_code(request, body, _):
    ticket = request.cookies.get(security.PENDING_COOKIE)
    p = security.pending(ticket)
    if not p:
        raise HTTPError(401, "This sign-in expired. Start again.")
    keys = (f"ip:{client_ip(request)}", f"2fa:{p['user_id']}")
    if security.too_many_attempts(*keys):
        security.end_pending(ticket)
        raise HTTPError(429, "Too many attempts. Wait 15 minutes and try again.")
    user = store.user_by_id(p["user_id"])
    code = body.get("code") if isinstance(body.get("code"), str) else ""
    if not user or not second_factor_ok(user, code):
        security.record_failure(*keys)
        if security.pending_failed(ticket) >= 5:
            security.end_pending(ticket)
            raise HTTPError(401, "Too many wrong codes. Start again.")
        raise HTTPError(401, "That code isn't right. Check your authenticator app and try again.")
    security.clear_failures(*keys)
    security.end_pending(ticket)
    return signed_in(request, user["id"], bool(p["remember"]), JSONResponse({"ok": True}))


def h_login_cancel(request, body, _):
    security.end_pending(request.cookies.get(security.PENDING_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(security.PENDING_COOKIE, path="/api/")
    return resp


def h_logout(request, body, user):
    security.end_session(request.cookies.get(security.SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(security.SESSION_COOKIE, path="/")
    return resp


def h_me(request, body, _):
    user = security.session_user(request.cookies.get(security.SESSION_COOKIE))
    if not user:
        return {"user": None, "setup_needed": store.user_count() == 0, "google": google_auth.enabled(),
                "pending_2fa": bool(security.pending(request.cookies.get(security.PENDING_COOKIE)))}
    return {"user": {"id": user["id"], "email": user["email"], "is_owner": bool(user["is_owner"]),
                     "role": user["role"], "two_factor": user["two_factor"]},
            "accounts": [public_account(a) for a in store.list_accounts()],
            "ai_available": ai.available(), "webhook_ready": bool(APP_SECRET and VERIFY_TOKEN),
            "key_warning": security.EPHEMERAL_KEY, "db_warning": ON_RENDER_WITHOUT_DB,
            "google": google_auth.enabled()}


def h_password(request, body, user):
    full = store.user_by_id(user["id"])
    if not security.check_password(body.get("current", "") if isinstance(body.get("current"), str) else "", full["pw_hash"]):
        raise HTTPError(403, "Your current password is wrong.")
    new = body.get("new") if isinstance(body.get("new"), str) else ""
    if problem := security.password_problem(new):
        raise HTTPError(422, problem)
    store.set_password(user["id"], security.hash_password(new))
    security.end_other_sessions(user["id"], request.cookies.get(security.SESSION_COOKIE))
    return {"ok": True}


def h_users(request, body, user):
    if request.method == "GET":
        return store.list_users()
    email = text_field(body, "email", 200, True, "Email").lower()
    if "@" not in email:
        raise HTTPError(422, "Enter a valid email.")
    pw = body.get("password") if isinstance(body.get("password"), str) else ""
    if not pw and google_auth.enabled():
        pw = secrets.token_urlsafe(32)      # Google-only: a random password nobody knows
    elif problem := security.password_problem(pw):
        raise HTTPError(422, problem)
    role = body.get("role", "editor")
    if role not in store.ROLES:
        raise HTTPError(422, "Choose a role.")
    if store.user_by_email(email):
        raise HTTPError(409, "That email already has access.")
    u = store.create_user(email, security.hash_password(pw), role=role)
    return {"id": u["id"], "email": u["email"], "is_owner": False, "role": role}


def h_user_update(request, body, user):
    uid = int(request.path_params["uid"])
    target = store.user_by_id(uid)
    if not target:
        raise HTTPError(404, "User not found.")
    if target["is_owner"]:
        raise HTTPError(422, "The owner's access can't be changed here.")
    if "role" in body:
        if body["role"] not in store.ROLES:
            raise HTTPError(422, "Choose a role.")
        store.set_role(uid, body["role"])
    if body.get("reset_2fa"):
        store.disable_totp(uid)
    return {u["id"]: u for u in store.list_users()}[uid]


def h_user_delete(request, body, user):
    uid = int(request.path_params["uid"])
    if uid == user["id"]:
        raise HTTPError(422, "You can't remove yourself.")
    if not store.delete_user(uid):
        raise HTTPError(404, "User not found.")
    return {"ok": True}


# ======================= your security: two-step login & devices =======================
def device_name(ua: str) -> dict:
    ua = ua or ""
    os_ = ("iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else "Android" if "Android" in ua
           else "Windows" if "Windows" in ua else "Mac" if "Macintosh" in ua else "Linux" if "Linux" in ua else "")
    browser = ("Edge" if "Edg/" in ua else "Samsung Internet" if "SamsungBrowser" in ua else "Opera" if "OPR/" in ua
               else "Firefox" if ("Firefox" in ua or "FxiOS" in ua) else "Chrome" if ("Chrome" in ua or "CriOS" in ua)
               else "Safari" if "Safari" in ua else "")
    return {"os": os_, "browser": browser}


def h_security(request, body, user):
    full = store.user_by_id(user["id"])
    current = security.session_id(request.cookies.get(security.SESSION_COOKIE))
    return {
        "two_factor": bool(full["totp_secret_enc"]),
        "backup_codes_left": twofa.backup_left(full["backup_codes"]),
        "can_enable": not security.EPHEMERAL_KEY,
        "sessions": [{"id": s["token_hash"][:16], **device_name(s["user_agent"]), "ip": s["ip"] or "",
                      "created_at": s["created_at"], "last_seen_at": s["last_seen_at"] or s["created_at"],
                      "current": s["token_hash"][:16] == current} for s in store.list_sessions(user["id"])],
    }


def _code(body) -> str:
    return body.get("code") if isinstance(body.get("code"), str) else ""


def h_2fa_setup(request, body, user):
    if security.EPHEMERAL_KEY:
        raise HTTPError(422, "Set SECRET_KEY on the server before turning on two-step login.")
    if user["two_factor"]:
        raise HTTPError(409, "Two-step login is already on.")
    secret = twofa.new_secret()
    store.set_totp_pending(user["id"], security.encrypt(secret))
    uri = twofa.otpauth_uri(secret, user["email"])
    return {"secret": twofa.pretty_secret(secret), "uri": uri, "qr": qr.svg(uri)}


def h_2fa_enable(request, body, user):
    full = store.user_by_id(user["id"])
    secret = security.decrypt(full["totp_pending_enc"])
    if not secret:
        raise HTTPError(409, "Start the setup again.")
    step = twofa.verify(secret, _code(body))
    if step is None:
        raise HTTPError(422, "That code isn't right. Check your authenticator app and try again.")
    codes, hashed = twofa.new_backup_codes()
    store.enable_totp(user["id"], security.encrypt(secret), step, hashed)
    security.end_other_sessions(user["id"], request.cookies.get(security.SESSION_COOKIE))
    return {"backup_codes": codes}


def h_2fa_disable(request, body, user):
    full = store.user_by_id(user["id"])
    if not full["totp_secret_enc"]:
        return {"ok": True}
    if not second_factor_ok(full, _code(body)):
        raise HTTPError(422, "That code isn't right. Check your authenticator app and try again.")
    store.disable_totp(user["id"])
    return {"ok": True}


def h_2fa_backup(request, body, user):
    full = store.user_by_id(user["id"])
    if not full["totp_secret_enc"]:
        raise HTTPError(409, "Turn on two-step login first.")
    if not second_factor_ok(full, _code(body)):
        raise HTTPError(422, "That code isn't right. Check your authenticator app and try again.")
    codes, hashed = twofa.new_backup_codes()
    store.set_backup_codes(user["id"], hashed)
    return {"backup_codes": codes}


def h_session_end(request, body, user):
    sid = request.path_params["sid"]
    if sid == security.session_id(request.cookies.get(security.SESSION_COOKIE)):
        raise HTTPError(422, "To sign out this device, use Sign out.")
    if not store.delete_session_by_prefix(user["id"], sid):
        raise HTTPError(404, "Device not found.")
    return {"ok": True}


def h_sessions_others(request, body, user):
    security.end_other_sessions(user["id"], request.cookies.get(security.SESSION_COOKIE))
    return {"ok": True}


# ======================= Sign in with Google =======================
def base_url(request: Request) -> str:
    scheme = "https" if is_https(request) else request.url.scheme
    return f"{scheme}://{request.headers.get('host', request.url.netloc)}"


async def google_start(request):
    if not google_auth.enabled():
        return RedirectResponse("/?login_error=google_off", 303)
    url, state = google_auth.start(base_url(request))
    resp = RedirectResponse(url, 303)
    resp.set_cookie(google_auth.STATE_COOKIE, state, max_age=google_auth.STATE_MAX_AGE, httponly=True,
                    samesite="lax", secure=is_https(request), path="/auth/google")
    return resp


async def google_callback(request):
    q = request.query_params
    if not google_auth.enabled():
        return RedirectResponse("/?login_error=google_off", 303)
    if q.get("error"):            # they pressed cancel on Google's page
        return _google_done(request, "/?login_error=cancelled")

    def work():
        email = google_auth.finish(base_url(request), q.get("code"), q.get("state"),
                                   request.cookies.get(google_auth.STATE_COOKIE))
        return store.user_by_email(email)

    try:
        user = await run_in_threadpool(work)
    except google_auth.GoogleError as e:
        print(f"[google] sign-in failed: {e}")
        return _google_done(request, f"/?login_error={e.code}")
    except Exception as e:        # network trouble reaching Google
        print(f"[google] sign-in failed: {e}")
        return _google_done(request, "/?login_error=failed")
    if not user:
        return _google_done(request, "/?login_error=not_allowed")
    if user.get("totp_secret_enc"):     # Google was right; still ask for the 6-digit code
        return await run_in_threadpool(ask_for_code, request, user["id"], True, _google_done(request, "/"))
    return await run_in_threadpool(signed_in, request, user["id"], True, _google_done(request, "/"))


def _google_done(request, to: str):
    resp = RedirectResponse(to, 303)
    resp.delete_cookie(google_auth.STATE_COOKIE, path="/auth/google")
    return resp


# ======================= Instagram accounts =======================
DEMO_RULES = [
    (None, {"name": "قیمت", "keywords": ["قیمت", "چنده", "چند", "price", "how much", "fiyat", "ne kadar"],
            "reply": "@{username} قیمت‌ها تو لینک بیو هست 💸"}),
    (None, {"name": "آدرس", "keywords": ["کجا", "آدرس", "where", "address", "nerede", "adres"],
            "reply": "@{username} ما تو آوجیلار استانبولیم 📍"}),
    ("demo_reel_1", {"name": "لینک منو", "keywords": ["لینک", "منو", "link", "menu", "menü"],
                     "reply": "@{username} دایرکتت رو چک کن 📩", "dm": "اینم منوی پاییزه‌مون 🌿 cafe.example/menu",
                     "followers_only": True, "gate_text": "برای دریافت لینک، نیاز هست صفحه‌ی ما رو دنبال داشته باشی",
                     "gate_button": "دنبال میکنم", "not_following_text": "هنوز صفحه رو دنبال نکردی 🙈 دنبال کن و دوباره بزن"}),
    ("demo_reel_1", {"name": "وگان", "keywords": ["وگان", "شیر گیاهی", "vegan", "oat milk", "yulaf"],
                     "reply": "@{username} آره! با شیر جو دوسر هم درست می‌کنیم 🥛"}),
    ("demo_post_2", {"name": "کد تخفیف", "keywords": ["کد", "تخفیف", "code", "kod"],
                     "dm": "کد تخفیف دانشجوییت: STUDENT20 🎓 دوشنبه‌ها موقع سفارش نشونش بده."}),
]


def rule_fields(body) -> dict:
    keywords = list_field(body, "keywords", 30, 60)
    if not keywords:
        raise HTTPError(422, "Add at least one keyword.")
    f = {
        "name": text_field(body, "name", 60, label="Name"),
        "keywords": keywords,
        "reply": text_field(body, "reply", 1000, label="Public reply"),
        "dm": text_field(body, "dm", 1000, label="DM"),
        "followers_only": bool_field(body, "followers_only"),
        "gate_text": text_field(body, "gate_text", store.HEADLINE_MAX, label="Headline"),
        "gate_button": text_field(body, "gate_button", store.BUTTON_MAX, label="Button text"),
        "not_following_text": text_field(body, "not_following_text", store.HEADLINE_MAX, label="Not-following message"),
        "enabled": bool_field(body, "enabled", True),
    }
    if not f["reply"] and not f["dm"]:
        raise HTTPError(422, "Add a public reply, a DM, or both.")
    f["followers_only"] = f["followers_only"] and bool(f["dm"])
    return f


def h_accounts(request, body, user):
    if request.method == "GET":
        return [public_account(a) for a in store.list_accounts()]
    if body.get("demo"):
        acc = store.upsert_account(f"demo-{secrets.token_hex(4)}", "demo_cafe", None, is_demo=True)
        for media_id, fields in DEMO_RULES:
            store.create_rule(acc["id"], media_id, {**dict.fromkeys(store.RULE_FIELDS, ""), "followers_only": False,
                                                   "enabled": True, **fields})
        store.save_post(acc["id"], "demo_reel_1", "لاته پسته، 140 لیر، تا یکشنبه. با شیر جو دوسر هم درست میشه.", True, True)
        return public_account(acc)
    token = text_field(body, "token", 1000, True, "Access token")
    info = instagram.whoami(token)
    acc = store.upsert_account(info["user_id"], info["username"], security.encrypt(token))
    warning = None
    try:
        instagram.subscribe_webhooks(token)
    except instagram.InstagramError as e:
        warning = f"Connected, but turning on webhooks failed: {e}. Check the webhook setup in your Meta app."
        store.update_account(acc["id"], last_error=warning)
    return {**public_account(store.get_account(acc["id"])), "warning": i18n.tr(warning)}


def h_account(request, body, user):
    acc = account_of(request)
    if request.method == "DELETE":
        store.delete_account(acc["id"])
        return {"ok": True}
    if "live" in body:
        live = bool_field(body, "live")
        if live and acc["is_demo"]:
            raise HTTPError(422, "The demo account can't go live.")
        if live and not security.decrypt(acc["token_enc"]):
            raise HTTPError(422, "This account's token can't be read. Reconnect it first.")
        if live and not (APP_SECRET and VERIFY_TOKEN):
            raise HTTPError(422, "Set APP_SECRET and VERIFY_TOKEN on the server before going live.")
        if live != acc["live"]:
            # the backup checker only answers comments written after going live
            store.update_account(acc["id"], live=live, live_since=store.now() if live else None)
    return public_account(store.get_account(acc["id"]))


# ======================= per-account API =======================
_media_cache: dict[int, tuple[float, list]] = {}


def media_for(acc, refresh=False) -> list[dict]:
    if acc["is_demo"]:
        return [{**m, "thumb": None, "permalink": None, "timestamp": None, "comments_count": 0} for m in instagram.DEMO_MEDIA]
    cached = _media_cache.get(acc["id"])
    if refresh or not cached or time.time() - cached[0] > 300:
        token = security.decrypt(acc["token_enc"])
        if not token:
            raise HTTPError(409, "This account's token can't be read. Reconnect it in Settings.")
        _media_cache[acc["id"]] = (time.time(), instagram.list_media(token))
    return _media_cache[acc["id"]][1]


def h_overview(request, body, user):
    acc = account_of(request)
    return {"account": public_account(acc), "stats": store.stats(acc["id"]), "counts": store.inbox_counts(acc["id"])}


def h_posts(request, body, user):
    acc = account_of(request)
    media = media_for(acc, request.query_params.get("refresh") == "true")
    counts, saved = store.rule_counts(acc["id"]), store.all_posts(acc["id"])
    return [{**m, **saved.get(m["id"], store.DEFAULT_POST),
             "rule_count": counts.get(m["id"], {}).get("n", 0), "gated": counts.get(m["id"], {}).get("gated", False)}
            for m in media]


def h_post_update(request, body, user):
    acc = account_of(request)
    media_id = request.path_params["media_id"]
    store.save_post(acc["id"], media_id, text_field(body, "context", 2000, label="Post info"),
                    bool_field(body, "ai_enabled", True), bool_field(body, "autoreply_enabled", True))
    return store.get_post(acc["id"], media_id)


def h_rules(request, body, user):
    acc = account_of(request)
    if request.method == "GET":
        mid = request.query_params.get("media_id", "global")
        return store.list_rules(acc["id"], None if mid == "global" else mid)
    media_id = body.get("media_id") or None
    if media_id is not None and not isinstance(media_id, str):
        raise HTTPError(422, "media_id must be text.")
    return store.create_rule(acc["id"], media_id, rule_fields(body))


def h_rule(request, body, user):
    acc = account_of(request)
    rid = int(request.path_params["rid"])
    if request.method == "DELETE":
        if not store.delete_rule(acc["id"], rid):
            raise HTTPError(404, "Rule not found.")
        return {"ok": True}
    r = store.update_rule(acc["id"], rid, rule_fields(body))
    if not r:
        raise HTTPError(404, "Rule not found.")
    return r


def h_reorder(request, body, user):
    acc = account_of(request)
    ids = body.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise HTTPError(422, "ids must be a list of rule ids.")
    store.reorder_rules(acc["id"], ids)
    return {"ok": True}


def h_settings(request, body, user):
    acc = account_of(request)
    if request.method == "GET":
        return store.get_settings(acc["id"])
    values = {
        "ai_fallback": bool_field(body, "ai_fallback", True),
        "brand_voice": text_field(body, "brand_voice", 1000, label="Brand voice"),
        "ignore_keywords": list_field(body, "ignore_keywords", 100, 60),
        "gate_message": text_field(body, "gate_message", store.HEADLINE_MAX, True, "First message"),
        "gate_button": text_field(body, "gate_button", store.BUTTON_MAX, True, "Button text"),
        "not_following_message": text_field(body, "not_following_message", store.HEADLINE_MAX, True, "Not-following message"),
        "check_failed_message": text_field(body, "check_failed_message", store.HEADLINE_MAX, True, "Check-failed message"),
    }
    store.save_settings(acc["id"], values)
    return store.get_settings(acc["id"])


def h_inbox(request, body, user):
    acc = account_of(request)
    q = request.query_params
    return store.inbox(acc["id"], q.get("filter", "all"), q.get("media_id") or None, q.get("limit", "100"))


def h_inbox_item(request, body, user):
    acc = account_of(request)
    c = store.comment(acc["id"], request.path_params["cid"])
    if not c:
        raise HTTPError(404, "Not found.")
    return c


def h_test(request, body, user):
    acc = account_of(request)
    text = text_field(body, "text", 1000, True, "Comment")
    return bot.decide(acc, text, "test_user", body.get("media_id") or None)


def _require_test_mode(acc):
    if acc["live"]:
        raise HTTPError(422, "Simulation only works in test mode.")


def h_simulate(request, body, user):
    acc = account_of(request)
    _require_test_mode(acc)
    text = text_field(body, "text", 1000, True, "Comment")
    username = text_field(body, "username", 30, label="Username") or "test_user"
    cid = f"sim-{secrets.token_hex(6)}"
    bot.handle_comment(acc, {"id": cid, "text": text, "from": {"id": f"sim-{secrets.token_hex(4)}", "username": username},
                             "media": {"id": body.get("media_id") or None}})
    return store.comment(acc["id"], cid)


def h_simulate_tap(request, body, user):
    acc = account_of(request)
    _require_test_mode(acc)
    cid = text_field(body, "comment_id", 100, True)
    req = store.dm_request_for_comment(acc["id"], cid)
    if not req:
        raise HTTPError(422, "This comment isn't waiting for a tap.")
    bot.handle_message(acc, {"sender": {"id": req["igsid"]},
                             "postback": {"mid": f"sim-{secrets.token_hex(6)}", "title": req["button"], "payload": instagram.FOLLOW_CHECK}},
                       follows_override=bool_field(body, "follows"))
    return store.comment(acc["id"], cid)


# ======================= insights =======================
def _days(request) -> int:
    d = request.query_params.get("days", "7")
    if d not in ("7", "30"):
        raise HTTPError(422, "days must be 7 or 30.")
    return int(d)


def _refresh(request) -> bool:
    return request.query_params.get("refresh") == "true"


def _tr_error(result: dict) -> dict:
    if result.get("error"):
        result = {**result, "error": i18n.tr(result["error"])}
    return result


def h_ins_account(request, body, user):
    return _tr_error(insights.account(account_of(request), _days(request), _refresh(request)))


def h_ins_posts(request, body, user):
    return _tr_error(insights.posts(account_of(request), _refresh(request)))


def h_ins_stories(request, body, user):
    return _tr_error(insights.stories(account_of(request), _days(request), _refresh(request)))


def h_ins_impact(request, body, user):
    return insights.impact(account_of(request), _days(request))


# ======================= webhook =======================
async def webhook(request: Request):
    if request.method == "GET":   # one-time handshake from the Meta dashboard
        q = request.query_params
        if VERIFY_TOKEN and q.get("hub.mode") == "subscribe" and secrets.compare_digest(q.get("hub.verify_token", ""), VERIFY_TOKEN):
            return PlainTextResponse(q.get("hub.challenge", ""))
        return PlainTextResponse("verify token mismatch", 403)

    body = await request.body()
    if not instagram.signature_ok(body, request.headers.get("x-hub-signature-256")):
        return PlainTextResponse("bad signature", 401)
    try:
        payload = json.loads(body)
    except ValueError:
        return PlainTextResponse("bad json", 400)

    tasks = BackgroundTasks()
    for entry in payload.get("entry", []):
        tasks.add_task(_process_entry, entry)
    return JSONResponse({"ok": True}, background=tasks)   # answer Meta fast; work happens after


def _process_entry(entry: dict):
    acc = store.account_by_ig_id(str(entry.get("id", "")))
    if not acc:
        return
    try:
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                bot.handle_comment(acc, change.get("value") or {})
        for event in entry.get("messaging", []):
            bot.handle_message(acc, event)
    except Exception as e:
        print(f"[webhook] {e}")


# ======================= pages =======================
async def index(request):
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def service_worker(request):
    return FileResponse(STATIC / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


async def manifest(request):
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


async def health(request):
    return PlainTextResponse("ok")


async def privacy(request):
    """Public page Meta asks for (Privacy Policy URL + data deletion instructions)."""
    import html
    contact = os.getenv("PRIVACY_CONTACT", "").strip()
    who = f'<a href="mailto:{html.escape(contact)}">{html.escape(contact)}</a>' if "@" in contact \
        else html.escape(contact) if contact else "us by Instagram direct message"
    page = (STATIC / "privacy.html").read_text(encoding="utf-8").replace("{{CONTACT}}", who)
    return HTMLResponse(page)


class SecurityHeaders(BaseHTTPMiddleware):
    CSP = ("default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
           "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; manifest-src 'self'; "
           "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = self.CSP
        if is_https(request):
            resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp


def on_startup():
    store.init()
    if store.user_count() == 0 and ADMIN_EMAIL and ADMIN_PASSWORD:
        store.create_user(ADMIN_EMAIL, security.hash_password(ADMIN_PASSWORD), is_owner=True)
        print(f"[setup] created owner account {ADMIN_EMAIL}")
    if security.EPHEMERAL_KEY:
        print("[warning] SECRET_KEY is not set: saved Instagram tokens won't survive a restart.")
    reset = os.getenv("RESET_2FA_EMAIL", "").strip().lower()
    if reset and (u := store.user_by_email(reset)) and u["totp_secret_enc"]:
        store.disable_totp(u["id"])
        print(f"[recovery] turned off two-step login for {reset}. Remove RESET_2FA_EMAIL now.")
    bot.start_background_jobs()


A = "/api/a/{aid:int}"
routes = [
    Route("/", index),
    Route("/sw.js", service_worker),
    Route("/manifest.webmanifest", manifest),
    Route("/health", health),
    Route("/privacy", privacy),
    Route("/webhook", webhook, methods=["GET", "POST"]),
    Route("/auth/google", google_start),
    Route("/auth/google/callback", google_callback),
    Route("/api/login", api(h_login, auth=False), methods=["POST"]),
    Route("/api/login/code", api(h_login_code, auth=False), methods=["POST"]),
    Route("/api/login/cancel", api(h_login_cancel, auth=False), methods=["POST"]),
    Route("/api/logout", api(h_logout, need="viewer"), methods=["POST"]),
    Route("/api/me", api(h_me, auth=False)),
    Route("/api/password", api(h_password, need="viewer"), methods=["POST"]),
    Route("/api/security", api(h_security)),
    Route("/api/2fa/setup", api(h_2fa_setup, need="viewer"), methods=["POST"]),
    Route("/api/2fa/enable", api(h_2fa_enable, need="viewer"), methods=["POST"]),
    Route("/api/2fa/disable", api(h_2fa_disable, need="viewer"), methods=["POST"]),
    Route("/api/2fa/backup-codes", api(h_2fa_backup, need="viewer"), methods=["POST"]),
    Route("/api/sessions/others", api(h_sessions_others, need="viewer"), methods=["POST"]),
    Route("/api/sessions/{sid}", api(h_session_end, need="viewer"), methods=["DELETE"]),
    Route("/api/users", api(h_users, owner=True), methods=["GET", "POST"]),
    Route("/api/users/{uid:int}", api(h_user_update, owner=True), methods=["PATCH"]),
    Route("/api/users/{uid:int}", api(h_user_delete, owner=True), methods=["DELETE"]),
    Route("/api/accounts", api(h_accounts, owner_write=True), methods=["GET", "POST"]),
    Route("/api/accounts/{aid}", api(h_account, owner_write=True), methods=["PATCH", "DELETE"]),
    Route(A + "/overview", api(h_overview)),
    Route(A + "/posts", api(h_posts)),
    Route(A + "/posts/{media_id}", api(h_post_update), methods=["PUT"]),
    Route(A + "/rules", api(h_rules), methods=["GET", "POST"]),
    Route(A + "/rules/reorder", api(h_reorder), methods=["POST"]),
    Route(A + "/rules/{rid:int}", api(h_rule), methods=["PUT", "DELETE"]),
    Route(A + "/settings", api(h_settings), methods=["GET", "PUT"]),
    Route(A + "/inbox", api(h_inbox)),
    Route(A + "/inbox/{cid}", api(h_inbox_item)),
    Route(A + "/test", api(h_test), methods=["POST"]),
    Route(A + "/simulate", api(h_simulate), methods=["POST"]),
    Route(A + "/simulate-tap", api(h_simulate_tap), methods=["POST"]),
    Route(A + "/insights/account", api(h_ins_account)),
    Route(A + "/insights/posts", api(h_ins_posts)),
    Route(A + "/insights/stories", api(h_ins_stories)),
    Route(A + "/insights/impact", api(h_ins_impact)),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
]

@contextlib.asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(on_startup)
    yield


app = Starlette(routes=routes, middleware=[Middleware(SecurityHeaders)], lifespan=lifespan)
