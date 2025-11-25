-- Migration: Add ticket lifecycle tracking columns
-- These columns were added to support precheck analysis and resolution verification

-- Add precheck analysis columns
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS precheck_analysis_result JSONB,
ADD COLUMN IF NOT EXISTS precheck_executed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS precheck_status VARCHAR(50);

-- Add resolution verification columns
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS resolution_verified_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS external_ticket_updated_at TIMESTAMP WITH TIME ZONE;

-- Add escalation reason column
ALTER TABLE tickets 
ADD COLUMN IF NOT EXISTS escalation_reason TEXT;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tickets_precheck_executed_at ON tickets(precheck_executed_at);
CREATE INDEX IF NOT EXISTS idx_tickets_resolution_verified_at ON tickets(resolution_verified_at);
CREATE INDEX IF NOT EXISTS idx_tickets_external_ticket_updated_at ON tickets(external_ticket_updated_at);
CREATE INDEX IF NOT EXISTS idx_tickets_precheck_status ON tickets(precheck_status);



