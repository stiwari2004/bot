-- Fix is_msp for existing tenants
-- Run this if you created MSP tenants before the backend persisted is_msp (create/update now do).
--
-- Option 1: Set is_msp = true for a specific tenant by name
-- UPDATE tenants SET is_msp = true WHERE name = 'Your MSP Tenant Name';
--
-- Option 2: Set is_msp = true by tenant id
-- UPDATE tenants SET is_msp = true WHERE id = 2;
--
-- Option 3: Ensure all customer (sub-)tenants have is_msp = false (they have parent_tenant_id set)
-- UPDATE tenants SET is_msp = false WHERE parent_tenant_id IS NOT NULL;
--
-- Check current state:
-- SELECT id, name, is_msp, parent_tenant_id FROM tenants ORDER BY id;

SELECT id, name, is_msp, parent_tenant_id FROM tenants ORDER BY id;
