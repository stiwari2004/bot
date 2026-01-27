-- Migration: Enhance Runbook Versioning tables (Feature 4)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

-- Add new columns to runbook_versions table
DO $$ 
BEGIN
    -- Add diff_summary column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'runbook_versions' AND column_name = 'diff_summary'
    ) THEN
        ALTER TABLE runbook_versions ADD COLUMN diff_summary JSONB;
    END IF;
    
    -- Add rollback_reason column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'runbook_versions' AND column_name = 'rollback_reason'
    ) THEN
        ALTER TABLE runbook_versions ADD COLUMN rollback_reason TEXT;
    END IF;
    
    -- Add deployment_approval_id column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'runbook_versions' AND column_name = 'deployment_approval_id'
    ) THEN
        ALTER TABLE runbook_versions ADD COLUMN deployment_approval_id INTEGER REFERENCES deployment_approvals(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_runbook_versions_deployment_approval ON runbook_versions(deployment_approval_id);
    END IF;
END $$;

COMMENT ON COLUMN runbook_versions.diff_summary IS 'Stores diff summary between versions';
COMMENT ON COLUMN runbook_versions.rollback_reason IS 'Reason for rollback if this version was rolled back';
COMMENT ON COLUMN runbook_versions.deployment_approval_id IS 'Links to deployment approval for promotion workflow';
