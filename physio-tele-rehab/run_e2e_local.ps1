param(
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Join-Path $ProjectRoot "backend"

Set-Location $BackendRoot

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:DATABASE_URL
}

if (-not $DatabaseUrl) {
    $DatabaseUrl = Read-Host "Paste your Neon or Supabase DATABASE_URL"
}

$env:DATABASE_URL = $DatabaseUrl
$env:PYTHONUNBUFFERED = "1"

Write-Host ""
Write-Host "Running full patient and therapist workflow test..." -ForegroundColor Cyan
Write-Host "This creates temporary test users and records in the configured database." -ForegroundColor Yellow
python tests/e2e_workflows.py
