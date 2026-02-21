-- Migration: Create table for execution command learnings (iterative refinement)
-- Stores (command, error, output, fix) from failures to improve runbooks and avoid hardcoded rules
-- Created: 2026-02-06

CREATE TABLE IF NOT EXISTS execution_command_learnings (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Execution context
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE SET NULL,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE SET NULL,
    step_number INTEGER,
    step_type VARCHAR(20),  -- precheck, main, postcheck
    
    -- Failure data (no hardcoded fixes - learned from execution)
    command TEXT NOT NULL,
    error_text TEXT,
    output_text TEXT,
    connector_type VARCHAR(32),  -- ssh, azure_bastion, local, etc.
    os_type VARCHAR(32),  -- windows, linux
    
    -- Fix applied (populated when correction succeeds)
    fix_applied TEXT,
    fix_source VARCHAR(32),  -- db_learning, perplexity
    success_after_fix BOOLEAN,
    
    -- Optional: connection context for RAG
    connection_config JSONB,
    issue_description TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_tenant ON execution_command_learnings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_connector ON execution_command_learnings(connector_type);
CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_os ON execution_command_learnings(os_type);
CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_command_hash ON execution_command_learnings(MD5(LEFT(command, 200)));
CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_success ON execution_command_learnings(success_after_fix) WHERE success_after_fix = true;
CREATE INDEX IF NOT EXISTS idx_execution_command_learnings_created ON execution_command_learnings(created_at DESC);

COMMENT ON TABLE execution_command_learnings IS 'Learned command corrections from execution failures - used for refinement without hardcoded rules';
