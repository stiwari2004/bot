# Current System Flow - Review Document

## 🎯 Complete End-to-End Flow (As Designed)

### Phase 1: Ticket Ingestion & Analysis

```
1. Ticket Arrives
   ├─ Via Webhook: POST /api/v1/tickets/webhook/{source}
   ├─ Via CSV Upload: POST /api/v1/tickets/upload-csv
   └─ Via API: POST /api/v1/tickets/demo/ticket
   
2. Ticket Normalization
   └─ Convert various formats (Prometheus, Datadog, etc.) → Standard format
   
3. Ticket Analysis (False Positive Detection)
   ├─ LLM analyzes ticket content
   ├─ Classification: false_positive | true_positive | uncertain
   └─ Confidence score: 0.0-1.0
   
4. False Positive Handling
   └─ If false_positive + confidence ≥0.8 → Close ticket automatically
```

### Phase 2: Runbook Matching & Execution

```
5. Runbook Search (if true_positive)
   ├─ Semantic search for matching runbooks
   ├─ Multi-factor confidence scoring:
   │   ├─ Semantic similarity
   │   ├─ Keyword match
   │   ├─ Historical success rate
   │   └─ Recency of use
   └─ Returns: runbook_id, confidence_score
   
6. Auto-Execution Decision
   ├─ If confidence ≥0.8 → Auto-start execution
   └─ Else → Manual runbook selection needed
   
7. Execution Session Creation
   ├─ Parse runbook into steps (prechecks, main, postchecks)
   ├─ Create ExecutionSession
   ├─ Create ExecutionStep records
   └─ Link to ticket (ticket_id)
   
8. Ticket Status Update
   └─ Status: analyzing → in_progress
```

### Phase 3: Step-by-Step Execution

```
9. Execute Steps Sequentially
   ├─ For each step:
   │   ├─ Check if requires_approval
   │   │   ├─ Yes → Wait for human approval
   │   │   │   ├─ Status: waiting_approval
   │   │   │   ├─ Show in Agent Dashboard
   │   │   │   └─ WebSocket notification
   │   │   └─ No → Execute immediately
   │   │
   │   ├─ Get connection config
   │   │   ├─ From ticket metadata
   │   │   ├─ From infrastructure connection
   │   │   └─ Default: local connector
   │   │
   │   ├─ Execute command via connector
   │   │   ├─ SSH Connector
   │   │   ├─ Database Connector
   │   │   ├─ API Connector
   │   │   └─ Local Connector
   │   │
   │   ├─ Capture output/error
   │   └─ Update step status
   │
   └─ If step fails → Stop execution, mark session as failed
```

### Phase 4: Human Approval Workflow

```
10. Approval Request
    ├─ Step requires_approval = true
    ├─ Session status = waiting_approval
    ├─ Approval step number recorded
    └─ Notification sent (WebSocket)
    
11. Human Review (Agent Dashboard)
    ├─ View pending approvals
    ├─ See runbook, step, command details
    ├─ Approve or Reject
    └─ Add notes (optional)
    
12. Approval Processing
    ├─ If Approved:
    │   ├─ Execute the step
    │   ├─ Continue to next step
    │   └─ Update session status
    └─ If Rejected:
        ├─ Mark session as failed/rejected
        └─ Update ticket status
```

### Phase 5: Resolution & Verification

```
13. Execution Completion
    ├─ All steps completed successfully
    ├─ Session status = completed
    └─ Calculate duration
    
14. Resolution Verification
    ├─ Analyze step success rates
    ├─ Check postcheck results
    ├─ Calculate confidence score
    └─ Determine if issue resolved
    
15. Ticket Status Update
    ├─ If resolved (high confidence) → Status: resolved
    ├─ If uncertain (medium confidence) → Status: in_progress (manual review)
    └─ If failed (low confidence) → Status: escalated
    
16. External System Update (if configured)
    └─ Update ticketing system (ServiceNow, etc.)
```

---

## 📊 Current Implementation Status

### ✅ Fully Implemented

1. **Ticket Ingestion**
   - Webhook receiver ✅
   - CSV upload ✅
   - Demo ticket API ✅
   - Normalization ✅

2. **Ticket Analysis**
   - LLM-based false positive detection ✅
   - Classification & confidence scoring ✅
   - Auto-close false positives ✅

3. **Runbook Search**
   - Semantic search ✅
   - Multi-factor confidence ✅
   - Auto-match tickets to runbooks ✅

4. **Execution Engine**
   - Step-by-step execution ✅
   - Approval checkpoints ✅
   - Connection config handling ✅
   - Error handling ✅

5. **Human Approval**
   - Pending approvals API ✅
   - Approve/reject endpoints ✅
   - Agent Dashboard UI ✅
   - WebSocket notifications ✅

