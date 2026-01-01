#!/bin/bash
# Script to apply license_plan_id migration to tenant_subscriptions table
# This can be run on the production server

set -e

echo "Applying license_plan_id migration to tenant_subscriptions table..."

# Use printf to avoid heredoc TTY issues
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai <<'SQL'
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'tenant_subscriptions' 
        AND column_name = 'license_plan_id'
    ) THEN
        IF EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'license_plans'
        ) THEN
            ALTER TABLE tenant_subscriptions 
            ADD COLUMN license_plan_id INTEGER NULL;
            
            ALTER TABLE tenant_subscriptions 
            ADD CONSTRAINT fk_subscription_license_plan 
            FOREIGN KEY (license_plan_id) 
            REFERENCES license_plans(id) 
            ON DELETE SET NULL;
            
            CREATE INDEX IF NOT EXISTS idx_subscription_license_plan 
            ON tenant_subscriptions(license_plan_id);
            
            RAISE NOTICE 'Successfully added license_plan_id column with foreign key constraint';
        ELSE
            ALTER TABLE tenant_subscriptions 
            ADD COLUMN license_plan_id INTEGER NULL;
            
            CREATE INDEX IF NOT EXISTS idx_subscription_license_plan 
            ON tenant_subscriptions(license_plan_id);
            
            RAISE NOTICE 'Added license_plan_id column without foreign key constraint (license_plans table does not exist yet)';
        END IF;
    ELSE
        RAISE NOTICE 'Column license_plan_id already exists in tenant_subscriptions';
    END IF;
END $$;
SQL

if [ $? -eq 0 ]; then
    echo "Migration applied successfully!"
    echo "Restarting backend service..."
    docker-compose -f docker-compose.production.yml restart backend
    echo "Done!"
else
    echo "Migration failed. Please check the error above."
    exit 1
fi

