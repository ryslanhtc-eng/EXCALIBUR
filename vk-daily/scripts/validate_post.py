"""Validate VK daily post + cover headline/description against tenant hard rules."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)

ALLOWED_EMOTION = set("😅😄😊😌🤔😬🔥💔❤")
METRO_PATTERNS = ("метро", "metro", "подземк", "метрополитен")
BANNED_DASHES = ("—", "–")


def load_banned(vk_root: Path) -> dict:
    return json.loads((vk_root / "data" / "banned.json").read_text(encoding="utf-8"))


def load_tenant(vk_root: Path) -> dict:
    return json.loads((vk_root / "tenant" / "tenant.json").read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def iter_emoji(text: str) -> list[str]:
    found: list[str] = []
    for match in EMOJI_RE.finditer(text):
        chunk = match.group(0)
        for ch in chunk:
            if ch in ("\u200d", "\ufe0f"):
                continue
            found.append(ch)
    return found


def _check_metro(text: str) -> list[str]:
    lowered = _norm(text)
    for pat in METRO_PATTERNS:
        if pat in lowered:
            return [f"hard rule violation: metro mentioned in text ('{pat}')"]
    return []


def _check_dashes(text: str) -> list[str]:
    errors: list[str] = []
    for dash in BANNED_DASHES:
        if dash in text:
            name = "em-dash (—)" if dash == "—" else "en-dash (–)"
            errors.append(f"hard rule violation: {name} found in text")
    return errors


def validate_headline(headline: str, tenant: dict, banned: dict | None = None) -> list[str]:
    errors: list[str] = []
    raw = headline.strip()
    if not raw:
        return ["cover headline is empty"]
    if raw[-1] in ".!?…":
        errors.append("cover headline must not end with period or ?!")
    if any(ch in raw for ch in ".!?"):
        errors.append("cover headline must not contain . ! ?")
    words = [w for w in raw.split() if w]
    lo = int(tenant["cover"]["headline_words_min"])
    hi = int(tenant["cover"]["headline_words_max"])
    if not (lo <= len(words) <= hi):
        errors.append(f"cover headline must be {lo}-{hi} words, got {len(words)}")
    if iter_emoji(raw):
        errors.append("cover headline must not contain emoji")
    if re.search(r"https?://|www\.|t\.me/|vk\.(?:com|ru|me)/", raw, re.I):
        errors.append("cover headline must not contain links")
    errors.extend(_check_metro(raw))
    errors.extend(_check_dashes(raw))
    return errors


def validate_description(description: str, tenant: dict | None = None, banned: dict | None = None) -> list[str]:
    errors: list[str] = []
    raw = description.strip()
    if not raw:
        return ["cover description (dek) is empty"]
    words = [w for w in raw.split() if w]
    if len(words) < 2 or len(words) > 15:
        errors.append(f"cover description must be 2-15 words, got {len(words)}")
    if iter_emoji(raw):
        errors.append("cover description must not contain emoji")
    if re.search(r"https?://|www\.|t\.me/|vk\.(?:com|ru|me)/", raw, re.I):
        errors.append("cover description must not contain links")
    errors.extend(_check_metro(raw))
    errors.extend(_check_dashes(raw))
    return errors


def validate_post(text: str, tenant: dict, banned: dict) -> list[str]:
    errors: list[str] = []
    body = text.strip()
    if not body:
        return ["post.txt is empty"]

    min_c = int(tenant["post"]["min_chars"])
    max_c = int(tenant["post"]["max_chars"])
    n = len(body)
    if n < min_c or n > max_c:
        errors.append(f"post length {n} not in {min_c}-{max_c}")

    if not tenant["post"].get("allow_links", False):
        for pat in banned.get("link_patterns", []):
            if pat.lower() in body.lower():
                errors.append(f"links are forbidden: found {pat}")

    errors.extend(_check_metro(body))
    errors.extend(_check_dashes(body))

    lowered = _norm(body)
    for stamp in banned.get("ai_stamps", []):
        if _norm(stamp) in lowered:
            errors.append(f"AI stamp forbidden: '{stamp}'")

    emojis = iter_emoji(body)
    object_set = set(banned.get("object_emoji", ""))
    for ch in emojis:
        if ch in object_set or (ch not in ALLOWED_EMOTION and unicodedata.category(ch).startswith("So")):
            if ch not in ALLOWED_EMOTION:
                errors.append(f"non-emotion emoji: {ch}")
    if len(emojis) > 2:
        errors.append(f"too many emoji: {len(emojis)} (max 2)")

    return errors
