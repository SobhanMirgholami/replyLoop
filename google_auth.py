"""Sign in with Google (OpenID Connect, server-side code flow).

Only people who already have access can use it: the Google email must match a user in the
database (the owner, or someone the owner added in Settings). There is still no sign-up.
"""
import base64
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, PUBLIC_URL

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
STATE_COOKIE = "rl_google"
STATE_MAX_AGE = 600     # the round trip to Google must finish within 10 minutes


class GoogleError(Exception):
    """`code` is shown to the user as a translated message on the login page."""
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


def enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def redirect_uri(base_url: str) -> str:
    """Where Google sends people back. Must be listed exactly like this in Google Cloud Console."""
    return (PUBLIC_URL or base_url).rstrip("/") + "/auth/google/callback"


def start(base_url: str) -> tuple[str, str]:
    """Returns (Google URL to send the browser to, value for the short-lived state cookie)."""
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    url = AUTH_URL + "?" + urlencode({
        "client_id": GOOGLE_CLIENT_ID, "redirect_uri": redirect_uri(base_url), "response_type": "code",
        "scope": "openid email", "state": state, "nonce": nonce, "prompt": "select_account",
    })
    return url, f"{state}.{nonce}"


def _claims(id_token: str) -> dict:
    """Reads the ID token's payload. It came straight from Google's token endpoint over HTTPS
    (authenticated with our client secret), so Google's docs say its signature needn't be re-checked."""
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        raise GoogleError("failed", "bad id_token")


def finish(base_url: str, code: str | None, state: str | None, cookie: str | None) -> str:
    """Checks Google's answer and returns the verified email address (lowercase)."""
    if not cookie or "." not in cookie or not state or not code:
        raise GoogleError("expired", "missing state")
    want_state, nonce = cookie.split(".", 1)
    if not hmac.compare_digest(want_state, state):
        raise GoogleError("expired", "state mismatch")
    r = httpx.post(TOKEN_URL, data={
        "code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri(base_url), "grant_type": "authorization_code",
    }, timeout=15)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or not data.get("id_token"):
        raise GoogleError("failed", data.get("error_description") or data.get("error") or f"HTTP {r.status_code}")
    c = _claims(data["id_token"])
    if c.get("aud") != GOOGLE_CLIENT_ID or c.get("iss") not in ISSUERS:
        raise GoogleError("failed", "token not for this app")
    if not hmac.compare_digest(str(c.get("nonce", "")), nonce):
        raise GoogleError("failed", "nonce mismatch")
    if int(c.get("exp", 0)) < time.time():
        raise GoogleError("expired", "token expired")
    if c.get("email_verified") not in (True, "true") or not c.get("email"):
        raise GoogleError("unverified", "email not verified")
    return str(c["email"]).strip().lower()
