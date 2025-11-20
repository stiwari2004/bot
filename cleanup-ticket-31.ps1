# Cleanup ticket 31 - remove archived runbook references
$containerName = "bot-postgres-1"

Write-Host "Cleaning up ticket 31..." -ForegroundColor Cyan

# Remove matched_runbooks and runbook_id from ticket 31
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "UPDATE tickets SET meta_data = COALESCE(meta_data, '{}'::jsonb) - 'matched_runbooks' - 'runbook_id' WHERE id = 31 AND tenant_id = 1;"

# Verify
Write-Host "`nVerifying ticket 31..." -ForegroundColor Yellow
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "SELECT id, title, meta_data->'matched_runbooks' as matched_runbooks, meta_data->>'runbook_id' as runbook_id FROM tickets WHERE id = 31;"

Write-Host "`nDone! Please refresh the ticket in the UI." -ForegroundColor Green