6. **Resolution Verification**
   - Step success analysis ✅
   - Confidence calculation ✅
   - Ticket status updates ✅

7. **Ticket Status Management**
   - Status updates throughout lifecycle ✅
   - Integration with execution engine ✅

### ⚠️ Partially Implemented

1. **Infrastructure Connectors**
   - Local: ✅ Fully working
   - SSH: ⚠️ Basic (uses ssh command, needs asyncssh)
   - Database: ⚠️ Basic (needs real drivers)
   - API: ⚠️ Basic (needs enhancement)

2. **External Tool Connectors**
   - Datadog: ⚠️ Basic (fetch alerts only)
   - ServiceNow: ⚠️ Basic (create/update tickets)
   - Prometheus: ✅ Webhook receiver
   - Others: ❌ Not implemented

3. **Credential Management**
   - Database storage: ✅
   - Encryption: ✅ (Fernet)
   - UI: ❌ Not implemented
   - Vault integration: ❌ Not implemented

### ❌ Not Implemented

1. **Connector Configuration UI**
   - No UI for managing credentials
   - No UI for infrastructure connections
   - No UI for external tool configuration

2. **Real Infrastructure Access**
   - SSH needs asyncssh library
   - Database needs proper drivers
   - Cloud APIs not integrated

3. **Complete External Integrations**
   - Zabbix, SolarWinds, ManageEngine
   - Zendesk, BMC Remedy
   - Bidirectional sync with ticketing systems

4. **Advanced Features**
   - Connection pooling
   - Health checks
   - Retry logic
   - Rollback mechanisms

---

## 🔄 Current Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TICKET INGESTION                         │
│  Webhook / CSV / API → Normalize → Analyze → Classify      │
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
                    │ Confidence ≥0.8? │
                    └─────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
      [Auto-Execute]          [Manual Selection]
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              EXECUTION SESSION                              │
│  Create Session → Parse Steps → Update Ticket Status       │
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
        │  [Continue]              [Fail & Stop]
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

## 🤔 Discussion Points

### 1. **Ticket → Runbook Matching**
**Current**: Auto-executes if confidence ≥0.8
**Question**: 
- Should we always require manual confirmation?
- Should there be different thresholds for different severities?
- Should we support multiple runbook suggestions?

### 2. **Approval Workflow**
**Current**: Step-by-step approval
**Question**:
- Should we support batch approvals?
- Should we support approval delegation?
- Should we support approval timeouts/auto-escalation?

### 3. **Infrastructure Access**
**Current**: Basic connectors, connection via ticket metadata
**Question**:
- How should runbooks specify which infrastructure to use?
- Should we support connection discovery?
- How do we handle multi-environment (prod/staging/dev)?

### 4. **External Tool Integration**
**Current**: Basic Datadog/ServiceNow
**Question**:
- Should we prioritize specific tools?
- How should we handle bidirectional sync?
- Should we support custom webhook formats?

### 5. **Error Handling & Recovery**
**Current**: Basic error handling
**Question**:
- Should we support automatic retries?
- Should we support rollback mechanisms?
- How should we handle partial failures?

### 6. **Credential Management**
**Current**: Database storage with encryption
**Question**:
- Should we build UI now or use API?
- Should we integrate Vault immediately?
- How should we handle credential rotation?

---

## 📋 Proposed Adjustments to Discuss

1. **Runbook Matching Strategy**
   - Add manual confirmation step before auto-execution
   - Support multiple runbook suggestions
   - Add severity-based thresholds

2. **Infrastructure Connection**
   - Add connection configuration UI
   - Support connection templates
   - Add connection testing/validation

3. **Approval Workflow**
   - Add approval delegation
   - Add approval timeouts
   - Add batch approval option

4. **External Tool Integration**
   - Prioritize most-used tools first
   - Add webhook configuration UI
   - Support custom integrations

5. **Error Handling**
   - Add retry logic
   - Add rollback support
   - Add failure notifications

---

## 🎯 Questions for You

1. **What's your priority?**
   - Complete connector UI?
   - Enhance specific external tool integrations?
   - Improve error handling?
   - Add new features?

2. **How should runbooks specify infrastructure?**
   - In runbook metadata?
   - Via connection name?
   - Via ticket metadata?

3. **What external tools are most critical?**
   - Which monitoring tools?
   - Which ticketing tools?

4. **Approval workflow preferences?**
   - Always require approval?
   - Auto-approve low-risk steps?
   - Support delegation?

5. **Infrastructure access model?**
   - Per-runbook configuration?
   - Per-ticket configuration?
   - Global connection pool?

Let's discuss these points and then make the adjustments!




