# Production Roadmap: Connector-Based Auto-Analysis

## Overview

This document outlines the planned production enhancements for the IT Troubleshooting RAG system, specifically focusing on automatic ticket analysis through system connectors.

## Current State (Phase 1 - POC)

### Manual Analysis
- Users manually enter issue descriptions via the Ticket Analyzer UI
- System searches existing runbooks and provides recommendations
- Suitable for pilot testing and small-scale evaluation

### Limitations
- No automatic ticket ingestion
- No connection to external systems
- No batch processing of historical tickets
- Manual trigger for gap analysis

## Phase 2: Agent with Human Approval

### Planned Connectors

#### 1. Ticketing Systems
**Priority: High**

- **ServiceNow**
  - Connection: REST API with OAuth2
  - Data: Incidents, Change Requests, Service Requests
  - Triggers: New ticket created, ticket updated
  - Frequency: Polling every 5 minutes or webhook-based

- **Jira**
  - Connection: REST API with API tokens
  - Data: Issues, Epics, Stories (filtered for infrastructure)
  - Triggers: Issue created, status change to "In Progress"
  - Frequency: Webhook-driven

- **ManageEngine ServiceDesk Plus**
  - Connection: REST API with API key
  - Data: Requests, Incidents, Change Requests
  - Triggers: Ticket creation, assignment
  - Frequency: Real-time webhooks

- **BMC Remedy**
  - Connection: REST API with authentication
  - Data: Incident, Problem, Change records
  - Triggers: Ticket lifecycle events
  - Frequency: Event-driven notifications

#### 2. Monitoring Systems
**Priority: Medium**

- **Datadog**
  - Connection: REST API with API/App keys
  - Data: Alerts, Monitors, Events
  - Triggers: Alert fired, monitor status changed
  - Use Case: Proactive runbook suggestions when alerts trigger

- **SolarWinds**
  - Connection: REST API with credentials
  - Data: Alerts, Events, Performance metrics
  - Triggers: Alert conditions met
  - Use Case: Automatic incident creation with suggested runbook

- **Zabbix**
  - Connection: HTTP API with authentication
  - Data: Triggers, Events, Problems
  - Triggers: Trigger fired
  - Use Case: Real-time incident correlation with runbooks

#### 3. Knowledge Bases
**Priority: Medium**

- **ServiceNow Knowledge Base**
  - Connection: REST API
  - Data: Knowledge articles, KBs
  - Use Case: Enrich runbook generation with existing articles
  - Frequency: Periodic sync (daily/hourly)

- **Confluence**
  - Connection: REST API with authentication
  - Data: Pages, spaces, attachments
  - Use Case: Extract existing procedures and documentation
  - Frequency: Initial bulk import, then incremental updates

- **ManageEngine KnowledgeBase**
  - Connection: REST API
  - Data: Knowledge articles, solutions
  - Use Case: Reference existing solutions during runbook creation
  - Frequency: Periodic sync

## Auto-Analysis Workflow

### 1. Ticket Ingestion
```
Ticket System Connector → Queue → Parser → Database
```

**Steps:**
1. Connector polls/webhook receives new ticket
2. Parse ticket metadata (title, description, assignee, severity)
3. Store in `tickets` table (new)
4. Queue for analysis

### 2. Automatic Analysis
```
Ticket → Runbook Search → Confidence Check → Recommendation Engine
```

**Logic:**
```python
# Pseudo-code
async def analyze_ticket(ticket: Ticket):
    # Search for similar runbooks
    matches = await runbook_search.search_similar_runbooks(
        issue_description=ticket.description,
        tenant_id=ticket.tenant_id,
        top_k=5
    )
    
    # Check confidence threshold
    best_match = matches[0] if matches else None
    confidence = best_match.confidence_score if best_match else 0.0
    
    if confidence >= THRESHOLD_EXISTING:
        # Auto-associate ticket with existing runbook
        return {
            'action': 'link_runbook',
            'runbook_id': best_match.id,
            'confidence': confidence
        }
    elif confidence >= THRESHOLD_PARTIAL:
        # Flag for human review
        return {
            'action': 'flag_review',
            'matches': matches,
            'confidence': confidence
        }
    else:
        # Flag for new runbook generation
        return {
            'action': 'generate_runbook',
            'ticket_id': ticket.id
        }
```

### 3. Runbook Generation Queue
```
High Confidence Gap → Auto-Generate → Send for Approval
Low Confidence Gap → Manual Trigger
```

