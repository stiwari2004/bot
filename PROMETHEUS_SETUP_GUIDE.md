# Prometheus Alertmanager Integration Setup Guide

This guide will walk you through setting up Prometheus Alertmanager to send webhooks to your troubleshooting AI system for validation and state checking.

## Prerequisites

- Prometheus installed and running
- Alertmanager installed and running
- Your troubleshooting AI system running and accessible (webhook endpoint)

## Step 1: Get Your Webhook URL

Your webhook endpoint URL is:
```
http://localhost:8000/api/v1/tickets/webhook/prometheus
```

**For production/testing from Alertmanager:**
- If running locally, use **ngrok** to expose your localhost
- Or deploy to a publicly accessible server
- The URL should be: `https://your-domain.com/api/v1/tickets/webhook/prometheus`

### Using ngrok (for local testing)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok.io
# Use: https://abc123.ngrok.io/api/v1/tickets/webhook/prometheus
```

## Step 2: Configure Prometheus Alertmanager

### Alertmanager Configuration File

Edit your `alertmanager.yml` file (usually located at `/etc/alertmanager/alertmanager.yml` or `./alertmanager.yml`):

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'troubleshooting-ai-webhook'
  routes:
    - match:
        severity: critical
      receiver: 'troubleshooting-ai-webhook'
      continue: true
    - match:
        severity: warning
      receiver: 'troubleshooting-ai-webhook'
      continue: true

receivers:
  - name: 'troubleshooting-ai-webhook'
    webhook_configs:
      - url: 'https://your-domain.com/api/v1/tickets/webhook/prometheus'
        send_resolved: true
        http_config:
          follow_redirects: true
```

### Key Configuration Options

- **`send_resolved: true`**: Send webhook when alert resolves
- **`url`**: Your webhook endpoint URL
- **`group_by`**: Group alerts by these labels
- **`group_wait`**: Wait time before sending grouped alerts
- **`repeat_interval`**: How often to resend alerts

## Step 3: Create Prometheus Alert Rules

Create or edit your Prometheus alert rules file (e.g., `alerts.yml`):

```yaml
groups:
  - name: infrastructure_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
          service: infrastructure
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% on {{ $labels.instance }}"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
          service: infrastructure
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% on {{ $labels.instance }}"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 10
        for: 5m
        labels:
          severity: critical
          service: infrastructure
        annotations:
          summary: "Low disk space"
          description: "Disk space is below 10% on {{ $labels.instance }}"
```

### Update Prometheus Configuration

Add the alert rules file to your `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"  # Path to your alert rules file

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
```

## Step 4: Restart Services

```bash
# Restart Prometheus
sudo systemctl restart prometheus
# Or if running in Docker:
docker-compose restart prometheus

# Restart Alertmanager
sudo systemctl restart alertmanager
# Or if running in Docker:
docker-compose restart alertmanager
```

## Step 5: Test the Alert

### Method 1: Trigger Alert Manually

**For CPU Alert:**
- Run a CPU-intensive task on the monitored server
- Or temporarily lower the threshold in the alert rule

**For Memory Alert:**
- Allocate large amounts of memory
- Or lower the threshold

**For Disk Alert:**
- Fill up disk space
- Or lower the threshold

### Method 2: Test with Sample Payload

You can test the webhook endpoint directly using the PowerShell script:

```powershell
.\test-prometheus-webhook.ps1
```

## Step 6: Verify Integration

1. **Check Backend Logs:**
   ```bash
   docker-compose logs -f backend
   ```

2. **Check Alertmanager Logs:**
   ```bash
   # If running in Docker
   docker-compose logs -f alertmanager
   
   # If running as service
   sudo journalctl -u alertmanager -f
   ```

3. **Check Alertmanager UI:**
   - Navigate to `http://localhost:9093` (Alertmanager UI)
   - Check "Alerts" tab to see active alerts
   - Check "Status" tab to see webhook delivery status

## Prometheus Alertmanager Webhook Format

The webhook payload format:

```json
{
  "version": "4",
  "groupKey": "{}:{alertname=\"HighCPUUsage\"}",
  "status": "firing",
  "receiver": "troubleshooting-ai-webhook",
  "groupLabels": {
    "alertname": "HighCPUUsage"
  },
  "commonLabels": {
    "alertname": "HighCPUUsage",
    "severity": "warning",
    "instance": "server1:9100",
    "job": "node_exporter"
  },
  "commonAnnotations": {
    "description": "CPU usage is above 80% on server1:9100",
    "summary": "High CPU usage detected"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighCPUUsage",
        "severity": "warning",
        "instance": "server1:9100",
        "job": "node_exporter"
      },
      "annotations": {
        "description": "CPU usage is above 80% on server1:9100",
        "summary": "High CPU usage detected"
      },
      "startsAt": "2025-12-01T10:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=...",
      "fingerprint": "abc123def456"
    }
  ]
}
```

## Troubleshooting

### Issue: Webhook not received

**Check Alertmanager configuration:**
```bash
# Validate configuration
amtool check-config alertmanager.yml

# Check Alertmanager status
amtool status
```

**Check webhook delivery:**
- Go to Alertmanager UI → Status → Receivers
- Check if webhook shows as "active"
- Check for any errors in delivery

**Common issues:**
- URL incorrect or unreachable
- Network/firewall blocking
- SSL certificate issues (if using HTTPS)

### Issue: Alerts not firing

**Check Prometheus:**
- Go to Prometheus UI → Alerts
- Verify alert rules are loaded
- Check if alerts are in "pending" or "firing" state

**Check alert rule syntax:**
```bash
# Validate alert rules
promtool check rules alerts.yml
```

### Issue: Webhook format errors

- Verify Alertmanager version (webhook format changed in v0.16.0)
- Check backend logs for parsing errors
- Ensure payload matches expected format

## Quick Reference

**Webhook URL:**
```
http://localhost:8000/api/v1/tickets/webhook/prometheus
```

**Test Command:**
```powershell
.\test-prometheus-webhook.ps1
```

**Alertmanager UI:**
```
http://localhost:9093
```

**Prometheus UI:**
```
http://localhost:9090
```

## Next Steps

Once Prometheus is working:
1. Test with different alert types
2. Verify alert resolution (when condition clears)
3. Test alert grouping
4. Move on to Datadog testing









