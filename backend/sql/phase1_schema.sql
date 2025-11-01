-- Phase 1 Schema: Intelligent Assistant Tracking
-- Create tables for runbook usage, citations, similarities, and system configuration

-- System configuration for thresholds
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, config_key)
);

-- Track runbook usage and feedback
CREATE TABLE IF NOT EXISTS runbook_usage (
    id SERIAL PRIMARY KEY,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES tenants(id),
    user_id INTEGER,
    issue_description TEXT,
    confidence_score NUMERIC(3,2),
    was_helpful BOOLEAN,
    feedback_text TEXT,
    execution_time_minutes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track runbook similarities (for duplicate detection)
CREATE TABLE IF NOT EXISTS runbook_similarities (
    id SERIAL PRIMARY KEY,
    runbook_id_1 INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    runbook_id_2 INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    similarity_score NUMERIC(3,2),
    status VARCHAR(20) DEFAULT 'detected',
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP,
    action_taken VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    CHECK (runbook_id_1 != runbook_id_2)
);

-- Citation tracking
CREATE TABLE IF NOT EXISTS runbook_citations (
    id SERIAL PRIMARY KEY,
    runbook_id INTEGER REFERENCES runbooks(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
    relevance_score NUMERIC(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_runbook_usage_runbook_id ON runbook_usage(runbook_id);
CREATE INDEX IF NOT EXISTS idx_runbook_usage_tenant_id ON runbook_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_runbook_usage_created_at ON runbook_usage(created_at);

CREATE INDEX IF NOT EXISTS idx_runbook_similarities_runbook_1 ON runbook_similarities(runbook_id_1);
CREATE INDEX IF NOT EXISTS idx_runbook_similarities_runbook_2 ON runbook_similarities(runbook_id_2);
CREATE INDEX IF NOT EXISTS idx_runbook_similarities_status ON runbook_similarities(status);

CREATE INDEX IF NOT EXISTS idx_runbook_citations_runbook_id ON runbook_citations(runbook_id);
CREATE INDEX IF NOT EXISTS idx_runbook_citations_document_id ON runbook_citations(document_id);

CREATE INDEX IF NOT EXISTS idx_system_config_tenant_key ON system_config(tenant_id, config_key);

-- Insert default config for demo tenant (tenant_id = 1)
INSERT INTO system_config (tenant_id, config_key, config_value, description) VALUES
(1, 'confidence_threshold_existing', '0.75', 'Minimum similarity to suggest existing runbook'),
(1, 'confidence_threshold_duplicate', '0.80', 'Similarity threshold to flag as duplicate'),
(1, 'min_runbook_success_rate', '0.70', 'Minimum success rate for high-quality runbook')
ON CONFLICT (tenant_id, config_key) DO NOTHING;

