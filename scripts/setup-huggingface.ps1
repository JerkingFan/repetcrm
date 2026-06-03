# RepetCRM: Hugging Face Qwen (без Ollama)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\backend

Write-Host "=== RepetCRM: Hugging Face AI ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) { python -m venv .venv }

Write-Host "Installing dependencies..." -ForegroundColor Yellow
.\.venv\Scripts\pip install torch transformers accelerate safetensors huggingface-hub -q

$smartDir = "models\Qwen2.5-1.5B-Instruct\model.safetensors"
if (Test-Path $smartDir) {
    Write-Host "Model ready: Qwen2.5-1.5B-Instruct" -ForegroundColor Green
} else {
    Write-Host "Downloading Qwen2.5-1.5B-Instruct (~3 GB)..." -ForegroundColor Cyan
    .\.venv\Scripts\python scripts\download_local_model.py smart
}

Write-Host ""
Write-Host "Done. Start backend:" -ForegroundColor Green
Write-Host "  ..\scripts\start-backend.ps1"
Write-Host ""
Write-Host "Other models:" -ForegroundColor Yellow
Write-Host "  upgrade-model.ps1     — 1.5B Instruct (recommended)"
Write-Host "  download_local_model.py 3b  — 3B, slowest/smartest"
Write-Host "  download_local_model.py math — math-only 1.5B"
