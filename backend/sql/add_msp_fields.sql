-- Add MSP/white-labeling fields to tenants table
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS is_msp BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS parent_tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tenants_parent_tenant ON tenants(parent_tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_is_msp ON tenants(is_msp);

COMMENT ON COLUMN tenants.is_msp IS 'Is this tenant an MSP that can create sub-tenants?';
COMMENT ON COLUMN tenants.parent_tenant_id IS 'If this is a sub-tenant, reference parent MSP';


