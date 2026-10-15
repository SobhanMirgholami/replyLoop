"""The bot: decides what to do with each comment, runs the followers-only DM flow,
and keeps an event timeline for the inbox. Works per Instagram account.

Test mode (account.live = False): everything is decided and logged, nothing is sent to Instagram.
"""
import threading
import time
from datetime import datetime

import ai
import instagram
import rules
import security
import store
from config import POLL_POSTS, POLL_SECONDS


def _token(account) -> str | None:
    return security.decrypt(account["token_enc"])


# ---------------- deciding ----------------
def decide(account: dict, text: str, username: str, media_id: str | None) -> dict:
    """What should happen for this comment? Used by the webhook, the simulator and the tester.
    Returns {source, reply, dm, followers_only, gate_text, gate_button, not_following_text}."""
    aid = account["id"]
    out = {"source": None, "reply": None, "dm": None, "followers_only": False,
           "gate_text": None, "gate_button": None, "not_following_text": None}
    settings = store.get_settings(aid)
    if rules.is_ignored(text, settings["ignore_keywords"]):
        return {**out, "source": "ignored"}

    post = store.get_post(aid, media_id)
    if not post["autoreply_enabled"]:
        return {**out, "source": "paused"}

    rule, source = rules.match_rule(aid, text, media_id)
    if rule:
        dm = rules.fill(rule["dm"], username) or None
        gated = bool(dm and rule["followers_only"])
        return {**out, "source": source, "reply": rules.fill(rule["reply"], username) or None, "dm": dm,
                "followers_only": gated,
                "gate_text": rules.fill(rule["gate_text"] or settings["gate_message"], username) if gated else None,
                "gate_button": (rule["gate_button"] or settings["gate_button"]) if gated else None,
                "not_following_text": rules.fill(rule["not_following_text"] or settings["not_following_message"], username) if gated else None}

    if settings["ai_fallback"] and post["ai_enabled"] and ai.available():
        reply = ai.ai_reply(text, username, settings["brand_voice"], post["context"])
        return {**out, "source": "ai" if reply else "ai-skip", "reply": reply}
    return {**out, "source": "no-match"}


# ---------------- a new comment ----------------
def handle_comment(account: dict, v: dict):
    aid = account["id"]
    comment_id = v.get("id")
    text = (v.get("text") or "").strip()
    sender = v.get("from") or {}
    username = sender.get("username", "")
    media_id = (v.get("media") or {}).get("id")

    if not comment_id or not text:
        return
    if str(sender.get("id")) == account["ig_user_id"] or (username and username == account["username"]):
        return   # our own comment/reply -> avoid an endless loop
    if not store.claim_comment(aid, comment_id, media_id, username, text):   # Meta sometimes delivers twice
        return
    store.add_event(aid, comment_id, "comment", text)
    d = decide(account, text, username, media_id)

    if not d["reply"] and not d["dm"]:
        store.save_comment(aid, comment_id, media_id, username, text, d["source"], None, "skipped", None)
        store.add_event(aid, comment_id, "skipped", d["source"])
        return

    status = _public_reply(account, comment_id, d["reply"]) if d["reply"] else "dm-only"
    dm_status = _start_dm(account, comment_id, sender.get("id"), media_id, d) if d["dm"] else None
    store.save_comment(aid, comment_id, media_id, username, text, d["source"], d["reply"], status, dm_status)


def _public_reply(account, comment_id, reply) -> str:
    aid = account["id"]
    if not account["live"]:
        store.add_event(aid, comment_id, "reply", reply)
        return "test"
    try:
        instagram.reply_to_comment(_token(account), comment_id, reply)
        store.add_event(aid, comment_id, "reply", reply)
        return "sent"
    except Exception as e:
        store.add_event(aid, comment_id, "error", f"Public reply failed: {e}")
        return f"error: {e}"


def _start_dm(account, comment_id, sender_id, media_id, d) -> str:
    """The one DM a comment allows. Followers-only: a headline + button; the tap lets us check follow status."""
    aid = account["id"]
    text, button = (d["gate_text"], d["gate_button"]) if d["followers_only"] else (d["dm"], None)
    try:
        if account["live"]:
            igsid = instagram.private_reply(_token(account), comment_id, text, button)
        else:
            igsid = str(sender_id or f"test-{comment_id}")
    except Exception as e:
        store.add_event(aid, comment_id, "error", f"DM failed: {e}")
        return f"error: {e}"
    store.add_event(aid, comment_id, "dm_button" if button else "dm", text, button)
    if d["followers_only"]:
        store.add_dm_request(aid, igsid, comment_id, media_id, d["dm"], button, d["not_following_text"])
        return "waiting_tap"
    return "sent"


