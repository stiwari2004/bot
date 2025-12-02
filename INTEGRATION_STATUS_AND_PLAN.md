# Integration Status & Implementation Plan

**Date**: 2025-11-29  
**Focus**: Complete ticketing and monitoring system integrations before going live

---

## 📊 Current Integration Status

### ✅ **Fully Implemented** (Ready to Use)

#### 1. **Zoho Desk** ✅
- **Status**: Complete
- **Features**:
  - ✅ OAuth authentication
  - ✅ API polling for new tickets
  - ✅ Status updates (resolved, closed, in progress)
  - ✅ Comment posting
  - ✅ Webhook support (listed)
- **Files**:
  - `backend/app/services/ticketing_connectors/zoho.py`
  - `backend/app/services/ticketing_connectors/zoho_oauth.py`
  - `backend/app/services/ticketing_poller.py` (includes Zoho)
  - `backend/app/services/ticketing_integration_service.py` (includes Zoho updates)

#### 2. **ManageEngine ServiceDesk** ✅
- **Status**: Complete
- **Features**:
  - ✅ OAuth authentication
  - ✅ API polling for new tickets
  - ✅ Status updates (resolved, closed, in progress)
  - ✅ Webhook support (listed)
- **Files**:
  - `backend/app/services/ticketing_connectors/manageengine.py`
  - `backend/app/services/ticketing_poller.py` (includes ManageEngine)
  - `backend/app/services/ticketing_integration_service.py` (includes ManageEngine updates)

---

### 🟡 **Partially Implemented** (Needs Completion)

#### 3. **ServiceNow** 🟡
- **Status**: Basic connector exists, needs integration
- **What Exists**:
  - ✅ Basic connector class (`ServiceNowConnector` in `connector_service.py`)
  - ✅ Create ticket functionality
  - ✅ Update ticket status functionality
- **What's Missing**:
  - ❌ Not integrated into `ticketing_integration_service.py`
  - ❌ No OAuth/token management
  - ❌ No API polling implementation
  - ❌ No webhook receiver
  - ❌ Not in ticketing poller service
- **Files to Update**:
  - `backend/app/services/ticketing_integration_service.py` (add ServiceNow)
  - `backend/app/services/ticketing_poller.py` (add ServiceNow fetcher)
  - `backend/app/services/ticketing_connectors/servicenow.py` (create new file)

#### 4. **Datadog** 🟡
- **Status**: Basic connector exists
- **What Exists**:
  - ✅ `DatadogConnector` class
  - ✅ Alert to ticket conversion
- **What's Missing**:
  - ❌ Not integrated into ticket ingestion flow
  - ❌ No webhook receiver
  - ❌ No API polling

---

### 🔴 **Not Implemented** (Need to Build)

#### 5. **Zabbix** 🔴 (Priority - User Requested)
- **Status**: Not implemented
- **What's Needed**:
  - ❌ Zabbix connector class
  - ❌ Webhook receiver for Zabbix alerts
  - ❌ API polling for Zabbix events/problems
  - ❌ Authentication (API token or basic auth)
  - ❌ Ticket creation from Zabbix triggers
  - ❌ Status updates back to Zabbix
- **Zabbix Integration Points**:
  - **Webhooks**: Zabbix can send webhooks on trigger events
  - **API**: Zabbix API for polling problems/events
  - **Authentication**: API token (Zabbix 5.4+) or HTTP basic auth

#### 6. **Jira** 🔴
- **Status**: Listed but not implemented
- **What's Needed**:
  - ❌ Jira connector class
  - ❌ OAuth or API token authentication
  - ❌ Webhook receiver
  - ❌ API polling
  - ❌ Create/update issues
  - ❌ Status transitions

#### 7. **Zendesk** 🔴
- **Status**: Listed but not implemented
- **What's Needed**:
  - ❌ Zendesk connector class
  - ❌ API token authentication
  - ❌ Webhook receiver
  - ❌ API polling
  - ❌ Create/update tickets

