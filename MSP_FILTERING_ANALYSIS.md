# MSP Filtering Analysis

## Question: Do we need an MSP field in connections tables?

### Current State
- All connection tables have `tenant_id` field:
  - `InfrastructureConnection.tenant_id`
  - `TicketingToolConnection.tenant_id`
  - `MonitoringToolConnection.tenant_id`
  - `Credential.tenant_id`

- Tenant table has:
  - `is_msp` (Boolean) - indicates if tenant is an MSP
  - `parent_tenant_id` (Integer) - for customer tenants, points to their MSP parent

### For MSP-Level Filtering

**We DON'T need an MSP field** - we can use the tenant relationship:

1. **For MSP Admins viewing customer connections:**
   - Query connections where `tenant.parent_tenant_id = MSP_tenant_id`
   - This gives all connections from customer tenants

2. **For Regular Tenant Admins:**
   - Query connections where `tenant_id = current_user.tenant_id`
   - This gives only their own connections

### Implementation Approach

For MSP admin endpoints, we can:
```python
# Get all customer tenant IDs for this MSP
customer_tenant_ids = db.query(Tenant.id).filter(
    Tenant.parent_tenant_id == msp_tenant_id,
    Tenant.is_msp == False
).all()

# Query connections from all customers
connections = db.query(InfrastructureConnection).filter(
    InfrastructureConnection.tenant_id.in_(customer_tenant_ids)
).all()
```

### Conclusion
**No MSP field needed** - we can use the existing `tenant_id` + `parent_tenant_id` relationship to filter connections by MSP.

