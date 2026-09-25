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

from generate_cover import generate_cover  # noqa: E402
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

    def test_no_person_t2i_prompt_has_no_people(self) -> None:
        from generate_cover import build_prompt
        prompt = build_prompt(
            headline="Титул на вторичке спасает деньги",
            composition_prompt="test scene",
            accent="#2F7BFF",
            dek="Когда полис защищает право собственности",
            no_person=True,
        )
        self.assertIn("NO PEOPLE", prompt)
        self.assertIn("Титул на вторичке спасает деньги", prompt)
        self.assertNotIn("Photoreal editorial portrait of the SAME man", prompt)


if __name__ == "__main__":
    unittest.main()
