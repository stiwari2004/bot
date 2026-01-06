# ServiceNow Escalation Flow Implementation

## Overview

This document describes the enhanced escalation flow that integrates with ServiceNow to properly assign tickets, set priorities, and provide detailed context when automated troubleshooting fails.

## Architecture

### Components

1. **EscalationService** (`backend/app/services/escalation_service.py`)
   - Determines escalation level (standard, urgent, critical)
   - Maps escalation levels to ServiceNow assignment groups, priority, urgency, and impact
   - Builds detailed escalation comments with execution context

2. **Enhanced TicketingIntegrationService** (`backend/app/services/ticketing_integration_service.py`)
   - `escalate_ticket()` method now supports escalation levels and execution context
   - `_update_servicenow_ticket()` method updated to set assignment groups, priority, urgency, and impact
   - `_resolve_servicenow_group_sys_id()` helper method to resolve group names to sys_id

3. **ResolutionVerificationService** (`backend/app/services/resolution_verification_service.py`)
   - Updated to pass execution context when escalating
   - Includes failed step details, success rates, and verification results

## Escalation Levels

### Standard Escalation
- **Trigger**: Issue not resolved after automated attempts (default)
- **Assignment Group**: `tier2_support`
- **Priority**: 3 (Moderate)
- **Urgency**: 2 (High)
- **Impact**: 3 (Low)

### Urgent Escalation
- **Trigger**: 
  - High severity tickets
  - 3+ retry attempts
  - Production environment with high severity
- **Assignment Group**: `tier3_support`
- **Priority**: 2 (High)
- **Urgency**: 1 (Critical)
- **Impact**: 2 (Medium)

### Critical Escalation
- **Trigger**: Critical severity tickets
- **Assignment Group**: `on_call_engineers`
- **Priority**: 1 (Critical)
- **Urgency**: 1 (Critical)
- **Impact**: 1 (High)

## Escalation Flow

```
Issue Not Resolved
    ↓
Resolution Verification Service
    ↓
Determine Escalation Level
  - Check ticket severity
  - Count retry attempts
  - Check environment
    ↓
Build Escalation Context
  - Execution summary
  - Failed step details
  - Success rates
    ↓
Update ServiceNow Ticket
  - Status: "In Progress" (state=2)
  - Assignment Group: Based on escalation level
  - Priority: Increased based on level
  - Urgency: Increased based on level
  - Impact: Set based on level
  - Work Notes: Detailed escalation comment
    ↓
ServiceNow Workflow Triggered
  - Notify assigned group
  - Start SLA timer
  - Create related tasks if needed
```

## Escalation Comment Format

The escalation comment includes:

```
🚨 ESCALATION: [LEVEL]

Reason: [Escalation reason]

Context:
  - Severity: [ticket severity]
  - Environment: [ticket environment]
  - Retry Attempts: [retry count]
  - Escalation Level: [standard/urgent/critical]

Execution Summary:
  - Total Steps: [count]
  - Successful: [count]
  - Failed: [count]
  - Success Rate: [percentage]
  - Verification Method: [method]
  - Confidence: [percentage]

Failed Steps:
  1. [Step name]: [Error message]
  2. [Step name]: [Error message]
  ...
```

## Configuration

### Assignment Groups

The escalation service uses the following assignment group names by default:
- `tier2_support` - Standard escalations
- `tier3_support` - Urgent escalations
- `on_call_engineers` - Critical escalations

**Note**: These group names must exist in your ServiceNow instance. The system will attempt to resolve them to sys_id automatically. If a group doesn't exist, the escalation will still proceed but without assignment.

### Customizing Assignment Groups

To customize assignment groups, edit `backend/app/services/escalation_service.py`:

```python
ESCALATION_LEVELS = {
    "standard": {
        "assignment_group": "your_tier2_group_name",
        ...
    },
    "urgent": {
        "assignment_group": "your_tier3_group_name",
        ...
    },
    "critical": {
        "assignment_group": "your_oncall_group_name",
        ...
    }
}
```

## ServiceNow Integration Details

### Group Resolution

The system automatically resolves assignment group names to sys_id by:
1. Checking if the provided name is already a sys_id (UUID format)
2. If not, querying ServiceNow `sys_user_group` table by name
3. Using the resolved sys_id for assignment

### Priority/Urgency/Impact Values

ServiceNow uses numeric values:
- **Priority**: 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning
- **Urgency**: 1=Critical, 2=High, 3=Medium, 4=Low
- **Impact**: 1=High, 2=Medium, 3=Low

## Usage Examples

### Automatic Escalation (Recommended)

The escalation happens automatically when:
- Resolution verification determines issue is not resolved
- Precheck analysis fails or is ambiguous
- Execution fails after retries

No code changes needed - the system handles it automatically.

### Manual Escalation

If you need to escalate manually:

```python
from app.services.ticketing_integration_service import get_ticketing_integration_service

ticketing_service = get_ticketing_integration_service()

await ticketing_service.escalate_ticket(
    db=db,
    ticket=ticket,
    escalation_reason="Manual escalation requested",
    escalation_level="urgent",  # Optional: standard, urgent, critical
    execution_context={  # Optional: provide execution context
        "failed_steps": 3,
        "total_steps": 5,
        "error_message": "Connection timeout"
    }
)
```

## Testing

To test the escalation flow:

1. Create a ticket with high/critical severity
2. Run a runbook that will fail
3. Verify resolution fails
4. Check ServiceNow ticket:
   - Status should be "In Progress"
   - Assignment group should be set based on escalation level
   - Priority/Urgency/Impact should be updated
   - Work notes should contain detailed escalation comment

## Troubleshooting

### Assignment Group Not Set

- Verify the group name exists in ServiceNow
- Check ServiceNow logs for group resolution errors
- Ensure the API user has permissions to read `sys_user_group` table

### Priority/Urgency Not Updated

- Verify the API user has permissions to update incident fields
- Check if ServiceNow business rules are blocking the update
- Review ServiceNow logs for field update errors

### Escalation Comment Not Appearing

- Verify work_notes field is being set in the update request
- Check ServiceNow ACLs for work_notes field
- Review ServiceNow logs for update errors

## Future Enhancements

Potential improvements:
1. Configurable escalation rules per tenant
2. Escalation based on SLA time remaining
3. Integration with ServiceNow workflows for automatic task creation
4. Escalation to multiple groups based on ticket type
5. Escalation history tracking

