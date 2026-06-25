param(
    [string]$ApiUrl = "http://127.0.0.1:8001/api"
)

$ErrorActionPreference = "Continue"

$RootUrl = $ApiUrl -replace "/api$", ""

Write-Host ""
Write-Host "Checking backend root: $RootUrl" -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri $RootUrl -TimeoutSec 8
    Write-Host "Backend root responded." -ForegroundColor Green
} catch {
    Write-Host "Backend root failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Checking API auth route availability: $ApiUrl/auth/login" -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "$ApiUrl/auth/login" -Method Post -Body "{}" -ContentType "application/json" -TimeoutSec 8 | Out-Null
    Write-Host "Login route responded." -ForegroundColor Green
} catch {
    if ($_.Exception.Response) {
        Write-Host "Login route is reachable. HTTP status: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Green
    } else {
        Write-Host "Login route failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}
