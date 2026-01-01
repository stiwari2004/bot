-- Create deployment_approvals table for tracking code and runbook promotions
-- This table tracks all approval requests for promoting changes from dev to production

CREATE TABLE IF NOT EXISTS deployment_approvals (
    id SERIAL PRIMARY KEY,
    deployment_type VARCHAR(50) NOT NULL, -- 'code' or 'runbook'
    target_environment VARCHAR(20) NOT NULL DEFAULT 'production', -- 'production'
    reference_id INTEGER, -- runbook_id for runbook deployments, commit_sha for code deployments
    reference_name VARCHAR(500), -- Human-readable name (runbook title, branch name, etc.)
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, deployed
    requested_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    deployed_at TIMESTAMP WITH TIME ZONE,
    deployment_log TEXT,
    approval_metadata JSONB, -- Additional metadata (commit diff, runbook diff, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_deployment_approvals_type ON deployment_approvals(deployment_type);
CREATE INDEX IF NOT EXISTS idx_deployment_approvals_status ON deployment_approvals(status);
CREATE INDEX IF NOT EXISTS idx_deployment_approvals_requested_by ON deployment_approvals(requested_by);
CREATE INDEX IF NOT EXISTS idx_deployment_approvals_approved_by ON deployment_approvals(approved_by);
CREATE INDEX IF NOT EXISTS idx_deployment_approvals_created_at ON deployment_approvals(created_at);

-- Comments for documentation
COMMENT ON TABLE deployment_approvals IS 'Tracks approval requests for promoting changes from dev to production';
COMMENT ON COLUMN deployment_approvals.deployment_type IS 'Type of deployment: code or runbook';
COMMENT ON COLUMN deployment_approvals.reference_id IS 'ID of the resource being deployed (runbook_id or commit reference)';
COMMENT ON COLUMN deployment_approvals.status IS 'Approval status: pending, approved, rejected, deployed';