# ---------------- a button tap or DM to the account ----------------
def handle_message(account: dict, event: dict, follows_override: bool | None = None):
    """Someone tapped our button or DMed the account. If they're waiting on followers-only
    details, check whether they follow. follows_override is used by the simulator in test mode."""
    aid = account["id"]
    sender = str((event.get("sender") or {}).get("id") or "")
    msg = event.get("message") or {}
    tap = event.get("postback") or {}
    if not sender or sender == account["ig_user_id"] or msg.get("is_echo") or not (msg or tap):
        return
    mid = msg.get("mid") or tap.get("mid")
    if mid and store.message_seen(mid):
        return
    pending = store.pending_dms(aid, sender)
    if not pending:
        return   # a normal DM, not for the bot

    settings = store.get_settings(aid)
    last = pending[-1]
    button = last["button"] or settings["gate_button"]
    for p in pending:
        store.add_event(aid, p["comment_id"], "tap" if tap else "message", tap.get("title") or msg.get("text"))

    try:
        if follows_override is not None:
            follows = follows_override
        else:
            follows = instagram.user_follows(_token(account), sender)
    except Exception as e:
        # Instagram wouldn't share the follow status. A typed message always unlocks it.
        try:
            _dm(account, sender, settings["check_failed_message"])
            for p in pending:
                store.add_event(aid, p["comment_id"], "check_failed", settings["check_failed_message"])
            store.set_dm_status(pending, "waiting_message")
        except Exception as e2:
            store.set_dm_status(pending, f"error: {e2}")
        return

    try:
        if follows:
            for text in dict.fromkeys(p["text"] for p in pending):   # the same details only once
                _dm(account, sender, text)
            for p in pending:
                store.add_event(aid, p["comment_id"], "details", p["text"])
            store.set_dm_status(pending, "delivered")
        else:
            not_following = last["not_following_text"] or settings["not_following_message"]
            _dm(account, sender, not_following, button)
            for p in pending:
                store.add_event(aid, p["comment_id"], "not_following", not_following, button)
            store.set_dm_status(pending, "waiting_follow")
    except Exception as e:
        for p in pending:
            store.add_event(aid, p["comment_id"], "error", f"DM failed: {e}")
        store.set_dm_status(pending, f"error: {e}")


def _dm(account, igsid, text, button=None):
    if account["live"]:
        instagram.send_dm(_token(account), igsid, text, button)


# ---------------- background: keep tokens fresh ----------------
def refresh_tokens_once():
    for acc in store.list_accounts():
        if acc["is_demo"] or not acc["token_enc"]:
            continue
        if (acc["token_refreshed_at"] or "") > store.ago(days=7):
            continue
        token = _token(acc)
        if not token:
            store.update_account(acc["id"], last_error="Saved token can't be read (SECRET_KEY changed?). Reconnect the account.")
            continue
        try:
            store.update_account(acc["id"], token_enc=security.encrypt(instagram.refresh_token(token)),
                                 token_refreshed_at=store.now(), last_error=None)
        except Exception as e:
            store.update_account(acc["id"], last_error=f"Token refresh failed: {e}")


# ---------------- background: backup comment checker ----------------
def _ts(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")          # Instagram: 2026-10-12T09:00:00+0000
    except ValueError:
        try:
            return datetime.fromisoformat(s)                          # ours: 2026-10-12T09:00:00.123+00:00
        except ValueError:
            return None


def poll_once():
    """Catches comments the webhook missed (or all of them, if Meta never sends webhooks).
    Only comments written after the account went live are answered; duplicates are skipped."""
    for acc in store.list_accounts():
        if not acc["live"] or acc["is_demo"]:
            continue
        token = _token(acc)
        since = _ts(acc.get("live_since"))
        if not token or not since:
            continue
        try:
            for m in instagram.list_media(token, limit=POLL_POSTS):
                for c in instagram.recent_comments(token, m["id"]):
                    t = _ts(c.get("timestamp"))
                    if not t or t < since:
                        continue
                    sender = c.get("from") or {"username": c.get("username", "")}
                    handle_comment(acc, {"id": c["id"], "text": c.get("text", ""), "from": sender, "media": {"id": m["id"]}})
        except Exception as e:
            store.update_account(acc["id"], last_error=f"Checking for new comments failed: {e}")


def start_background_jobs():
    def maintenance():
        while True:
            try:
                refresh_tokens_once()
                store.purge_old()
            except Exception as e:
                print(f"[background] {e}")
            time.sleep(6 * 3600)

    def poller():
        while True:
            time.sleep(POLL_SECONDS)
            try:
                poll_once()
            except Exception as e:
                print(f"[poll] {e}")

    def hourly():
        import insights   # stories vanish from Instagram after 24h: save their stats every hour
        while True:
            try:
                insights.hourly_job()
            except Exception as e:
                print(f"[insights] {e}")
            time.sleep(3600)

    threading.Thread(target=maintenance, daemon=True, name="maintenance").start()
    threading.Thread(target=hourly, daemon=True, name="insights").start()
    if POLL_SECONDS > 0:
        threading.Thread(target=poller, daemon=True, name="comment-poller").start()
