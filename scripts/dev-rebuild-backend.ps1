# Clean rebuild of dev backend (fixes "image already exists" and ensures worker events route)
# Run from repo root: .\scripts\dev-rebuild-backend.ps1

$ErrorActionPreference = "Stop"
$project = "bot-dev"
$compose = "docker-compose.dev.yml"
$backendImage = "bot-dev_backend"

Write-Host "=== Dev Backend Clean Rebuild ===" -ForegroundColor Cyan
Write-Host ""

# Remove backend image so build can export successfully
Write-Host "1. Removing existing backend image (if present)..." -ForegroundColor Yellow
docker image rm ${backendImage}:latest 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "   (image not found or already removed)" }
Write-Host "   Done." -ForegroundColor Green
Write-Host ""

# Build with no cache
Write-Host "2. Building backend (--no-cache)..." -ForegroundColor Yellow
docker compose -f $compose -p $project build --no-cache backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}
Write-Host "   Done." -ForegroundColor Green
Write-Host ""

# Restart backend
Write-Host "3. Restarting backend service..." -ForegroundColor Yellow
docker compose -f $compose -p $project up -d backend
Write-Host "   Done." -ForegroundColor Green
Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Worker events route: POST /api/v1/agent/workers/events"
Write-Host "Check: curl -X POST http://localhost:8000/api/v1/agent/workers/events -H 'Content-Type: application/json' -d '{\"session_id\":1,\"event\":\"test\",\"payload\":{}}'"
