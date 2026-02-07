-- Add current_discovery_run_id to tenants for "current" vs "history" lifecycle
-- Idempotent
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS current_discovery_run_id INTEGER REFERENCES discovery_runs(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_tenants_current_discovery_run ON tenants(current_discovery_run_id);
