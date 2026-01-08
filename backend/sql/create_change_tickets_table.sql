-- Create change_tickets table for tracking change windows
CREATE TABLE IF NOT EXISTS change_tickets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    change_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'scheduled',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    affected_services TEXT[],
    affected_environments TEXT[],
    suppression_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, external_id, source)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_change_tickets_tenant ON change_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_change_tickets_time ON change_tickets(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_change_tickets_status ON change_tickets(status);
CREATE INDEX IF NOT EXISTS idx_change_tickets_active ON change_tickets(start_time, end_time) 
    WHERE status IN ('scheduled', 'in_progress');
CREATE INDEX IF NOT EXISTS idx_change_tickets_external ON change_tickets(tenant_id, external_id, source);

-- Add comments for documentation
COMMENT ON TABLE change_tickets IS 'Change tickets from ticketing tools (ServiceNow, ManageEngine) for suppressing tickets during change windows';
COMMENT ON COLUMN change_tickets.external_id IS 'Change ticket ID from external ticketing tool';
COMMENT ON COLUMN change_tickets.source IS 'Source ticketing tool (servicenow, manageengine, etc.)';
COMMENT ON COLUMN change_tickets.change_type IS 'Type of change (standard, emergency, normal)';
COMMENT ON COLUMN change_tickets.status IS 'Change status (scheduled, in_progress, completed, cancelled)';
COMMENT ON COLUMN change_tickets.affected_services IS 'Array of service names affected by this change';
COMMENT ON COLUMN change_tickets.affected_environments IS 'Array of environments affected by this change';
COMMENT ON COLUMN change_tickets.suppression_enabled IS 'Whether ticket suppression is enabled for this change window';

