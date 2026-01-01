-- Add license_plan_id column to tenant_subscriptions table
-- This migration is idempotent and can be run multiple times safely

DO $$ 
BEGIN
    -- Add license_plan_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'tenant_subscriptions' 
        AND column_name = 'license_plan_id'
    ) THEN
        -- First, ensure license_plans table exists (or create it if needed)
        -- If license_plans doesn't exist, we'll still add the column but without FK constraint
        IF EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'license_plans'
        ) THEN
            -- Add column with foreign key constraint
            ALTER TABLE tenant_subscriptions 
            ADD COLUMN license_plan_id INTEGER NULL;
            
            ALTER TABLE tenant_subscriptions 
            ADD CONSTRAINT fk_subscription_license_plan 
            FOREIGN KEY (license_plan_id) 
            REFERENCES license_plans(id) 
            ON DELETE SET NULL;
            
            CREATE INDEX IF NOT EXISTS idx_subscription_license_plan 
            ON tenant_subscriptions(license_plan_id);
            
            COMMENT ON COLUMN tenant_subscriptions.license_plan_id IS 'Reference to license plan (Free, Starter, etc.)';
        ELSE
            -- Add column without foreign key if license_plans table doesn't exist yet
            ALTER TABLE tenant_subscriptions 
            ADD COLUMN license_plan_id INTEGER NULL;
            
            CREATE INDEX IF NOT EXISTS idx_subscription_license_plan 
            ON tenant_subscriptions(license_plan_id);
            
            COMMENT ON COLUMN tenant_subscriptions.license_plan_id IS 'Reference to license plan (Free, Starter, etc.)';
            
            RAISE NOTICE 'Added license_plan_id column without foreign key constraint (license_plans table does not exist yet)';
        END IF;
        
        RAISE NOTICE 'Successfully added license_plan_id column to tenant_subscriptions';
    ELSE
        RAISE NOTICE 'Column license_plan_id already exists in tenant_subscriptions';
    END IF;
END $$;

