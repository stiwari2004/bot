-- Clear / cancel pending and queued execution sessions
-- Use when the queue is stuck with many pending sessions and you want to reset.
--
-- Step 1: List sessions that will be affected (run this first to review)
SELECT id, tenant_id, runbook_id, status, created_at, started_at
FROM execution_sessions
WHERE status IN ('pending', 'queued')
ORDER BY id DESC;

-- Step 2: Mark those sessions as failed and set completed_at so the UI shows them as finished
-- Uncomment and run when you are ready to clear the queue.
/*
UPDATE execution_sessions
SET status = 'failed',
    completed_at = COALESCE(completed_at, now())
WHERE status IN ('pending', 'queued');
*/

-- Optional: Also mark related agent_worker_assignments as failed (uncomment if needed)
/*
UPDATE agent_worker_assignments a
SET status = 'failed',
    failure_reason = 'Cleared by admin (pending session cleanup)',
    completed_at = COALESCE(a.completed_at, now())
FROM execution_sessions s
WHERE a.session_id = s.id
  AND s.status = 'failed'
  AND s.completed_at IS NOT NULL;
*/

-- One-shot: clear all pending/queued sessions (run in one go)
-- UPDATE execution_sessions SET status = 'failed', completed_at = COALESCE(completed_at, now()) WHERE status IN ('pending', 'queued');

-- After running the UPDATE, run the SELECT again to confirm no pending/queued remain:
-- SELECT id, status FROM execution_sessions WHERE status IN ('pending', 'queued');
