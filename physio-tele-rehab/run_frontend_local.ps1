param(
    [string]$ApiUrl = "http://127.0.0.1:8001/api",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ProjectRoot))
$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

Set-Location $FrontendRoot

$env:API_URL = $ApiUrl

Write-Host ""
Write-Host "Starting Physio Tele-Rehab frontend on http://localhost:$Port" -ForegroundColor Green
Write-Host "Frontend API target: $ApiUrl" -ForegroundColor Cyan
Write-Host "Keep this window open while testing." -ForegroundColor Yellow
Write-Host "Python: $PythonExe" -ForegroundColor DarkGray
& $PythonExe -m streamlit run app.py --server.port $Port