**Decision Tree:**
- If confidence < 50%: Queue for manual runbook generation
- If confidence 50-70%: Prompt user to review and approve generation
- If confidence > 70%: Auto-generate and send for approval

### 4. Execution Tracking
```
Runbook Execution → Feedback Loop → Success Metrics → Improve Confidence
```

## Data Models (New Tables)

### Tickets Table
```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255),  -- From ticketing system
    source_system VARCHAR(50),  -- 'servicenow', 'jira', etc.
    title TEXT NOT NULL,
    description TEXT,
    status VARCHAR(50),
    severity VARCHAR(20),
    assignee VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    tenant_id INTEGER REFERENCES tenants(id),
    UNIQUE(external_id, source_system, tenant_id)
);
```

### Ticket Runbook Links
```sql
CREATE TABLE ticket_runbook_links (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id),
    runbook_id INTEGER REFERENCES runbooks(id),
    confidence_score NUMERIC(3,2),
    linked_automatically BOOLEAN DEFAULT FALSE,
    linked_at TIMESTAMP DEFAULT NOW(),
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP
);
```

### Connector Configurations
```sql
CREATE TABLE connector_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    connector_type VARCHAR(50),  -- 'servicenow', 'datadog', etc.
    name VARCHAR(255),
    config_json JSONB,  -- API keys, endpoints, credentials (encrypted)
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    last_successful_sync_at TIMESTAMP,
    sync_frequency_minutes INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Implementation Phases

### Phase 2.1: ServiceNow Connector
- Implement ServiceNow REST API integration
- Parse incident data
- Auto-analyze and link tickets to runbooks
- **Timeline: 2-3 weeks**

### Phase 2.2: Batch Analysis Tool
- Build admin interface for bulk ticket import (CSV/JSON)
- Analyze historical tickets for coverage gaps
- Generate gap report
- **Timeline: 1 week**

### Phase 2.3: Datadog + SolarWinds Integration
- Connect monitoring alerts to ticket creation
- Proactive runbook suggestions
- **Timeline: 2-3 weeks**

### Phase 2.4: KB Enrichment
- Extract knowledge from ServiceNow KB, Confluence
- Use as context for runbook generation
- **Timeline: 2 weeks**

### Phase 2.5: Connector Framework
- Generic connector architecture
- Plugin-based system for easy addition
- **Timeline: 3-4 weeks**

## Security Considerations

1. **Credential Management**
   - Encrypt API keys/credentials at rest
   - Use secret management service (AWS Secrets Manager, HashiCorp Vault)
   - Rotate credentials regularly

2. **Data Isolation**
   - Enforce RLS (Row-Level Security) in PostgreSQL
   - Tenant-aware API calls
   - Audit logging for all connector activities

3. **Access Control**
   - Role-based access to connector configurations
   - OAuth2 flow for user consent (ServiceNow, Jira)

## Monitoring & Observability

### Metrics to Track
- Tickets ingested per hour/day
- Auto-link success rate
- Connector sync failures
- Average confidence scores
- Manual intervention rate

### Alerts
- Connector sync failure > 3 attempts
- High volume of unlinked tickets
- Confidence scores dropping below threshold
- API rate limit approaching

## Rollout Strategy

### 1. Pilot Program
- Select 1-2 early adopter customers
- Deploy ServiceNow connector only
- Gather feedback and iterate

### 2. Beta Release
- Add Jira connector
- Expand to 5-10 customers
- Refine confidence thresholds based on real data

### 3. General Availability
- All connectors available
- Self-service onboarding
- Documentation and training materials

## Success Criteria

- **Coverage**: 70%+ of tickets automatically linked to runbooks
- **Accuracy**: < 10% false positive rate on auto-links
- **Time to Resolution**: 20% reduction in MTTR
- **Adoption**: 50+ active customers within 6 months

## Future Enhancements (Phase 3)

### Autonomous Execution
- Auto-execute runbooks for low-risk issues
- Self-healing capabilities
- Automatic escalation on failure

### ML Improvements
- Fine-tune confidence models based on feedback
- Learn from successful runbook associations
- Predictive ticket routing

### Advanced Analytics
- Trend analysis across ticket patterns
- Proactive runbook generation
- Anomaly detection in ticket volumes

---

**Last Updated:** November 2025  
**Status:** Planning Phase  
**Next Review:** After Phase 1 completion

