#!/usr/bin/env python3
"""Thin wrapper: python3 scripts/vk_daily_today.py → vk-daily/scripts/run_today.py."""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "vk-daily" / "scripts" / "run_today.py"
    runpy.run_path(str(target), run_name="__main__")
