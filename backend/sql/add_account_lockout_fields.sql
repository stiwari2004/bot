-- Add account lockout fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_failed_login_at TIMESTAMP WITH TIME ZONE;

-- Create index for efficient lockout queries
CREATE INDEX IF NOT EXISTS idx_users_locked ON users(locked_until) 
    WHERE locked_until IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN users.failed_login_attempts IS 'Number of consecutive failed login attempts';
COMMENT ON COLUMN users.locked_until IS 'Account lockout expiration timestamp (auto-unlock after 30 minutes)';
COMMENT ON COLUMN users.last_failed_login_at IS 'Timestamp of last failed login attempt';

