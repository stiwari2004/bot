-- Execution tracking schema for manual runbook execution
-- This enables Phase 1 "Assistant Mode" where operators manually execute runbooks with system guidance

-- Manual execution sessions (when operator starts executing a runbook)
CREATE TABLE IF NOT EXISTS execution_sessions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    issue_description TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- pending, waiting_approval, in_progress, completed, failed, abandoned, escalated
    current_step INTEGER DEFAULT 0,
    waiting_for_approval BOOLEAN DEFAULT FALSE,
    approval_step_number INTEGER,
    transport_channel VARCHAR(32) DEFAULT 'redis',
    last_event_seq VARCHAR(64),
    assignment_retry_count INTEGER DEFAULT 0,
    sandbox_profile VARCHAR(64),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track individual step completion
CREATE TABLE IF NOT EXISTS execution_steps (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type VARCHAR(20), -- precheck, main, postcheck
    command TEXT,
    rollback_command TEXT,
    requires_approval BOOLEAN DEFAULT FALSE,
    approved BOOLEAN,
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    sandbox_profile VARCHAR(64),
    blast_radius VARCHAR(32),
    approval_policy VARCHAR(64),
    command_payload JSONB,
    rollback_payload JSONB,
    credentials_used JSONB,
    completed BOOLEAN DEFAULT FALSE,
    success BOOLEAN,
    output TEXT,
    error TEXT,
    notes TEXT,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
CREATE INDEX IF NOT EXISTS idx_execution_sessions_ticket ON execution_sessions(ticket_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_waiting ON execution_sessions(waiting_for_approval);
CREATE INDEX IF NOT EXISTS idx_execution_steps_session ON execution_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_execution_steps_approval ON execution_steps(requires_approval);
CREATE INDEX IF NOT EXISTS idx_execution_feedback_session ON execution_feedback(session_id);

-- Event stream table for replay/diagnostics
CREATE TABLE IF NOT EXISTS execution_events (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE CASCADE,
    step_number INTEGER,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    stream_id VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_execution_events_session ON execution_events(session_id);
CREATE INDEX IF NOT EXISTS idx_execution_events_type ON execution_events(event_type);
CREATE INDEX IF NOT EXISTS idx_execution_events_stream ON execution_events(stream_id);

-- Worker assignment tracking
CREATE TABLE IF NOT EXISTS agent_worker_assignments (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE CASCADE,
    worker_id VARCHAR(128),
    status VARCHAR(32) DEFAULT 'pending',
    attempt INTEGER DEFAULT 0,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_reason TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worker_assignments_worker ON agent_worker_assignments(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_assignments_status ON agent_worker_assignments(status);

-- Backwards-compatible ALTERs for existing databases
ALTER TABLE execution_sessions
    ADD COLUMN IF NOT EXISTS transport_channel VARCHAR(32) DEFAULT 'redis',
    ADD COLUMN IF NOT EXISTS last_event_seq VARCHAR(64),
    ADD COLUMN IF NOT EXISTS assignment_retry_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sandbox_profile VARCHAR(64);

ALTER TABLE execution_steps
    ADD COLUMN IF NOT EXISTS sandbox_profile VARCHAR(64),
    ADD COLUMN IF NOT EXISTS blast_radius VARCHAR(32),
    ADD COLUMN IF NOT EXISTS approval_policy VARCHAR(64),
    ADD COLUMN IF NOT EXISTS command_payload JSONB,
    ADD COLUMN IF NOT EXISTS rollback_payload JSONB,
    ADD COLUMN IF NOT EXISTS credentials_used JSONB;

-- Add comments for documentation
COMMENT ON TABLE execution_sessions IS 'Tracks manual execution sessions when operators execute runbooks';
COMMENT ON TABLE execution_steps IS 'Tracks individual step completion within an execution session';
COMMENT ON TABLE execution_feedback IS 'Stores user feedback after runbook execution';
COMMENT ON TABLE execution_events IS 'Stores orchestrator events for replay and diagnostics';
COMMENT ON TABLE agent_worker_assignments IS 'Tracks worker assignment attempts for execution sessions';

