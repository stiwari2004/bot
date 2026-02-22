-- Migration: Create central_runbooks table for Resolvify-hosted library
-- Idempotent - safe to run multiple times
-- Manual import from library copies into tenant runbooks

CREATE TABLE IF NOT EXISTS central_runbooks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    body_md TEXT NOT NULL,
    meta_data TEXT,
    category VARCHAR(100),
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_central_runbooks_category ON central_runbooks(category);
CREATE INDEX IF NOT EXISTS idx_central_runbooks_active ON central_runbooks(is_active);

COMMENT ON TABLE central_runbooks IS 'Resolvify-hosted runbook library for import into tenant runbooks';
