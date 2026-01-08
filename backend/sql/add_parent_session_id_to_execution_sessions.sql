-- Add parent_session_id to execution_sessions for self-healing remediation tracking
ALTER TABLE execution_sessions 
ADD COLUMN IF NOT EXISTS parent_session_id INTEGER REFERENCES execution_sessions(id) ON DELETE SET NULL;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_execution_sessions_parent ON execution_sessions(parent_session_id) 
    WHERE parent_session_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN execution_sessions.parent_session_id IS 'Parent execution session ID for self-healing remediation sessions';

