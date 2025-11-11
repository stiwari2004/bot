# Connector Status & How to Connect

## ✅ CSV Upload Feature (READY NOW!)

**Frontend Tab**: "Upload Tickets" (Added to navigation)

**How to Use**:
1. Click "Upload Tickets" tab
2. Download CSV template (button in UI)
3. Fill in tickets:
   ```csv
   title,description,severity,environment,service,source
   Database connection timeout,Unable to connect to PostgreSQL,high,prod,database,prometheus
   ```
4. Upload CSV
5. System will analyze each ticket and optionally auto-execute matching runbooks

**Sample File**: `tickets_sample.csv` in project root

---

## 🔌 Connector Status

### Monitoring Tools

| Tool | Status | How to Connect |
|------|--------|----------------|
| **Datadog** | ✅ Basic | API: Fetch alerts → Tickets |
| **Prometheus** | ✅ Webhook | Send webhooks to `/api/v1/tickets/webhook/prometheus` |
| **Zabbix** | ⏳ Planned | Not implemented yet |
| **SolarWinds** | ⏳ Planned | Not implemented yet |
| **ManageEngine** | ⏳ Planned | Not implemented yet |

### Ticketing Tools

| Tool | Status | How to Connect |
|------|--------|----------------|
| **ServiceNow** | ✅ Basic | API: Create/update tickets |
| **Zendesk** | ⏳ Planned | Not implemented yet |
| **ManageEngine** | ⏳ Planned | Not implemented yet |
| **BMC Remedy** | ⏳ Planned | Not implemented yet |

---

## 🔧 Infrastructure Access (For Troubleshooting)

### Current Implementation

**Local Connector** ✅
- Executes commands on agent server
- Works out of the box

**SSH Connector** ✅ (Basic)
- Uses `ssh` command
- Supports password/key authentication
- **Limitation**: Requires SSH access from agent server

**Database Connector** ✅ (Basic)
- PostgreSQL: Uses `asyncpg`
- MySQL: Uses `aiomysql`
- **Limitation**: Requires database credentials

**API Connector** ✅ (Basic)
- REST API calls via `aiohttp`
- Supports API key authentication

### How to Configure Infrastructure Access

**Option 1: Via API** (Available Now)
```bash
# 1. Create credential
POST /api/v1/connectors/credentials
{
  "name": "prod-db-credentials",
  "credential_type": "database",
  "environment": "prod",
  "username": "admin",
  "password": "secret",
  "host": "db.example.com",
  "port": 5432,
  "database_name": "mydb"
}

# 2. Create infrastructure connection
POST /api/v1/connectors/infrastructure-connections
{
  "name": "prod-db-01",
  "connection_type": "database",
  "credential_id": 1,
  "target_host": "db.example.com",
  "target_port": 5432,
  "target_service": "postgresql",
  "environment": "prod"
}
```

**Option 2: Via Ticket Metadata** (Current)
```json
{
  "ticket_id": 123,
  "meta_data": {
    "connection_config": {
      "connector_type": "ssh",
      "host": "192.168.1.100",
      "port": 22,
      "username": "admin",
      "credential_id": 5
    }
  }
}
```

**Option 3: Via Runbook Metadata** (Future)
- Runbooks will specify which connection to use
- Execution engine will use that connection

---

## 🚀 Next Steps for Production

### Phase 1: Connector Configuration UI
- [ ] Create "Connectors" tab in frontend
- [ ] Build credential management UI
- [ ] Build infrastructure connection UI
- [ ] Add connector status indicators

### Phase 2: Complete External Tool Integrations
- [ ] Datadog: Complete webhook setup
- [ ] Zabbix: Implement API connector
- [ ] SolarWinds: Implement API connector
- [ ] ServiceNow: Complete bidirectional sync
- [ ] Zendesk: Implement connector

### Phase 3: Enhanced Infrastructure Connectors
- [ ] Replace SSH with `asyncssh` library
- [ ] Add WinRM support for Windows
- [ ] Add Kubernetes API client
- [ ] Add AWS/Azure/GCP SDKs
- [ ] Connection pooling and health checks

---

## 📝 API Endpoints

### Connector Management
- `GET /api/v1/connectors/monitoring` - List monitoring connectors
- `GET /api/v1/connectors/ticketing` - List ticketing connectors
- `POST /api/v1/connectors/credentials` - Create credential
- `GET /api/v1/connectors/credentials` - List credentials
- `POST /api/v1/connectors/infrastructure-connections` - Create connection
- `GET /api/v1/connectors/infrastructure-connections` - List connections

### CSV Upload
- `POST /api/v1/tickets/upload-csv` - Upload tickets from CSV

---

## 💡 Current Workaround for Testing

1. **Use CSV Upload**:
   - Create tickets manually via CSV
   - System analyzes and auto-executes if runbook matches

2. **Use Webhook Endpoint**:
   - Configure monitoring tool to send webhooks
   - Endpoint: `POST /api/v1/tickets/webhook/{source}`

3. **Use Demo Ticket API**:
   - Create tickets programmatically
   - Endpoint: `POST /api/v1/tickets/demo/ticket`

---

## 🎯 To Generate Pending Approvals

1. **Ensure you have approved runbooks** with approval steps (`requires_approval: true`)
2. **Upload tickets** via CSV or API that match those runbooks
3. **Check Agent Dashboard** - approvals will appear automatically

**Example Runbook with Approval**:
```markdown
# Fix Database Connection

## Prechecks
- `check_db_status.sh` (requires_approval: true)

## Main Steps
- `restart_db_service.sh` (severity: high_risk, requires_approval: true)

## Postchecks
- `verify_db_connection.sh`
```

When tickets matching this runbook are uploaded, system will:
1. Create execution session
2. Stop at first approval step
3. Show in Agent Dashboard




