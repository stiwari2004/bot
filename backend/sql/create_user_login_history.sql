-- Create user_login_history table
CREATE TABLE IF NOT EXISTS user_login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    login_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_login_history_user ON user_login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_login_at ON user_login_history(login_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_history_success ON user_login_history(success);

-- Add comments for documentation
COMMENT ON TABLE user_login_history IS 'History of user login attempts (successful and failed)';
COMMENT ON COLUMN user_login_history.ip_address IS 'IP address of login attempt';
COMMENT ON COLUMN user_login_history.user_agent IS 'User agent string from login request';
COMMENT ON COLUMN user_login_history.success IS 'Whether login was successful';
COMMENT ON COLUMN user_login_history.failure_reason IS 'Reason for login failure (if unsuccessful)';

