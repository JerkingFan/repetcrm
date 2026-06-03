# Один бэкенд на порту 8000 (убивает старые процессы)
$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $root "backend"

foreach ($p in (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique) {
    taskkill /F /PID $p /T 2>$null
}
Start-Sleep -Seconds 2

Set-Location $backend
Write-Host "Starting RepetCRM backend (trust-tex-v3) on http://localhost:8000" -ForegroundColor Green
& ".\.venv\Scripts\uvicorn.exe" app.main:app --reload --host 0.0.0.0 --port 8000
