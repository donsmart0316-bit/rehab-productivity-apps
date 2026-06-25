param(
    [string]$DatabaseUrl = "",
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Join-Path $ProjectRoot "backend"
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ProjectRoot))
$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

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
& $PythonExe -m alembic upgrade head

Write-Host ""
Write-Host "Starting Physio Tele-Rehab backend on http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Keep this window open while testing." -ForegroundColor Yellow
Write-Host "Python: $PythonExe" -ForegroundColor DarkGray
& $PythonExe -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
