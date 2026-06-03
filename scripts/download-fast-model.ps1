$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\backend
if (-not (Test-Path ".venv")) { python -m venv .venv }
Write-Host "=== Fast AI model (~500 MB) ===" -ForegroundColor Cyan
.\.venv\Scripts\pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu huggingface-hub -q
.\.venv\Scripts\python scripts\download_fast_model.py
Write-Host "Done. Restart backend." -ForegroundColor Green
