-- Cleanup script to abandon stuck execution sessions
-- Run this if you have execution sessions stuck in "in_progress" state
-- that reference archived or deleted runbooks

-- First, check what sessions are stuck
SELECT 
    es.id, 
    es.runbook_id, 
    es.status, 
    es.ticket_id, 
    es.created_at,
    r.title as runbook_title,
    r.is_active as runbook_status
FROM execution_sessions es
LEFT JOIN runbooks r ON es.runbook_id = r.id
WHERE es.tenant_id = 1 
  AND es.status IN ('in_progress', 'pending')
ORDER BY es.created_at DESC;

-- Abandon stuck sessions (uncomment to execute)
-- UPDATE execution_sessions 
-- SET status = 'abandoned', 
--     completed_at = NOW()
-- WHERE tenant_id = 1 
--   AND status IN ('in_progress', 'pending')
--   AND id IN (1, 2);  -- Replace with actual session IDs




