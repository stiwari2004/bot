# Cloud Connection Implementation Plan

## Current Status

### ✅ What's Already Implemented
1. **Backend Infrastructure:**
   - `AzureBastionConnector` - Uses Azure Run Command API (fully functional)
   - `GcpIapConnector` - Stub implementation (needs completion)
   - `InfrastructureConnection` model with `meta_data` field for cloud-specific data
   - `Credential` model supports `azure`, `gcp`, `aws` credential types
   - API endpoints: `/api/v1/connectors/credentials` and `/api/v1/connectors/infrastructure-connections`
   - Credential encryption service (Fernet-based)

2. **What Works:**
   - Azure Run Command API execution (no public IP needed)
   - Credential storage and encryption
   - Infrastructure connection database model

### ❌ What's Missing
1. **Frontend UI:**
   - No UI for managing cloud infrastructure connections
   - No UI for creating Azure/GCP/AWS credentials
   - Settings page only shows ticketing connections

2. **Backend Enhancements:**
   - API needs to handle cloud-specific metadata (subscription_id, project_id, resource_id, etc.)
   - Credential service needs to support Azure service principal credentials
   - GCP IAP connector needs full implementation

3. **Integration:**
   - Need to link cloud connections to runbook execution
   - Need to support credential aliases for cloud accounts

## Implementation Steps

### Phase 1: Backend API Enhancements
1. Extend `InfrastructureConnectionCreate` to support cloud metadata
2. Update credential creation to handle Azure service principal (tenant_id, client_id, client_secret)
3. Add validation for cloud connection metadata

### Phase 2: Frontend UI
1. Add "Infrastructure Connections" section to Settings page
2. Create modal for adding cloud connections (Azure, GCP, AWS)
3. Create modal for managing cloud credentials
4. Display list of existing cloud connections

### Phase 3: Integration
1. Update runbook execution to use cloud connections
2. Support credential resolution for cloud accounts
3. Test end-to-end flow

## Azure Connection Requirements

### Credential Metadata:
```json
{
  "tenant_id": "xxx",
  "client_id": "xxx",
  "client_secret": "xxx",
  "subscription_id": "xxx"
}
```

### Infrastructure Connection Metadata:
```json
{
  "resource_id": "/subscriptions/.../virtualMachines/...",
  "subscription_id": "xxx",
  "resource_group": "xxx",
  "vm_name": "xxx",
  "use_ssh": false,
  "bastion_host": "optional",
  "target_host": "optional"
}
```

## GCP Connection Requirements

### Credential Metadata:
```json
{
  "service_account_key": "base64-encoded-json",
  "project_id": "xxx"
}
```

### Infrastructure Connection Metadata:
```json
{
  "project_id": "xxx",
  "zone": "xxx",
  "instance_name": "xxx",
  "port": 22
}
```





