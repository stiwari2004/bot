-- Add license activation fields to tenant_subscriptions table
-- For PaaS deployments: tracks license key and server activation

-- Add license activation columns
ALTER TABLE tenant_subscriptions 
ADD COLUMN IF NOT EXISTS license_key VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS server_fingerprint VARCHAR(255),
ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS activation_ip VARCHAR(45);

-- Create indexes for license activation lookups
CREATE INDEX IF NOT EXISTS idx_subscription_license_key ON tenant_subscriptions(license_key);
CREATE INDEX IF NOT EXISTS idx_subscription_fingerprint ON tenant_subscriptions(server_fingerprint);

-- Add comment to license_key column
COMMENT ON COLUMN tenant_subscriptions.license_key IS 'Unique license key for PaaS activation (generated when subscription created)';
COMMENT ON COLUMN tenant_subscriptions.server_fingerprint IS 'Server fingerprint where license is activated (prevents reuse on other servers)';
COMMENT ON COLUMN tenant_subscriptions.activated_at IS 'Timestamp when license was activated on server';
COMMENT ON COLUMN tenant_subscriptions.activation_ip IS 'IP address that performed license activation';

