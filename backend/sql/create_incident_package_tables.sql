-- Migration: Create tables for Post-Incident Package (Feature 6)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

-- IncidentPackage table
CREATE TABLE IF NOT EXISTS incident_packages (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES execution_sessions(id) ON DELETE SET NULL,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE SET NULL,
    
    -- Incident timing
    incident_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    incident_end_time TIMESTAMP WITH TIME ZONE,
    resolution_time_minutes INTEGER,
    
    -- Analysis
    root_cause_analysis TEXT,
    timeline JSONB,
    actions_taken JSONB,
    
    -- Learning
    lessons_learned TEXT,
    recommendations TEXT,
    
    -- Compliance
    compliance_data JSONB,
    
    -- Generation metadata
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    generated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    export_format VARCHAR(20) -- 'pdf', 'markdown', 'json'
);

CREATE INDEX IF NOT EXISTS idx_incident_packages_ticket ON incident_packages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_incident_packages_session ON incident_packages(session_id);
CREATE INDEX IF NOT EXISTS idx_incident_packages_generated ON incident_packages(generated_at);

COMMENT ON TABLE incident_packages IS 'Stores comprehensive incident documentation for compliance and learning';
