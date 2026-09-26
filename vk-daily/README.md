# VK daily — готовый пост для Grok Bot

Cursor Cloud делает тяжёлую работу (факты, текст ~2000 знаков, обложка KIE).  
**Grok Bot только публикует** в группу [vk.ru/samolet_plus_sipa](https://vk.ru/samolet_plus_sipa). Текст не переписывать. Обложку не рисовать заглушкой.

Это **отдельный** пайплайн. Он не запускает Excalibur BLOG и не вызывает blog-субагентов.

## Артефакты для оркестратора

Корень репозитория = `<PROJECT_ROOT>`.

| Файл | Назначение |
|------|------------|
| `memory/vk-daily/latest/meta.json` | статус, headline, blocker, `publish_ready` |
| `memory/vk-daily/latest/post.txt` | текст поста (без ссылок) |
| `memory/vk-daily/latest/post-plain.txt` | чистый утверждённый текст поста |
| `memory/vk-daily/latest/cover.png` | обложка, **только если KIE отработал** |
| `memory/vk-daily/latest/cover-url.txt` | HTTPS URL той же картинки (если KIE отработал) |

Архив того же прогона: `memory/vk-daily/runs/YYYY-MM-DD/`.

## Шаг Grok Bot (publish)

1. Прочитай `memory/vk-daily/latest/meta.json`.
2. Публикуй **только если** `publish_ready === true` и `cover.status === "ok"`.
3. Если есть `blocker` / `blocker_message` — **стоп**. Не выкладывай пост без обложки и не подставляй сток, коллаж, скрин, «потом картинку».
4. Текст бери **как есть** из `post.txt` (включая переносы). Не добавляй ссылки.
5. Картинку бери из `cover.png`. Если файла нет — смотри `cover-url.txt` и скачай. Если нет обоих — стоп.
6. Цель: стена сообщества `samolet_plus_sipa` (`vk_group_url` в meta).
7. После публикации оркестратор может пометить прогон у себя. В этот репозиторий бот **не обязан** коммитить.

`VK_DAILY_ALLOW_TEXT_ONLY=yes` разрешает `publish_ready` без обложки. По умолчанию выключено.

## Запуск на Cursor Cloud

```bash
python3 vk-daily/scripts/run_today.py
```

Нужен секрет `KIE_API_KEY` (KIE Market, модель `gpt-image-2-image-to-image`).  
Если ключа нет, скрипт всё равно пишет `post.txt` + `meta.json` с `❌ VK COVER BLOCKER` и **не** создаёт фейковый `cover.png`.

Селфи для i2i:

- `vk-daily/refs/ruslan_selfie_blue.jpg`
- `vk-daily/refs/ruslan_selfie_black.jpg`

```bash
python3 vk-daily/scripts/import_refs.py --blue /path/blue.jpg --black /path/black.jpg
```

Канон тенанта: `vk-daily/tenant/` (`SOUL.md`, `cover-style.md`, `cover-headline.md`, `emoji-rules.md`, `news-pipeline.md`).  
Пошагово: `vk-daily/RUNBOOK.md`.

## Тесты

```bash
python3 -m unittest vk-daily.tests.test_vk_daily
```
