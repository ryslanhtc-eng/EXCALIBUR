"""Host a local image to a public HTTPS URL for KIE input_urls.

Mirrors catbox / 0x0 flow from scripts/excalibur_blog_hero_reference_url.py
without changing that blog helper (JPEG MIME is required for VK face refs).

Anonymous hosts (catbox / 0x0) often 412/timeout from Cloud. Face refs already
on GitHub master are reused as raw / jsDelivr URLs — no extra copy of the face.
"""
from __future__ import annotations

import os
import re
import subprocess
import urllib.request
from pathlib import Path

from paths import repo_root

GITHUB_REMOTE_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


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


def parse_github_owner_repo(remote: str) -> str | None:
    """Return 'owner/repo' from a git remote URL. Credentials are discarded."""
    text = (remote or "").strip()
    if not text:
        return None
    match = GITHUB_REMOTE_RE.search(text.replace("\\", "/"))
    if not match:
        return None
    owner = match.group("owner")
    repo = match.group("repo")
    if not owner or not repo or "@" in owner or ":" in owner:
        return None
    return f"{owner}/{repo}"


def origin_owner_repo(root: Path | None = None) -> str | None:
    env = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if env.count("/") == 1 and "@" not in env:
        return env
    cwd = str(root or repo_root())
    try:
        raw = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=cwd,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_github_owner_repo(raw)


def repo_relative_posix(image_path: Path, root: Path) -> str | None:
    try:
        return image_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def github_raw_url(image_path: Path, root: Path, *, ref: str = "master") -> str | None:
    rel = repo_relative_posix(image_path, root)
    owner_repo = origin_owner_repo(root)
    if not rel or not owner_repo:
        return None
    return f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{rel}"


def jsdelivr_url(image_path: Path, root: Path, *, ref: str = "master") -> str | None:
    rel = repo_relative_posix(image_path, root)
    owner_repo = origin_owner_repo(root)
    if not rel or not owner_repo:
        return None
    return f"https://cdn.jsdelivr.net/gh/{owner_repo}@{ref}/{rel}"


def assert_public_image(url: str, *, timeout: int = 20) -> str:
    if not url.startswith("https://"):
        raise RuntimeError(f"host URL is not https: {url[:80]}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ExcaliburVkDaily/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        chunk = response.read(24)
        ctype = (response.headers.get("Content-Type") or "").lower()
    jpeg = chunk.startswith(b"\xff\xd8\xff")
    png = chunk.startswith(b"\x89PNG")
    webp = chunk.startswith(b"RIFF") and b"WEBP" in chunk
    if jpeg or png or webp or ctype.startswith("image/"):
        return url
    raise RuntimeError(f"public URL is not an image ({ctype or 'unknown'})")


def upload_catbox(image_path: Path, *, timeout: int = 25) -> str:
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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        url = response.read().decode("utf-8", errors="replace").strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"catbox upload failed: {url[:200]}")
    return url


def upload_0x0(image_path: Path, *, timeout: int = 15) -> str:
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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        url = response.read().decode("utf-8", errors="replace").strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"0x0 upload failed: {url[:200]}")
    return url


def _ref_host_ref() -> str:
    return (os.environ.get("VK_DAILY_REF_HOST_REF") or "master").strip() or "master"


def host_github_raw(image_path: Path, root: Path) -> str:
    url = github_raw_url(image_path, root, ref=_ref_host_ref())
    if not url:
        raise RuntimeError("github-raw URL could not be built")
    return assert_public_image(url)


def host_jsdelivr(image_path: Path, root: Path) -> str:
    url = jsdelivr_url(image_path, root, ref=_ref_host_ref())
    if not url:
        raise RuntimeError("jsdelivr URL could not be built")
    return assert_public_image(url)


DEFAULT_PROVIDERS = ("catbox", "github-raw", "jsdelivr", "0x0")


def host_image(
    image_path: Path,
    providers: tuple[str, ...] | None = None,
    *,
    root: Path | None = None,
) -> str:
    root = root or repo_root()
    last: Exception | None = None
    for provider in providers or DEFAULT_PROVIDERS:
        try:
            if provider == "catbox":
                return upload_catbox(image_path)
            if provider == "0x0":
                return upload_0x0(image_path)
            if provider == "github-raw":
                return host_github_raw(image_path, root)
            if provider == "jsdelivr":
                return host_jsdelivr(image_path, root)
            raise RuntimeError(f"unknown host provider {provider}")
        except Exception as exc:  # noqa: BLE001 - try next host
            last = exc
    raise RuntimeError(f"could not host {image_path.name}: {last}")
