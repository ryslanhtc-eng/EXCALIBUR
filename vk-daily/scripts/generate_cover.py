"""KIE gpt-image-2-image-to-image cover, or a hard blocker (no fake image)."""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

from host_image import host_image
from kie_client import KieError, MODEL, create_i2i_task, result_urls, wait_for_success

RAW_GITHUB_FACE_REFS = [
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
]

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


def resolve_face_ref_urls(root: Path, refs: list[Path]) -> list[str]:
    """Prefer stable GitHub raw selfies; fall back to catbox/0x0 hosting."""
    try:
        req = urllib.request.Request(
            RAW_GITHUB_FACE_REFS[0],
            headers={"User-Agent": "ExcaliburVkDaily/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return list(RAW_GITHUB_FACE_REFS)
    except Exception:
        pass
    return [host_image(path) for path in refs]


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
    realtor_expression: str = "calm, serious, focused expert demeanor explaining real risks, no goofy grin, confident reassuring professional",
) -> str:
    parts = [
        "High quality editorial animation and graphic novel art style cover in 16:9 widescreen format.",
        "The scene features the SAME man as in the reference selfies.",
        "Face identity and lock details: Russian man, 45-50 years old, short buzz cut hair with subtle grey touches, very clean-shaven face (no beard, no mustache, no messy stubble),",
        f"light grey-blue eyes, {realtor_expression}, small distinct mole near bridge of nose,",
        "golden wedding band on his finger. Do not make him look too young. If any name is written, only РУСЛАН МУХТАРОВ or without name.",
        f"Scene and interaction: {composition_prompt}",
        f"Top-left magazine/editorial masthead text clearly readable, exactly: «{masthead}».",
        f"Top-right date badge clearly readable, exactly: «{date_badge}».",
        f"Main bold Cyrillic headline on the layout, exactly: «{headline}».",
    ]
    if dek:
        parts.append(f"Short sub-headline dek under the main headline, exactly: «{dek}».")
    parts.extend([
        f"Brand accent color {accent} on typography, badge or interior accents (no pink highlighter, no cheap red banners).",
        "No period at end of headline, no emojis, no URLs, no phone numbers, no extra promotional text.",
        "Setting is Ufa, Russia. Polished modern graphic novel aesthetic.",
        "NEGATIVE: photo of another man, happy smiling laughing client, metro / subway / underground station in Ufa, Moscow, Red Square, English poster text,",
        "watermark, bank logos, nudity, NSFW, extra limbs, deformed fingers, low resolution, dirty sketch, ugly face.",
    ])
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
    date_badge: str = "ОКТЯБРЬ 2026",
    dek: str = "",
    realtor_expression: str = "calm, serious, focused expert demeanor explaining real risks, no goofy grin, confident reassuring professional",
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
        input_urls = resolve_face_ref_urls(root, refs)
        print(f"Face ref URLs ({len(input_urls)}): using {input_urls}", flush=True)
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
        realtor_expression=realtor_expression,
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
            "aspect_ratio": aspect_ratio,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_KIE,
            "blocker_message": f"❌ VK COVER BLOCKER: KIE i2i failed: {exc}",
            "model": MODEL,
        }
