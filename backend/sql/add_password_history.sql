-- Add password history and expiration fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_history JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN users.password_history IS 'Array of last 5 password hashes to prevent reuse';
COMMENT ON COLUMN users.password_expires_at IS 'Password expiration date (90 days default, configurable per tenant)';
COMMENT ON COLUMN users.password_changed_at IS 'Timestamp when password was last changed';

