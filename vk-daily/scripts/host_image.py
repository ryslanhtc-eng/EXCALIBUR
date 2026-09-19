"""Host a local image to a public HTTPS URL for KIE input_urls.

Mirrors catbox / 0x0 flow from scripts/excalibur_blog_hero_reference_url.py
without changing that blog helper (JPEG MIME is required for VK face refs).
"""
from __future__ import annotations

import urllib.request
from pathlib import Path


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _multipart(path: Path, *, field: str, extra: list[tuple[str, str]], boundary: str) -> bytes:
    chunks: list[bytes] = []
    for name, value in extra:
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    mime = _mime(path)
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    chunks.append(header + path.read_bytes() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def upload_catbox(image_path: Path) -> str:
    boundary = "----VkDailyHeroBoundary"
    body = _multipart(
        image_path,
        field="fileToUpload",
        extra=[("reqtype", "fileupload")],
        boundary=boundary,
    )
    request = urllib.request.Request(
        "https://catbox.moe/user/api.php",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ExcaliburVkDaily/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        url = response.read().decode("utf-8", errors="replace").strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"catbox upload failed: {url[:200]}")
    return url


def upload_0x0(image_path: Path) -> str:
    boundary = "----VkDailyHero0x0"
    body = _multipart(image_path, field="file", extra=[], boundary=boundary)
    request = urllib.request.Request(
        "https://0x0.st",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ExcaliburVkDaily/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        url = response.read().decode("utf-8", errors="replace").strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"0x0 upload failed: {url[:200]}")
    return url


def upload_uguu(image_path: Path) -> str:
    boundary = "----VkDailyHeroUguu"
    chunks: list[bytes] = []
    mime = _mime(image_path)
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[]"; filename="{image_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    chunks.append(header + image_path.read_bytes() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)

    request = urllib.request.Request(
        "https://uguu.se/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ExcaliburVkDaily/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8", errors="replace").strip()
    import json
    data = json.loads(raw)
    if not data.get("success"):
        raise RuntimeError(f"uguu upload failed: {raw[:200]}")
    files = data.get("files") or []
    if not files or not files[0].get("url"):
        raise RuntimeError(f"uguu upload missing url: {raw[:200]}")
    return files[0]["url"]


def host_image(image_path: Path, providers: tuple[str, ...] = ("uguu", "catbox")) -> str:
    last: Exception | None = None
    for provider in providers:
        try:
            if provider == "uguu":
                return upload_uguu(image_path)
            elif provider == "catbox":
                return upload_catbox(image_path)
            else:
                return upload_0x0(image_path)
        except Exception as exc:  # noqa: BLE001 - try next host
            last = exc
    raise RuntimeError(f"could not host {image_path.name}: {last}")
