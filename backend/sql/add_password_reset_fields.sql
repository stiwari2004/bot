-- Add password reset and email verification fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(password_reset_token) 
    WHERE password_reset_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token) 
    WHERE email_verification_token IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN users.password_reset_token IS 'Secure token for password reset (expires in 1 hour)';
COMMENT ON COLUMN users.password_reset_expires IS 'Expiration timestamp for password reset token';
COMMENT ON COLUMN users.email_verified IS 'Whether user email has been verified';
COMMENT ON COLUMN users.email_verification_token IS 'Token for email verification';

