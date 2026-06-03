# Архив проекта для загрузки на сервер (без тяжёлых папок)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root "repetcrm-deploy.zip"

if (Test-Path $out) { Remove-Item $out -Force }

$items = @(
    "backend\app",
    "backend\requirements-prod.txt",
    "backend\Dockerfile.prod",
    "backend\.env.example",
    "frontend\app",
    "frontend\components",
    "frontend\lib",
    "frontend\public",
    "frontend\package.json",
    "frontend\package-lock.json",
    "frontend\next.config.ts",
    "frontend\tsconfig.json",
    "frontend\tailwind.config.ts",
    "frontend\postcss.config.mjs",
    "frontend\Dockerfile",
    "frontend\.env.local.example",
    "deploy",
    "docker-compose.prod.yml",
    ".env.production.example",
    "README.md",
    "landing"
)

$temp = Join-Path $env:TEMP "repetcrm-pack"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
New-Item -ItemType Directory -Path $temp | Out-Null

foreach ($rel in $items) {
    $src = Join-Path $root $rel
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $temp $rel
    $parent = Split-Path $dst -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item $src $dst -Recurse -Force
}

Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $out -Force
Remove-Item $temp -Recurse -Force
Write-Host "Done: $out" -ForegroundColor Green
