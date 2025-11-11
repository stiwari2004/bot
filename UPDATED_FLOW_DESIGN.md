# Updated Flow Design - Based on User Feedback

## 🎯 Key Design Decisions

### 1. **Runbook Matching Mode Selection**
- **Settings**: Add mode selection (HIL mode vs Auto mode)
- **HIL Mode**: Always require manual approval before execution
- **Auto Mode**: Use configurable threshold (default: 0.8) for auto-execution
- **Implementation**: Add `execution_mode` setting (stored in config or user preferences)

### 2. **Infrastructure Access from Tickets**
- **CI/Server Name Extraction**: Parse from ticket details:
  - `ticket.meta_data.ci_association` (if present)
  - `ticket.description` (extract server/CI names via regex/LLM)
  - `ticket.service` field
- **Connection Resolution**: 
  - Match extracted CI/server name to `InfrastructureConnection` table
  - Fallback to ticket metadata connection config
  - Default to local connector if no match

### 3. **Approval Workflow**
- **Current**: Step-by-step approval ✅ (Keep as-is)
- **Enhancement**: Add approval delegation and timeouts (future)

### 4. **External Tool Priority**
- **Monitoring**: SolarWinds, Zabbix, Datadog (prioritize these)
- **Ticketing**: ServiceNow (already basic), then Zendesk, BMC Remedy

### 5. **Rollback Mechanism**
- **Full Rollback**: When execution fails, rollback ALL changes made
- **Implementation**: 
  - Track all executed commands in reverse order
  - Execute rollback commands in reverse sequence
  - Store rollback commands in runbook metadata

### 6. **Frontend UI Improvements**
- **New Component**: "Tickets" tab showing all tickets
- **Features**:
  - List all tickets with status, severity, classification
  - View ticket details
  - See matched runbooks for each ticket
  - Execute runbook from ticket
  - Create new runbook from ticket
  - Filter by status, severity, source
- **Integration**: 
  - Link tickets to execution sessions
  - Show execution status on ticket card
  - Quick actions: Execute, View Runbook, Create Runbook

---

## 📊 Updated Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TICKET INGESTION                         │
│  Webhook / CSV / API → Normalize → Extract CI/Server Info   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Extract CI/Server     │
            │  from ticket metadata │
            └───────┬───────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              TICKET ANALYSIS                                 │
│  False Positive Detection → Classification                   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  False Positive?       │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   [Close Ticket]      [Search Runbook]
                              │
                              ▼
                    ┌─────────────────┐
                    │ Match Found?     │
                    └─────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
      ┌───────────────┐      ┌───────────────┐
      │ Check Mode    │      │ Manual        │
      │ (HIL/Auto)    │      │ Selection     │
      └───────┬───────┘      └───────────────┘
              │
      ┌───────┴───────┐
      │               │
      ▼               ▼
  [HIL Mode]    [Auto Mode]
      │               │
      │               ▼
      │      ┌─────────────────┐
      │      │ Confidence ≥0.8? │
      │      └─────┬───────────┘
      │            │
      │    ┌───────┴───────┐
      │    │               │
      │    ▼               ▼
      │ [Wait Approval] [Auto-Execute]
      │    │
      └────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              EXECUTION SESSION                              │
│  Create Session → Resolve Infrastructure Connection         │
│  → Parse Steps → Update Ticket Status                       │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Step Requires         │
            │  Approval?             │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
  [Wait Approval]        [Execute Step]
        │                       │
        │                       ▼
        │              ┌─────────────────┐
        │              │ Step Success?    │
        │              └─────┬───────────┘
        │                    │
        │        ┌───────────┴───────────┐
        │        │                       │
        │        ▼                       ▼
        │  [Continue]              [Rollback ALL]
        │                                    │
        │                                    ▼
        │                          ┌─────────────────┐
        │                          │ Execute Rollback │
        │                          │ Commands Reverse │
        │                          └─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              HUMAN APPROVAL                                │
│  Agent Dashboard → Review → Approve/Reject                 │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Approved?             │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
  [Execute Step]        [Mark Failed]
        │                       │
        │                       ▼
        │              ┌─────────────────┐
        │              │ Rollback ALL     │
        │              └─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              ALL STEPS COMPLETE?                           │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Yes                  │
            └───────┬───────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              RESOLUTION VERIFICATION                       │
│  Analyze Steps → Calculate Confidence → Update Ticket      │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Issue Resolved?       │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
  [Resolved]            [Escalated/Review]
```

---

## 🎨 Frontend UI Structure

### Main Navigation
1. **Tickets** (NEW) - View all tickets, execute runbooks
2. **Agent Dashboard** - Pending approvals (existing)
3. **Ticket Analysis** - Analyze issues (existing)
4. **Upload Tickets** - CSV upload (existing)
5. **View Runbooks** - List runbooks (existing)
6. **Generate Runbook** - Create new (existing)
7. **Execution History** - Past executions (existing)
8. **Settings** (NEW) - Mode selection, connectors, etc.

### Tickets Tab Features
- **Ticket List View**:
  - Cards showing: Title, Status, Severity, Source, Classification
  - Filter by: Status, Severity, Source, Date
  - Sort by: Date, Severity, Status
  - Search by: Title, Description

- **Ticket Detail View**:
  - Full ticket information
  - Extracted CI/Server information
  - Matched runbooks (with confidence scores)
  - Execution history for this ticket
  - Quick actions:
    - Execute Runbook
    - Create New Runbook
    - View Runbook Details
    - Update Status

- **Ticket Card Actions**:
  - View Details (modal or page)
  - Execute Runbook (if matched)
  - Create Runbook (if no match)
  - View Execution Status

---

## 🔧 Implementation Plan

### Phase 1: Core Flow Updates
1. ✅ Add execution mode setting (HIL vs Auto)
2. ✅ Extract CI/Server from ticket metadata
3. ✅ Match CI/Server to infrastructure connections
4. ✅ Implement full rollback mechanism

### Phase 2: Frontend UI
1. ✅ Create Tickets component (list view)
2. ✅ Create Ticket Detail component
3. ✅ Integrate runbook matching/execution
4. ✅ Add Settings component for mode selection

### Phase 3: External Tools
1. ⏳ Prioritize SolarWinds connector
2. ⏳ Prioritize Zabbix connector
3. ⏳ Enhance Datadog connector

---

## 📝 API Endpoints Needed

### Tickets
- `GET /api/v1/tickets/demo/tickets` ✅ (exists)
- `GET /api/v1/tickets/demo/tickets/{ticket_id}` ⚠️ (need to add)
- `POST /api/v1/tickets/demo/tickets/{ticket_id}/execute` ⚠️ (need to add)
- `GET /api/v1/tickets/demo/tickets/{ticket_id}/runbooks` ⚠️ (need to add)

### Settings
- `GET /api/v1/settings/execution-mode` ⚠️ (need to add)
- `POST /api/v1/settings/execution-mode` ⚠️ (need to add)

### Infrastructure
- `POST /api/v1/infrastructure/extract-ci` ⚠️ (need to add - extract CI from ticket)

---

## 🚀 Next Steps

1. **Implement execution mode setting**
2. **Create Tickets UI component**
3. **Add CI/Server extraction logic**
4. **Implement rollback mechanism**
5. **Add Settings UI**

Let's start implementing!



