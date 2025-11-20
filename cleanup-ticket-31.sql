-- Simple cleanup for ticket 31 - remove any archived runbook references
UPDATE tickets 
SET meta_data = COALESCE(meta_data, '{}'::jsonb) - 'matched_runbooks' - 'runbook_id'
WHERE id = 31 AND tenant_id = 1;

-- Verify
SELECT id, title, meta_data->'matched_runbooks' as matched_runbooks, meta_data->>'runbook_id' as runbook_id 
FROM tickets 
WHERE id = 31;


