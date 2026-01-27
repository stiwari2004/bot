-- Migration: Create tables for priority features (Features 1-6)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

-- ============================================================================
-- Feature 2: Human-in-the-Loop Workspace
-- ============================================================================

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

-- ============================================================================
-- Feature 3: Guardrails for Automation Storms
-- ============================================================================

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

-- ============================================================================
-- Feature 4: Runbook Versioning Enhancements
-- ============================================================================

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

-- ============================================================================
-- Feature 5: Remediation Effectiveness Analytics
-- ============================================================================

-- RemediationAnalytics table
CREATE TABLE IF NOT EXISTS remediation_analytics (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Time period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    
    -- MTTR (Mean Time To Resolution)
    mttr_minutes NUMERIC(10, 2),
    
    -- Automation coverage
    automation_coverage_pct NUMERIC(5, 2),
    manual_intervention_count INTEGER NOT NULL DEFAULT 0,
    auto_resolution_count INTEGER NOT NULL DEFAULT 0,
    total_incidents INTEGER NOT NULL DEFAULT 0,
    
    -- ROI metrics
    roi_metrics JSONB,
    
    -- Top failing steps
    top_failing_steps JSONB,
    
    -- Improvement trends
    improvement_trends JSONB,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remediation_analytics_tenant ON remediation_analytics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_remediation_analytics_period ON remediation_analytics(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_remediation_analytics_type ON remediation_analytics(period_type);

COMMENT ON TABLE remediation_analytics IS 'Tracks remediation effectiveness analytics including MTTR, automation coverage, and ROI';

-- ============================================================================
-- Feature 6: Post-Incident Package
-- ============================================================================

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
