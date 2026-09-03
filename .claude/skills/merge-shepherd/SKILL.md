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
- `cleanup`: GitHub уже подтвердил merge; вызови показанный
  `complete merge-cleanup` с неизменённым `lease` и не отправляй второй merge;
- `wait` или `empty`: ничего не меняй, `ИТОГ: ПУСТО`;
- `fallback`: полностью прочитай
  [references/legacy-protocol.md](references/legacy-protocol.md) и следуй ему;
- `error`: `ИТОГ: НЕ СМОГ`, без ручного обхода отказа.

Быстрый путь допустим только для `CLEAN` PR с обычным каноничным proof, новым
trusted `ship` и зелёной проверкой `validate`. Base-sync, carry, legacy re-ship,
конфликт и recovery всегда обрабатывает полная процедура.

До merge CLI сохраняет точный `pp:merge-cleanup-intent`. После сбоя следующий
MERGE находит intent даже у уже закрытого PR и возвращает `action=cleanup`:
проверяет серверный `MergedEvent`, снимает `in-work` только с закрытых
same-repository issues, идемпотентно завершает PLAN-handoff, снимает `ship` и
последним пишет `pp:merge-cleanup-done`. Пока самый ранний intent не завершён
либо не эскалирован как неоднозначный, следующую merge-цель не выбирай.

После merge plan-PR со строками `Plan-Issue: #N` и `Plan-Path: Plans/<file>.md`
заверши PLAN-handoff: проверь открытую issue с `approved` + `plan-in-review`,
опубликуй `pp:plan-ready`, добавь `ready-fix`, затем сними `plan-in-review` и
`needs-decision`. Если handoff не завершился, не скрывай post-merge блокер.

Только `action=completed` означает `ИТОГ: ГОТОВО`; ожидание без мутации —
`ИТОГ: ПУСТО`.
