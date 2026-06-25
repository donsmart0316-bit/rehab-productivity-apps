param(
    [string]$DatabaseUrl = "",
    [int]$Port = 8001
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

Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Cyan
python -m alembic upgrade head

Write-Host ""
Write-Host "Starting Physio Tele-Rehab backend on http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Keep this window open while testing." -ForegroundColor Yellow
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
