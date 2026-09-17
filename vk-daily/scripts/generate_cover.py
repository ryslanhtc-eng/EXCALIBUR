"""KIE gpt-image-2-image-to-image cover, or a hard blocker (no fake image)."""
from __future__ import annotations

import os
import sys
import urllib.request
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

# Stable public GitHub raw URLs for reference selfies
RAW_GITHUB_FACE_REFS = [
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
    "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
]


def face_ref_paths(root: Path) -> list[Path]:
    names = ("ruslan_selfie_blue.jpg", "ruslan_selfie_black.jpg")
    found: list[Path] = []
    for name in names:
        path = root / "vk-daily" / "refs" / name
        if path.is_file() and path.stat().st_size > 1000:
            found.append(path)
    return found


def pose_ref_path(root: Path, filename: str) -> Path | None:
    if not filename:
        return None
    path = root / "vk-daily" / "refs" / "poses-wardrobe" / filename
    if path.is_file() and path.stat().st_size > 1000:
        return path
    return None


def resolve_face_ref_urls(root: Path, refs: list[Path]) -> list[str]:
    """Obtain public HTTPS URLs for face refs, prioritizing raw GitHub refs."""
    try:
        req = urllib.request.Request(RAW_GITHUB_FACE_REFS[0], headers={"User-Agent": "ExcaliburVkDaily/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return list(RAW_GITHUB_FACE_REFS)
    except Exception:
        pass

    return [host_image(path) for path in refs]


def build_prompt(
    *,
    headline: str,
    composition_prompt: str,
    accent: str = "#2F7BFF",
    dek: str = "",
    month_date: str = "СЕНТЯБРЬ 2026",
    pose_wardrobe: dict | None = None,
) -> str:
    pose_desc = ""
    if pose_wardrobe:
        wardrobe = pose_wardrobe.get("wardrobe", "")
        pose = pose_wardrobe.get("pose", "")
        vibe = pose_wardrobe.get("vibe", "")
        pose_desc = (
            f"Outfit and styling reference: {wardrobe}. "
            f"Posture and gesture reference: {pose}. "
            f"Vibe reference: {vibe}. "
        )

    parts = [
        "High-end editorial magazine cover portrait (16:9 aspect ratio) of the SAME man as in the reference selfies.",
        "Preserve exact facial identity: oval face shape, short dark hair neatly cut and faded on sides, light grey-blue eyes, natural warm confident smile showing upper teeth, cheek dimples, light neat stubble, no glasses, no beautifying into a different person.",
        "CRITICAL: preserve facial identity from selfies only, NEVER copy faces from pose reference models.",
        "Wardrobe & styling: styled as a top-tier premium real-estate agent in a sharp tailored dark wool coat, structured blazer or suit jacket, crisp dress shirt or dark fine-knit turtleneck. Clean, wealthy, polished editorial aesthetic with a calm expensive vibe.",
        f"{pose_desc}",
        "Strictly NO hoodie, NO everyday casual sweatshirt, NO sportswear, NO cheap jacket, NO home clothes.",
        f"Location & background: beautiful, recognizable Ufa location ({composition_prompt}). Elegant architectural depth, authentic city atmosphere. Strictly NO generic gray stairwell with no place identity, NO placeless interiors, NO landmarks or skyline of Moscow or other cities.",
        f"Typography & layout: authentic magazine cover design with large prominent bold Cyrillic masthead 'УФА' at the top left in brand blue ({accent}), and date plate '{month_date}' at top right.",
        f"Large crisp bold Cyrillic headline on the left side: «{headline}».",
    ]
    if dek:
        parts.append(f"Clear elegant Cyrillic subheadline (dek) below headline: «{dek}».")
    parts.extend([
        f"Brand pure blue color accent ({accent}) on graphical elements, badges, or accessories. Strictly NO hex codes (such as '#2F7BFF'), NO RGB/RAL numbers or color labels printed or written on props, folders, or clothing.",
        "No period at end of headline, no emoji, no website URLs, no phone numbers, no subway/metro mentions.",
        "NEGATIVE: hoodie, sweatshirt, casual windbreaker, cheap clothes, sportswear, home clothes, "
        "gray featureless dingy stairwell, subway station, metro in Ufa, Moscow landmarks, Red Square, "
        "printed hex code text, #2F7BFF text, RAL code text, English poster text, "
        "watermark, distorted hands, extra fingers, cartoon, 3d render, plastic skin, neon cyberpunk, different face, foreign model face.",
    ])
    return " ".join(parts)


def generate_cover(
    *,
    root: Path,
    out_dir: Path,
    headline: str,
    composition_prompt: str,
    accent: str = "#2F7BFF",
    dek: str = "",
    month_date: str = "СЕНТЯБРЬ 2026",
    aspect_ratio: str = "16:9",
    resolution: str = "2K",
    pose_wardrobe: dict | None = None,
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

    pose_filename = (pose_wardrobe or {}).get("filename", "")
    pose_img = pose_ref_path(root, pose_filename) if pose_filename else None

    try:
        input_urls = resolve_face_ref_urls(root, refs)
        if pose_img:
            try:
                input_urls.append(host_image(pose_img))
            except Exception:
                pass
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_HOST,
            "blocker_message": f"❌ VK COVER BLOCKER: could not host refs: {exc}",
            "model": MODEL,
        }

    prompt = build_prompt(
        headline=headline,
        composition_prompt=composition_prompt,
        accent=accent,
        dek=dek,
        month_date=month_date,
        pose_wardrobe=pose_wardrobe,
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
            "urls": [cover_url],
            "cover_sniff": kind,
            "input_urls_count": len(input_urls),
            "pose_ref_id": (pose_wardrobe or {}).get("id"),
            "aspect_ratio": aspect_ratio,
            "headline": headline,
            "dek": dek,
            "masthead": "УФА",
            "date_badge": month_date,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "blocker": BLOCKER_KIE,
            "blocker_message": f"❌ VK COVER BLOCKER: KIE i2i failed: {exc}",
            "model": MODEL,
        }
