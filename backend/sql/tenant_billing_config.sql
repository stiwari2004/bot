-- Tenant Billing Configuration Tables
-- Supports flexible billing: fixed monthly + per-node + per-usage (tickets, executions, API calls, LLM tokens)

CREATE TABLE IF NOT EXISTS tenant_billing_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Fixed Monthly Cost
    fixed_monthly_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Per-Node Configuration
    per_node_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_node_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    node_count_override INTEGER NULL,
    
    -- Variable Costs - Ticket Based
    per_ticket_received_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_ticket_received_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    per_ticket_resolved_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_ticket_resolved_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Variable Costs - Execution Based
    per_execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_execution_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Variable Costs - API Based
    per_api_call_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_api_call_cost NUMERIC(10, 4) NOT NULL DEFAULT 0.0000,
    
    -- Variable Costs - LLM Based
    per_llm_token_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    per_llm_token_cost NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    
    -- Billing Period Configuration
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',
    billing_day INTEGER NOT NULL DEFAULT 1 CHECK (billing_day >= 1 AND billing_day <= 28),
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_billing_config_tenant ON tenant_billing_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_config_active ON tenant_billing_configs(is_active);

-- Tenant Billing Usage Tracking
CREATE TABLE IF NOT EXISTS tenant_billing_usage (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Usage Metrics
    tickets_received INTEGER NOT NULL DEFAULT 0,
    tickets_resolved INTEGER NOT NULL DEFAULT 0,
    execution_sessions INTEGER NOT NULL DEFAULT 0,
    api_calls INTEGER NOT NULL DEFAULT 0,
    llm_tokens INTEGER NOT NULL DEFAULT 0,  -- In thousands
    
    -- Node count (snapshot at period end)
    active_nodes INTEGER NOT NULL DEFAULT 0,
    
    -- Calculated costs
    fixed_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    node_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    ticket_received_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    ticket_resolved_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    execution_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    api_call_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    llm_token_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    total_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, calculated, invoiced, paid
    invoice_number VARCHAR(50) NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_billing_usage_tenant_period ON tenant_billing_usage(tenant_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_billing_usage_status ON tenant_billing_usage(status);

COMMENT ON TABLE tenant_billing_configs IS 'Billing configuration per tenant - allows flexible pricing models';
COMMENT ON TABLE tenant_billing_usage IS 'Track usage metrics and calculated costs per billing period';


