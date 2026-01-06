# License Activation System for PaaS Deployments

## Overview

This implementation adds license key activation for Platform-as-a-Service (PaaS) deployments, ensuring that:
1. **One license key = one server instance** - Prevents license reuse across multiple servers
2. **License telemetry** - Tracks seat/node usage for monitoring
3. **PaaS restrictions** - Disables reset functionality in PaaS mode for security

## Features Implemented

### 1. License Key Generation
- Automatically generates unique license keys when subscriptions are created in PaaS mode
- Format: `LIC-XXXXXXXX-XXXXXXXX-XXXXXXXX` (e.g., `LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2`)
- Keys are cryptographically secure and unique

### 2. Server Fingerprinting
- Generates unique server identifier based on:
  - Machine ID (`/etc/machine-id` on Linux, Windows registry GUID)
  - Hostname
  - MAC address
  - Docker container ID (if applicable)
  - Platform information
- SHA256 hash ensures uniqueness and privacy

### 3. License Activation
- **Endpoint**: `POST /api/v1/license/activate`
- Binds license key to server fingerprint
- Prevents same key from being activated on different servers
- Returns activation confirmation with server details

### 4. License Validation
- **Startup validation**: Checks license activation on application startup
- **Runtime validation**: Can be checked via status endpoint
- **Endpoint**: `GET /api/v1/license/status`

### 5. License Telemetry
- **Endpoint**: `GET /api/v1/license/telemetry`
- Provides:
  - Current seat/node usage
  - Usage percentages
  - Remaining capacity
  - Server information

### 6. PaaS Mode Restrictions
- Reset functionality disabled in PaaS mode
- Prevents accidental data loss in production deployments
- Controlled via `DEPLOYMENT_MODE=paas` environment variable

## Database Changes

### New Fields in `tenant_subscriptions` Table
- `license_key` (VARCHAR(255), UNIQUE) - Generated license key
- `server_fingerprint` (VARCHAR(255)) - Server where license is activated
- `activated_at` (TIMESTAMP) - Activation timestamp
- `activation_ip` (VARCHAR(45)) - IP that performed activation

### Migration Script
- `backend/sql/add_license_activation_fields.sql`
- Run this migration to add the new fields

## Configuration

### Environment Variable
```bash
DEPLOYMENT_MODE=paas  # Set to "paas" for PaaS deployments, "saas" for SaaS (default)
```

## API Endpoints

### 1. Activate License
```http
POST /api/v1/license/activate
Content-Type: application/json

{
  "license_key": "LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2"
}
```

**Response:**
```json
{
  "success": true,
  "message": "License activated successfully",
  "license_key": "LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2",
  "activated_at": "2026-01-06T12:00:00Z",
  "server_fingerprint": "abc123...",
  "server_hostname": "server-01",
  "max_seats": 1000,
  "max_nodes": 500
}
```

### 2. Get License Status
```http
GET /api/v1/license/status
```

**Response:**
```json
{
  "is_paas_mode": true,
  "is_activated": true,
  "error": null,
  "activation": {
    "license_key": "LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2",
    "activated_at": "2026-01-06T12:00:00Z",
    "server_fingerprint": "abc123...",
    "max_seats": 1000,
    "max_nodes": 500,
    "current_seats": 150,
    "current_nodes": 45
  },
  "server_info": {
    "hostname": "server-01",
    "platform": "Linux",
    "architecture": "x86_64"
  }
}
```

### 3. Get License Telemetry
```http
GET /api/v1/license/telemetry
```

**Response:**
```json
{
  "license_key": "LIC-A1B2C3D4-E5F6G7H8-I9J0K1L2",
  "activated_at": "2026-01-06T12:00:00Z",
  "subscription": {
    "max_seats": 1000,
    "max_nodes": 500,
    "current_seats": 150,
    "current_nodes": 45,
    "seats_remaining": 850,
    "nodes_remaining": 455,
    "seats_usage_percent": 15.0,
    "nodes_usage_percent": 9.0
  },
  "server_info": {
    "hostname": "server-01",
    "platform": "Linux"
  }
}
```

## Usage Flow

### 1. Subscription Creation (Admin)
When a super admin creates a subscription in PaaS mode:
- System automatically generates a unique license key
- License key is stored in `tenant_subscriptions.license_key`
- Key is returned in subscription response

### 2. License Activation (Customer)
1. Customer installs Docker image
2. Sets `DEPLOYMENT_MODE=paas` in environment
3. On first startup, system requires license activation
4. Customer calls `/api/v1/license/activate` with license key
5. System:
   - Validates license key
   - Generates server fingerprint
   - Binds key to server
   - Returns activation confirmation

### 3. Subsequent Starts
- System validates license on startup
- Checks if fingerprint matches current server
- If match: allows operations
- If mismatch: blocks operations (key already used on another server)

## Security Features

1. **One-Time Activation**: License key can only be activated once
2. **Server Binding**: Key is bound to specific server fingerprint
3. **Fingerprint Validation**: Prevents key reuse on different servers
4. **Reset Protection**: Reset functionality disabled in PaaS mode

## Files Created/Modified

### New Files
- `backend/app/services/license/server_fingerprint.py` - Server fingerprinting utility
- `backend/app/services/license/license_activation_service.py` - License activation service
- `backend/app/services/license/__init__.py` - Package init
- `backend/app/api/v1/endpoints/license_activation.py` - Activation endpoints
- `backend/sql/add_license_activation_fields.sql` - Database migration

### Modified Files
- `backend/app/core/config.py` - Added `DEPLOYMENT_MODE` setting
- `backend/app/models/tenant_subscription.py` - Added license activation fields
- `backend/app/api/v1/endpoints/subscriptions.py` - License key generation on creation
- `backend/app/api/v1/api.py` - Added license activation router
- `backend/app/main.py` - Added startup license validation
- `backend/scripts/reset_sandbox.py` - Disabled reset in PaaS mode

## Testing

### Test License Activation
```bash
# 1. Set PaaS mode
export DEPLOYMENT_MODE=paas

# 2. Create subscription (generates license key)
curl -X POST /api/v1/subscriptions \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"tenant_id": 1, "max_seats": 1000, "max_nodes": 500}'

# 3. Activate license
curl -X POST /api/v1/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "LIC-..."}'

# 4. Check status
curl /api/v1/license/status

# 5. Get telemetry
curl /api/v1/license/telemetry
```

## Notes

- License keys are only generated in PaaS mode (`DEPLOYMENT_MODE=paas`)
- In SaaS mode, no license keys are generated (existing behavior)
- Existing seat/node limit enforcement continues to work as before
- Telemetry endpoint requires active license activation
- Reset scripts check PaaS mode and exit early if enabled

