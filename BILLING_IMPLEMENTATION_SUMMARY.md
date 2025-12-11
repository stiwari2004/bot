# Billing System Implementation Summary

## ✅ What's Been Implemented

### 1. Database Models
- **`TenantBillingConfig`**: Stores flexible billing configuration per tenant
  - Fixed monthly cost
  - Per-node billing (enable/disable, cost, manual override)
  - Per-ticket-received billing
  - Per-ticket-resolved billing
  - Per-execution billing
  - Per-API-call billing
  - Per-LLM-token billing
  - Billing cycle configuration

- **`TenantBillingUsage`**: Tracks usage metrics and calculated costs per billing period
  - Tickets received/resolved
  - Execution sessions
  - API calls
  - LLM tokens
  - Active nodes count
  - Calculated costs breakdown

### 2. Billing Services
- **`BillingTracker`**: Tracks usage events
  - `track_ticket_received()` - When ticket is created
  - `track_ticket_resolved()` - When ticket is resolved
  - `track_execution_session()` - When execution session is created
  - `track_api_call()` - When API is called
  - `track_llm_tokens()` - When LLM tokens are consumed
  - `count_active_nodes()` - Counts active InfrastructureConnections

- **`BillingCalculator`**: Calculates monthly bills
  - Reads billing config
  - Gets usage metrics
  - Calculates all cost components
  - Returns detailed breakdown

### 3. API Endpoints (Super Admin Only)
- `GET /api/v1/billing/config/{tenant_id}` - Get billing configuration
- `PUT /api/v1/billing/config/{tenant_id}` - Update billing configuration
- `GET /api/v1/billing/preview/{tenant_id}` - Preview billing calculation
- `GET /api/v1/billing/usage/{tenant_id}` - Get usage metrics

### 4. Automatic Tracking Integration
- **Ticket Creation**: Tracks `ticket_received` when new ticket is created (ticketing_poller.py)
- **Ticket Resolution**: Tracks `ticket_resolved` when ticket status changes to "resolved" (ticket_status_service.py)
- **Execution Sessions**: Tracks execution when session is created (session_service.py)

## 📊 Billing Model Structure

```
Fixed Monthly Cost (₹X,XXX/month)
  ↓
+ Per-Node Cost (₹XXX/node/month) [Optional]
  ↓
+ Per-Ticket-Received Cost (₹XX/ticket) [Optional]
  ↓
+ Per-Ticket-Resolved Cost (₹XX/ticket) [Optional]
  ↓
+ Per-Execution Cost (₹XX/execution) [Optional]
  ↓
+ Per-API-Call Cost (₹X.XX/call) [Optional]
  ↓
+ Per-LLM-Token Cost (₹X.XX/1K tokens) [Optional]
  ↓
= Total Monthly Bill
```

## 🔧 Next Steps

### 1. Run Database Migration
```bash
# Apply the SQL migration
docker-compose exec backend psql -U postgres -d troubleshooting_ai -f /app/sql/tenant_billing_config.sql
```

Or manually run:
```sql
-- Copy contents from backend/sql/tenant_billing_config.sql
```

### 2. Test the Implementation
1. Create billing config for a tenant via API
2. Create some tickets (should track `tickets_received`)
3. Resolve some tickets (should track `tickets_resolved`)
4. Create execution sessions (should track `executions`)
5. Preview billing to see calculated costs

### 3. Super Admin UI (Frontend)
Create Super Admin billing management UI:
- List all tenants
- Configure billing per tenant
- View usage and billing preview
- Generate invoices

### 4. Additional Integrations Needed
- **API Call Tracking**: Add middleware to track API calls
- **LLM Token Tracking**: Integrate with LLM service to track tokens
- **Invoice Generation**: Create invoice PDFs
- **Payment Processing**: Integrate Razorpay/Stripe

## 📝 Example API Usage

### Configure Billing for Tenant
```bash
PUT /api/v1/billing/config/1
{
  "fixed_monthly_cost": 9999,
  "per_node_enabled": true,
  "per_node_cost": 999,
  "per_ticket_received_enabled": true,
  "per_ticket_received_cost": 10,
  "per_ticket_resolved_enabled": true,
  "per_ticket_resolved_cost": 15,
  "per_execution_enabled": true,
  "per_execution_cost": 20,
  "billing_cycle": "monthly",
  "billing_day": 1
}
```

### Preview Billing
```bash
GET /api/v1/billing/preview/1
Response: {
  "fixed_cost": 9999,
  "node_cost": 49950,  # 50 nodes × ₹999
  "ticket_received_cost": 5000,  # 500 tickets × ₹10
  "ticket_resolved_cost": 4500,  # 300 tickets × ₹15
  "execution_cost": 4000,  # 200 executions × ₹20
  "total_cost": 72449
}
```

## 🎯 Key Features

✅ **Flexible Configuration**: Super admin can configure any combination of billing metrics
✅ **Automatic Tracking**: Usage is tracked automatically when events occur
✅ **Node-Based Billing**: Counts active InfrastructureConnections as billable nodes
✅ **Separate Ticket Metrics**: Tracks tickets received and resolved separately
✅ **Real-time Preview**: Can preview billing calculation anytime
✅ **Period-Based**: Tracks usage per billing period (monthly by default)

## ⚠️ Notes

- All billing endpoints require Super Admin authentication
- Usage tracking happens automatically (no manual intervention needed)
- Node count is auto-calculated from InfrastructureConnections (can be overridden)
- Billing calculation happens on-demand (not automatically scheduled yet)


