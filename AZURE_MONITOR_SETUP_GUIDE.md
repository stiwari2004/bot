# Azure Monitor Integration Setup Guide

This guide will walk you through setting up Azure Monitor alerts to send webhooks to your troubleshooting AI system.

## Prerequisites

- Azure subscription with access to Azure Portal
- Resource to monitor (VM, App Service, Database, etc.)
- Your troubleshooting AI system running and accessible (webhook endpoint)

## Step 1: Get Your Webhook URL

Your webhook endpoint URL is:
```
http://localhost:8000/api/v1/tickets/webhook/azure_monitor
```

**For production/testing from Azure:**
- If running locally, use a tool like **ngrok** to expose your localhost
- Or deploy to a publicly accessible server
- The URL should be: `https://your-domain.com/api/v1/tickets/webhook/azure_monitor`

### Using ngrok (for local testing)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok.io
# Use: https://abc123.ngrok.io/api/v1/tickets/webhook/azure_monitor
```

## Step 2: Create an Azure Monitor Alert Rule

### Option A: Metric Alert (Recommended for Testing)

1. **Navigate to Azure Portal** → Your Resource (e.g., Virtual Machine, App Service)

2. **Go to Alerts** → Click **"New alert rule"**

3. **Configure Signal:**
   - **Signal type**: Select "Metrics"
   - **Signal**: Choose a metric (e.g., "Percentage CPU", "Memory", "Disk Read Bytes/sec")
   - **Condition**: Set threshold (e.g., CPU > 80%)

4. **Configure Alert Logic:**
   - **Aggregation type**: Average, Maximum, or Minimum
   - **Aggregation granularity**: 5 minutes
   - **Threshold value**: Set your threshold (e.g., 80)
   - **Frequency of evaluation**: Every 5 minutes

5. **Configure Actions:**
   - Click **"Add action groups"** or **"Create action group"**
   - **Action Group Name**: e.g., "TroubleshootingAI-Webhook"
   - **Short name**: e.g., "TSAI-Webhook"
   - **Resource Group**: Select your resource group

6. **Add Webhook Action:**
   - In the Action Group, click **"Actions"** tab
   - **Action type**: Select "Webhook"
   - **Name**: "Send to Troubleshooting AI"
   - **URI**: Paste your webhook URL
     ```
     https://your-domain.com/api/v1/tickets/webhook/azure_monitor
     ```
   - **Enable common alert schema**: ✅ Yes (recommended)

7. **Configure Alert Details:**
   - **Alert rule name**: e.g., "High CPU Alert"
   - **Description**: Optional
   - **Severity**: Select (Critical, Error, Warning, Informational, Verbose)
   - **Enable alert rule**: ✅ Yes

8. **Review and Create**

### Option B: Activity Log Alert

1. **Navigate to Azure Portal** → **Monitor** → **Alerts**

2. **Click "New alert rule"**

3. **Select Resource:**
   - Choose the resource you want to monitor
   - Or select subscription/resource group

4. **Configure Condition:**
   - **Signal type**: Activity Log
   - **Event category**: Administrative, Service Health, Resource Health, etc.
   - **Operation name**: Select specific operations (e.g., "Restart Virtual Machine")

5. **Configure Actions:**
   - Same as Option A - add webhook action with your URL

6. **Configure Alert Details:**
   - Same as Option A

### Option C: Log Alert (Advanced)

1. **Navigate to Azure Portal** → **Monitor** → **Alerts**

2. **Click "New alert rule"**

3. **Select Resource:**
   - Choose Log Analytics workspace

4. **Configure Condition:**
   - **Signal type**: Log
   - **Search query**: Write a KQL query
     ```kusto
     // Example: Find errors in logs
     search "error" or "failed" or "exception"
     | where TimeGenerated > ago(5m)
     ```
   - **Based on**: Number of results
   - **Threshold**: Greater than 0

5. **Configure Actions:**
   - Add webhook action with your URL

6. **Configure Alert Details:**
   - Same as Option A

## Step 3: Test the Alert

### Method 1: Trigger the Alert Manually

**For Metric Alert:**
- If monitoring CPU, run a CPU-intensive task on the VM
- Or temporarily lower the threshold to trigger immediately

**For Activity Log Alert:**
- Perform the action being monitored (e.g., restart VM, scale resource)

**For Log Alert:**
- Generate log entries that match your query

### Method 2: Test with Sample Payload

You can test the webhook endpoint directly using curl:

```bash
# Test Azure Monitor Metric Alert payload
curl -X POST http://localhost:8000/api/v1/tickets/webhook/azure_monitor \
  -H "Content-Type: application/json" \
  -d '{
    "schemaId": "AzureMonitorMetricAlert",
    "data": {
      "essentials": {
        "alertId": "test-alert-123",
        "alertRule": "High CPU Alert",
        "severity": "Sev2",
        "signalType": "Metric",
        "monitorCondition": "Fired",
        "monitoringService": "Platform",
        "firedDateTime": "2025-12-01T10:00:00Z",
        "description": "CPU usage exceeded 80% threshold"
      },
      "alertContext": {
        "properties": {},
        "conditionType": "StaticThreshold",
        "condition": {
          "windowSize": "PT5M",
          "allOf": [
            {
              "metricName": "Percentage CPU",
              "metricNamespace": "Microsoft.Compute/virtualMachines",
              "operator": "GreaterThan",
              "threshold": "80",
              "timeAggregation": "Average"
            }
          ]
        }
      }
    }
  }'
