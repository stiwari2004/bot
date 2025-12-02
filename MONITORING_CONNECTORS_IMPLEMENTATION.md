# Monitoring Connectors Implementation

**Date**: December 1, 2025  
**Status**: ✅ Complete

## Overview

Implemented 4 monitoring tool connectors for webhook-based alert ingestion:

1. **Datadog** - Cloud monitoring and alerting platform
2. **Azure Monitor** - Microsoft Azure monitoring service
3. **Prometheus Alertmanager** - Open-source monitoring toolkit
4. **Splunk** - Log aggregation and SIEM platform

## Implementation Details

### Files Created

1. `backend/app/services/monitoring_connectors/__init__.py`
   - Module initialization and exports

2. `backend/app/services/monitoring_connectors/datadog.py`
   - `DatadogConnector` class
   - Webhook normalization
   - API integration for fetching alerts

3. `backend/app/services/monitoring_connectors/azure_monitor.py`
   - `AzureMonitorConnector` class
   - Supports Activity Log Alerts, Metric Alerts, and Log Alerts
   - Environment extraction from resource groups

4. `backend/app/services/monitoring_connectors/prometheus.py`
   - `PrometheusConnector` class
   - Alertmanager webhook format parsing
   - Handles multiple alerts in single webhook

5. `backend/app/services/monitoring_connectors/splunk.py`
   - `SplunkConnector` class
   - Webhook normalization for Splunk alerts
   - HTTP Event Collector (HEC) integration for sending events

### Files Modified

1. `backend/app/services/ticket/ticket_normalizer.py`
   - Updated to use connector-specific normalization
   - Falls back to legacy normalization if connectors unavailable
   - Instance-based (was static before)

2. `backend/app/api/v1/endpoints/ticket_ingestion.py`
   - Added `azure_monitor` and `splunk` to `WebhookSource` enum
   - Updated documentation

3. `backend/app/services/connector_service.py`
   - Registered new monitoring connectors
   - Added imports for new connectors

4. `backend/app/controllers/connector_controller.py`
   - Updated `list_monitoring_connectors()` to include new connectors
   - Added status and capability information

## Webhook Endpoints

All connectors support webhook ingestion via:

```
POST /api/v1/tickets/webhook/{source}
```

Where `{source}` can be:
- `datadog`
- `azure_monitor`
- `prometheus`
- `splunk`

## Connector Features

### Datadog
- ✅ Webhook normalization
- ✅ API integration for fetching alerts
- ✅ Priority mapping (critical, high, medium, low)
- ✅ Tag parsing (environment, service extraction)

### Azure Monitor
- ✅ Activity Log Alert normalization
- ✅ Metric Alert normalization
- ✅ Log Alert normalization
- ✅ Environment extraction from resource groups
- ✅ Severity mapping (Sev0-Sev4)

### Prometheus Alertmanager
- ✅ Alertmanager webhook format parsing
- ✅ Multiple alert handling
- ✅ Label and annotation extraction
- ✅ Severity mapping (critical, warning, info, error)

### Splunk
- ✅ Alert result format normalization
- ✅ Custom alert format normalization
- ✅ Severity extraction from logs
- ✅ HTTP Event Collector (HEC) support for sending events

## Testing

### Webhook Testing

You can test each connector by sending a POST request to:

```bash
curl -X POST http://localhost:8000/api/v1/tickets/webhook/datadog \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Alert",
    "text": "This is a test alert",
    "alert_id": "12345",
    "priority": "high"
  }'
```

### Example Payloads

See each connector file for example webhook payload formats in the docstrings.

## Next Steps

1. **Testing**: Test with real webhooks from each monitoring tool
2. **Documentation**: Add setup guides for each connector
3. **Error Handling**: Enhance error handling and retry logic
4. **Metrics**: Add metrics collection for connector usage
5. **SolarWinds & Zabbix**: Add additional connectors as needed

## API Endpoints

### List Monitoring Connectors

```
GET /api/v1/connectors/monitoring
```

Returns list of available monitoring connectors with status and capabilities.

## Notes

- All connectors normalize webhook payloads to a common internal ticket format
- Connectors preserve original payload in `metadata.raw_payload` for debugging
- Severity mapping is consistent across all connectors (critical, high, medium, low)
- Environment and service extraction is attempted from various fields/labels/tags


