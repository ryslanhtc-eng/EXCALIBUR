# Refs

- Селфи Руслана (оригиналы, не сгенерированные лица, основа Face Lock):
  - `ruslan_selfie_blue.jpg`
  - `ruslan_selfie_black.jpg`
- Каталог референсов поз и гардероба:
  - Папка `poses-wardrobe/` (см. `poses-wardrobe/README.md`)

Импорт селфи:

```bash
python3 vk-daily/scripts/import_refs.py --blue /path/to/blue.jpg --black /path/to/black.jpg
```

Если файлы приехали в `vk-handoff/`, скрипт подхватит их сам.

