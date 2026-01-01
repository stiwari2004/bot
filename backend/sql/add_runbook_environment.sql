-- Add environment tracking to runbooks table
-- This migration adds support for dev/production environment separation

-- Add environment column (default to 'production' for existing runbooks)
ALTER TABLE runbooks ADD COLUMN IF NOT EXISTS environment VARCHAR(20) DEFAULT 'production';

-- Add promoted_from_id to track which dev runbook was promoted
ALTER TABLE runbooks ADD COLUMN IF NOT EXISTS promoted_from_id INTEGER REFERENCES runbooks(id) ON DELETE SET NULL;

-- Add promoted_at timestamp for audit trail
ALTER TABLE runbooks ADD COLUMN IF NOT EXISTS promoted_at TIMESTAMP WITH TIME ZONE;

-- Add index for faster queries by environment
CREATE INDEX IF NOT EXISTS idx_runbooks_environment ON runbooks(environment);

-- Add index for promoted_from_id lookups
CREATE INDEX IF NOT EXISTS idx_runbooks_promoted_from ON runbooks(promoted_from_id);

-- Update existing runbooks to have 'production' environment (if not already set)
UPDATE runbooks SET environment = 'production' WHERE environment IS NULL OR environment = '';

-- Add comment for documentation
COMMENT ON COLUMN runbooks.environment IS 'Environment where runbook exists: dev or production';
COMMENT ON COLUMN runbooks.promoted_from_id IS 'Reference to dev runbook that was promoted to create this production runbook';
COMMENT ON COLUMN runbooks.promoted_at IS 'Timestamp when runbook was promoted from dev to production';

