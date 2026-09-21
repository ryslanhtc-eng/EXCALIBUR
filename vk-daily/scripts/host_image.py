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
    body = _multipart(image_path, field="files[]", extra=[], boundary=boundary)
    request = urllib.request.Request(
        "https://uguu.se/upload.php",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    import json
    data = json.loads(raw)
    if data.get("success") and data.get("files"):
        url = data["files"][0].get("url")
        if url and url.startswith("https://"):
            return url
    raise RuntimeError(f"uguu upload failed: {raw[:200]}")


def host_image(image_path: Path, providers: tuple[str, ...] = ("uguu", "catbox", "0x0")) -> str:
    last: Exception | None = None
    for provider in providers:
        try:
            if provider == "uguu":
                return upload_uguu(image_path)
            return upload_catbox(image_path) if provider == "catbox" else upload_0x0(image_path)
        except Exception as exc:  # noqa: BLE001 - try next host
            last = exc
    raise RuntimeError(f"could not host {image_path.name}: {last}")
