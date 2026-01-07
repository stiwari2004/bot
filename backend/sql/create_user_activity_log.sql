-- Create user_activity_log table
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_activity_log_user ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON user_activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_log_action ON user_activity_log(action);
CREATE INDEX IF NOT EXISTS idx_activity_log_resource ON user_activity_log(resource_type, resource_id);

-- Add comments for documentation
COMMENT ON TABLE user_activity_log IS 'Audit log of user actions and activities';
COMMENT ON COLUMN user_activity_log.action IS 'Action performed (e.g., create, update, delete, view)';
COMMENT ON COLUMN user_activity_log.resource_type IS 'Type of resource affected (e.g., ticket, runbook, user)';
COMMENT ON COLUMN user_activity_log.resource_id IS 'ID of resource affected';
COMMENT ON COLUMN user_activity_log.details IS 'Additional details about the action (JSON)';

