"""Talks to the Instagram API (Instagram API with Instagram Login, host graph.instagram.com).
Every call takes the account's own access token."""
import hashlib
import hmac

import httpx

from config import APP_SECRET, GRAPH_VERSION

BASE = f"https://graph.instagram.com/{GRAPH_VERSION}"
FOLLOW_CHECK = "FOLLOW_CHECK"   # what our button sends back to the webhook when tapped
TIMEOUT = 15


class InstagramError(Exception):
    pass


def _check(r: httpx.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or "error" in data:
        msg = (data.get("error") or {}).get("message") or f"HTTP {r.status_code}"
        raise InstagramError(msg)
    return data


def _get(path: str, token: str, **params) -> dict:
    return _check(httpx.get(f"{BASE}/{path}", params={**params, "access_token": token}, timeout=TIMEOUT))


def _post(path: str, token: str, json_body: dict | None = None, **params) -> dict:
    return _check(httpx.post(f"{BASE}/{path}", params=params or None, json=json_body,
                             headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT))


# ---------------- account ----------------
def whoami(token: str) -> dict:
    """Checks a token. Returns {"user_id": <IG account id used by webhooks>, "username": ...}."""
    d = _get("me", token, fields="user_id,username")
    if not d.get("user_id"):
        raise InstagramError("This token doesn't belong to an Instagram professional account.")
    return {"user_id": str(d["user_id"]), "username": d.get("username", "")}


def subscribe_webhooks(token: str):
    """Tells Meta to send this account's comments, DMs and button taps to our webhook."""
    _post("me/subscribed_apps", token, subscribed_fields="comments,messages,messaging_postbacks")


def refresh_token(token: str) -> str:
    """Long-lived tokens last 60 days; refreshing gives a fresh 60 days (token must be 24h+ old)."""
    r = httpx.get("https://graph.instagram.com/refresh_access_token",
                  params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=TIMEOUT)
    return _check(r)["access_token"]


def list_media(token: str, limit: int = 25) -> list[dict]:
    d = _get("me/media", token, limit=limit,
             fields="id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp,comments_count")
    out = []
    for m in d.get("data", []):
        kind = "REEL" if m.get("media_product_type") == "REELS" else "CAROUSEL" if m.get("media_type") == "CAROUSEL_ALBUM" else "POST"
        out.append({"id": m["id"], "caption": m.get("caption", ""), "type": kind,
                    "thumb": m.get("thumbnail_url") or m.get("media_url"), "permalink": m.get("permalink"),
                    "timestamp": m.get("timestamp"), "comments_count": m.get("comments_count", 0)})
    return out


# ---------------- insights ----------------
def _value(m: dict):
    """A metric's number, whichever shape Meta returns it in."""
    if "total_value" in m:
        return (m["total_value"] or {}).get("value")
    vals = m.get("values") or []
    return vals[0].get("value") if vals else None


def _breakdown(m: dict) -> dict:
    """{"TR": 120, "IR": 80, ...} from a metric requested with a breakdown."""
    out = {}
    for b in ((m.get("total_value") or {}).get("breakdowns") or []):
        for r in b.get("results", []):
            out["/".join(map(str, r.get("dimension_values", [])))] = r.get("value", 0)
    return out


def profile(token: str) -> dict:
    return _get("me", token, fields="user_id,username,followers_count,media_count")


def account_totals(token: str, since: int, until: int) -> dict:
    metrics = "views,reach,total_interactions,accounts_engaged,profile_links_taps,likes,comments,shares,saves"
    d = _get("me/insights", token, metric=metrics, period="day", metric_type="total_value", since=since, until=until)
    out = {m["name"]: _value(m) for m in d.get("data", [])}
    try:   # not returned under 100 followers
        f = _get("me/insights", token, metric="follows_and_unfollows", period="day", metric_type="total_value",
                 breakdown="follow_type", since=since, until=until)
        b = _breakdown((f.get("data") or [{}])[0])
        out["follows"], out["unfollows"] = b.get("FOLLOWER"), b.get("NON_FOLLOWER")
    except InstagramError:
        out["follows"] = out["unfollows"] = None
    return out


def reach_by_day(token: str, since: int, until: int) -> list[dict]:
    d = _get("me/insights", token, metric="reach", period="day", metric_type="time_series", since=since, until=until)
    vals = ((d.get("data") or [{}])[0]).get("values", [])
    return [{"day": v.get("end_time", "")[:10], "value": v.get("value", 0)} for v in vals]


def audience(token: str) -> dict:
    """Follower demographics (needs 100+ followers). {"country": {...}, "city": {...}, "age": {...}, "gender": {...}}"""
    out = {}
    for dim in ("country", "city", "age", "gender"):
        try:
            d = _get("me/insights", token, metric="follower_demographics", period="lifetime", metric_type="total_value",
                     timeframe="this_month", breakdown=dim)
            out[dim] = _breakdown((d.get("data") or [{}])[0])
        except InstagramError:
            out[dim] = {}
    return out


MEDIA_METRICS = {
    "REEL": "views,reach,likes,comments,saved,shares,total_interactions,ig_reels_avg_watch_time",
    "POST": "views,reach,likes,comments,saved,shares,total_interactions,follows,profile_visits",
    "CAROUSEL": "views,reach,likes,comments,saved,shares,total_interactions",
}


def media_insights(token: str, media_id: str, kind: str) -> dict:
    d = _get(f"{media_id}/insights", token, metric=MEDIA_METRICS.get(kind, MEDIA_METRICS["CAROUSEL"]))
    return {m["name"]: _value(m) for m in d.get("data", [])}


def active_stories(token: str) -> list[dict]:
    d = _get("me/stories", token, fields="id,media_type,media_url,thumbnail_url,permalink,timestamp")
    return d.get("data", [])


def story_insights(token: str, story_id: str) -> dict:
    d = _get(f"{story_id}/insights", token, metric="views,reach,replies,shares,total_interactions,follows,profile_visits")
    out = {m["name"]: _value(m) for m in d.get("data", [])}
    try:
        n = _get(f"{story_id}/insights", token, metric="navigation", breakdown="story_navigation_action_type")
        out["navigation"] = _breakdown((n.get("data") or [{}])[0])
    except InstagramError:
        out["navigation"] = {}
    try:
        out["link_clicks"] = _value((_get(f"{story_id}/insights", token, metric="link_clicks").get("data") or [{}])[0])
    except InstagramError:
        pass
    return out


def recent_comments(token: str, media_id: str, limit: int = 50) -> list[dict]:
    """Top-level comments on a post, newest first (used by the backup checker)."""
    return _get(f"{media_id}/comments", token, fields="id,text,timestamp,username,from", limit=limit).get("data", [])


# ---------------- replies & DMs ----------------
def reply_to_comment(token: str, comment_id: str, message: str):
    _post(f"{comment_id}/replies", token, message=message)


def _message(text: str, button: str | None) -> dict:
    """Plain text, or a 'button template': text with one tappable button under it."""
    if not button:
        return {"text": text}
    return {"attachment": {"type": "template", "payload": {
        "template_type": "button", "text": text,
        "buttons": [{"type": "postback", "title": button, "payload": FOLLOW_CHECK}]}}}


def private_reply(token: str, comment_id: str, text: str, button: str | None = None) -> str:
    """DMs the person who wrote a comment (once per comment, within 7 days). Returns their IGSID."""
    return _post("me/messages", token, {"recipient": {"comment_id": comment_id},
                                        "message": _message(text, button)})["recipient_id"]


def send_dm(token: str, igsid: str, text: str, button: str | None = None):
    """A normal DM. Only allowed within 24h of the person's last message or button tap."""
    _post("me/messages", token, {"recipient": {"id": igsid}, "message": _message(text, button)})


def user_follows(token: str, igsid: str) -> bool:
    """Does this person follow the account? Only works after they've interacted with your DMs."""
    return bool(_get(igsid, token, fields="is_user_follow_business").get("is_user_follow_business"))


# ---------------- webhook signature ----------------
def signature_ok(body: bytes, header: str | None) -> bool:
    """Meta signs each webhook with the app secret (X-Hub-Signature-256: sha256=...)."""
    if not APP_SECRET:
        return False
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


DEMO_MEDIA = [
    {"id": "demo_reel_1", "caption": "لاته پسته‌ای رسید 🌿 فقط همین هفته!", "type": "REEL"},
    {"id": "demo_post_1", "caption": "منوی پاییزه‌مون اومد، ورق بزن همه‌ش رو ببین 🍂", "type": "CAROUSEL"},
    {"id": "demo_reel_2", "caption": "کلد برو رو چطوری درست می‌کنیم؟ (18 ساعت دم می‌کشه!)", "type": "REEL"},
    {"id": "demo_post_2", "caption": "دوشنبه‌ها تخفیف دانشجویی داریم 🎓", "type": "POST"},
]
