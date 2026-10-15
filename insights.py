"""Insights for the dashboard: account, posts & reels, stories, and bot impact.

Instagram data is cached so the app stays well under Instagram's rate limits:
  account totals 1h · audience 24h · post stats 3h · stories are captured every hour by a background job
(story stats disappear from Instagram after 24 hours, so they're saved before that).
"""
import random
import time
from datetime import datetime, timedelta, timezone

import instagram
import security
import store
from instagram import InstagramError

PERMISSION_HINT = ("Instagram didn't allow reading insights. Generate a new token with the "
                   "instagram_business_manage_insights permission and reconnect the account in Settings.")


def _token(acc):
    t = security.decrypt(acc["token_enc"])
    if not t:
        raise InstagramError("This account's token can't be read. Reconnect it in Settings.")
    return t


def _friendly(e: Exception) -> str:
    msg = str(e)
    return PERMISSION_HINT if ("permission" in msg.lower() or "(#10)" in msg or "(#200)" in msg) else f"Instagram: {msg}"


def _rate(part, whole):
    return round(100 * part / whole, 1) if part is not None and whole else None


# ---------------- account ----------------
def account(acc: dict, days: int, refresh=False) -> dict:
    if acc["is_demo"]:
        return _demo_account(acc, days)
    aid = acc["id"]
    key = f"account:{days}"
    data = None if refresh else store.cache_get(aid, key, 3600)
    if data is None:
        try:
            token = _token(acc)
            until = int(time.time())
            since = until - days * 86400
            totals = instagram.account_totals(token, since, until)
            reach = instagram.reach_by_day(token, since, until)
            prof = instagram.profile(token)
            store.save_followers(aid, _today(), prof.get("followers_count") or 0)
            data = {"totals": totals, "reach_by_day": reach, "followers": prof.get("followers_count"),
                    "media_count": prof.get("media_count")}
            store.cache_put(aid, key, data)
        except InstagramError as e:
            return {"error": _friendly(e)}
    aud = store.cache_get(aid, "audience", 86400)
    if aud is None:
        try:
            aud = instagram.audience(_token(acc))
            store.cache_put(aid, "audience", aud)
        except InstagramError:
            aud = {}
    t = data["totals"]
    return {**data, "audience": aud, "follower_history": store.follower_history(aid, max(days, 30)),
            "net_follows": (t.get("follows") or 0) - (t.get("unfollows") or 0) if t.get("follows") is not None else None,
            "engagement_rate": _rate(t.get("total_interactions"), t.get("reach"))}


# ---------------- posts & reels ----------------
def posts(acc: dict, refresh=False) -> dict:
    if acc["is_demo"]:
        return _demo_posts(acc)
    aid = acc["id"]
    cached = None if refresh else store.cache_get(aid, "posts", 3 * 3600)
    if cached is not None:
        return cached
    try:
        token = _token(acc)
        out, failed = [], 0
        for m in instagram.list_media(token):
            try:
                stats = instagram.media_insights(token, m["id"], m["type"])
            except InstagramError as e:
                if "permission" in str(e).lower():
                    raise
                stats, failed = {}, failed + 1
            out.append({**m, "stats": stats, "engagement_rate": _rate(stats.get("total_interactions"), stats.get("reach"))})
        data = {"posts": out, "fetched_at": store.now(), "partial": failed}
        store.cache_put(aid, "posts", data)
        return data
    except InstagramError as e:
        return {"error": _friendly(e), "posts": []}


# ---------------- stories ----------------
def capture_stories(acc: dict) -> int:
    """Saves the stats of the account's live stories. Run hourly; returns how many were saved."""
    token = _token(acc)
    saved = 0
    for s in instagram.active_stories(token):
        try:
            metrics = instagram.story_insights(token, s["id"])
        except InstagramError as e:
            if "(#10)" in str(e) or "viewers" in str(e).lower():
                metrics = {"too_few_viewers": True}   # Instagram hides stats for stories with fewer than 5 viewers
            else:
                raise
        store.save_story(acc["id"], s, metrics)
        saved += 1
    return saved


def stories(acc: dict, days: int, refresh=False) -> dict:
    if acc["is_demo"]:
        return _demo_stories(acc, days)
    error = None
    if refresh:
        try:
            capture_stories(acc)
        except InstagramError as e:
            error = _friendly(e)
    out = []
    for s in store.list_stories(acc["id"], days):
        m = s["metrics"]
        nav = m.get("navigation") or {}
        out.append({"id": s["story_id"], "media_type": s["media_type"], "thumb": s["thumb"], "permalink": s["permalink"],
                    "posted_at": s["posted_at"], "captured_at": s["captured_at"], "stats": m,
                    "exits": nav.get("TAP_EXIT"), "forward": nav.get("TAP_FORWARD"), "back": nav.get("TAP_BACK"),
                    "exit_rate": _rate(nav.get("TAP_EXIT"), m.get("views"))})
    return {"stories": out, "error": error}


