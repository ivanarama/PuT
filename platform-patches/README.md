# Поддерживаемая сборка платформы

Основа — `ivanarama/onebase`, commit `ac6231b8dd7a88e1ca19d532e0ac15e60c73bbca`.
PuT 1.3.4 требует OneBase не ниже **0.13.0** (`min_engine_version` в `config/app.yaml`). Платформа показывает предупреждение при несоответствии и не запрещает запуск. Для выпуска и развёртывания этой версии используется сборка **0.13.0+put.5.ac6231b8**. Точный commit, номер сборки и SHA256 патча записаны в `runtime.json`.

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
- обработку кириллицы в URL отчёта этапов и возврат в исходный объект по проверенному UUID;
- расчёт остатков и оборотов в PostgreSQL для регистров со ссылочными реквизитами, включая проверку денег при проведении кассового документа;
- создание таблиц аудита и истории этапов при миграции базы, до запуска параллельных обработок;
- регрессионные Go- и JavaScript-тесты.

## Сборка для Windows

Понадобятся Git, Go и Python 3 в PATH, а также доступ к GitHub и модулям Go. В CI используется Go 1.27.0. Если PuT ещё не скачан, откройте PowerShell в папке, где хотите хранить проект, и выполните команды ниже.

```powershell
git clone https://github.com/ivanarama/PuT.git PuT
Set-Location -LiteralPath .\PuT
```

Следующий блок выполняется один раз из любой папки внутри свежего клона PuT. Исходники платформы появятся в `.local/onebase-src`, исполняемый файл — в `.local/onebase-preview.exe`. Все пути берутся относительно корня клона.

```powershell
$ErrorActionPreference = 'Stop'
$projectDir = (git rev-parse --show-toplevel)
$runtime = Get-Content -Raw -Encoding UTF8 (Join-Path $projectDir 'platform-patches/runtime.json') | ConvertFrom-Json
$localDir = Join-Path $projectDir '.local'
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$sourceDir = Join-Path $localDir 'onebase-src'
$patch = Join-Path $projectDir $runtime.patch
$binary = Join-Path $localDir 'onebase-preview.exe'

git init --quiet $sourceDir
if ($LASTEXITCODE) { throw 'git init failed' }
git -C $sourceDir config core.autocrlf false
if ($LASTEXITCODE) { throw 'git config failed' }
git -C $sourceDir fetch --quiet --depth 1 $runtime.repository $runtime.commit
if ($LASTEXITCODE) { throw 'git fetch failed' }
git -C $sourceDir checkout --quiet --detach FETCH_HEAD
if ($LASTEXITCODE) { throw 'git checkout failed' }
git -C $sourceDir apply --check $patch
if ($LASTEXITCODE) { throw 'git apply --check failed' }
git -C $sourceDir apply $patch
if ($LASTEXITCODE) { throw 'git apply failed' }
go -C $sourceDir build -ldflags "-X github.com/ivantit66/onebase/internal/version.Build=$($runtime.build)" -o $binary ./cmd/onebase
if ($LASTEXITCODE) { throw 'go build failed' }
python -X utf8 (Join-Path $projectDir 'scripts/check_runtime.py') --onebase $binary
if ($LASTEXITCODE) { throw 'check_runtime failed' }
```

При успешной проверке появится строка с версиями PuT и OneBase и сообщением `patch SHA256 OK`. После этого можно [запустить локальный стенд](../docs/LOCAL_PREVIEW.md).

## Проверки для разработчиков платформы

В той же сессии PowerShell можно проверить изменённые пакеты Go, поведение интерфейса и переводы. Для тестов JavaScript потребуется Node.js.

```powershell
go -C $sourceDir test ./internal/ui ./internal/widget ./internal/configcheck -run 'Test(ProcessorFormScalarState|ProcessorRequest|ProcessorParam|ValueTableReadonly|WidgetFilters|LintYAML_LiveListKeysKnown|ManagedFileReader|StaticAssetsCompressedOnPublicRoutes|VersionedAppScriptsCacheAndRevalidate|StagesReportEncodedEntityAndReturnLink)' -count=1 -timeout 240s
node --test (Join-Path $sourceDir 'internal/ui/static/widget_filters_behavior_test.js') (Join-Path $sourceDir 'internal/ui/static/managed_file_reader_behavior_test.js')
go -C $sourceDir run ./tools/i18ncheck
```

Проверка скалярного состояния допускает только объявленные и размещённые редактируемые элементы формы. Неразмещённые и нередактируемые поля, служебные поля и значения только из query string не принимаются. Это состояние остаётся вводом пользователя: номер задачи проверяется API очереди, права операций задаются правами обработки.

Для Orange Pi собирается отдельный Linux ARM64-бинарь с этим же патчем (`GOOS=linux`, `GOARCH=arm64`, `CGO_ENABLED=0`). Релиз проверяется сначала на отдельной PostgreSQL, затем развёртывается в `/opt/onebase-put/releases/<версия>/`; ссылка `/opt/onebase-put/current` выбирает активную поставку. Общий бинарь остальных приложений не заменяется.
