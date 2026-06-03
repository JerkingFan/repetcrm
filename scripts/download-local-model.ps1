# RepetCRM: download embedded Qwen2.5-Math-1.5B-Instruct
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\backend

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host "=== Installing AI dependencies ===" -ForegroundColor Cyan
.\.venv\Scripts\pip install torch transformers accelerate safetensors huggingface-hub -q

Write-Host "=== Downloading Qwen2.5-1.5B-Instruct (~3 GB) ===" -ForegroundColor Cyan
.\.venv\Scripts\python scripts\download_local_model.py

Write-Host ""
Write-Host "Done. Restart the backend." -ForegroundColor Green
