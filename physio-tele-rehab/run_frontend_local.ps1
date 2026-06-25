param(
    [string]$ApiUrl = "http://127.0.0.1:8001/api",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"

Set-Location $FrontendRoot

$env:API_URL = $ApiUrl

Write-Host ""
Write-Host "Starting Physio Tele-Rehab frontend on http://localhost:$Port" -ForegroundColor Green
Write-Host "Frontend API target: $ApiUrl" -ForegroundColor Cyan
Write-Host "Keep this window open while testing." -ForegroundColor Yellow
python -m streamlit run app.py --server.port $Port
