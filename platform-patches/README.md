# Поддерживаемая сборка платформы

Основа — `ivanarama/onebase`, commit `ac6231b8dd7a88e1ca19d532e0ac15e60c73bbca`.
PuT 1.3.2 требует OneBase не ниже **0.13.0** (`min_engine_version` в `config/app.yaml`). Платформа показывает предупреждение при несоответствии и не запрещает запуск. Для выпуска и развёртывания этой версии используется проверенная сборка **0.13.0+put.2.ac6231b8**: точный commit, номер сборки и SHA256 патча записаны в `runtime.json`.

Перед развёртыванием выполните `python scripts/check_runtime.py --onebase <путь-к-бинарю>`. Проверка отказывает при другой сборке, изменённом патче или рассогласовании версий конфигурации. Будущая версия платформы может оказаться совместимой, но её нужно проверить и обновить lock-файл; номер `0.13.0` сам по себе не доказывает наличие текущих патчей. CI собирает платформу из этого же commit с этим же патчем, вместо плавающего `main`.
Патч `put-ui.patch` обязателен для этой версии конфигурации. Он включает:

- сворачиваемые отборы виджетов с количеством активных условий;
- сохранение представлений ссылочных колонок виджетов;
- отсутствие повторного заголовка у таблицы без явно заданного заголовка;
- отсутствие добавления/удаления строк у сводных таблиц только для чтения, включая обновление после события;
- передачу скалярного состояния формы обработки между событиями: номер фонового задания больше не теряется;
- многострочное отображение результата фоновой операции в реквизите формы;
- исправление ложного предупреждения линта о поддерживаемом `list_filters`;
- URL общих скриптов с хэшем содержимого и immutable-кэш только для актуального хэша;
- gzip для публичной статики с сохранением ответов 304, диапазонов и несжатых SSE;
- регрессионные Go- и JavaScript-тесты.

Собирайте в отдельном чистом checkout платформы, затем применяйте патч:

```powershell
git checkout ac6231b8dd7a88e1ca19d532e0ac15e60c73bbca
git apply --check D:/Projects/PuT/platform-patches/put-ui.patch
git apply D:/Projects/PuT/platform-patches/put-ui.patch
go build -ldflags '-X github.com/ivantit66/onebase/internal/version.Build=0.13.0+put.2.ac6231b8' -o D:/Projects/PuT/.local/onebase-preview.exe ./cmd/onebase
```

Проверки изменённых частей платформы:

```powershell
go test ./internal/ui ./internal/widget ./internal/configcheck -run 'Test(ProcessorFormScalarState|ProcessorRequest|ProcessorParam|ValueTableReadonly|WidgetFilters|LintYAML_LiveListKeysKnown|ManagedFileReader|StaticAssetsCompressedOnPublicRoutes|VersionedAppScriptsCacheAndRevalidate)' -count=1 -timeout 240s
node --test internal/ui/static/widget_filters_behavior_test.js internal/ui/static/managed_file_reader_behavior_test.js
go run ./tools/i18ncheck
```

Проверка скалярного состояния допускает только объявленные и размещённые редактируемые элементы формы. Неразмещённые и нередактируемые поля, служебные поля и значения только из query string не принимаются. Это состояние остаётся вводом пользователя: номер задачи проверяется API очереди, права операций задаются правами обработки.

Для Orange Pi собирается отдельный Linux ARM64-бинарь с этим же патчем (`GOOS=linux`, `GOARCH=arm64`, `CGO_ENABLED=0`). Релиз проверяется сначала на отдельной PostgreSQL, затем развёртывается в `/opt/onebase-put/releases/<версия>/`; ссылка `/opt/onebase-put/current` выбирает активную поставку. Общий бинарь остальных приложений не заменяется.
