"""Repo and vk-daily paths. Isolated from blog pipeline."""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = (os.environ.get("EXCALIBUR_PROJECT_ROOT") or os.environ.get("VK_DAILY_ROOT") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def vk_daily_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "vk-daily"


def latest_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "memory" / "vk-daily" / "latest"


def runs_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "memory" / "vk-daily" / "runs"
