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


def host_image(image_path: Path, providers: tuple[str, ...] = ("github", "catbox", "0x0")) -> str:
    github_urls = {
        "ruslan_selfie_blue.jpg": "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
        "ruslan_selfie_black.jpg": "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
    }
    last: Exception | None = None
    for provider in providers:
        if provider == "github" and image_path.name in github_urls:
            return github_urls[image_path.name]
        try:
            return upload_catbox(image_path) if provider == "catbox" else upload_0x0(image_path)
        except Exception as exc:  # noqa: BLE001 - try next host
            last = exc
    raise RuntimeError(f"could not host {image_path.name}: {last}")