```

## Step 4: Verify Integration

1. **Check Backend Logs:**
   ```bash
   # View backend logs
   docker-compose logs -f backend
   ```

2. **Check Tickets in UI:**
   - Navigate to your application
   - Go to Tickets section
   - You should see the alert as a new ticket

3. **Verify Ticket Details:**
   - Title should match alert name
   - Description should contain alert details
   - Severity should be mapped correctly
   - Metadata should contain Azure-specific information

## Step 5: Monitor and Debug

### Check Webhook Delivery

In Azure Portal:
1. Go to **Monitor** → **Alerts**
2. Click on your alert rule
3. Check **"History"** tab to see if webhook was sent
4. Check **"Action groups"** → Your action group → **"History"** to see webhook delivery status

### Common Issues

**Issue: Webhook not received**
- Verify webhook URL is correct and accessible
- Check if ngrok is running (if using localhost)
- Verify firewall/network allows Azure IPs
- Check backend logs for errors

**Issue: 401/403 Errors**
- Azure Monitor webhooks don't require authentication by default
- If you added authentication, ensure it's configured correctly

**Issue: Payload format errors**
- Check backend logs for parsing errors
- Verify "Enable common alert schema" is enabled in Azure
- Ensure payload matches expected format

## Azure Monitor Alert Payload Formats

### Metric Alert Format
```json
{
  "schemaId": "AzureMonitorMetricAlert",
  "data": {
    "essentials": {
      "alertId": "guid",
      "alertRule": "Alert Name",
      "severity": "Sev0|Sev1|Sev2|Sev3|Sev4",
      "monitorCondition": "Fired|Resolved",
      "firedDateTime": "ISO8601 timestamp",
      "description": "Alert description"
    },
    "alertContext": {
      "conditionType": "StaticThreshold",
      "condition": {...}
    }
  }
}
```

### Activity Log Alert Format
```json
{
  "schemaId": "Microsoft.Insights/activityLogs",
  "data": {
    "status": "Activated|Resolved",
    "context": {
      "activityLog": {
        "authorization": {...},
        "channels": "Operation",
        "caller": "user@example.com",
        "correlationId": "guid",
        "description": "Alert description",
        "eventSource": "Administrative",
        "eventTimestamp": "ISO8601 timestamp",
        "level": "Critical|Error|Warning|Informational",
        "operationName": "Microsoft.Compute/virtualMachines/restart/action",
        "resourceGroupName": "myResourceGroup",
        "resourceId": "/subscriptions/.../resourceGroups/.../providers/...",
        "resourceType": "Microsoft.Compute/virtualMachines",
        "status": "Succeeded|Failed|Started"
      }
    }
  }
}
```

## Next Steps

Once Azure Monitor is working:
1. Test with different alert types (Metric, Activity Log, Log)
2. Verify severity mapping is correct
3. Test alert resolution (when condition clears)
4. Move on to Prometheus setup
5. Then Datadog setup

## Quick Reference

**Webhook URL:**
```
http://localhost:8000/api/v1/tickets/webhook/azure_monitor
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/v1/tickets/webhook/azure_monitor \
  -H "Content-Type: application/json" \
  -d @azure_test_payload.json
```

**Check Tickets:**
```
GET http://localhost:8000/api/v1/tickets/demo/tickets
```


