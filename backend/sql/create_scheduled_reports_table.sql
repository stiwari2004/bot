-- Migration: Create scheduled_reports table for automated report generation
-- This migration is idempotent - safe to run multiple times

-- Create enum types if they don't exist
DO $$ BEGIN
    CREATE TYPE reportfrequency AS ENUM ('daily', 'weekly', 'monthly', 'custom');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE reportformat AS ENUM ('pdf', 'csv', 'excel');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE reporttype AS ENUM ('overview', 'tenants', 'revenue', 'usage', 'custom');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create scheduled_reports table
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Report configuration
    report_type reporttype NOT NULL DEFAULT 'custom',
    format reportformat NOT NULL DEFAULT 'pdf',
    
    -- Filters and parameters (stored as JSONB for better querying)
    filters JSONB DEFAULT '{}',
    
    -- Scheduling
    frequency reportfrequency NOT NULL,
    schedule_config JSONB DEFAULT '{}',
    
    -- Recipients
    recipients JSONB NOT NULL DEFAULT '[]',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    
    -- Owner
    created_by_id INTEGER NOT NULL REFERENCES super_admins(id) ON DELETE CASCADE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_created_by_id ON scheduled_reports(created_by_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_is_active ON scheduled_reports(is_active);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next_run_at ON scheduled_reports(next_run_at) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_created_at ON scheduled_reports(created_at DESC);

-- Add comment to table
COMMENT ON TABLE scheduled_reports IS 'Stores scheduled report configurations for automated report generation and email delivery';
