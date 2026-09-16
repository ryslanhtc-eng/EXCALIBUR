---
name: vk-daily
description: VK daily для Руслана Мухтарова / Самолет Плюс Уфа. Один пост + KIE-обложка. Публикует внешний Grok Bot.
---

# VK daily

Не путать с Excalibur BLOG. Не вызывай blog Task.

1. Прочитай `vk-daily/RUNBOOK.md` и `vk-daily/tenant/SOUL.md`.
2. При необходимости обнови `vk-daily/data/news-bank.json`.
3. `python3 vk-daily/scripts/run_today.py`
4. Отдай артефакты из `memory/vk-daily/latest/` оркестратору. Сам во ВКонтакте не пости.

Жёстко: Уфа, без метро-как-факта, ~2000 знаков, синий акцент, новая композиция и ротация поз/гардероба (каталог `vk-daily/refs/poses-wardrobe/`, лицо только с селфи), эмодзи только эмоция, без ссылок, без фейковой обложки.
