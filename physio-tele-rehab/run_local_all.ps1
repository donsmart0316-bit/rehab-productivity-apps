param(
    [string]$DatabaseUrl = "",
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 8501
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendScript = Join-Path $ProjectRoot "run_backend_local.ps1"
$FrontendScript = Join-Path $ProjectRoot "run_frontend_local.ps1"

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:DATABASE_URL
}

if (-not $DatabaseUrl) {
    $DatabaseUrl = Read-Host "Paste your Neon or Supabase DATABASE_URL"
}

$ApiUrl = "http://127.0.0.1:$BackendPort/api"

Write-Host ""
Write-Host "Opening backend window..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $BackendScript,
    "-DatabaseUrl",
    $DatabaseUrl,
    "-Port",
    "$BackendPort"
)

Write-Host "Waiting briefly for backend startup..." -ForegroundColor Cyan
Start-Sleep -Seconds 8

Write-Host "Opening frontend window..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $FrontendScript,
    "-ApiUrl",
    $ApiUrl,
    "-Port",
    "$FrontendPort"
)

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:$BackendPort" -ForegroundColor Green
Write-Host "Frontend: http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host ""
Write-Host "If login fails, check the backend window first. It will show the real error." -ForegroundColor Yellow
