-- Migration: Create discovery tables (L1 assets, L2 components, L3 edges, runs, snapshots)
-- Idempotent - safe to run multiple times
-- Architecture: discovery_run first-class; assets keyed by (source, source_native_id); components/edges with confidence+evidence

-- discovery_runs: first-class run entity
CREATE TABLE IF NOT EXISTS discovery_runs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_config TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(30) NOT NULL DEFAULT 'running',
    stage_log TEXT,
    artifact_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_tenant ON discovery_runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_started ON discovery_runs(started_at);

-- discovery_assets: L1 asset inventory (identity by source + source_native_id; IPs are attributes)
CREATE TABLE IF NOT EXISTS discovery_assets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_native_id VARCHAR(512) NOT NULL,
    fingerprint VARCHAR(512),
    primary_ip VARCHAR(45),
    ips TEXT,
    name VARCHAR(255),
    tags TEXT,
    current_run_id INTEGER REFERENCES discovery_runs(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_discovery_asset_tenant_source_native UNIQUE (tenant_id, source, source_native_id)
);
CREATE INDEX IF NOT EXISTS idx_discovery_assets_tenant ON discovery_assets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_discovery_assets_source ON discovery_assets(source);
CREATE INDEX IF NOT EXISTS idx_discovery_assets_primary_ip ON discovery_assets(primary_ip);
CREATE INDEX IF NOT EXISTS idx_discovery_assets_current_run ON discovery_assets(current_run_id);

-- discovery_components: L2 component inventory (service endpoints with confidence + evidence)
CREATE TABLE IF NOT EXISTS discovery_components (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES discovery_assets(id) ON DELETE CASCADE,
    run_id INTEGER NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    component_type VARCHAR(80) NOT NULL,
    bind_address VARCHAR(255),
    port INTEGER,
    meta TEXT,
    confidence VARCHAR(20),
    evidence TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_components_tenant ON discovery_components(tenant_id);
CREATE INDEX IF NOT EXISTS idx_discovery_components_asset ON discovery_components(asset_id);
CREATE INDEX IF NOT EXISTS idx_discovery_components_run ON discovery_components(run_id);

-- discovery_edges: L3 dependency mapping (endpoint to endpoint with confidence + evidence)
CREATE TABLE IF NOT EXISTS discovery_edges (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id INTEGER NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    from_asset_id INTEGER NOT NULL REFERENCES discovery_assets(id) ON DELETE CASCADE,
    from_component_id INTEGER REFERENCES discovery_components(id) ON DELETE CASCADE,
    to_asset_id INTEGER NOT NULL REFERENCES discovery_assets(id) ON DELETE CASCADE,
    to_component_id INTEGER REFERENCES discovery_components(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,
    meta TEXT,
    confidence VARCHAR(20),
    evidence TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_edges_tenant ON discovery_edges(tenant_id);
CREATE INDEX IF NOT EXISTS idx_discovery_edges_run ON discovery_edges(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_edges_from_asset ON discovery_edges(from_asset_id);
CREATE INDEX IF NOT EXISTS idx_discovery_edges_to_asset ON discovery_edges(to_asset_id);

-- discovery_asset_snapshots: optional history snapshot per run
CREATE TABLE IF NOT EXISTS discovery_asset_snapshots (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES discovery_assets(id) ON DELETE CASCADE,
    snapshot TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovery_asset_snapshots_run ON discovery_asset_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_asset_snapshots_asset ON discovery_asset_snapshots(asset_id);

COMMENT ON TABLE discovery_runs IS 'First-class discovery run; deterministic and debuggable';
COMMENT ON TABLE discovery_assets IS 'L1 asset inventory; identity by (source, source_native_id)';
COMMENT ON TABLE discovery_components IS 'L2 component inventory; service endpoints with confidence and evidence';
COMMENT ON TABLE discovery_edges IS 'L3 dependency mapping; endpoint to endpoint with confidence and evidence';
