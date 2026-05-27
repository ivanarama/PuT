# Скрипт проверки полноты локализации конфигурации
# Сканирует все YAML-файлы и проверяет наличие переводов для всех поддерживаемых языков
# Запуск: powershell -File scripts/check_i18n.ps1 [-Langs "en,de,sr"] [-Fix]
#
# Параметры:
#   -Langs  — список языков через запятую (по умолчанию все 16)
#   -Fix    — если указан, выводит шаблон для добавления недостающих переводов

param(
    [string]$Langs = "az,de,en,es,fr,hy,ka,kk,pt,ro,ru,sr,tr,uk,uz,zh",
    [switch]$Fix
)

$ErrorActionPreference = "Stop"
$requiredLangs = $Langs -split "," | ForEach-Object { $_.Trim() }

# Каталоги для сканирования
$dirs = @("documents", "catalogs", "registers", "inforegs", "enums", "reports",
          "processors", "printforms", "widgets", "roles", "scheduled", "journals",
          "subsystems", "constants", "config")

$root = $PSScriptRoot | Split-Path
Set-Location $root

$totalFiles = 0
$totalMissing = 0
$missingByLang = @{}
foreach ($lang in $requiredLangs) { $missingByLang[$lang] = 0 }

foreach ($dir in $dirs) {
    $dirPath = Join-Path $root $dir
    if (-not (Test-Path $dirPath)) { continue }

    $files = Get-ChildItem -Path $dirPath -Filter "*.yaml" -File
    foreach ($file in $files) {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        if (-not $content) { continue }

        $totalFiles++
        $fileMissing = @()
        $relPath = $file.FullName.Replace("$root\", "")

        # Проверяем блоки titles: и labels:
        # Ищем все блоки titles:/labels: и проверяем наличие каждого языка
        $lines = Get-Content $file.FullName -Encoding UTF8
        $i = 0
        $inBlock = $false
        $blockType = ""
        $blockLangs = @{}
        $blockIndent = 0
        $blockStartLine = 0
        $parentKey = ""

        while ($i -lt $lines.Count) {
            $line = $lines[$i]

            # Определяем начало блока titles: или labels:
            if ($line -match '^(\s*)(titles|labels):\s*$') {
                if ($inBlock -and $blockType -ne "") {
                    # Сохраняем предыдущий блок
                    $missing = $requiredLangs | Where-Object { -not $blockLangs.ContainsKey($_) }
                    if ($missing) {
                        foreach ($lang in $missing) {
                            $missingByLang[$lang]++
                            $totalMissing++
                        }
                        $fileMissing += @{
                            Type = $blockType
                            Line = $blockStartLine
                            Parent = $parentKey
                            MissingLangs = $missing -join ", "
                        }
                    }
                }

                $inBlock = $true
                $blockType = $Matches[2]
                $blockIndent = $Matches[1].Length
                $blockStartLine = $i + 1
                $blockLangs = @{}

                # Определяем родительский ключ (поле выше)
                if ($i -gt 0) {
                    for ($j = $i - 1; $j -ge 0; $j--) {
                        if ($lines[$j] -match '^\s*name:\s*(.+)$') {
                            $parentKey = $Matches[1].Trim('"').Trim("'")
                            break
                        }
                        if ($lines[$j] -match '^\s*-?\s*name:\s*(.+)$') {
                            $parentKey = $Matches[1].Trim('"').Trim("'")
                            break
                        }
                    }
                }
                $i++
                continue
            }

            if ($inBlock) {
                # Строка внутри блока titles:/labels:
                if ($line -match '^\s{2,}(\w[\w-]*):\s*.+$' -and $line.Length - ($line.TrimStart()).Length -gt $blockIndent) {
                    $lang = $Matches[1]
                    $blockLangs[$lang] = $true
                }
                elseif ($line.Trim() -eq "" -or $line -match '^\s*[^#\s]' -and ($line.Length - ($line.TrimStart()).Length) -le $blockIndent) {
                    # Блок закончился
                    $missing = $requiredLangs | Where-Object { -not $blockLangs.ContainsKey($_) }
                    if ($missing) {
                        foreach ($lang in $missing) {
                            $missingByLang[$lang]++
                            $totalMissing++
                        }
                        $fileMissing += @{
                            Type = $blockType
                            Line = $blockStartLine
                            Parent = $parentKey
                            MissingLangs = $missing -join ", "
                        }
                    }
                    $inBlock = $false
                    $blockType = ""
                    $blockLangs = @{}
                }
            }

            $i++
        }

        # Проверяем последний блок
        if ($inBlock) {
            $missing = $requiredLangs | Where-Object { -not $blockLangs.ContainsKey($_) }
            if ($missing) {
                foreach ($lang in $missing) {
                    $missingByLang[$lang]++
                    $totalMissing++
                }
                $fileMissing += @{
                    Type = $blockType
                    Line = $blockStartLine
                    Parent = $parentKey
                    MissingLangs = $missing -join ", "
                }
            }
        }

        if ($fileMissing.Count -gt 0) {
            Write-Host ""
            Write-Host ">>> $relPath" -ForegroundColor Yellow
            foreach ($m in $fileMissing) {
                $msg = "  стр.$($m.Line): $($m.Type) [$($m.Parent)] — нет: $($m.MissingLangs)"
                Write-Host $msg -ForegroundColor Red
            }
        }
    }
}

# Итоги
Write-Host ""
Write-Host "=== ИТОГИ ===" -ForegroundColor Cyan
Write-Host "Файлов просканировано: $totalFiles"
Write-Host "Всего пропущенных переводов: $totalMissing"
Write-Host ""
Write-Host "По языкам:"
$langOrder = $requiredLangs | Sort-Object
foreach ($lang in $langOrder) {
    $count = $missingByLang[$lang]
    $color = if ($count -eq 0) { "Green" } else { "Red" }
    $status = if ($count -eq 0) { "OK" } else { "$count пропусков" }
    Write-Host ("  {0,-4} {1}" -f $lang, $status) -ForegroundColor $color
}

if ($totalMissing -eq 0) {
    Write-Host ""
    Write-Host "Все переводы на месте!" -ForegroundColor Green
}
