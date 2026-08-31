# Auto-documentation script for OneBase configuration
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "=== OneBase Auto-Documentation Generator ===" -ForegroundColor Cyan

# 1. Update AGENTS.md via platform if onebase is present
if (Get-Command "onebase" -ErrorAction SilentlyContinue) {
    Write-Host "[1/2] Updating AGENTS.md via 'onebase ai-guide'..." -ForegroundColor Yellow
    onebase ai-guide --output (Join-Path $repoRoot "AGENTS.md")
    Write-Host "  -> AGENTS.md updated" -ForegroundColor Green
} else {
    Write-Host "  -> onebase not found in PATH, skipping AGENTS.md" -ForegroundColor Gray
}

# 2. Update DOCS.md via python script
Write-Host "[2/2] Generating metadata catalog in DOCS.md..." -ForegroundColor Yellow
python (Join-Path $repoRoot "scripts\gen_docs.py")
Write-Host "  -> DOCS.md successfully generated!" -ForegroundColor Green

Write-Host ""
Write-Host "All documentation is up to date." -ForegroundColor Cyan
