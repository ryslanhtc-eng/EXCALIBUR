"""Copy Ruslan face refs into vk-daily/refs/."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from paths import repo_root, vk_daily_root

CANDIDATES_BLUE = (
    "vk-handoff/ruslan_selfie_blue.jpg",
    "ruslan_selfie_blue.jpg",
)
CANDIDATES_BLACK = (
    "vk-handoff/ruslan_selfie_black.jpg",
    "ruslan_selfie_black.jpg",
)


def _first_existing(root: Path, rels: tuple[str, ...], explicit: str) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        return path if path.is_file() else None
    for rel in rels:
        path = root / rel
        if path.is_file():
            return path
    return None


def import_refs(root: Path | None = None, *, blue: str = "", black: str = "") -> int:
    root = root or repo_root()
    dest_dir = vk_daily_root(root) / "refs"
    dest_dir.mkdir(parents=True, exist_ok=True)

    blue_path = _first_existing(root, CANDIDATES_BLUE, blue)
    black_path = _first_existing(root, CANDIDATES_BLACK, black)
    copied = 0
    dest_blue = dest_dir / "ruslan_selfie_blue.jpg"
    dest_black = dest_dir / "ruslan_selfie_black.jpg"
    if blue_path:
        shutil.copy2(blue_path, dest_blue)
        copied += 1
        print(f"OK blue={blue_path}")
    elif dest_blue.is_file() and dest_blue.stat().st_size > 1000:
        copied += 1
        print(f"OK blue already at {dest_blue}")
    else:
        print("WARN missing blue selfie", file=sys.stderr)
    if black_path:
        shutil.copy2(black_path, dest_black)
        copied += 1
        print(f"OK black={black_path}")
    elif dest_black.is_file() and dest_black.stat().st_size > 1000:
        copied += 1
        print(f"OK black already at {dest_black}")
    else:
        print("WARN missing black selfie", file=sys.stderr)
    return 0 if copied else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blue", default="")
    ap.add_argument("--black", default="")
    args = ap.parse_args()
    return import_refs(blue=args.blue, black=args.black)


if __name__ == "__main__":
    raise SystemExit(main())
