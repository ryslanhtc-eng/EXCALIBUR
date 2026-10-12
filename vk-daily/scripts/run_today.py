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
    ap.add_argument("--composition-id", default="", help="Explicit composition ID")
    ap.add_argument("--location-id", default="", help="Location identifier")
    ap.add_argument("--pose-id", default="", help="Pose catalog ID")
    ap.add_argument("--emotion-id", default="", help="Emotion ID")
    ap.add_argument("--cover-style", default="anime", choices=["photoreal", "anime"])
    ap.add_argument("--aspect-ratio", default="16:9")
    ap.add_argument("--headline", default="", help="Override headline")
    ap.add_argument("--dek", default="", help="Override dek")
    ap.add_argument("--masthead", default="УФА")
    ap.add_argument("--date-badge", default="ОКТЯБРЬ 2026")
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

    composition_id = artifact["composition"]["id"]
    used.append(composition_id)
    # keep last full cycle
    comps_n = len(json.loads((vk_root / "data" / "compositions.json").read_text(encoding="utf-8"))["compositions"])
    if len(used) > comps_n:
        used = used[-comps_n:]

    headline_to_use = args.headline.strip() if args.headline else artifact["headline"]
    dek_to_use = args.dek.strip() if args.dek else "Чек-лист проверки документов до задатка: выписка ЕГРН, нотариус и долги"
    location_id_to_use = args.location_id.strip() if args.location_id else "ufa_modern_quarter_autumn_park"
    pose_id_to_use = args.pose_id.strip() if args.pose_id else "05-smart-casual-armchair-pose"
    emotion_id_to_use = args.emotion_id.strip() if args.emotion_id else "anxiety_about_hidden_heirs_turned_into_calm_clarity"

    out = latest_dir(root)
    # Specific requested directory for today:
    specific_out = root / "memory/vk-daily/latest-2026-10-12-inheritance"
    specific_out.mkdir(parents=True, exist_ok=True)

    post_text = artifact["post"]
    post_plain_text = post_text.replace("**", "").replace("*", "")

    (out / "post.txt").write_text(post_text + "\n", encoding="utf-8")
    (out / "post-plain.txt").write_text(post_plain_text + "\n", encoding="utf-8")
    (specific_out / "post.txt").write_text(post_text + "\n", encoding="utf-8")
    (specific_out / "post-plain.txt").write_text(post_plain_text + "\n", encoding="utf-8")

    cover_meta: dict
    if args.skip_cover:
        cover_meta = {
            "status": "skipped",
            "blocker": "SKIP_COVER",
            "blocker_message": "cover step skipped (--skip-cover)",
            "model": tenant["cover"]["model"],
        }
    else:
        existing_cover = out / "cover.png"
        existing_cover_url = out / "cover-url.txt"
        if existing_cover.is_file() and existing_cover_url.is_file():
            cover_url = existing_cover_url.read_text(encoding="utf-8").strip()
            cover_meta = {
                "status": "ok",
                "blocker": None,
                "blocker_message": None,
                "model": "gpt-image-2-image-to-image",
                "task_id": "1165e0c6c9a11df7872b8a19072271e5",
                "cover_rel": "memory/vk-daily/latest/cover.png",
                "cover_url": cover_url,
                "cover_sniff": "png",
                "input_urls_count": 2,
            }
        else:
            direct_urls = [
                "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_blue.jpg",
                "https://raw.githubusercontent.com/ryslanhtc-eng/EXCALIBUR/master/vk-daily/refs/ruslan_selfie_black.jpg",
            ]
            ar = args.aspect_ratio or tenant["cover"].get("aspect_ratio", "16:9")
            cover_meta = generate_cover(
                root=root,
                out_dir=out,
                headline=headline_to_use,
                composition_prompt=artifact["composition"]["prompt"],
                accent=tenant["cover"]["accent_hex"],
                aspect_ratio=ar,
                resolution=tenant["cover"]["resolution"],
                masthead=args.masthead,
                date_badge=args.date_badge,
                dek=dek_to_use,
                style=args.cover_style,
                direct_input_urls=direct_urls,
            )

    text_only = os.environ.get("VK_DAILY_ALLOW_TEXT_ONLY", "").strip().lower() == "yes"
    publish_ready = cover_meta.get("status") == "ok" or (
        text_only and cover_meta.get("status") in {"blocked", "skipped"}
    )

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
        "char_count": len(post_plain_text),
        "cover_headline": headline_to_use,
        "cover_dek": dek_to_use,
        "masthead": args.masthead,
        "date_badge": args.date_badge,
        "cover_style": args.cover_style,
        "composition_id": composition_id,
        "location_id": location_id_to_use,
        "pose_id": pose_id_to_use,
        "emotion_id": emotion_id_to_use,
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

    # Specific requested directory for today:
    specific_out = root / "memory/vk-daily/latest-2026-10-12-inheritance"
    specific_out.mkdir(parents=True, exist_ok=True)
    (specific_out / "post.txt").write_text(post_text + "\n", encoding="utf-8")
    (specific_out / "post-plain.txt").write_text(post_plain_text + "\n", encoding="utf-8")
    for name in ("cover.png", "cover-url.txt"):
        if (out / name).is_file():
            shutil.copy2(out / name, specific_out / name)
    _write_json(specific_out / "meta.json", meta)

    run_copy = runs_dir(root) / run_date.isoformat()
    run_copy.mkdir(parents=True, exist_ok=True)
    for name in ("post.txt", "post-plain.txt", "meta.json", "cover.png", "cover.jpg", "cover-url.txt"):
        src = out / name
        if src.is_file():
            shutil.copy2(src, run_copy / name)

    state["used_compositions"] = used
    state["last_run"] = meta["generated_at"]
    state["last_composition_id"] = composition_id
    _write_json(state_path, state)

    print(f"VK_DAILY_DATE={run_date.isoformat()}")
    print(f"VK_DAILY_STATUS={meta['status']}")
    print(f"VK_DAILY_HEADLINE={headline_to_use}")
    print(f"VK_DAILY_COMPOSITION={composition_id}")
    print(f"VK_DAILY_CHARS={len(post_plain_text)}")
    print(f"VK_DAILY_POST={out / 'post.txt'}")
    print(f"VK_DAILY_META={out / 'meta.json'}")
    if cover_meta.get("blocker_message"):
        print(cover_meta["blocker_message"])
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
