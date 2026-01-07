-- Add user preferences JSONB field to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';

-- Create index for efficient preference queries
CREATE INDEX IF NOT EXISTS idx_users_preferences ON users USING GIN(preferences);

-- Add comment for documentation
COMMENT ON COLUMN users.preferences IS 'User preferences (theme, notifications, etc.) stored as JSON';

