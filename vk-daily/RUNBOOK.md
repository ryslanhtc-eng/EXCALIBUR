# RUNBOOK — VK daily (Cursor Cloud)

Язык: русский. Пайплайн **не** является Excalibur BLOG. Не вызывай `Task(excalibur-blog-*)`.

Тенент: Руслан Мухтаров, Самолет Плюс, Уфа, группа `https://vk.ru/samolet_plus_sipa`.

## 0. Preflight

```bash
python3 vk-daily/scripts/import_refs.py
ls vk-daily/refs/ruslan_selfie_blue.jpg vk-daily/refs/ruslan_selfie_black.jpg
test -n "$KIE_API_KEY" && echo KIE_ok || echo KIE_missing
```

Прочитай:

- `vk-daily/tenant/SOUL.md`
- `vk-daily/tenant/news-pipeline.md`
- `vk-daily/data/news-bank.json`

Жёстко: база Уфа; слово «метро» строго запрещено; ~2000 знаков; синий акцент; новая композиция; эмодзи только чувства; ссылок нет.

## 1. Факты дня

Обнови `vk-daily/data/news-bank.json` записью с `date` ≤ сегодня (таймзона Уфы), одной методикой цифр, локальным источником.

Не смешивай 197,8 тыс. (РБК, первичка) и 177 тыс. / 8,2 млн (Мир квартир / Башинформ).

## 2. Собрать latest/

```bash
python3 vk-daily/scripts/run_today.py
```

Опции: `--date YYYY-MM-DD`, `--force-new-composition`, `--skip-cover` (только отладка).

Скрипт пишет `memory/vk-daily/latest/{post.txt,meta.json}` и при успехе KIE ещё `cover.png` + `cover-url.txt`.

## 3. Живой текст (опционально)

Можно переписать `post.txt` голосом из SOUL, затем:

```bash
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "vk-daily/scripts")
from paths import repo_root, vk_daily_root
from validate_post import load_banned, load_tenant, validate_post
root = repo_root()
vk = vk_daily_root(root)
text = (root / "memory/vk-daily/latest/post.txt").read_text(encoding="utf-8")
errs = validate_post(text, load_tenant(vk), load_banned(vk))
raise SystemExit("FAIL: " + "; ".join(errs) if errs else 0)
PY
```

Headline обложки — 4–8 слов, без точки и эмодзи, без вранья (`cover-headline.md`). Если менял смысл поста — перезапусти cover (новый `run_today.py` или cover-only после правки meta). Проще полный `run_today.py`.

## 4. Обложка

Только KIE `gpt-image-2-image-to-image` + `input_urls` селфи (и референс позы из каталога `vk-daily/refs/poses-wardrobe/` при наличии файла).  
Нет ключа / нет refs / ошибка хоста / ошибка KIE → блокер в `meta.json`, **никакой** заглушки.

Каждый run берёт новый id из `vk-daily/data/compositions.json` и новый референс позы/гардероба из `vk-daily/data/pose_wardrobe.json` (ротация через `used_pose_refs` в `memory/vk-daily/state.json`). Лицо всегда строго фиксируется по селфи Руслана.

## 5. Отдать Grok Bot

Не публикуй из Cloud. Оркестратор читает пути из `vk-daily/README.md`.

Готово, если:

- `post.txt` 1700–2300 знаков, без URL;
- `meta.json` заполнен;
- либо `cover.png` (и `publish_ready: true`), либо явный `❌ VK COVER BLOCKER` без файла обложки.
