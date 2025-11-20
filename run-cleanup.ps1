# PowerShell script to run cleanup SQL for ticket runbook references
$containerName = "bot-postgres-1"

Write-Host "Running cleanup script to remove archived runbook references from tickets..." -ForegroundColor Cyan

# Check which runbooks are archived
Write-Host "`nChecking archived runbooks..." -ForegroundColor Yellow
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "SELECT id, title, is_active FROM runbooks WHERE tenant_id = 1 AND is_active = 'archived';"

# Clean up: Remove archived runbook references from ticket meta_data
Write-Host "`nCleaning up ticket references..." -ForegroundColor Yellow
docker exec $containerName psql -U postgres -d troubleshooting_ai -c @"
UPDATE tickets t
SET meta_data = jsonb_set(
    COALESCE(t.meta_data, '{}'::jsonb),
    '{matched_runbooks}',
    (
        SELECT jsonb_agg(rb)
        FROM jsonb_array_elements(COALESCE(t.meta_data->'matched_runbooks', '[]'::jsonb)) rb
        WHERE NOT EXISTS (
            SELECT 1 
            FROM runbooks r 
            WHERE r.id = (rb->>'id')::int 
            AND r.tenant_id = 1 
            AND r.is_active = 'archived'
        )
    )
)
WHERE t.tenant_id = 1
  AND t.meta_data IS NOT NULL
  AND t.meta_data->'matched_runbooks' IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(t.meta_data->'matched_runbooks') rb
      WHERE EXISTS (
          SELECT 1 
          FROM runbooks r 
          WHERE r.id = (rb->>'id')::int 
          AND r.tenant_id = 1 
          AND r.is_active = 'archived'
      )
  );
"@

# Also remove direct runbook_id references
Write-Host "`nRemoving direct runbook_id references..." -ForegroundColor Yellow
docker exec $containerName psql -U postgres -d troubleshooting_ai -c @"
UPDATE tickets t
SET meta_data = t.meta_data - 'runbook_id'
WHERE t.tenant_id = 1
  AND t.meta_data IS NOT NULL
  AND t.meta_data->>'runbook_id' IS NOT NULL
  AND EXISTS (
      SELECT 1 
      FROM runbooks r 
      WHERE r.id = (t.meta_data->>'runbook_id')::int 
      AND r.tenant_id = 1 
      AND r.is_active = 'archived'
  );
"@

# Verify ticket 31
Write-Host "`nVerifying ticket 31..." -ForegroundColor Yellow
docker exec $containerName psql -U postgres -d troubleshooting_ai -c "SELECT id, title, meta_data->'matched_runbooks' as matched_runbooks, meta_data->>'runbook_id' as runbook_id FROM tickets WHERE id = 31 AND tenant_id = 1;"

Write-Host "`nCleanup complete!" -ForegroundColor Green


