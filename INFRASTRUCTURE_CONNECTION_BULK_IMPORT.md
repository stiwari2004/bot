# Infrastructure Connection Bulk Import - Refactored Implementation

## Overview
Refactored to use existing `InfrastructureConnection` model instead of creating a separate `NetworkDevice` model. Added bulk Excel import functionality to the existing infrastructure connections system.

## Changes Made

### 1. Excel Importer (`backend/app/services/infrastructure/excel_importer.py`)
- **InfrastructureConnectionExcelImporter** class
- Flexible column mapping (case-insensitive)
- Required columns: `name`, `target_host`, `connection_type`
- Optional columns: `target_port`, `environment`, `username`, `password`
- Network device metadata stored in `meta_data` JSON field:
  - vendor, model, device_type, location, network_segment, site
  - serial_number, firmware_version, snmp_community, snmp_version
- Auto-creates credentials if username/password provided

### 2. API Endpoint (`backend/app/api/v1/endpoints/connectors.py`)
- Added `POST /api/v1/connectors/infrastructure-connections/import-excel`
- Bulk import endpoint that:
  - Parses Excel file
  - Creates InfrastructureConnection records
  - Auto-creates Credential records if username/password provided
  - Stores network device metadata in `meta_data` field
  - Returns import results (success/errors)

### 3. Frontend (`frontend-nextjs/src/features/settings/components/InfrastructureConnectionsSection.tsx`)
- Added "Import from Excel" button
- Import modal with:
  - File upload
  - Column requirements display
  - Import results (success/errors)
- Integrated into existing Infrastructure Connections section

### 4. Removed Separate NetworkDevice Model
- Deleted `backend/app/models/network_device.py`
- Deleted `backend/app/services/network/excel_importer.py`
- Deleted `backend/app/api/v1/endpoints/network_devices.py`
- Deleted frontend network device components
- Updated all references to use `InfrastructureConnection`

### 5. Updated Rollback Service
- Modified to work with `InfrastructureConnection` instead of `NetworkDevice`
- Config backups stored in `connection.meta_data.config_backups`
- Keeps last 10 backups per connection
- Works with existing network device execution engine

## Excel Import Format

### Required Columns:
- `name` (or hostname, device_name, connection_name)
- `target_host` (or host, ip, ip_address, management_ip)
- `connection_type` (ssh, network_device, database, api, etc.)

### Optional Columns:
- `target_port` (default: 22 for SSH)
- `environment` (prod, staging, dev - default: prod)
- `username`, `password` (creates credential automatically)
- `target_service` (for database connections)

### Network Device Specific (stored in meta_data):
- `vendor` (Cisco, Juniper, Palo Alto, etc.)
- `model` (device model)
- `device_type` (router, switch, firewall, etc.)
- `location`, `network_segment`, `site`
- `serial_number`, `firmware_version`
- `snmp_community`, `snmp_version`

### Example Excel Row for Network Device:
```
name: core-switch-01
target_host: 192.168.1.10
connection_type: network_device
target_port: 22
environment: prod
vendor: Cisco
model: Nexus 9000
device_type: switch
network_segment: Core
location: Datacenter A
username: admin
password: secret123
```

### Example Excel Row for SSH Server:
```
name: web-server-01
target_host: 10.0.1.50
connection_type: ssh
target_port: 22
environment: prod
username: ubuntu
password: secret123
```

## API Usage

### Import Connections:
```bash
curl -X POST http://localhost:8000/api/v1/connectors/infrastructure-connections/import-excel \
  -F "file=@connections.xlsx"
```

### Response:
```json
{
  "message": "Import completed: 10 connections imported, 0 errors",
  "imported": [
    {
      "row": 1,
      "name": "core-switch-01",
      "host": "192.168.1.10",
      "type": "network_device",
      "id": 123
    }
  ],
  "errors": [],
  "total": 10
}
```

## Architecture

### Data Model:
- **InfrastructureConnection**: Main model (already existed)
  - `name`, `connection_type`, `target_host`, `target_port`
  - `credential_id` (references Credential)
  - `meta_data` (JSON) - stores network device metadata and config backups

### Flow:
1. **Excel Import** → Creates `InfrastructureConnection` records
2. **Network Device Metadata** → Stored in `meta_data` JSON field
3. **Config Backups** → Stored in `meta_data.config_backups`
4. **Execution** → Uses existing `InfrastructureConnection` with `connection_type="network_device"`
5. **Rollback** → Retrieves backups from `meta_data.config_backups`

## Benefits of Refactoring

1. **Simpler Architecture**: One model instead of two
2. **Reuses Existing System**: Leverages existing infrastructure connection management
3. **Consistent UI**: All connections in one place
4. **Less Code**: Removed duplicate models and endpoints
5. **Flexible**: `meta_data` field allows storing any device-specific info

## Files Created/Modified

### Created:
- `backend/app/services/infrastructure/excel_importer.py`

### Modified:
- `backend/app/api/v1/endpoints/connectors.py` - Added bulk import endpoint
- `frontend-nextjs/src/features/settings/components/InfrastructureConnectionsSection.tsx` - Added import button and modal
- `frontend-nextjs/src/lib/api-config.ts` - Added import endpoint
- `backend/app/services/execution/rollback_service.py` - Updated to use InfrastructureConnection

### Deleted:
- `backend/app/models/network_device.py`
- `backend/app/services/network/excel_importer.py`
- `backend/app/api/v1/endpoints/network_devices.py`
- `frontend-nextjs/src/features/network/` (entire directory)

## Testing Checklist

- [ ] Excel import with various column names
- [ ] Network device import (with metadata)
- [ ] SSH server import
- [ ] Auto-credential creation
- [ ] Import error handling
- [ ] Frontend import modal
- [ ] Config backup for network devices
- [ ] Config rollback on failure


