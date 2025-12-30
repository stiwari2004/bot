-- Migration: Add role_id column to users table for RBAC support
-- This migration is idempotent - safe to run multiple times

-- Add role_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'role_id'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN role_id INTEGER;
        
        -- Add foreign key constraint if roles table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'roles') THEN
            ALTER TABLE users 
            ADD CONSTRAINT fk_users_role_id 
            FOREIGN KEY (role_id) 
            REFERENCES roles(id) 
            ON DELETE SET NULL;
        END IF;
        
        -- Add index for performance
        CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
        
        RAISE NOTICE 'Added role_id column to users table';
    ELSE
        RAISE NOTICE 'role_id column already exists in users table';
    END IF;
END $$;

