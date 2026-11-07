# Генератор манги (облачный контейнер, без видеокарты)

- `gen.py` — генерация панелей: diffusers + Meina/MeinaMix_V11 (SD 1.5, аниме), ускорение LCM-LoRA (8 шагов, ~55 с на панель на 4 ядрах CPU). Модели скачиваются с Hugging Face, в репозиторий не кладутся.
- `compose.py` — сборка страниц 1200×1800: рамки по разметке `кадры/<NNN>/panels/pNN.json`, баблы (обычный/крик/шёпот), подписи, SFX, окно Системы. Шрифты: PT Sans Narrow и Russo One (Google Fonts, лицензия OFL), латиница и кириллица склеены через fontTools.
- Порядок: `compose.py jobs <panels_dir> jobs.json` → `gen.py jobs.json <out>` → `compose.py all <panels_dir> <out> <pages>`.
- Метки пола для аниме-модели ставятся автоматически по словам промпта; для чудовищ пиши в промпте `monster, no humans`.
