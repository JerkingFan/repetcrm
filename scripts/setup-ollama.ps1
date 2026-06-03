# RepetCRM: Ollama setup (light model qwen2.5:3b)
$ErrorActionPreference = "Stop"
$model = "qwen2.5:3b"

Write-Host "=== RepetCRM: Ollama setup ===" -ForegroundColor Cyan

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host ""
    Write-Host "Ollama not found in PATH." -ForegroundColor Yellow
    Write-Host "1. Download: https://ollama.com/download/windows"
    Write-Host "2. Install and restart terminal"
    Write-Host "3. Run this script again"
    Write-Host ""
    Write-Host "Alternative (embedded model ~500 MB):"
    Write-Host "  cd backend"
    Write-Host "  ..\scripts\download-local-model.ps1"
    exit 1
}

Write-Host "Ollama found: $($ollama.Source)" -ForegroundColor Green

try {
    $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
} catch {
    Write-Host "Starting Ollama serve..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
    $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 10
}

$hasModel = $tags.models | Where-Object { $_.name -like "$model*" }
if ($hasModel) {
    Write-Host "Model $model already installed." -ForegroundColor Green
} else {
    Write-Host "Pulling model $model (about 2 GB)..." -ForegroundColor Cyan
    ollama pull $model
}

Write-Host ""
Write-Host "Done. Homework AI is ready." -ForegroundColor Green
Write-Host "Model: $model"
Write-Host "API: http://localhost:11434"
