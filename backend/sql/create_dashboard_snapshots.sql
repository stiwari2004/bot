-- Dashboard Snapshot Tables (CQRS-lite pattern)
-- These tables store pre-computed dashboard data for fast reads

-- Tenant Dashboard Hourly Snapshot
CREATE TABLE IF NOT EXISTS tenant_dashboard_hourly_snapshot (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    snapshot_hour TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Summary metrics
    total_users INTEGER NOT NULL DEFAULT 0,
    active_users INTEGER NOT NULL DEFAULT 0,
    total_nodes INTEGER NOT NULL DEFAULT 0,
    plan_name VARCHAR(255),
    nodes_used INTEGER NOT NULL DEFAULT 0,
    nodes_limit INTEGER NOT NULL DEFAULT 0,
    
    -- Usage metrics (current hour)
    total_executions INTEGER NOT NULL DEFAULT 0,
    total_tickets INTEGER NOT NULL DEFAULT 0,
    total_llm_tokens INTEGER NOT NULL DEFAULT 0,
    total_api_calls INTEGER NOT NULL DEFAULT 0,
    
    -- Billing metrics
    monthly_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    overage_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT idx_tenant_snapshot_tenant_hour UNIQUE (tenant_id, snapshot_hour)
);

CREATE INDEX IF NOT EXISTS idx_tenant_snapshot_hour ON tenant_dashboard_hourly_snapshot(snapshot_hour DESC);
CREATE INDEX IF NOT EXISTS idx_tenant_snapshot_tenant ON tenant_dashboard_hourly_snapshot(tenant_id, snapshot_hour DESC);

-- Platform Dashboard Daily Snapshot
CREATE TABLE IF NOT EXISTS platform_dashboard_daily_snapshot (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    
    -- Summary metrics
    total_tenants INTEGER NOT NULL DEFAULT 0,
    active_tenants INTEGER NOT NULL DEFAULT 0,
    inactive_tenants INTEGER NOT NULL DEFAULT 0,
    trial_tenants INTEGER NOT NULL DEFAULT 0,
    paid_tenants INTEGER NOT NULL DEFAULT 0,
    total_users INTEGER NOT NULL DEFAULT 0,
    active_users INTEGER NOT NULL DEFAULT 0,
    total_nodes INTEGER NOT NULL DEFAULT 0,
    
    -- Growth metrics
    tenant_growth_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,
    user_growth_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,
    node_growth_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,
    
    -- Revenue metrics (for the day)
    total_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    fixed_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    node_overage_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    llm_overage_revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
    estimated_margin_percent DECIMAL(5, 2),
    
    -- Usage metrics (for the day)
    total_executions INTEGER NOT NULL DEFAULT 0,
    total_tickets INTEGER NOT NULL DEFAULT 0,
    total_llm_tokens INTEGER NOT NULL DEFAULT 0,
    total_api_calls INTEGER NOT NULL DEFAULT 0,
    
    -- Plan distribution (JSON)
    plan_distribution JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT idx_platform_snapshot_date UNIQUE (snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_platform_snapshot_date_desc ON platform_dashboard_daily_snapshot(snapshot_date DESC);

-- Connector Health 5-minute Snapshot
CREATE TABLE IF NOT EXISTS connector_health_5min_snapshot (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    connector_id INTEGER NOT NULL,
    connector_type VARCHAR(50) NOT NULL, -- 'monitoring', 'ticketing', 'infrastructure'
    connector_name VARCHAR(255) NOT NULL,
    
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Health metrics
    status VARCHAR(20) NOT NULL, -- 'healthy', 'degraded', 'failed'
    last_success TIMESTAMP WITH TIME ZONE,
    error_rate_1h DECIMAL(5, 2) NOT NULL DEFAULT 0,
    error_rate_24h DECIMAL(5, 2) NOT NULL DEFAULT 0,
    
    -- Operational metrics
    last_check_time TIMESTAMP WITH TIME ZONE,
    response_time_ms INTEGER,
    auth_status VARCHAR(20), -- 'valid', 'expired', 'invalid'
    ingestion_lag_seconds INTEGER,
    queue_lag_seconds INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT idx_connector_snapshot_unique UNIQUE (connector_id, snapshot_time)
);

CREATE INDEX IF NOT EXISTS idx_connector_snapshot_time ON connector_health_5min_snapshot(snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_connector_snapshot_tenant ON connector_health_5min_snapshot(tenant_id, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_connector_snapshot_status ON connector_health_5min_snapshot(status, snapshot_time DESC);

-- Comments
COMMENT ON TABLE tenant_dashboard_hourly_snapshot IS 'Hourly snapshots of tenant dashboard metrics for fast reads';
COMMENT ON TABLE platform_dashboard_daily_snapshot IS 'Daily snapshots of platform-wide dashboard metrics for fast reads';
COMMENT ON TABLE connector_health_5min_snapshot IS '5-minute snapshots of connector health status for monitoring';
