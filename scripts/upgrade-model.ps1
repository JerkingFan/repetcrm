# Скачать умную модель Qwen2.5-1.5B-Instruct (~3 ГБ) и переключить бэкенд
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot + "\..\backend"
Set-Location $root

Write-Host "=== RepetCRM: умная модель 1.5B ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) { python -m venv .venv }

Write-Host "Зависимости..." -ForegroundColor Yellow
.\.venv\Scripts\pip install torch transformers accelerate safetensors huggingface-hub -q

$target = "models\Qwen2.5-1.5B-Instruct\model.safetensors"
if (Test-Path $target) {
    Write-Host "Qwen2.5-1.5B-Instruct уже скачана." -ForegroundColor Green
} else {
    Write-Host "Скачивание Qwen2.5-1.5B-Instruct (~3 ГБ)..." -ForegroundColor Cyan
    .\.venv\Scripts\python scripts\download_local_model.py smart
}

$envPath = ".env"
$envLines = @(
    "LOCAL_MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct",
    "LOCAL_MODEL_DIR=./models/Qwen2.5-1.5B-Instruct",
    "LOCAL_MODEL_MAX_TOKENS=1200",
    "LOCAL_TRANSFORMERS_TIMEOUT_SEC=900",
    "LOCAL_ENABLE_TRANSFORMERS=true",
    "AI_USE_OLLAMA=false"
)
if (Test-Path $envPath) {
    $content = Get-Content $envPath -Raw
    foreach ($line in $envLines) {
        $key = ($line -split "=")[0]
        if ($content -match "(?m)^$key=") {
            $content = $content -replace "(?m)^$key=.*", $line
        } else {
            $content += "`n$line"
        }
    }
    Set-Content $envPath $content.TrimEnd() -Encoding UTF8
} else {
    Copy-Item ".env.example" $envPath -ErrorAction SilentlyContinue
    Add-Content $envPath "`n" + ($envLines -join "`n")
    foreach ($line in $envLines) {
        $key = ($line -split "=")[0]
        (Get-Content $envPath) -replace "(?m)^$key=.*", $line | Set-Content $envPath
    }
}

Write-Host ""
Write-Host "Готово. Перезапустите бэкенд (scripts\start-backend.ps1)" -ForegroundColor Green
Write-Host "Пока 1.5B качается — будет использована Math-1.5B или 0.5B из models\" -ForegroundColor Yellow
