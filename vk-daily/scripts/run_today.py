"""Produce memory/vk-daily/latest/{post.txt, cover.png|cover-url.txt, meta.json}."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_cover import generate_cover  # noqa: E402
from generate_post import generate  # noqa: E402
from import_refs import import_refs  # noqa: E402
from paths import latest_dir, repo_root, runs_dir, vk_daily_root  # noqa: E402

UFA_TZ = ZoneInfo("Asia/Yekaterinburg")
STATE_REL = Path("memory/vk-daily/state.json")


def _load_state(path: Path) -> dict:
    if not path.is_file():
        return {"used_compositions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"used_compositions": []}
    if not isinstance(data, dict):
        return {"used_compositions": []}
    data.setdefault("used_compositions", [])
    return data


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="VK daily: one ready-to-publish post for Grok Bot")
    ap.add_argument("--date", default="", help="YYYY-MM-DD (default: today in Ufa)")
    ap.add_argument("--skip-cover", action="store_true")
    ap.add_argument("--force-new-composition", action="store_true")
    ap.add_argument("--composition-id", default="", help="Specific composition_id from compositions.json")
    ap.add_argument("--location-id", default="", help="Specific location_id")
    ap.add_argument("--pose-id", default="", help="Specific pose_id")
    ap.add_argument("--emotion-id", default="", help="Specific emotion_id")
    ap.add_argument("--headline", default="", help="Custom headline for cover (4-8 words)")
    ap.add_argument("--dek", default="", help="Sub-headline / description under headline")
    ap.add_argument("--aspect-ratio", default="", help="Override aspect ratio (e.g. 16:9 or 3:4)")
    ap.add_argument("--named-slug", default="", help="Suffix for latest-<date>-<slug> folder")
    ap.add_argument("--cover-style", default="anime", help="Cover style (anime or photoreal)")
    args = ap.parse_args()

    root = repo_root()
    vk_root = vk_daily_root(root)
    tenant = json.loads((vk_root / "tenant" / "tenant.json").read_text(encoding="utf-8"))

    now = datetime.now(UFA_TZ)
    if args.date:
        run_date = datetime.fromisoformat(args.date).date()
    else:
        run_date = now.date()

    import_refs(root)

    state_path = root / STATE_REL
    state = _load_state(state_path)
    used = list(state.get("used_compositions") or [])
    if args.force_new_composition:
        seed = f"{run_date.isoformat()}|{now.isoformat()}|{uuid.uuid4()}"
    else:
        seed = f"{run_date.isoformat()}|{now.strftime('%Y-%m-%dT%H:%M')}|{uuid.uuid4()}"

    artifact = generate(vk_root, run_date, seed, used)
    if args.composition_id:
        comps = json.loads((vk_root / "data" / "compositions.json").read_text(encoding="utf-8"))["compositions"]
        matching = [c for c in comps if c.get("id") == args.composition_id]
        if matching:
            artifact["composition"] = matching[0]
    if args.headline:
        artifact["headline"] = args.headline
        from validate_post import validate_headline
        head_errs = validate_headline(args.headline, tenant)
        if head_errs:
            print(f"WARN headline validation: {head_errs}", file=sys.stderr)

    composition_id = artifact["composition"]["id"]
    used.append(composition_id)
    # keep last full cycle
    comps_n = len(json.loads((vk_root / "data" / "compositions.json").read_text(encoding="utf-8"))["compositions"])
    if len(used) > comps_n:
        used = used[-comps_n:]

    out = latest_dir(root)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    post_content = artifact["post"]
    (out / "post.txt").write_text(post_content + "\n", encoding="utf-8")

    # Plain text without markdown * or ** and without long em-dash
    plain_content = post_content.replace("**", "").replace("*", "").replace("—", "-")
    (out / "post-plain.txt").write_text(plain_content + "\n", encoding="utf-8")

    masthead = "УФА"
    date_badge = "ОКТЯБРЬ 2026"
    dek = args.dek or "Альтернативная сделка в Уфе: как продать и купить квартиру в один день и не потерять жилье"
    aspect_ratio = args.aspect_ratio or "16:9"

    cover_meta: dict
    if args.skip_cover:
        cover_meta = {
            "status": "skipped",
            "blocker": "SKIP_COVER",
            "blocker_message": "cover step skipped (--skip-cover)",
            "model": tenant["cover"]["model"],
        }
    else:
        cover_meta = generate_cover(
            root=root,
            out_dir=out,
            headline=artifact["headline"],
            composition_prompt=artifact["composition"]["prompt"],
            accent=tenant["cover"]["accent_hex"],
            aspect_ratio=aspect_ratio,
            resolution=tenant["cover"]["resolution"],
            masthead=masthead,
            date_badge=date_badge,
            dek=dek,
            cover_style=args.cover_style,
        )

    text_only = os.environ.get("VK_DAILY_ALLOW_TEXT_ONLY", "").strip().lower() == "yes"
    publish_ready = cover_meta.get("status") == "ok" or (
        text_only and cover_meta.get("status") in {"blocked", "skipped"}
    )

    location_id = args.location_id or "belaya_riverside_autumn_embankment"
    pose_id = args.pose_id or "01-studio-navy-suit-grid"
    emotion_id = args.emotion_id or "anxiety_turned_into_calm_and_clarity"

    meta = {
        "pipeline": "vk-daily",
        "status": "ready" if cover_meta.get("status") == "ok" else cover_meta.get("status"),
        "publish_ready": bool(publish_ready),
        "date": run_date.isoformat(),
        "generated_at": now.isoformat(timespec="seconds"),
        "timezone": "Asia/Yekaterinburg",
        "tenant_id": tenant["tenant_id"],
        "person_name_ru": tenant["person_name_ru"],
        "brand_ru": tenant["brand_ru"],
        "vk_group_url": tenant["vk_group_url"],
        "vk_group_screen_name": tenant["vk_group_screen_name"],
        "city": tenant["city"],
        "char_count": artifact["char_count"],
        "cover_headline": artifact["headline"],
        "cover_dek": dek,
        "masthead": masthead,
        "date_badge": date_badge,
        "cover_style": args.cover_style,
        "composition_id": composition_id,
        "location_id": location_id,
        "pose_id": pose_id,
        "emotion_id": emotion_id,
        "accent_hex": tenant["cover"]["accent_hex"],
        "news_id": artifact["news"].get("id"),
        "news_source_name": artifact["news"].get("source_name"),
        "artifacts": {
            "post": "memory/vk-daily/latest/post.txt",
            "post_plain": "memory/vk-daily/latest/post-plain.txt",
            "meta": "memory/vk-daily/latest/meta.json",
            "cover": "memory/vk-daily/latest/cover.png",
            "cover_url": "memory/vk-daily/latest/cover-url.txt",
        },
        "cover": cover_meta,
        "orchestrator": {
            "publisher": "Grok Bot",
            "must_not_rewrite": True,
            "must_not_invent_cover": True,
            "publish_if": "cover.status == ok and files exist",
            "skip_if_blocker": True,
        },
        "links_in_post": False,
    }
    if cover_meta.get("blocker"):
        meta["blocker"] = cover_meta["blocker"]
        meta["blocker_message"] = cover_meta["blocker_message"]

    _write_json(out / "meta.json", meta)

    run_copy = runs_dir(root) / run_date.isoformat()
    run_copy.mkdir(parents=True, exist_ok=True)
    slug = args.named_slug or "alt-deal"
    named_run_copy = runs_dir(root) / f"latest-{run_date.isoformat()}-{slug}"
    named_run_copy.mkdir(parents=True, exist_ok=True)
    latest_named_copy = root / "memory" / "vk-daily" / f"latest-{run_date.isoformat()}-{slug}"
    latest_named_copy.mkdir(parents=True, exist_ok=True)
    for name in ("post.txt", "post-plain.txt", "meta.json", "cover.png", "cover.jpg", "cover-url.txt"):
        src = out / name
        if src.is_file():
            shutil.copy2(src, run_copy / name)
            shutil.copy2(src, named_run_copy / name)
            shutil.copy2(src, latest_named_copy / name)

    state["used_compositions"] = used
    state["last_run"] = meta["generated_at"]
    state["last_composition_id"] = composition_id
    _write_json(state_path, state)

    print(f"VK_DAILY_DATE={run_date.isoformat()}")
    print(f"VK_DAILY_STATUS={meta['status']}")
    print(f"VK_DAILY_HEADLINE={artifact['headline']}")
    print(f"VK_DAILY_COMPOSITION={composition_id}")
    print(f"VK_DAILY_CHARS={artifact['char_count']}")
    print(f"VK_DAILY_POST={out / 'post.txt'}")
    print(f"VK_DAILY_META={out / 'meta.json'}")
    if cover_meta.get("blocker_message"):
        print(cover_meta["blocker_message"])
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
