"""VK daily unit tests (no KIE network)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "vk-daily" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from generate_cover import (  # noqa: E402
    PUBLIC_FACE_REF_URLS,
    build_prompt,
    generate_cover,
    resolve_face_ref_urls,
)
from generate_post import generate, pick_composition  # noqa: E402
from paths import vk_daily_root  # noqa: E402
from validate_post import load_banned, load_tenant, validate_headline, validate_post  # noqa: E402


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vk = vk_daily_root(ROOT)
        self.tenant = load_tenant(self.vk)
        self.banned = load_banned(self.vk)

    def test_headline_ok(self) -> None:
        self.assertEqual([], validate_headline("Уфа снова в тройке", self.tenant))

    def test_headline_rejects_period_and_emoji(self) -> None:
        self.assertTrue(validate_headline("Уфа снова в тройке.", self.tenant))
        self.assertTrue(validate_headline("Уфа снова в тройке 😅", self.tenant))

    def test_links_banned(self) -> None:
        text = ("а" * 1800) + " https://vk.ru/samolet_plus_sipa"
        errs = validate_post(text, self.tenant, self.banned)
        self.assertTrue(any("links" in e for e in errs))

    def test_metro_copy_banned_but_denial_ok(self) -> None:
        bad = ("а" * 1700) + " квартира у метро в Сипайлово, отличный район"
        good = ("а" * 1700) + " В Уфе нет метро. Копипаст про станцию закрывайте."
        self.assertTrue(validate_post(bad, self.tenant, self.banned))
        self.assertEqual([], validate_post(good, self.tenant, self.banned))

    def test_object_emoji_banned(self) -> None:
        text = ("а" * 1800) + " 🏠"
        self.assertTrue(any("emoji" in e for e in validate_post(text, self.tenant, self.banned)))


class GenerateTests(unittest.TestCase):
    def test_today_post_fits_contract(self) -> None:
        vk = vk_daily_root(ROOT)
        tenant = load_tenant(vk)
        banned = load_banned(vk)
        art = generate(vk, date(2026, 9, 12), "seed-a", [])
        self.assertEqual([], validate_post(art["post"], tenant, banned))
        self.assertEqual([], validate_headline(art["headline"], tenant))
        self.assertGreaterEqual(art["char_count"], tenant["post"]["min_chars"])
        self.assertLessEqual(art["char_count"], tenant["post"]["max_chars"])
        self.assertNotIn("http://", art["post"].lower())
        self.assertNotIn("https://", art["post"].lower())

    def test_composition_changes_with_seed(self) -> None:
        comps = json.loads((ROOT / "vk-daily/data/compositions.json").read_text(encoding="utf-8"))["compositions"]
        seen = {pick_composition(comps, f"seed-{i}", []).get("id") for i in range(24)}
        self.assertGreaterEqual(len(seen), 4)

    def test_used_compositions_skipped(self) -> None:
        comps = json.loads((ROOT / "vk-daily/data/compositions.json").read_text(encoding="utf-8"))["compositions"]
        used = [c["id"] for c in comps[:-1]]
        picked = pick_composition(comps, "x", used)
        self.assertEqual(picked["id"], comps[-1]["id"])


class CoverBlockerTests(unittest.TestCase):
    def test_missing_key_does_not_write_cover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            env = {k: v for k, v in os.environ.items() if k != "KIE_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                meta = generate_cover(
                    root=ROOT,
                    out_dir=out,
                    headline="Уфа снова в тройке",
                    composition_prompt="test",
                    accent="#2F7BFF",
                    aspect_ratio="3:4",
                    resolution="2K",
                )
            self.assertEqual(meta["status"], "blocked")
            self.assertEqual(meta["blocker"], "KIE_API_KEY")
            self.assertFalse((out / "cover.png").exists())
            self.assertFalse((out / "cover-url.txt").exists())

    def test_public_github_urls_default(self) -> None:
        urls = resolve_face_ref_urls()
        self.assertEqual(list(PUBLIC_FACE_REF_URLS), urls)
        self.assertTrue(all(u.startswith("https://raw.githubusercontent.com/") for u in urls))

    def test_prompt_locks_mukhtarov_and_masthead(self) -> None:
        prompt = build_prompt(
            headline="Титул на вторичке спасает деньги",
            composition_prompt="editorial mono shirt",
            accent="#2F7BFF",
            dek="Когда полис защищает право собственности, а когда важнее юридическая проверка",
        )
        self.assertIn("РУСЛАН МУХТАРОВ", prompt)
        self.assertIn("УФА", prompt)
        self.assertIn("СЕНТЯБРЬ 2026", prompt)
        self.assertIn("Титул на вторичке спасает деньги", prompt)
        self.assertIn("Never write Хабибуллин", prompt)

    def test_kie_call_uses_github_raw_not_host_image(self) -> None:
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch.dict(os.environ, {"KIE_API_KEY": "test-key"}):
                with patch("generate_cover.create_i2i_task", return_value="task-1") as create:
                    with patch("generate_cover.wait_for_success", return_value={"state": "success"}):
                        with patch(
                            "generate_cover.result_urls",
                            return_value=["https://example.com/cover.png"],
                        ):
                            with patch(
                                "generate_cover.download_url_bytes",
                                return_value=(fake_png, {}),
                            ):
                                meta = generate_cover(
                                    root=ROOT,
                                    out_dir=out,
                                    headline="Титул на вторичке спасает деньги",
                                    composition_prompt="editorial mono shirt",
                                    accent="#2F7BFF",
                                    aspect_ratio="16:9",
                                    resolution="2K",
                                )
            self.assertEqual(meta["status"], "ok")
            self.assertEqual(create.call_args.kwargs["input_urls"], list(PUBLIC_FACE_REF_URLS))
            self.assertEqual(create.call_args.kwargs["aspect_ratio"], "16:9")
            self.assertTrue((out / "cover.png").exists())
            self.assertNotIn("host_image", generate_cover.__globals__)


if __name__ == "__main__":
    unittest.main()
