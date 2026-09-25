"""KIE gpt-image-2-image-to-image cover, or a hard blocker (no fake image).

Face refs: public GitHub raw URLs. Do NOT upload to catbox/0x0 (REF_HOST).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from kie_client import KieError, MODEL, create_i2i_task, result_urls, wait_for_success

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_SCRIPTS = REPO_ROOT / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

from asset_download import download_url_bytes  # noqa: E402
from image_validate import sniff_image_format  # noqa: E402


BLOCKER_NO_KEY = "KIE_API_KEY"
BLOCKER_REFS = "FACE_REFS"
BLOCKER_HOST = "REF_HOST"
BLOCKER_KIE = "KIE_TASK"

PUBLIC_FACE_REF_URLS = (
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
)


def face_ref_paths(root: Path) -> list[Path]:
    names = ("ruslan_selfie_blue.jpg", "ruslan_selfie_black.jpg")
    found: list[Path] = []
    for name in names:
        path = root / "vk-daily" / "refs" / name
        if path.is_file() and path.stat().st_size > 1000:
            found.append(path)
    return found


def resolve_face_ref_urls(*, explicit: list[str] | None = None) -> list[str]:
    """Public HTTPS selfie URLs for KIE input_urls. Never catbox/0x0."""
    if explicit:
        urls = [
            u.strip()
            for u in explicit
            if isinstance(u, str) and u.strip().startswith("https://")
        ]
        if urls:
            return urls
    env = (os.environ.get("VK_DAILY_FACE_REF_URLS") or "").strip()
    if env:
        urls = [
            u.strip()
            for u in env.replace(";", ",").split(",")
            if u.strip().startswith("https://")
        ]
        if urls:
            return urls
    return list(PUBLIC_FACE_REF_URLS)


def build_prompt(
    *,
    headline: str,
    composition_prompt: str,
    accent: str,
    masthead: str = "УФА",
    date_badge: str = "СЕНТЯБРЬ 2026",
    dek: str = "",
    person_name: str = "РУСЛАН МУХТАРОВ",
) -> str:
    parts = [
        "Glossy magazine cover, horizontal 16:9 landscape layout, high production value.",
        "Photoreal editorial portrait of the SAME man as in the two reference selfies.",
        "Preserve exact facial identity: short dark hair faded on sides, light grey-blue eyes,",
        "natural smile, light stubble, no glasses, no beautifying into another person.",
        "Outfit: premium real-estate agent in a fitted monochrome crisp white or pale-blue dress shirt",
        "(unbuttoned collar), slim dark trousers, leather watch. No hoodie, no casual sweatshirt from the selfies.",
        "Editorial fashion poses: three-quarter portrait, confident wall-lean or seated-on-armrest,",
        "arms folded naturally or one hand in a pocket. Not a river-window-morning apartment interior.",
        f"Scene: {composition_prompt}",
        f"Masthead at the top in bold Cyrillic: «{masthead}».",
        f"Issue date badge: «{date_badge}».",
        f"Name on the cover in Cyrillic, exactly: «{person_name}». Never write Хабибуллин or any other surname.",
        f"Brand accent color {accent} only (no pink highlighter, no red sale banner).",
        f"Large readable Cyrillic headline on the image, exactly: «{headline}».",
    ]
    if dek:
        parts.append(f"Subheadline / dek under the headline, exactly: «{dek}».")
    parts.extend(
        [
            "No period at the end of the headline, no emoji, no URLs, no phone number, no extra slogans.",
            "Background is recognizable Ufa, Russia: Belaya river embankment, autumn city architecture,",
            "Sipaylovo panels or Lala-Tulpan mosque silhouette softly out of focus. Not Moscow, not Red Square.",
            "NEGATIVE: metro / subway station in Ufa, Moscow skyline, Red Square, English poster text,",
            "watermark, extra fingers, hoodie, river-window-morning composition, Khabibullin, neon cyberpunk, different face.",
        ]
    )
    return " ".join(parts)


def generate_cover(
    *,
    root: Path,
    out_dir: Path,
    headline: str,
    composition_prompt: str,
    accent: str,
    aspect_ratio: str = "16:9",
    resolution: str = "2K",
    masthead: str = "УФА",
    date_badge: str = "СЕНТЯБРЬ 2026",
    dek: str = "",
    person_name: str = "РУСЛАН МУХТАРОВ",
    input_urls: list[str] | None = None,
) -> dict:
    """Return cover meta. Never writes a fake raster if generation did not happen."""
    api_key = (os.environ.get("KIE_API_KEY") or "").strip()
    if not api_key:
        return {
            "status": "blocked",
            "blocker": BLOCKER_NO_KEY,
            "blocker_message": (
                "❌ VK COVER BLOCKER: KIE_API_KEY is not set. "
                "Cover not generated. Do not publish a fake image."
            ),
            "model": MODEL,
        }

    urls = resolve_face_ref_urls(explicit=input_urls)
    if len(urls) < 1:
        return {
            "status": "blocked",
            "blocker": BLOCKER_REFS,
            "blocker_message": (
                "❌ VK REFS BLOCKER: no public HTTPS face-ref URLs for KIE input_urls. "
                "Cover not generated. Do not invent a face. Do not host via catbox/0x0."
            ),
            "model": MODEL,
        }

    prompt = build_prompt(
        headline=headline,
        composition_prompt=composition_prompt,
        accent=accent,
        masthead=masthead,
        date_badge=date_badge,
        dek=dek,
        person_name=person_name,
    )
    try:
        task_id = create_i2i_task(
            api_key,
            prompt=prompt,
            input_urls=urls,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        task = wait_for_success(api_key, task_id)
        result = result_urls(task)
        if not result:
            raise KieError("success without resultUrls")
        cover_url = result[0]
        data, _evidence = download_url_bytes(cover_url)
        kind = sniff_image_format(data)
        if kind not in {"png", "jpeg", "webp"}:
            raise KieError(f"downloaded cover is not an image: {kind!r}")
        cover_path = out_dir / "cover.png"
        cover_path.write_bytes(data)
        (out_dir / "cover-url.txt").write_text(cover_url + "\n", encoding="utf-8")
        try:
            cover_rel = cover_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            cover_rel = cover_path.as_posix()
        return {
            "status": "ok",
            "blocker": None,
            "blocker_message": None,
            "model": MODEL,
            "task_id": task_id,
            "cover_rel": cover_rel,
            "cover_url": cover_url,
            "cover_sniff": kind,
            "input_urls_count": len(urls),
            "input_urls": urls,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_KIE,
            "blocker_message": f"❌ VK COVER BLOCKER: KIE i2i failed: {exc}",
            "model": MODEL,
        }