# ---------------- bot impact ----------------
def impact(acc: dict, days: int) -> dict:
    return store.impact(acc["id"], days, include_test=acc["is_demo"])


# ---------------- background jobs ----------------
def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def hourly_job():
    for acc in store.list_accounts():
        if acc["is_demo"] or not acc["token_enc"]:
            continue
        try:
            capture_stories(acc)
            store.save_followers(acc["id"], _today(), instagram.profile(_token(acc)).get("followers_count") or 0)
        except Exception as e:
            print(f"[insights] @{acc['username']}: {e}")


# ---------------- demo data (realistic, stable per account) ----------------
def _rng(acc, salt) -> random.Random:
    return random.Random(f"{acc['id']}-{salt}")


def _demo_account(acc, days):
    r = _rng(acc, days)
    today = datetime.now(timezone.utc).date()
    reach = [{"day": (today - timedelta(days=days - 1 - i)).isoformat(), "value": int(900 + 400 * r.random() + 25 * i)} for i in range(days)]
    followers = 2480
    hist = []
    for i in range(max(days, 30)):
        followers += r.randint(-3, 14)
        hist.append({"day": (today - timedelta(days=max(days, 30) - 1 - i)).isoformat(), "followers": followers})
    total_reach = int(sum(p["value"] for p in reach) * 0.62)
    inter = int(total_reach * 0.071)
    totals = {"views": int(total_reach * 3.4), "reach": total_reach, "total_interactions": inter,
              "accounts_engaged": int(inter * 0.74), "profile_links_taps": int(inter * 0.11), "likes": int(inter * 0.7),
              "comments": int(inter * 0.12), "shares": int(inter * 0.08), "saves": int(inter * 0.1),
              "follows": 9 * days + r.randint(0, 20), "unfollows": 3 * days + r.randint(0, 8)}
    return {"totals": totals, "reach_by_day": reach, "followers": hist[-1]["followers"], "media_count": 48,
            "follower_history": hist, "net_follows": totals["follows"] - totals["unfollows"],
            "engagement_rate": _rate(inter, total_reach),
            "audience": {"country": {"TR": 1120, "IR": 690, "DE": 210, "US": 140, "GB": 95, "AE": 70},
                         "city": {"Istanbul, Türkiye": 860, "Tehran, Iran": 410, "Ankara, Türkiye": 120, "Berlin, Germany": 90, "Shiraz, Iran": 70},
                         "age": {"13-17": 60, "18-24": 980, "25-34": 870, "35-44": 330, "45-54": 120, "55-64": 40},
                         "gender": {"F": 1390, "M": 980, "U": 110}},
            "demo": True}


def _demo_posts(acc):
    r = _rng(acc, "posts")
    out = []
    for m in instagram.DEMO_MEDIA:
        reach = r.randint(1200, 9000) * (2 if m["type"] == "REEL" else 1)
        inter = int(reach * r.uniform(0.03, 0.11))
        stats = {"views": int(reach * r.uniform(1.4, 2.6)), "reach": reach, "likes": int(inter * 0.72), "comments": int(inter * 0.1),
                 "saved": int(inter * 0.09), "shares": int(inter * 0.09), "total_interactions": inter}
        if m["type"] == "REEL":
            stats["ig_reels_avg_watch_time"] = r.randint(4200, 11800)
        else:
            stats["follows"], stats["profile_visits"] = r.randint(2, 40), r.randint(30, 300)
        out.append({**m, "thumb": None, "permalink": None, "stats": stats, "engagement_rate": _rate(inter, reach)})
    return {"posts": out, "fetched_at": store.now(), "partial": 0, "demo": True}


def _demo_stories(acc, days):
    r = _rng(acc, f"stories{days}")
    now = datetime.now(timezone.utc)
    out = []
    for i in range(min(days, 9)):
        views = r.randint(300, 1400)
        exits = int(views * r.uniform(0.04, 0.2))
        stats = {"views": views, "reach": int(views * 0.86), "replies": r.randint(0, 25), "shares": r.randint(0, 12),
                 "follows": r.randint(0, 9), "profile_visits": r.randint(5, 60), "link_clicks": r.choice([None, r.randint(10, 90)]),
                 "total_interactions": r.randint(10, 80)}
        posted = (now - timedelta(hours=8 + 19 * i)).isoformat()
        out.append({"id": f"demo-story-{i}", "media_type": r.choice(["IMAGE", "VIDEO"]), "thumb": None, "permalink": None,
                    "posted_at": posted, "captured_at": posted, "stats": stats, "exits": exits,
                    "forward": int(views * r.uniform(0.3, 0.6)), "back": int(views * r.uniform(0.02, 0.08)),
                    "exit_rate": _rate(exits, views)})
    return {"stories": out, "error": None, "demo": True}
