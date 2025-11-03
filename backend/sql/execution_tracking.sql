-- Execution tracking schema for manual runbook execution
-- This enables Phase 1 "Assistant Mode" where operators manually execute runbooks with system guidance

-- Manual execution sessions (when operator starts executing a runbook)
CREATE TABLE IF NOT EXISTS execution_sessions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    issue_description TEXT,
    status VARCHAR(20) DEFAULT 'in_progress', -- in_progress, completed, failed, abandoned
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_duration_minutes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track individual step completion
CREATE TABLE IF NOT EXISTS execution_steps (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type VARCHAR(20), -- precheck, main, postcheck
    command TEXT,
    completed BOOLEAN DEFAULT FALSE,
    success BOOLEAN,
    output TEXT,
    notes TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Execution feedback
CREATE TABLE IF NOT EXISTS execution_feedback (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE CASCADE,
    was_successful BOOLEAN NOT NULL,
    issue_resolved BOOLEAN,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    suggestions TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_execution_sessions_runbook ON execution_sessions(runbook_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_status ON execution_sessions(status);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_tenant ON execution_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_execution_steps_session ON execution_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_execution_feedback_session ON execution_feedback(session_id);

-- Add comments for documentation
COMMENT ON TABLE execution_sessions IS 'Tracks manual execution sessions when operators execute runbooks';
COMMENT ON TABLE execution_steps IS 'Tracks individual step completion within an execution session';
COMMENT ON TABLE execution_feedback IS 'Stores user feedback after runbook execution';

