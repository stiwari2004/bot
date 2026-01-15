-- Performance optimization indexes
-- Add indexes for frequently queried columns to improve query performance

-- Runbooks table indexes
CREATE INDEX IF NOT EXISTS idx_runbooks_tenant_id ON runbooks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_runbooks_status ON runbooks(status);
CREATE INDEX IF NOT EXISTS idx_runbooks_created_at ON runbooks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runbooks_tenant_status ON runbooks(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_runbooks_is_active ON runbooks(is_active) WHERE is_active = 'active';

-- Tickets table indexes
CREATE INDEX IF NOT EXISTS idx_tickets_tenant_id ON tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_tenant_status ON tickets(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_classification ON tickets(classification);
CREATE INDEX IF NOT EXISTS idx_tickets_source ON tickets(source);

-- Execution sessions table indexes
CREATE INDEX IF NOT EXISTS idx_execution_sessions_tenant_id ON execution_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_status ON execution_sessions(status);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_runbook_id ON execution_sessions(runbook_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_ticket_id ON execution_sessions(ticket_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_created_at ON execution_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_tenant_status ON execution_sessions(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_waiting_approval ON execution_sessions(waiting_for_approval) WHERE waiting_for_approval = true;

-- Execution steps table indexes
CREATE INDEX IF NOT EXISTS idx_execution_steps_session_id ON execution_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_execution_steps_step_number ON execution_steps(session_id, step_number);
CREATE INDEX IF NOT EXISTS idx_execution_steps_completed ON execution_steps(completed) WHERE completed = false;

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = true;

-- User sessions table indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_revoked ON user_sessions(is_revoked) WHERE is_revoked = false;

-- Documents table indexes (for vector search)
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Chunks table indexes (for vector search)
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tenant_id ON chunks(tenant_id);

-- Credentials table indexes
CREATE INDEX IF NOT EXISTS idx_credentials_tenant_id ON credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credentials_infrastructure_connection_id ON credentials(infrastructure_connection_id);

-- Infrastructure connections table indexes
CREATE INDEX IF NOT EXISTS idx_infrastructure_connections_tenant_id ON infrastructure_connections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_infrastructure_connections_type ON infrastructure_connections(connection_type);

-- Log entries table indexes (for prediction system)
CREATE INDEX IF NOT EXISTS idx_log_entries_tenant_id ON log_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_log_entries_timestamp ON log_entries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_log_entries_source ON log_entries(source);
CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS idx_log_entries_tenant_timestamp ON log_entries(tenant_id, timestamp DESC);

-- Predictions table indexes
CREATE INDEX IF NOT EXISTS idx_predictions_tenant_id ON predictions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_occurred ON predictions(occurred) WHERE occurred = false;

-- Change tickets table indexes
CREATE INDEX IF NOT EXISTS idx_change_tickets_tenant_id ON change_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_change_tickets_status ON change_tickets(status);
CREATE INDEX IF NOT EXISTS idx_change_tickets_start_time ON change_tickets(start_time);
CREATE INDEX IF NOT EXISTS idx_change_tickets_end_time ON change_tickets(end_time);

-- Analyze tables to update statistics
ANALYZE runbooks;
ANALYZE tickets;
ANALYZE execution_sessions;
ANALYZE execution_steps;
ANALYZE users;
ANALYZE user_sessions;
ANALYZE documents;
ANALYZE chunks;
ANALYZE credentials;
ANALYZE infrastructure_connections;
ANALYZE log_entries;
ANALYZE predictions;
ANALYZE change_tickets;


