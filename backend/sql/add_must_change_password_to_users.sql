-- Add must_change_password column to users table
-- This flag forces users to change their password on next login

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'must_change_password'
    ) THEN
        ALTER TABLE users
        ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;

        CREATE INDEX IF NOT EXISTS idx_users_must_change_password
        ON users(must_change_password);

        COMMENT ON COLUMN users.must_change_password IS 'If true, user must change password on next login';

        RAISE NOTICE 'Successfully added must_change_password column to users table';
    ELSE
        RAISE NOTICE 'Column must_change_password already exists in users table';
    END IF;
END $$;

