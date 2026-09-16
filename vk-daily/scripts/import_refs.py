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


POSE_FILENAMES = (
    "01-studio-navy-suit-grid.jpg",
    "02-office-navy-suit-lifestyle-grid.jpg",
    "03-black-suit-tie-formal-grid.jpg",
    "04-mono-shirt-editorial-poses-grid.jpg",
    "05-smart-casual-armchair-pose.jpg",
    "06-work-lifestyle-desk-poses-grid.jpg",
)


def import_pose_refs(root: Path) -> int:
    pose_dest = vk_daily_root(root) / "refs" / "poses-wardrobe"
    pose_dest.mkdir(parents=True, exist_ok=True)
    handoff_dir = root / "vk-handoff" / "poses-wardrobe"
    copied = 0
    for name in POSE_FILENAMES:
        src = handoff_dir / name
        dst = pose_dest / name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
            copied += 1
            print(f"OK pose_ref={name}")
    return copied


def import_refs(root: Path | None = None, *, blue: str = "", black: str = "") -> int:
    root = root or repo_root()
    dest_dir = vk_daily_root(root) / "refs"
    dest_dir.mkdir(parents=True, exist_ok=True)

    blue_path = _first_existing(root, CANDIDATES_BLUE, blue)
    black_path = _first_existing(root, CANDIDATES_BLACK, black)
    copied = 0
    if blue_path:
        shutil.copy2(blue_path, dest_dir / "ruslan_selfie_blue.jpg")
        copied += 1
        print(f"OK blue={blue_path}")
    else:
        print("WARN missing blue selfie", file=sys.stderr)
    if black_path:
        shutil.copy2(black_path, dest_dir / "ruslan_selfie_black.jpg")
        copied += 1
        print(f"OK black={black_path}")
    else:
        print("WARN missing black selfie", file=sys.stderr)

    import_pose_refs(root)
    return 0 if copied else 1



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blue", default="")
    ap.add_argument("--black", default="")
    args = ap.parse_args()
    return import_refs(blue=args.blue, black=args.black)


if __name__ == "__main__":
    raise SystemExit(main())