#### 8. **Prometheus** 🔴
- **Status**: Mentioned but not implemented
- **What's Needed**:
  - ❌ Prometheus Alertmanager webhook receiver
  - ❌ Alert to ticket conversion
  - ❌ (Prometheus itself doesn't have tickets, but Alertmanager does)

#### 9. **PagerDuty** 🔴
- **Status**: Not implemented
- **What's Needed**:
  - ❌ PagerDuty webhook receiver
  - ❌ Incident to ticket conversion
  - ❌ Status updates

---

## 🎯 Implementation Priority

### **Phase 1: Critical Integrations** (This Week)

1. **Zabbix** 🔴 (User Requested)
   - **Estimated Time**: 4-6 hours
   - **Why**: User specifically requested this
   - **Components**:
     - Zabbix webhook receiver
     - Zabbix API connector
     - Ticket creation from triggers
     - Status updates back to Zabbix

2. **ServiceNow** 🟡 (Complete Integration)
   - **Estimated Time**: 2-3 hours
   - **Why**: Connector exists, just needs integration
   - **Components**:
     - Integrate into `ticketing_integration_service.py`
     - Add to ticketing poller
     - Add OAuth/token management
     - Create ServiceNow fetcher class

### **Phase 2: Important Integrations** (Next Week)

3. **Jira** 🔴
   - **Estimated Time**: 4-5 hours
   - **Why**: Common ticketing tool
   - **Components**:
     - Jira connector
     - OAuth or API token auth
     - Webhook receiver
     - API polling

4. **Zendesk** 🔴
   - **Estimated Time**: 3-4 hours
   - **Why**: Common ticketing tool
   - **Components**:
     - Zendesk connector
     - API token auth
     - Webhook receiver
     - API polling

### **Phase 3: Monitoring Integrations** (Later)

5. **Prometheus/Alertmanager** 🔴
6. **PagerDuty** 🔴
7. **Datadog** (Complete integration)

---

## 📋 Implementation Plan: Zabbix Integration

### Step 1: Create Zabbix Connector Class
**File**: `backend/app/services/ticketing_connectors/zabbix.py`

**Features**:
- Zabbix API client
- Authentication (API token or basic auth)
- Fetch problems/events
- Create tickets from triggers
- Update problem status

### Step 2: Add Zabbix Webhook Receiver
**File**: `backend/app/api/v1/endpoints/ticket_ingestion.py` (extend)

**Features**:
- Receive Zabbix webhook alerts
- Parse Zabbix trigger format
- Create tickets from webhooks
- Handle authentication/verification

### Step 3: Add Zabbix to Poller
**File**: `backend/app/services/ticketing_poller.py` (extend)

**Features**:
- Poll Zabbix API for new problems
- Convert problems to tickets
- Handle sync intervals

### Step 4: Add Zabbix Status Updates
**File**: `backend/app/services/ticketing_integration_service.py` (extend)

**Features**:
- Update Zabbix problem status when ticket resolved
- Add acknowledgments
- Close problems

### Step 5: Add Zabbix to UI
**File**: `backend/app/api/v1/endpoints/ticketing_connections.py` (extend)

**Features**:
- Add Zabbix to available tools list
- Connection configuration UI
- Test connection endpoint

---

## 📋 Implementation Plan: ServiceNow Completion

### Step 1: Create ServiceNow Fetcher
**File**: `backend/app/services/ticketing_connectors/servicenow.py` (new)

**Features**:
- OAuth or basic auth
- Fetch incidents from ServiceNow
- Token management
- Error handling

### Step 2: Integrate into Poller
**File**: `backend/app/services/ticketing_poller.py`

**Features**:
- Add ServiceNow fetcher
- Poll for new incidents
- Convert to tickets

### Step 3: Integrate into Status Updates
**File**: `backend/app/services/ticketing_integration_service.py`

**Features**:
- Add `_update_servicenow_ticket()` method
- Map statuses correctly
- Handle comments

### Step 4: Add Webhook Receiver
**File**: `backend/app/api/v1/endpoints/ticket_ingestion.py`

**Features**:
- ServiceNow webhook format
- Parse incident data
- Create tickets

---

## 🔧 Technical Details

### Zabbix Integration Points

#### 1. **Zabbix Webhook Format**
```json
{
  "event": {
    "id": "12345",
    "source": 0,
    "object": 0,
    "objectid": "12345",
    "clock": "1234567890",
    "value": 1,
    "acknowledged": 0,
    "ns": 0,
    "name": "High CPU usage",
    "severity": 4
  },
  "host": {
    "name": "server01",
    "host": "server01.example.com"
  },
  "trigger": {
    "id": "12345",
    "name": "High CPU usage on {HOST.NAME}",
    "description": "CPU usage is above 80%",
    "expression": "{server01:system.cpu.util.avg(5m)}>80",
    "url": "",
    "status": "0",
    "value": "1",
    "priority": "4"
  }
}
```

#### 2. **Zabbix API Endpoints**
- **Get Problems**: `problem.get`
- **Acknowledge Problem**: `event.acknowledge`
- **Get Events**: `event.get`
- **Get Triggers**: `trigger.get`

#### 3. **Authentication**
- **API Token** (Zabbix 5.4+): `X-Auth-Token` header
- **Basic Auth**: Username/password
- **Session**: Login via `user.login`, use session ID

### ServiceNow Integration Points

#### 1. **ServiceNow API**
- **Base URL**: `https://{instance}.service-now.com`
- **Incidents Table**: `/api/now/table/incident`
- **Authentication**: OAuth 2.0 or Basic Auth

#### 2. **Incident States**
- `1` - New
- `2` - In Progress
- `3` - On Hold
- `4` - Resolved
- `5` - Closed
- `6` - Canceled

---

## 📝 TODO List

### Zabbix Integration
- [ ] Create `zabbix.py` connector class
- [ ] Add Zabbix webhook receiver to ticket ingestion
- [ ] Add Zabbix to ticketing poller
- [ ] Add Zabbix status updates to integration service
- [ ] Add Zabbix to available tools list
- [ ] Test Zabbix webhook flow
- [ ] Test Zabbix API polling
- [ ] Test Zabbix status updates

### ServiceNow Completion
- [ ] Create `servicenow.py` fetcher class
- [ ] Add ServiceNow to ticketing poller
- [ ] Add ServiceNow status updates to integration service
- [ ] Add ServiceNow webhook receiver
- [ ] Test ServiceNow OAuth flow
- [ ] Test ServiceNow API polling
- [ ] Test ServiceNow status updates

### General
- [ ] Update API documentation
- [ ] Add integration tests
- [ ] Update UI for new integrations
- [ ] Create setup guides for each integration

---

## 🚀 Next Steps

1. **Start with Zabbix** (user priority)
   - Create connector class
   - Add webhook receiver
   - Test with real Zabbix instance

2. **Complete ServiceNow** (quick win)
   - Integrate existing connector
   - Add to poller and status updates

3. **Add Jira** (common tool)
   - Full implementation

4. **Add Zendesk** (common tool)
   - Full implementation

---

## 📚 Resources

### Zabbix
- **API Documentation**: https://www.zabbix.com/documentation/current/manual/api
- **Webhook Format**: https://www.zabbix.com/documentation/current/manual/config/notifications/media/webhook
- **Authentication**: https://www.zabbix.com/documentation/current/manual/api/reference/user/login

### ServiceNow
- **REST API**: https://developer.servicenow.com/dev.do#!/reference/api/rome/rest/c_TableAPI
- **OAuth**: https://developer.servicenow.com/dev.do#!/reference/api/rome/rest/c_OAuth2API
- **Webhooks**: https://docs.servicenow.com/bundle/rome-platform-integration/page/integration/web-services/concept/webhook.html

### Jira
- **REST API**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **Webhooks**: https://developer.atlassian.com/cloud/jira/platform/webhooks/

---

## ✅ Success Criteria

An integration is "complete" when:
1. ✅ Can receive tickets via webhook
2. ✅ Can poll for new tickets via API
3. ✅ Can update ticket status in external system
4. ✅ Can add comments/notes
5. ✅ Authentication works (OAuth/API token)
6. ✅ Error handling is robust
7. ✅ Logging is comprehensive
8. ✅ Tested with real system

---

**Ready to start?** Let's begin with Zabbix integration! 🚀



