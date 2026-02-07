-- Add current_discovery_run_id to tenants for "current" vs "history" lifecycle
-- Idempotent. Column only (no FK) so this runs even if discovery_runs does not exist yet.
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS current_discovery_run_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_tenants_current_discovery_run ON tenants(current_discovery_run_id);
