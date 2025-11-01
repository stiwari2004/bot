-- Add status column to runbooks table for approval workflow
-- Run this migration after updating the model

ALTER TABLE runbooks ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft';

-- Set existing runbooks to 'approved' status for backward compatibility
UPDATE runbooks SET status = 'approved' WHERE status IS NULL OR status = 'draft';

-- Add index for faster queries by status
CREATE INDEX IF NOT EXISTS idx_runbooks_status ON runbooks(status);


