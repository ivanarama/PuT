# Конвейер сопровождения PuT

Репозиторий обслуживается пятью независимыми этапами PromptPilot:

```text
issue → TRIAGE → ready-fix/needs-decision → PLAN при необходимости → FIX → PR → REVIEW
      → reviewed → решение человека ship → MERGE
```

Каждый запуск выполняет только один этап и заканчивается строкой `ИТОГ:`.
Упоминание следующего этапа не разрешает запускать его автоматически.

## Этапы

| Этап | Каноническая процедура | Лимит одного прогона |
|---|---|---:|
| TRIAGE | `.claude/skills/triage-issues/SKILL.md` | 5 issues |
| PLAN | `.claude/skills/plan-approved/SKILL.md` | 1 issue |
| FIX | `.claude/skills/fix-approved/SKILL.md` | 1 issue или PR |
| REVIEW | `.claude/skills/review-queue/SKILL.md` | 2 PR |
| MERGE | `.claude/skills/merge-shepherd/SKILL.md` | 3 PR |

Файлы `.agents/skills/*` — только адаптеры Codex. Правила очереди и полномочия
задаются каноническими процедурами в `.claude/skills/*`.

## Метки маршрута

- `ready-fix` — очевидный воспроизведённый дефект, который разрешено исправить автоматически.
- `needs-decision` — требуется решение человека.
- `approved` и `decision:N` — человек разрешил реализацию и выбрал вариант.
- `plan-needed` — выбранный вариант требует сначала отдельный plan-PR.
- `plan-in-review` — plan-PR создан; после его merge issue вернётся в FIX.
- `in-work` — по issue уже открыт PR.
- `changes-requested` — REVIEW вернул PR на доработку.
- `reviewed` — блокирующих замечаний нет, но merge ещё не разрешён.
- `ship` — человек явно разрешил слияние.
- `hold` и `manual` — автоматика не должна брать элемент.

Автоматические этапы не ставят `approved`, `decision:*` или `ship`.
GitHub-запись разрешена только от аккаунта `ivanarama`.

## Синхронизация PR с main без повторного ship

Если MERGE должен обновить одобренный PR от `main`, он публикует неизменяемые
`pp:base-sync-intent` и `pp:base-sync-done`, сохраняет человеческий `ship` и
передаёт точный новый HEAD на интеграционное REVIEW. После успешной проверки
MERGE продолжает без второго решения человека. Для веток, обновлённых до
появления этих маркеров, новый человеческий `ship` после точного merge HEAD
разрешает узкий legacy re-ship; произвольный push его не наследует.

Handoff работает single-flight только в интеграционной полосе. MERGE обновляет
первый PR; REVIEW проверяет его интеграционную дельту; следующий MERGE обязан
сначала довести владельца до слияния. Следующий PR нельзя обновлять или
интеграционно ревьюить заранее: merge первого снова изменит `main` и обесценит
такой аудит. Обычные содержательные ревью других PR при ожидании MERGE/recovery
продолжаются: они привязаны к HEAD и не подтверждают совместимость с будущим
tip `main`.
Интеграционная проверка переиспользует content-proof исходного `from` и смотрит
только переход `from → to`: parents, разрешение конфликтов, дельту base-sync и
CI. Собственное изменение PR вне валидного base-sync требует нового полного
содержательного ревью.
Если исторический intent/done ссылается на stale `ship-event`, человек может
переавторизовать точный текущий HEAD новым `ship` после done. REVIEW доказывает
parents, source proof и отсутствие последующего push; следующий base-sync
начинает исправленную цепочку с `previous=none`.
Tip `main` для intent читается напрямую из `git/ref/heads/main`, не из
`PullRequest.baseRefOid`; done записывает фактический второй parent. Сдвиг base
между intent и done виден как `base_sync_base_advanced` и требует ancestry gate.

## Восстановление после merge

Перед compare-and-merge общий `pipelinectl` PromptPilot публикует неизменяемый
`pp:merge-cleanup-intent`, привязанный к exact HEAD, review-proof, raw UTF-8
телу PR и closing issues только репозитория `ivanarama/PuT`. После marker он
повторяет timeline, label, proof и CI-гейты. Qualified-ссылка на другой
repository не превращается в локальный номер issue.

Если процесс оборвался, следующий MERGE сначала восстанавливает самый ранний
незавершённый intent. Для уже merged PR он возвращает `action=cleanup` и не
посылает merge второй раз. `complete merge-cleanup` доказывает серверный
`MergedEvent`, снимает `in-work` только с закрытых связанных issues,
идемпотентно завершает PLAN-handoff, снимает `ship` и последним публикует
`pp:merge-cleanup-done`. Неоднозначный или изменившийся intent блокирует новую
merge-цель и сразу виден как причина эскалации, а не теряется до следующего дня.

## Обязательные проверки PuT

```text
onebase check --project .
onebase lint --project .
go test ./...
```

Для изменений метаданных, миграций или исполняемой логики дополнительно
выполняется smoke-цикл из `.github/workflows/ci.yml`.

## Операционная диагностика

`tools/pipelinehealth` читает открытые PR и доверенные маркеры `pp:*`,
проверяет конфликтующие маршрутные метки, незавершённые review/base-sync-
транзакции, single-flight-владельца и breadth-first порядок REVIEW. Проверка
read-only, не вызывает LLM и выдаёт JSON
для дашборда PromptPilot:

```powershell
go run ./tools/pipelinehealth/main.go -json
go test ./tools/pipelinehealth/...
```

Для REVIEW вывод `review_candidates` является закрытым исполняемым allowlist, а
не только операторским отчётом. Этап запускает health-check перед выбором PR и
ещё раз перед первой мутацией. При `single_flight_barrier` он может проверить
только указанного владельца интеграционной полосы. Если владелец уже ждёт
MERGE/recovery, обычные stage `review` остаются исполняемыми, но следующий
интеграционный PR запрещён. Если GraphQL gate владельца не сошёлся, переходить к
обычной очереди в этом же запуске запрещено.
На Windows preflight ищет `gh` и `go` в `PATH`, затем в стандартных
`C:\Program Files\GitHub CLI\gh.exe` и `C:\Program Files\Go\bin\go.exe`;
оба инструмента вызываются по найденным абсолютным путям.

Зелёный статус означает, что инварианты соблюдены. Жёлтый означает ожидаемый
handoff или восстанавливаемую незавершённую транзакцию. Красный означает
конфликт маршрута либо нарушение review-протокола.
