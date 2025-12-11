-- Tenant Subscriptions (License Management)
-- Tracks seats (users) and nodes (infrastructure) limits with enforcement

CREATE TABLE IF NOT EXISTS tenant_subscriptions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Subscription Limits
    max_seats INTEGER NOT NULL,
    max_nodes INTEGER NOT NULL,
    
    -- Current Usage (snapshot, updated periodically)
    current_seats INTEGER NOT NULL DEFAULT 0,
    current_nodes INTEGER NOT NULL DEFAULT 0,
    
    -- Subscription Details
    subscription_name VARCHAR(255) NULL,
    monthly_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Overage Rates (if limits exceeded)
    seat_overage_rate NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    node_overage_rate NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_enforced BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Dates
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    notes VARCHAR(500) NULL,
    created_by INTEGER REFERENCES super_admins(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscription_tenant ON tenant_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscription_status ON tenant_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscription_enforced ON tenant_subscriptions(is_enforced);

-- Subscription Usage Tracking (for reporting)
CREATE TABLE IF NOT EXISTS subscription_usage (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES tenant_subscriptions(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Peak Usage (highest during period)
    peak_seats INTEGER NOT NULL DEFAULT 0,
    peak_nodes INTEGER NOT NULL DEFAULT 0,
    
    -- Average Usage
    avg_seats NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    avg_nodes NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Overage
    seat_overage_days INTEGER NOT NULL DEFAULT 0,
    node_overage_days INTEGER NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_subscription_period ON subscription_usage(subscription_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_period ON subscription_usage(tenant_id, period_start, period_end);

COMMENT ON TABLE tenant_subscriptions IS 'Subscription/license management with seat and node limits';
COMMENT ON TABLE subscription_usage IS 'Track subscription usage over time for reporting';


