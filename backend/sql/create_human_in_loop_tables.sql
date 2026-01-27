-- Migration: Create tables for Human-in-the-Loop Workspace (Feature 2)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

-- ParameterTuning table
CREATE TABLE IF NOT EXISTS parameter_tunings (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES execution_sessions(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES execution_steps(id) ON DELETE CASCADE,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    
    -- Parameter details
    parameter_name VARCHAR(255) NOT NULL,
    parameter_type VARCHAR(50),
    original_value TEXT,
    tuned_value TEXT NOT NULL,
    
    -- Tuning metadata
    tuned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    tuned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    reason TEXT,
    
    -- Effectiveness tracking
    effectiveness_score NUMERIC(5, 2),
    execution_success VARCHAR(10),
    notes TEXT,
    
    -- Indexes
    CONSTRAINT idx_parameter_tunings_session UNIQUE NULLS NOT DISTINCT (session_id),
    CONSTRAINT idx_parameter_tunings_step UNIQUE NULLS NOT DISTINCT (step_id),
    CONSTRAINT idx_parameter_tunings_runbook UNIQUE NULLS NOT DISTINCT (runbook_id),
    CONSTRAINT idx_parameter_tunings_tuned_at UNIQUE NULLS NOT DISTINCT (tuned_at)
);

CREATE INDEX IF NOT EXISTS idx_parameter_tunings_session ON parameter_tunings(session_id);
CREATE INDEX IF NOT EXISTS idx_parameter_tunings_step ON parameter_tunings(step_id);
CREATE INDEX IF NOT EXISTS idx_parameter_tunings_runbook ON parameter_tunings(runbook_id);
CREATE INDEX IF NOT EXISTS idx_parameter_tunings_tuned_at ON parameter_tunings(tuned_at);

COMMENT ON TABLE parameter_tunings IS 'Tracks parameter tuning/modifications made during execution approval';

-- ApprovalAudit table
CREATE TABLE IF NOT EXISTS approval_audits (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES execution_sessions(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES execution_steps(id) ON DELETE CASCADE,
    
    -- Action details
    action VARCHAR(50) NOT NULL, -- 'approve', 'reject', 'modify', 'defer'
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Decision details
    reason TEXT,
    modified_parameters JSONB,
    original_parameters JSONB,
    
    -- Outcome tracking
    outcome VARCHAR(20), -- 'success', 'failure', 'partial', 'pending'
    outcome_notes TEXT,
    
    -- Additional metadata
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_approval_audits_session ON approval_audits(session_id);
CREATE INDEX IF NOT EXISTS idx_approval_audits_step ON approval_audits(step_id);
CREATE INDEX IF NOT EXISTS idx_approval_audits_user ON approval_audits(user_id);
CREATE INDEX IF NOT EXISTS idx_approval_audits_action ON approval_audits(action);
CREATE INDEX IF NOT EXISTS idx_approval_audits_timestamp ON approval_audits(timestamp);

COMMENT ON TABLE approval_audits IS 'Tracks all approval-related actions for audit and compliance';
