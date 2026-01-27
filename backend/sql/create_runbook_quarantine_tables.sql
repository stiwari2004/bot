-- Migration: Create tables for Runbook Quarantine (Feature 3)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

-- RunbookQuarantine table
CREATE TABLE IF NOT EXISTS runbook_quarantines (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    runbook_id INTEGER NOT NULL REFERENCES runbooks(id) ON DELETE CASCADE,
    runbook_version_id INTEGER REFERENCES runbook_versions(id) ON DELETE SET NULL,
    
    -- Quarantine details
    quarantine_reason VARCHAR(50) NOT NULL, -- 'auto_quarantine', 'manual', 'review_flag'
    failure_count INTEGER NOT NULL DEFAULT 0,
    
    -- Failure pattern tracking
    failure_pattern JSONB,
    
    -- Quarantine metadata
    quarantined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    quarantined_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Review status
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending_review', -- 'pending_review', 'reviewed', 'auto_released'
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    
    -- Auto-release
    auto_release_after TIMESTAMP WITH TIME ZONE,
    auto_release_reason VARCHAR(255),
    
    -- Additional metadata
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_runbook_quarantines_runbook ON runbook_quarantines(runbook_id);
CREATE INDEX IF NOT EXISTS idx_runbook_quarantines_version ON runbook_quarantines(runbook_version_id);
CREATE INDEX IF NOT EXISTS idx_runbook_quarantines_status ON runbook_quarantines(review_status);
CREATE INDEX IF NOT EXISTS idx_runbook_quarantines_tenant ON runbook_quarantines(tenant_id);
CREATE INDEX IF NOT EXISTS idx_runbook_quarantines_quarantined_at ON runbook_quarantines(quarantined_at);

COMMENT ON TABLE runbook_quarantines IS 'Tracks runbook quarantine status to prevent automation storms';
