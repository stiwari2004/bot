# Alerts vs Tickets - Correct Architecture

## ✅ Fixed Architecture

### Separation of Concerns

**Alerts** (from Monitoring Tools):
- Source: Prometheus, Datadog, Azure Monitor, Splunk
- Purpose: Validation, state checking, matching with tickets
- Storage: `alerts` table
- API: `/api/v1/alerts/*`

**Tickets** (from Ticketing Tools):
- Source: ServiceNow, ManageEngine, Zoho
- Purpose: Actual work items that need resolution
- Storage: `tickets` table
- API: `/api/v1/tickets/*`

## Correct Flow

```
┌─────────────────────────────────────────────────────────┐
│  Customer's Existing Setup (Already Configured)         │
│                                                          │
│  Monitoring Tool → Alert → Ticketing Tool               │
│  (Azure/Prometheus/etc) → (ServiceNow/ManageEngine)     │
└─────────────────────────────────────────────────────────┘
                          │
                          │ Ticket Created in Ticketing Tool
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Our System                                             │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Polling Service                                  │  │
│  │  ServiceNow/ManageEngine → Poll → Tickets (DB)    │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Webhook Service                                  │  │
│  │  Monitoring Tools → Webhook → Alerts (DB)         │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Matching Service (Future)                        │  │
│  │  Match Alerts with Tickets for Validation         │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Runbook Execution                                │  │
│  │  Execute → Resolve → Update Ticketing Tool        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### Alerts Table
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    external_id VARCHAR(255),  -- Alert fingerprint/ID
    source VARCHAR(100),      -- prometheus, datadog, azure_monitor, splunk
    title VARCHAR(500),
    description TEXT,
    severity VARCHAR(20),     -- critical, high, medium, low
    environment VARCHAR(20),  -- prod, staging, dev
    service VARCHAR(255),
    status VARCHAR(50),       -- firing, resolved, acknowledged
    raw_payload JSONB,
    meta_data JSONB,
    received_at TIMESTAMP,
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    resolved_at TIMESTAMP,
    matched_ticket_id INTEGER REFERENCES tickets(id),  -- Link to ticket if matched
    matched_at TIMESTAMP
);
```

### Tickets Table
```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    external_id VARCHAR(255),  -- Ticket number from ticketing tool
    source VARCHAR(100),       -- servicenow, manageengine, zoho
    title VARCHAR(500),
    description TEXT,
    severity VARCHAR(20),
    environment VARCHAR(20),
    service VARCHAR(255),
    status VARCHAR(50),        -- open, in_progress, resolved, closed
    -- ... other fields
);
```

## API Endpoints

### Alerts (Monitoring Tools)
- `POST /api/v1/tickets/webhook/{source}` - Receive alert webhook
  - Sources: `prometheus`, `datadog`, `azure_monitor`, `splunk`
  - Creates: **Alert** (not ticket)
  
- `GET /api/v1/alerts/alerts` - List alerts
  - Query params: `status`, `source`, `limit`
  
- `GET /api/v1/alerts/alerts/{id}` - Get alert details

### Tickets (Ticketing Tools)
- `GET /api/v1/tickets/demo/tickets` - List tickets (from polling)
- `GET /api/v1/tickets/demo/tickets/{id}` - Get ticket details

## UI Structure (Future)

### Single Pane of Glass

```
┌─────────────────────────────────────────────────┐
│  Dashboard                                      │
│                                                 │
│  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Tickets Tab     │  │  Alerts Tab      │    │
│  │  (From SN/ME)   │  │  (From Monitors) │    │
│  │                 │  │                 │    │
│  │  - INC0010003   │  │  - High CPU     │    │
│  │  - INC0010004   │  │  - Disk Full    │    │
│  │  - INC0010005   │  │  - Memory High  │    │
│  └─────────────────┘  └─────────────────┘    │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │  Matched View (Future)                  │  │
│  │  Ticket + Alert Correlation             │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Value Proposition

1. **No Duplication**: We don't create tickets - customers already have this
2. **Single Pane of Glass**: View tickets and alerts together
3. **Validation**: Match alerts with tickets to verify issues
4. **State Checking**: Use alerts to verify resolution
5. **Simple**: Clear separation of concerns

## Summary

✅ **Alerts** = From monitoring tools, for validation  
✅ **Tickets** = From ticketing tools, for work items  
✅ **No ticket creation** from monitoring webhooks  
✅ **Single pane of glass** for viewing both  

This is the correct architecture!


