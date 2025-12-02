# Monitoring Connectors - Correct Architecture

## Key Insight

**Customers already have monitoring → ticketing tool integration configured!**

We should NOT duplicate this. Instead, we add value by:
1. Polling tickets from ticketing tools (already implemented ✅)
2. Using monitoring alerts for validation/verification
3. Matching tickets with alerts for context
4. Executing runbooks and updating tickets

## Correct Flow

```
Customer's Existing Setup (Already Configured):
┌──────────────┐         ┌──────────────┐
│  Monitoring  │────────▶│  Ticketing   │
│   Tool       │ Alert   │    Tool      │
│ (Azure/etc)  │────────▶│(ServiceNow/  │
└──────────────┘         │ ManageEngine)│
                         └──────────────┘
                                │
                                │ Ticket Created
                                ▼
                         ┌──────────────┐
                         │  Our System  │
                         │  (Polling)   │
                         └──────────────┘
                                │
                                │ Get Ticket
                                ▼
                         ┌──────────────┐
                         │  Match with  │
                         │   Alerts     │
                         │ (Validation) │
                         └──────────────┘
                                │
                                │ Execute Runbook
                                ▼
                         ┌──────────────┐
                         │  Resolve     │
                         │  & Update    │
                         └──────────────┘
```

## What Monitoring Connectors Are For

### ✅ Primary Use: Validation & State Checking

1. **Match Tickets with Alerts**
   - When a ticket comes in from ServiceNow/ManageEngine
   - Check if corresponding alert exists in monitoring tool
   - Validate the issue is still active
   - Provide context (metrics, logs, etc.)

2. **Pre-Execution Verification**
   - Before running a runbook, check current state
   - Verify the issue still exists
   - Check if metrics show the problem is already resolved

3. **Post-Execution Verification**
   - After runbook execution, verify issue is resolved
   - Query monitoring tool to confirm metrics are back to normal
   - Auto-close ticket if verification passes

4. **False Positive Detection**
   - Compare ticket with alert data
   - Check if alert was a false positive
   - Auto-close if false positive detected

### ❌ NOT For: Creating Tickets

- Customers already have this configured
- We would just duplicate their existing setup
- No value-add in creating tickets from alerts

## Implementation

### Current Status

✅ **Ticketing Tool Polling** (Already Working)
- ServiceNow polling ✅
- ManageEngine polling ✅
- Zoho polling ✅
- Creates tickets in our database from ticketing tools

✅ **Monitoring Connectors** (Implemented)
- Datadog connector ✅
- Azure Monitor connector ✅
- Prometheus connector ✅
- Splunk connector ✅
- **Purpose**: Validation, state checking, matching

### Webhook Endpoints

The webhook endpoints (`/api/v1/tickets/webhook/{source}`) are available but:

**Recommended Usage:**
- Use for testing/validation
- Use for matching tickets with alerts
- **NOT** for production ticket creation

**Production Flow:**
- Tickets come from ticketing tools (via polling)
- Monitoring tools used for validation/verification

## Value Proposition

1. **No Duplication**: We don't recreate what customers already have
2. **Adds Value**: We provide intelligence (matching, validation, automation)
3. **Simple**: Less code, less complexity, easier to maintain
4. **Flexible**: Works with any customer's existing setup

## Next Steps

1. ✅ Keep monitoring connectors for validation
2. ✅ Keep ticketing tool polling (already working)
3. ✅ Add ticket-alert matching logic (future enhancement)
4. ✅ Add pre/post-execution verification (future enhancement)
5. ❌ Don't create tickets from monitoring webhooks in production

## Summary

**Keep it simple:**
- Poll tickets from ticketing tools ✅
- Use monitoring for validation ✅
- Don't duplicate customer's existing alert→ticket flow ❌

This is the right architecture!


