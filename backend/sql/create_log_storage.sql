-- Log Storage Schema for Incident Prediction
-- Create tables for log entries, patterns, predictions, and models

-- Log entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,  -- application, infrastructure, monitoring
    log_type VARCHAR(50) NOT NULL,  -- error, warning, info, metric
    level VARCHAR(20),  -- DEBUG, INFO, WARN, ERROR, CRITICAL
    message TEXT NOT NULL,
    raw_log TEXT,
    parsed_fields JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    service VARCHAR(255),
    environment VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Log patterns table
CREATE TABLE IF NOT EXISTS log_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    pattern_signature VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(50),  -- error_pattern, warning_pattern, anomaly
    frequency INTEGER DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    associated_incidents INTEGER DEFAULT 0,
    confidence_score FLOAT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    prediction_type VARCHAR(50) NOT NULL,  -- short_term, medium_term, long_term
    predicted_incident_type VARCHAR(100),
    confidence_score FLOAT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    time_horizon_minutes INTEGER NOT NULL,
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    occurred BOOLEAN DEFAULT FALSE,
    occurred_at TIMESTAMP WITH TIME ZONE,
    false_positive BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Prediction patterns (link predictions to log patterns)
CREATE TABLE IF NOT EXISTS prediction_patterns (
    prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    pattern_id INTEGER NOT NULL REFERENCES log_patterns(id) ON DELETE CASCADE,
    weight FLOAT NOT NULL,
    PRIMARY KEY (prediction_id, pattern_id)
);

-- Prediction models metadata
CREATE TABLE IF NOT EXISTS prediction_models (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    model_type VARCHAR(50) NOT NULL,  -- short_term, medium_term, long_term
    model_version VARCHAR(50) NOT NULL,
    model_path VARCHAR(500),
    training_data_count INTEGER,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    trained_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_log_entries_tenant_timestamp ON log_entries(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS idx_log_entries_source ON log_entries(source);
CREATE INDEX IF NOT EXISTS idx_log_entries_service ON log_entries(service);
CREATE INDEX IF NOT EXISTS idx_log_patterns_signature ON log_patterns(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_log_patterns_type ON log_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_predictions_tenant_predicted ON predictions(tenant_id, predicted_at);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_level ON predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_predictions_type ON predictions(prediction_type);
CREATE INDEX IF NOT EXISTS idx_prediction_models_tenant_type ON prediction_models(tenant_id, model_type);

-- Comments for documentation
COMMENT ON TABLE log_entries IS 'Stores raw log entries from various sources for analysis';
COMMENT ON TABLE log_patterns IS 'Stores extracted patterns and signatures from logs';
COMMENT ON TABLE predictions IS 'Stores incident predictions with confidence scores';
COMMENT ON TABLE prediction_patterns IS 'Links predictions to the log patterns that contributed to them';
COMMENT ON TABLE prediction_models IS 'Stores metadata about ML models used for predictions';

