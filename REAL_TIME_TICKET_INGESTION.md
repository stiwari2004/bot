# Real-Time Ticket Ingestion - How It Works

## 🎯 Overview

The system supports **real-time ticket ingestion** from external ticketing tools via webhooks. The CSV upload feature is **only for testing/demo purposes**.

---

## 📥 Real-Time Ticket Flow

### 1. **Webhook Endpoint** (Primary Method)
```
External Ticketing Tool → Webhook → POST /api/v1/tickets/webhook/{source}
```

**Supported Sources:**
- `servicenow` - ServiceNow webhooks
- `zendesk` - Zendesk webhooks  
- `jira` - Jira webhooks
- `prometheus` - Prometheus alerts
- `datadog` - Datadog alerts
- `pagerduty` - PagerDuty incidents
- `custom` - Custom webhook format

**Example:**
```bash
# ServiceNow webhook
curl -X POST http://localhost:8000/api/v1/tickets/webhook/servicenow \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection timeout",
    "description": "Unable to connect to PostgreSQL",
    "severity": "high",
    "environment": "prod",
    "service": "database",
    "ci_association": "prod-db-01"
  }'
```

### 2. **What Happens When Ticket Arrives**

```
1. Webhook Received
   ↓
2. Ticket Normalized & Created in Database
   ↓
3. False Positive Detection (LLM Analysis)
   ↓
4. If True Positive:
   - Search for Matching Runbook
   - Extract CI/Server Name
   - Match to Infrastructure Connection
   - Check Execution Mode (HIL vs Auto)
   - Auto-Start Execution (if Auto mode & confidence ≥0.8)
   ↓
5. Ticket Status Updated
   ↓
6. Ticket Appears in "Tickets" Tab (Real-time)
```

---

## 📊 Where to See Tickets

### **Tickets Tab** (Main View)
- **Location**: Click "Tickets" tab in navigation
- **Features**:
  - Lists ALL tickets from all sources
  - Real-time updates (auto-refreshes every 10 seconds)
  - Filter by status, severity, source
  - Search tickets
  - View ticket details
  - See matched runbooks
  - Execute runbooks directly

### **Ticket Sources Displayed**
Each ticket shows:
- **Source**: Which tool sent it (ServiceNow, Zendesk, Prometheus, etc.)
- **Status**: Current status (open, analyzing, in_progress, resolved, etc.)
- **Severity**: critical, high, medium, low
- **Classification**: false_positive, true_positive, uncertain
- **Created At**: When ticket was received

---

## 🔌 Setting Up Real-Time Ingestion

### For ServiceNow:
1. Go to ServiceNow → System Webhooks
2. Create new webhook
3. URL: `http://your-server:8000/api/v1/tickets/webhook/servicenow`
4. Method: POST
5. Trigger on: Incident created/updated

### For Zendesk:
1. Go to Zendesk → Admin → Webhooks
2. Create new webhook
3. URL: `http://your-server:8000/api/v1/tickets/webhook/zendesk`
4. Method: POST
5. Trigger on: Ticket created

### For Prometheus:
1. Configure Alertmanager
2. Add webhook receiver
3. URL: `http://your-server:8000/api/v1/tickets/webhook/prometheus`

---

## 🧪 CSV Upload (Testing Only)

The "Upload Tickets" tab is **only for testing**:
- Create test tickets quickly
- Test the flow without external tools
- Demo purposes

**For Production**: Use webhooks from your ticketing tools!

---

## 📝 Ticket Data Structure

When a ticket arrives via webhook, it's stored with:

```json
{
  "id": 123,
  "source": "servicenow",
  "title": "Database connection timeout",
  "description": "Unable to connect to PostgreSQL",
  "severity": "high",
  "environment": "prod",
  "service": "database",
  "status": "open",
  "classification": "true_positive",
  "meta_data": {
    "ci_association": "prod-db-01",
    "connection_config": {...}
  },
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

## 🔍 How to Verify Real-Time Ingestion

1. **Send Test Webhook**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tickets/webhook/servicenow \
     -H "Content-Type: application/json" \
     -d '{"title": "Test Ticket", "description": "Test", "severity": "medium"}'
   ```

2. **Check Tickets Tab**:
   - Open "Tickets" tab
   - New ticket should appear within 10 seconds
   - Shows source, status, severity

3. **Check Logs**:
   - Backend logs show: "Ticket {id} received from {source}"
   - Analysis logs show classification result

---

## 🚀 Next Steps

1. **Configure Your Ticketing Tool** to send webhooks
2. **View Tickets** in the "Tickets" tab
3. **Monitor Real-Time** - tickets appear automatically
4. **Execute Runbooks** directly from tickets

**The CSV upload is just for testing - use webhooks for production!**



