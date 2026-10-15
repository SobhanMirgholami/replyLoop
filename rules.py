"""Keyword matching. A post's own rules are checked before the global ones; the first match wins."""
import store

# Fold Turkish letters on BOTH sides, so "FISTIK", "fıstık" and "fistik" all match each other.
_TR = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ç": "c", "ç": "c",
                     "Ğ": "g", "ğ": "g", "Ö": "o", "ö": "o", "Ü": "u", "ü": "u"})
# Persian/Arabic variants of the same letters ("ي"/"ی", "ك"/"ک") and invisible joiners.
_FA = str.maketrans({"ي": "ی", "ك": "ک", "‌": " ", "ـ": ""})


def norm(s: str) -> str:
    return " ".join(s.translate(_TR).translate(_FA).casefold().split())


def fill(template: str, username: str) -> str:
    return (template or "").replace("{username}", username).strip()


def is_ignored(text: str, ignore_keywords: list[str]) -> bool:
    t = norm(text)
    return any(norm(k) in t for k in ignore_keywords if k.strip())


def match_rule(aid: int, text: str, media_id: str | None):
    """Returns (rule, source), e.g. ({...}, "post:Menu link"), or (None, None)."""
    t = norm(text)
    for rule, scope in store.rules_for(aid, media_id):
        if any(norm(k) in t for k in rule["keywords"] if k.strip()):
            return rule, f"{scope}:{rule['name'] or rule['id']}"
    return None, None
