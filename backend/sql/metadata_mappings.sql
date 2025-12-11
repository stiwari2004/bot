-- Metadata mappings table for learned input extraction rules
-- This table stores mappings learned from user input to improve automatic extraction

CREATE TABLE IF NOT EXISTS metadata_mappings (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    input_name VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    metadata_path VARCHAR(255) NOT NULL,
    confidence FLOAT DEFAULT 0.8,
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_mapping_source_input ON metadata_mappings(source, input_name);
CREATE INDEX IF NOT EXISTS idx_mapping_tenant ON metadata_mappings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mapping_active ON metadata_mappings(is_active);




