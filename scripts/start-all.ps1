# RepetCRM: start backend + frontend
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot + "\.."

Write-Host "Starting backend on http://localhost:8000" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; if (-not (Test-Path .venv)) { python -m venv .venv }; .\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

Write-Host "Starting frontend on http://localhost:3000" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run clean 2>`$null; npm run dev"

Start-Sleep -Seconds 5
Write-Host ""
Write-Host "Open in browser: http://localhost:3000/login" -ForegroundColor Green
Write-Host "API docs:        http://localhost:8000/docs" -ForegroundColor Green
