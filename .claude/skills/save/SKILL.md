---
name: save
description: Сохранение кампании «Жнец» после сцены — обновить character.md, journal.md, время в .gm/мир_состояние.md, лист персонажа (sheet/index.html и republish артефакта), затем commit и push в main. Использовать по команде /save, «сохрани», «сохранить игру», а также самому после крупной сцены.
---
1. `character.md`: HP, Энергия, XP, деньги, предметы, эффекты, отношения (числа).
2. `journal.md`: 1–4 строки о сцене, без тайн.
3. `.gm/мир_состояние.md`: текущая дата/время, где Шин и отряд.
4. `.gm/отряд.md` и файлы NPC сцены: память, отношение (если менялось).
5. `.gm/последствия.md`: новые значимые решения Шина (дата, выбор, кто знает, отклик).
6. `sheet/index.html`, блок `const D`: те же числа; затем republish артефакта листа (https://claude.ai/artifact/X7gSxmajMcn4AGb7XmJUqY).
7. `git add` только файлы кампании → `git commit --author="undertaker-68 <undertaker-68@users.noreply.github.com>"` (коммиттер — текущий git config) → `git push origin main`.
Игроку — одна строка: «Сохранено». Ошибку push сообщить прямо.
