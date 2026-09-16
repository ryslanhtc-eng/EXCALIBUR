"""Validate VK daily post + cover headline against tenant hard rules."""
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


def validate_headline(headline: str, tenant: dict) -> list[str]:
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
    if re.search(r"https?://|www\.|t\.me/", raw, re.I):
        errors.append("cover headline must not contain links")
    return errors


def _metro_mention(text: str) -> list[str]:
    """Never mention метро in posts at all — not as fact, not as denial, not as comparison."""
    if re.search(r"\bметро\b|\bметрополитен|\bподземк", text, re.IGNORECASE):
        return ["metro mention is forbidden (never mention metro in posts at all)"]
    return []


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
                errors.append(f"links are forbidden for now: found {pat}")

    if "—" in body or "–" in body:
        errors.append("em/en dashes forbidden (use regular hyphen -)")

    errors.extend(_metro_mention(body))

    emojis = iter_emoji(body)
    object_set = set(banned.get("object_emoji", ""))
    for ch in emojis:
        if ch in object_set or (ch not in ALLOWED_EMOTION and unicodedata.category(ch).startswith("So")):
            if ch not in ALLOWED_EMOTION:
                errors.append(f"non-emotion emoji: {ch}")
    if len(emojis) > 2:
        errors.append(f"too many emoji: {len(emojis)} (max 2)")

    return errors
