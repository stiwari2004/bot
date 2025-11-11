# Phase 2 Agent POC - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose installed
- Backend and frontend services running

### Starting the Services

```bash
# Start all services
docker-compose up -d

# Or start individually
docker-compose up backend frontend postgres
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🎯 Testing the Agent Flow

### Step 1: Create a Ticket

```bash
curl -X POST http://localhost:8000/api/v1/tickets/demo/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection timeout",
    "description": "Unable to connect to PostgreSQL database on server db-prod-01",
    "severity": "high",
    "environment": "prod",
    "source": "prometheus"
  }'
```

Expected response:
```json
{
  "ticket_id": 1,
  "status": "analyzing",
  "classification": "true_positive",
  "confidence": 0.85,
  "reasoning": "..."
}
```

### Step 2: Start Execution

```bash
curl -X POST http://localhost:8000/api/v1/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "runbook_id": 1,
    "issue_description": "Database connection timeout",
    "ticket_id": 1
  }'
```

Expected response:
```json
{
  "session_id": 1,
  "status": "waiting_approval",
  "waiting_for_approval": true,
  "approval_step_number": 1,
  "current_step": 0
}
```

### Step 3: Approve Step (via UI or API)

**Via UI:**
1. Navigate to "Agent Dashboard" tab in frontend
2. Click "Approve & Continue" for the pending approval

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/agent/1/approve-step?step_number=1" \
  -H "Content-Type: application/json" \
  -d '{
    "approve": true,
    "notes": "Looks good to proceed"
  }'
```

### Step 4: Check Execution Status

```bash
curl http://localhost:8000/api/v1/agent/1
```

## 📊 Monitoring

### View Pending Approvals

```bash
curl http://localhost:8000/api/v1/agent/pending-approvals
```

### View All Tickets

```bash
curl http://localhost:8000/api/v1/tickets/demo/tickets
```

## 🎨 Frontend Features

### Agent Dashboard
- **Location**: Sidebar → "Agent Dashboard"
- **Features**:
  - ✅ Real-time pending approvals list
  - ✅ One-click approve/reject
  - ✅ Execution detail modal
  - ✅ Step-by-step progress view
  - ✅ Auto-refresh every 5 seconds

### Ticket Analysis
- **Location**: Sidebar → "Ticket Analysis"
- Analyze tickets and find matching runbooks

### Execution History
- **Location**: Sidebar → "Execution History"
- View all past execution sessions

## 🔧 Troubleshooting

### Backend Not Starting
```bash
# Check logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose ps postgres

# Restart database
docker-compose restart postgres
```

### Frontend Not Loading
```bash
# Check logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

## 📝 Notes

- All endpoints work without authentication for POC (using tenant_id=1)
- Credentials are stored encrypted in database (not Vault)
- Execution uses local connector by default
- For production, migrate to proper authentication and credential vault

## 🎉 Next Steps

1. **Test End-to-End**: Create ticket → Start execution → Approve step → Verify completion
2. **Add More Connectors**: Configure SSH/Database connectors for real infrastructure
3. **Add Credentials**: Test with real infrastructure credentials
4. **Enhance UI**: Add more execution monitoring features




