---
name: merge-shepherd
description: Безопасное слияние PR ivanarama/PuT через pipelinectl с fallback для base-sync, конфликтов и recovery.
---

# MERGE

Обрабатывай только PR с `ship` и без `hold`/`needs-decision`.

Выполни команду `pipelinectl`, данную PromptPilot. При ручном запуске:

```powershell
python -m promptpilot.project_pipeline --config pipelinectl.json next merge
```

- `merge`: вызови показанный `complete merge` с неизменённым `lease`;
- `wait` или `empty`: ничего не меняй, `ИТОГ: ПУСТО`;
- `fallback`: полностью прочитай
  [references/legacy-protocol.md](references/legacy-protocol.md) и следуй ему;
- `error`: `ИТОГ: НЕ СМОГ`, без ручного обхода отказа.

Быстрый путь допустим только для `CLEAN` PR с обычным каноничным proof, новым
trusted `ship` и зелёной проверкой `validate`. Base-sync, carry, legacy re-ship,
конфликт и recovery всегда обрабатывает полная процедура.

Только `action=completed` означает `ИТОГ: ГОТОВО`; ожидание без мутации —
`ИТОГ: ПУСТО`.
