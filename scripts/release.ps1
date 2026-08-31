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
    Не создавать git commit и tag (только обновить config/app.yaml).

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

# 1. Извлекаем текущую версию
$currentStr = "1.0.0"
if ($rawContent -match '(?m)^version:\s*["'']?([^"''\r\n#]+)["'']?') {
    $currentStr = $matches[1].Trim()
}

# Нормализуем текущую версию в формат major.minor.patch
$parts = $currentStr.Split('.')
$major = 1
$minor = 0
$patch = 0

if ($parts.Length -ge 1 -and [int]::TryParse($parts[0], [ref]$null)) { $major = [int]$parts[0] }
if ($parts.Length -ge 2 -and [int]::TryParse($parts[1], [ref]$null)) { $minor = [int]$parts[1] }
if ($parts.Length -ge 3 -and [int]::TryParse($parts[2], [ref]$null)) { $patch = [int]$parts[2] }

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

# 3. Обновляем config/app.yaml (сохраняя комментарии и структуру)
if ($rawContent -match '(?m)^version:\s*.*$') {
    $updatedContent = $rawContent -replace '(?m)^version:\s*.*$', "version: `"$newVersion`""
} else {
    $updatedContent = $rawContent -replace '(?m)^(name:\s*.*)$', "`$1`nversion: `"$newVersion`""
}

[System.IO.File]::WriteAllText($appYaml, $updatedContent, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Обновлён config/app.yaml -> version: `"$newVersion`"" -ForegroundColor Yellow

# 4. Git commit & tag
if (-not $NoCommit) {
    Push-Location $repoRoot
    try {
        $tag = "v$newVersion"
        $commitMsg = "release: $tag"
        if ($Message -ne "") {
            $commitMsg = "release: $tag - $Message"
        }

        git add config/app.yaml
        git commit -m $commitMsg
        git tag -a $tag -m $commitMsg

        Write-Host "Создан Git-коммит: '$commitMsg'" -ForegroundColor Green
        Write-Host "Создан Git-тег:    $tag" -ForegroundColor Green

        if ($Push) {
            Write-Host ">>> Отправка в origin..." -ForegroundColor Yellow
            git push origin HEAD --tags
            Write-Host "Отправлено в remote!" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Готово! Версия конфигурации: $newVersion" -ForegroundColor Cyan
