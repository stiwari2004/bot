-- PaaS: users synced from edge for billing/reporting on central
-- Run on central Resolvify only

CREATE TABLE IF NOT EXISTS paas_synced_users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    edge_user_id INTEGER,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50),
    node_details JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50) NOT NULL DEFAULT 'paas_edge',
    UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_paas_synced_users_tenant ON paas_synced_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_paas_synced_users_synced_at ON paas_synced_users(synced_at);

COMMENT ON TABLE paas_synced_users IS 'Users synced from PaaS edge for billing; upserted by tenant_id + email';
