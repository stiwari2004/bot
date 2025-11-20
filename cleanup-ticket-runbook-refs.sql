-- Cleanup script to remove archived runbook references from tickets
-- This removes runbook IDs from ticket meta_data.matched_runbooks

-- First, check what tickets have runbook references
SELECT 
    t.id,
    t.title,
    t.meta_data->'matched_runbooks' as matched_runbooks,
    jsonb_array_length(COALESCE(t.meta_data->'matched_runbooks', '[]'::jsonb)) as runbook_count
FROM tickets t
WHERE t.tenant_id = 1
  AND t.meta_data IS NOT NULL
  AND t.meta_data->'matched_runbooks' IS NOT NULL
  AND jsonb_array_length(COALESCE(t.meta_data->'matched_runbooks', '[]'::jsonb)) > 0
ORDER BY t.id;

-- Check which runbooks are archived
SELECT id, title, is_active FROM runbooks WHERE tenant_id = 1 AND is_active = 'archived';

-- Clean up: Remove archived runbook references from ticket meta_data
-- This updates tickets to remove any runbook IDs that are archived
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

-- Also remove direct runbook_id references if present
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

-- Verify cleanup
SELECT 
    t.id,
    t.title,
    t.meta_data->'matched_runbooks' as matched_runbooks
FROM tickets t
WHERE t.tenant_id = 1
  AND t.meta_data IS NOT NULL
ORDER BY t.id;

