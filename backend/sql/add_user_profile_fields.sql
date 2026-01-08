-- Add user profile fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS department VARCHAR(255),
ADD COLUMN IF NOT EXISTS job_title VARCHAR(255),
ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC',
ADD COLUMN IF NOT EXISTS locale VARCHAR(10) DEFAULT 'en-US';

-- Add comments for documentation
COMMENT ON COLUMN users.avatar_url IS 'URL to user avatar image';
COMMENT ON COLUMN users.phone_number IS 'User phone number';
COMMENT ON COLUMN users.department IS 'User department';
COMMENT ON COLUMN users.job_title IS 'User job title';
COMMENT ON COLUMN users.timezone IS 'User timezone (e.g., America/New_York)';
COMMENT ON COLUMN users.locale IS 'User locale (e.g., en-US)';

