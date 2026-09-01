# Конвейер сопровождения PuT

Репозиторий обслуживается четырьмя независимыми этапами PromptPilot:

```text
issue → TRIAGE → ready-fix/needs-decision → FIX → PR → REVIEW
      → reviewed → решение человека ship → MERGE
```

Каждый запуск выполняет только один этап и заканчивается строкой `ИТОГ:`.
Упоминание следующего этапа не разрешает запускать его автоматически.

## Этапы

| Этап | Каноническая процедура | Лимит одного прогона |
|---|---|---:|
| TRIAGE | `.claude/skills/triage-issues/SKILL.md` | 5 issues |
| FIX | `.claude/skills/fix-approved/SKILL.md` | 1 issue или PR |
| REVIEW | `.claude/skills/review-queue/SKILL.md` | 2 PR |
| MERGE | `.claude/skills/merge-shepherd/SKILL.md` | 3 PR |

Файлы `.agents/skills/*` — только адаптеры Codex. Правила очереди и полномочия
задаются каноническими процедурами в `.claude/skills/*`.

## Метки маршрута

- `ready-fix` — очевидный воспроизведённый дефект, который разрешено исправить автоматически.
- `needs-decision` — требуется решение человека.
- `approved` и `decision:N` — человек разрешил реализацию и выбрал вариант.
- `in-work` — по issue уже открыт PR.
- `changes-requested` — REVIEW вернул PR на доработку.
- `reviewed` — блокирующих замечаний нет, но merge ещё не разрешён.
- `ship` — человек явно разрешил слияние.
- `hold` и `manual` — автоматика не должна брать элемент.

Автоматические этапы не ставят `approved`, `decision:*` или `ship`.
GitHub-запись разрешена только от аккаунта `ivanarama`.

## Обязательные проверки PuT

```text
onebase check --project .
onebase lint --project .
```

Для изменений метаданных, миграций или исполняемой логики дополнительно
выполняется smoke-цикл из `.github/workflows/ci.yml`.

## Операционная диагностика

`tools/pipelinehealth` читает открытые PR и доверенные маркеры `pp:*`,
проверяет конфликтующие маршрутные метки, незавершённые review-транзакции и
breadth-first порядок REVIEW. Проверка read-only, не вызывает LLM и выдаёт JSON
для дашборда PromptPilot:

```powershell
go run ./tools/pipelinehealth/main.go -json
```

Зелёный статус означает, что инварианты соблюдены. Жёлтый означает ожидаемый
handoff или восстанавливаемую незавершённую транзакцию. Красный означает
конфликт маршрута либо нарушение review-протокола.
