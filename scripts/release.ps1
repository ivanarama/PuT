<#
.SYNOPSIS
    Управление версионированием и релизами конфигурации OneBase.

.DESCRIPTION
    Скрипт читает текущую версию из config/app.yaml, инкрементирует её
    по SemVer (patch/minor/major) или устанавливает заданную, обновляет
    config/app.yaml, создаёт git commit и git tag.

.PARAMETER Type
    Тип инкремента версии: patch (по умолчанию), minor, major.

.PARAMETER Version
    Явный номер версии (например: "1.2.0"). Переопределяет Type.

.PARAMETER Message
    Комментарий к релизу (добавляется в commit и tag).

.PARAMETER NoCommit
    Не создавать git commit и tag (только обновить config/app.yaml и platform-patches/runtime.json).

.PARAMETER Push
    Сразу отправить коммит и теги в git remote (origin).

.EXAMPLE
    .\scripts\release.ps1
    # 1.0.0 -> 1.0.1 (patch) + git commit + git tag v1.0.1

.EXAMPLE
    .\scripts\release.ps1 -Type minor -Message "Добавлен новый блок отчётов"
    # 1.0.1 -> 1.1.0 (minor) + commit + tag

.EXAMPLE
    .\scripts\release.ps1 -Version "2.0.0" -Push
    # Установить 2.0.0 + commit + tag + git push
#>
param(
    [ValidateSet("patch", "minor", "major")]
    [string]$Type = "patch",

    [string]$Version = "",

    [string]$Message = "",

    [switch]$NoCommit,

    [switch]$Push
)

$ErrorActionPreference = "Stop"

# Определяем корень репозитория
$repoRoot = $PSScriptRoot
if (Test-Path (Join-Path $repoRoot "..\config\app.yaml")) {
    $repoRoot = (Resolve-Path (Join-Path $repoRoot "..")).Path
}

$appYaml = Join-Path $repoRoot "config\app.yaml"
if (-not (Test-Path $appYaml)) {
    Write-Host "ОШИБКА: Файл config/app.yaml не найден по пути $appYaml" -ForegroundColor Red
    exit 1
}

$rawContent = [System.IO.File]::ReadAllText($appYaml, [System.Text.Encoding]::UTF8)

$lockPath = Join-Path $repoRoot "platform-patches/runtime.json"
$lockContent = [IO.File]::ReadAllText($lockPath)
$utf8 = New-Object System.Text.UTF8Encoding($false)
if ($rawContent -notmatch '(?m)^version:\s*["'']?(\d+\.\d+\.\d+)["'']?\s*$') {
    throw "Некорректная версия в config/app.yaml"
}
$currentStr = $matches[1]
if (($lockContent | ConvertFrom-Json).configuration_version -ne $currentStr) {
    throw "Версии в app.yaml и runtime.json должны совпадать"
}
$major, $minor, $patch = $currentStr.Split('.') | ForEach-Object { [int]$_ }

# 2. Вычисляем новую версию
if ($Version -ne "") {
    $newVersion = $Version.TrimStart('v')
} else {
    switch ($Type) {
        "patch" { $patch++ }
        "minor" { $minor++; $patch = 0 }
        "major" { $major++; $minor = 0; $patch = 0 }
    }
    $newVersion = "$major.$minor.$patch"
}

Write-Host "=== Релиз конфигурации ===" -ForegroundColor Cyan
Write-Host "Текущая версия: $currentStr" -ForegroundColor Gray
Write-Host "Новая версия:   $newVersion" -ForegroundColor Green

if ($newVersion -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$' -or $newVersion -eq $currentStr) {
    throw "Укажите новую версию в формате major.minor.patch"
}
$updatedContent = $rawContent -replace '(?m)^version:[^\r\n]*', ('version: "' + $newVersion + '"')
$updatedLock = $lockContent -replace '("configuration_version"\s*:\s*")[^"]+(")', ('${1}' + $newVersion + '${2}')
if (($updatedLock | ConvertFrom-Json).configuration_version -ne $newVersion) { throw "Не удалось обновить runtime.json" }
if (-not $NoCommit) {
    git -C $repoRoot rev-parse -q --verify "refs/tags/v$newVersion" *> $null
    if ($LASTEXITCODE -eq 0) { throw "Тег v$newVersion уже существует" }
}
try {
    [IO.File]::WriteAllText($appYaml, $updatedContent, $utf8)
    [IO.File]::WriteAllText($lockPath, $updatedLock, $utf8)
} catch {
    [IO.File]::WriteAllText($appYaml, $rawContent, $utf8)
    [IO.File]::WriteAllText($lockPath, $lockContent, $utf8)
    throw
}

# 4. Git commit & tag
if (-not $NoCommit) {
    Push-Location $repoRoot
    try {
        $tag = "v$newVersion"
        $commitMsg = "release: $tag"
        if ($Message -ne "") {
            $commitMsg = "release: $tag - $Message"
        }

        git commit --only -m $commitMsg -- config/app.yaml platform-patches/runtime.json
        if ($LASTEXITCODE -ne 0) { throw "Не удалось создать релизный коммит" }
        git tag -a $tag -m $commitMsg
        if ($LASTEXITCODE -ne 0) { throw "Не удалось создать релизный тег" }

        Write-Host "Создан Git-коммит: '$commitMsg'" -ForegroundColor Green
        Write-Host "Создан Git-тег:    $tag" -ForegroundColor Green

        if ($Push) {
            Write-Host ">>> Отправка в origin..." -ForegroundColor Yellow
            git push --atomic origin HEAD "refs/tags/$tag"
            if ($LASTEXITCODE -ne 0) { throw "Не удалось отправить релиз" }
            Write-Host "Отправлено в remote!" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Готово! Версия конфигурации: $newVersion" -ForegroundColor Cyan
