# PowerShell script to check ticket 31 and clean up runbook references
# This avoids Docker command hanging issues

$containerName = "bot-postgres-1"

Write-Host "Checking ticket 31..." -ForegroundColor Cyan

# Check if container is running
$containerStatus = docker ps --filter "name=$containerName" --format "{{.Status}}"
if (-not $containerStatus) {
    Write-Host "Error: Container $containerName is not running!" -ForegroundColor Red
    exit 1
}

Write-Host "Container is running. Querying database..." -ForegroundColor Green

# Query ticket 31
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "SELECT id, title, meta_data FROM tickets WHERE id = 31 AND tenant_id = 1;" 2>&1

Write-Host "`nChecking for runbook references in meta_data..." -ForegroundColor Cyan
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "SELECT id, title, meta_data->'matched_runbooks' as matched_runbooks FROM tickets WHERE id = 31 AND tenant_id = 1;" 2>&1


