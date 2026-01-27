-- Migration: Create tables for Remediation Effectiveness Analytics (Feature 5)
-- This migration is idempotent - safe to run multiple times
-- Created: 2026-01-27

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
