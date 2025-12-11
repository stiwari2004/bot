-- Migration script to add new columns to tenants table
-- Run this to update existing tenants table with new fields

-- Add new columns (with defaults for existing rows)
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS subdomain_slug VARCHAR(100),
ADD COLUMN IF NOT EXISTS deployment_type VARCHAR(20) DEFAULT 'saas',
ADD COLUMN IF NOT EXISTS platform_managed BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS setup_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS setup_token_expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS setup_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS self_hosted_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS onboarding_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(50),
ADD COLUMN IF NOT EXISTS config_metadata JSON;

-- Update existing rows to have proper defaults
UPDATE tenants 
SET deployment_type = 'saas', 
    platform_managed = TRUE, 
    onboarding_status = 'completed'
WHERE deployment_type IS NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tenants_subdomain_slug ON tenants(subdomain_slug);
CREATE INDEX IF NOT EXISTS idx_tenants_deployment_type ON tenants(deployment_type);
CREATE INDEX IF NOT EXISTS idx_tenants_setup_token ON tenants(setup_token);

-- Add unique constraint on subdomain_slug (if not null)
-- Note: PostgreSQL doesn't support unique constraints with NULL values directly
-- We'll use a partial unique index instead
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_subdomain_slug_unique 
ON tenants(subdomain_slug) 
WHERE subdomain_slug IS NOT NULL;

-- Add unique constraint on setup_token (if not null)
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_setup_token_unique 
ON tenants(setup_token) 
WHERE setup_token IS NOT NULL;

-- Change description from VARCHAR(1000) to TEXT if needed
-- (This is safe - TEXT can hold more data)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' 
        AND column_name = 'description' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE tenants ALTER COLUMN description TYPE TEXT;
    END IF;
END $$;







