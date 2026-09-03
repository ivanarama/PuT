---
name: plan-approved
description: "Создание отдельного plan-PR для одобренных issues ivanarama/PuT с меткой plan-needed. Использовать для очереди PLAN или вызова $plan-approved."
---

# Codex-адаптер PLAN

1. Полностью прочитать [каноническую процедуру](../../../.claude/skills/plan-approved/SKILL.md), `AGENTS.md` и `CLAUDE.md`.
2. `$plan-approved [N]` эквивалентен `/plan-approved <N>`; номер не отменяет eligibility.
3. До мутаций проверить логин `ivanarama` и перечитать issue/PR.
4. Создавать только plan-PR в изолированном worktree. Не менять конфигурацию, не ставить `ship`, не сливать и не запускать FIX.
5. На Windows сохранять `Get-Content -Encoding UTF8 -Raw`, проверку через `@base64` и сравнение байт-в-байт.
6. В коммите использовать `Generated-with: Codex`; сохранять приоритеты, маркеры, переходы меток и формат `ИТОГ:`.
