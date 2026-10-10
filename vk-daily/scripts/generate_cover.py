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
    masthead: str = "УФА",
    date_badge: str = "ОКТЯБРЬ 2026",
    dek: str = "",
    style: str = "anime",
) -> str:
    prompt_parts = [
        "Vibrant anime cel-shaded illustration, 16:9 widescreen format, high quality 2D anime graphic art style, clean dynamic linework, rich flat cel-shading colors, not photographic, not photoreal, not realistic, not 3D render, not CGI.",
        "REFERENCE FACE IDENTITY IN ANIME STYLE: Capture the recognizable facial likeness of the SAME man as in the reference selfies adapted into Japanese anime aesthetic: "
        "Russian man ~45-50 years old, short dark buzz cut hair with distinguished grey touches at temples, light grey-blue eyes, "
        "warm authentic confident smile, clean shaven with subtle mature facial lines, distinctive small beauty mark / mole near the bridge of nose, simple gold wedding ring on hand. "
        "Do NOT make him look like a generic teenage anime boy, preserve his mature 45-50 age character while strictly in anime illustration drawing style.",
        f"Scene: {composition_prompt}",
        f"Brand accent color: {accent} touches (modern corporate blue).",
        f"Prominent stylish magazine masthead in crisp Cyrillic letters at top: «{masthead}».",
        f"Elegant issue date badge: «{date_badge}».",
        f"Large bold readable Cyrillic headline on the cover, exactly: «{headline}».",
    ]
    if dek:
        prompt_parts.append(f"Clear secondary Cyrillic sub-headline (dek) under the main headline: «{dek}».")
    prompt_parts.extend([
        "No period at end of headline, no emoji, no URLs, no phone number, no extra marketing slogans.",
        "Setting is Ufa, Russia.",
        "NEGATIVE: photorealistic, photo, real photography, 3D CGI render, realistic skin pore textures, metro / subway station in Ufa, Moscow, Red Square, English poster text, "
        "watermark, bad anatomy, deformed hands, extra fingers, nudity, NSFW, neon cyberpunk, beard, different face.",
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
    masthead: str = "УФА",
    date_badge: str = "ОКТЯБРЬ 2026",
    dek: str = "",
    cover_style: str = "anime",
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

    direct_urls = [
        "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
        "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
    ]
    if os.environ.get("VK_DAILY_DIRECT_INPUT_URLS", "yes").strip().lower() in {"yes", "true", "1"}:
        input_urls = direct_urls
    else:
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
        masthead=masthead,
        date_badge=date_badge,
        dek=dek,
        style=cover_style,
    )
    try:
        print(f"Creating KIE i2i task with prompt: {prompt}")
        print(f"Input URLs: {input_urls}")
        task_id = create_i2i_task(
            api_key,
            prompt=prompt,
            input_urls=input_urls,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        print(f"KIE task created: taskId={task_id}, waiting for completion...")
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
