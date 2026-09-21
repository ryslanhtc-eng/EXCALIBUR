"""KIE gpt-image-2-image-to-image cover, or a hard blocker (no fake image)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from host_image import host_image
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


def face_ref_paths(root: Path) -> list[Path]:
    names = ("ruslan_selfie_blue.jpg", "ruslan_selfie_black.jpg")
    found: list[Path] = []
    for name in names:
        path = root / "vk-daily" / "refs" / name
        if path.is_file() and path.stat().st_size > 1000:
            found.append(path)
    return found


def build_prompt(
    *,
    headline: str,
    composition_prompt: str,
    accent: str,
    dek: str = "",
    masthead: str = "УФА",
    date_badge: str = "СЕНТЯБРЬ 2026",
) -> str:
    prompt_parts = [
        "Photoreal glossy editorial magazine cover format (16:9 landscape) of the SAME man as in the reference selfies.",
        "Preserve exact facial identity: short dark hair faded on sides, light grey-blue eyes, natural smile, light stubble, no glasses, no beautifying into another person.",
        "Character styling: stylish premium real estate broker wearing a tailored dark navy suit jacket and crisp white shirt (or elegant coat), refined and confident, NOT a hoodie or casual t-shirt.",
        f"Scene: {composition_prompt}",
        "Setting is recognizable modern beautiful Ufa residential setting: beautiful embankment or modern comfortable courtyard in Ufa, clean architecture.",
        f"Brand accent color {accent} subtle touches.",
        f"Top magazine masthead text clearly legible in Cyrillic: «{masthead}».",
        f"Small date badge in corner: «{date_badge}».",
        f"Large bold readable Cyrillic headline on the cover: «{headline}».",
    ]
    if dek:
        prompt_parts.append(f"Subtitle dek line below headline: «{dek}».")
    prompt_parts.extend([
        "No period at the end of headline, no emoji, no URLs, no phone numbers, no extra fake slogans.",
        "NEGATIVE: metro / subway station in Ufa, Moscow skyline, Red Square, English poster text, watermark, extra fingers, cartoonish look, neon cyberpunk, casual hoodie, different face.",
    ])
    return " ".join(prompt_parts)


def generate_cover(
    *,
    root: Path,
    out_dir: Path,
    headline: str,
    composition_prompt: str,
    accent: str,
    aspect_ratio: str,
    resolution: str,
    dek: str = "",
    masthead: str = "УФА",
    date_badge: str = "СЕНТЯБРЬ 2026",
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

    refs = face_ref_paths(root)
    if len(refs) < 1:
        return {
            "status": "blocked",
            "blocker": BLOCKER_REFS,
            "blocker_message": (
                "❌ VK REFS BLOCKER: missing vk-daily/refs/ruslan_selfie_{blue,black}.jpg. "
                "Cover not generated. Do not invent a face."
            ),
            "model": MODEL,
        }

    try:
        input_urls = [host_image(path) for path in refs]
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_HOST,
            "blocker_message": f"❌ VK COVER BLOCKER: could not host face refs: {exc}",
            "model": MODEL,
        }

    prompt = build_prompt(
        headline=headline,
        composition_prompt=composition_prompt,
        accent=accent,
        dek=dek,
        masthead=masthead,
        date_badge=date_badge,
    )
    try:
        task_id = create_i2i_task(
            api_key,
            prompt=prompt,
            input_urls=input_urls,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        task = wait_for_success(api_key, task_id)
        urls = result_urls(task)
        if not urls:
            raise KieError("success without resultUrls")
        cover_url = urls[0]
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
            "input_urls_count": len(input_urls),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_KIE,
            "blocker_message": f"❌ VK COVER BLOCKER: KIE i2i failed: {exc}",
            "model": MODEL,
        }
