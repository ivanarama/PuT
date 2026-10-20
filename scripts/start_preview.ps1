param(
    [string]$Binary = '',
    [int]$Port = 8100,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path $PSScriptRoot -Parent
$localDir = Join-Path $projectDir '.local'
New-Item -ItemType Directory -Path $localDir -Force | Out-Null
if (-not $Binary) { $Binary = Join-Path $localDir 'onebase-preview.exe' }
$exePath = (Resolve-Path -LiteralPath $Binary).Path
$database = Join-Path $localDir 'preview.db'
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $running = Get-Process -Id $listener.OwningProcess
    if ($running.Path -ne $exePath) { throw "Port $Port is occupied by another application" }
} else {
    if (-not (Test-Path -LiteralPath $database)) {
        & $exePath --no-gui migrate --project $projectDir --sqlite $database
        if ($LASTEXITCODE) { throw 'Migration failed' }
        & $exePath --no-gui procrun --project $projectDir --sqlite $database --proc ЗаполнитьТестовуюБазу
        if ($LASTEXITCODE) { throw 'Demo seed failed' }
        $credentials = & $exePath --no-gui user add preview --project $projectDir --sqlite $database --admin --generate
        if ($LASTEXITCODE) { throw 'User creation failed' }
        $credentials | Set-Content -LiteralPath (Join-Path $localDir 'credentials.txt') -Encoding utf8
    }
    Start-Process -FilePath $exePath -ArgumentList @('--no-gui','run','--project',('"'+$projectDir+'"'),'--sqlite',('"'+$database+'"'),'--port',$Port,'--host','127.0.0.1') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localDir 'server.log') -RedirectStandardError (Join-Path $localDir 'server-error.log') | Out-Null
}
$address = "http://127.0.0.1:$Port/ui/"
Write-Host $address
Write-Host ('Credentials: ' + (Join-Path $localDir 'credentials.txt'))
if (-not $NoBrowser) { Start-Process $address }
