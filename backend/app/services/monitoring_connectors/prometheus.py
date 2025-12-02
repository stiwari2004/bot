"""
Prometheus Alertmanager Connector
Handles webhook alerts from Prometheus Alertmanager
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.logging import get_logger

logger = get_logger(__name__)


class PrometheusConnector:
    """Connector for Prometheus Alertmanager webhooks"""
    
    def __init__(self):
        self.name = "prometheus"
    
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Prometheus Alertmanager webhook payload to internal ticket format
        
        Prometheus Alertmanager webhook format:
        {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPU\"}",
            "status": "firing|resolved",
            "receiver": "webhook",
            "groupLabels": {
                "alertname": "HighCPU"
            },
            "commonLabels": {
                "alertname": "HighCPU",
                "severity": "warning",
                "instance": "server1:9100",
                "job": "node_exporter"
            },
            "commonAnnotations": {
                "description": "CPU usage is above 80%",
                "summary": "High CPU usage on server1"
            },
            "externalURL": "http://alertmanager:9093",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPU",
                        "severity": "warning",
                        "instance": "server1:9100",
                        "job": "node_exporter"
                    },
                    "annotations": {
                        "description": "CPU usage is above 80%",
                        "summary": "High CPU usage on server1"
                    },
                    "startsAt": "2025-01-01T00:00:00Z",
                    "endsAt": "2025-01-01T00:00:00Z",
                    "generatorURL": "http://prometheus:9090/graph?...",
                    "fingerprint": "abc123"
                }
            ]
        }
        """
        try:
            # Prometheus sends multiple alerts in one webhook
            # We'll process the first firing alert, or create a summary if multiple
            alerts = payload.get("alerts", [])
            status = payload.get("status", "firing")
            group_labels = payload.get("groupLabels", {})
            common_labels = payload.get("commonLabels", {})
            common_annotations = payload.get("commonAnnotations", {})
            
            # Find firing alerts (not resolved)
            firing_alerts = [a for a in alerts if a.get("status") == "firing"]
            
            if not firing_alerts and alerts:
                # All alerts resolved, return resolved status
                alert = alerts[0]
                return self._normalize_single_alert(alert, group_labels, common_labels, common_annotations, "resolved")
            
            # Use first firing alert, or first alert if none firing
            alert = firing_alerts[0] if firing_alerts else alerts[0]
            
            return self._normalize_single_alert(alert, group_labels, common_labels, common_annotations, status)
            
        except Exception as e:
            logger.error(f"Error normalizing Prometheus webhook: {e}", exc_info=True)
            return self._normalize_generic(payload)
    
    def _normalize_single_alert(
        self,
        alert: Dict[str, Any],
        group_labels: Dict[str, Any],
        common_labels: Dict[str, Any],
        common_annotations: Dict[str, Any],
        status: str
    ) -> Dict[str, Any]:
        """Normalize a single Prometheus alert"""
        # Merge labels (alert-specific override common)
        labels = {**common_labels, **alert.get("labels", {})}
        annotations = {**common_annotations, **alert.get("annotations", {})}
        
        # Extract key information
        alertname = labels.get("alertname") or group_labels.get("alertname", "Prometheus Alert")
        severity = labels.get("severity", "warning")
        instance = labels.get("instance", "")
        job = labels.get("job", "")
        description = annotations.get("description", "")
        summary = annotations.get("summary", alertname)
        fingerprint = alert.get("fingerprint")
        
        # Map Prometheus severity to internal severity
        severity_map = {
            "critical": "critical",
            "warning": "medium",
            "info": "low",
            "error": "high"
        }
        internal_severity = severity_map.get(severity.lower(), "medium")
        
        # Extract service/environment from labels
        service = labels.get("service") or labels.get("job") or instance.split(":")[0] if instance else None
        environment = labels.get("environment") or labels.get("env") or "prod"
        
        # Build title
        title = summary or f"{alertname} on {instance}" if instance else alertname
        
        return {
            "external_id": fingerprint or f"{alertname}_{instance}",
            "title": title,
            "description": description or summary or alertname,
            "severity": internal_severity,
            "environment": environment,
            "service": service,
            "status": "open" if status == "firing" else "resolved",
            "metadata": {
                "prometheus_alertname": alertname,
                "prometheus_fingerprint": fingerprint,
                "prometheus_instance": instance,
                "prometheus_job": job,
                "prometheus_severity": severity,
                "prometheus_status": alert.get("status", status),
                "prometheus_starts_at": alert.get("startsAt"),
                "prometheus_ends_at": alert.get("endsAt"),
                "prometheus_generator_url": alert.get("generatorURL"),
                "prometheus_labels": labels,
                "prometheus_annotations": annotations,
                "raw_payload": alert
            }
        }
    
    def _normalize_generic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generic normalization fallback"""
        group_labels = payload.get("groupLabels", {})
        common_labels = payload.get("commonLabels", {})
        common_annotations = payload.get("commonAnnotations", {})
        
        alertname = group_labels.get("alertname") or common_labels.get("alertname", "Prometheus Alert")
        description = common_annotations.get("description", "")
        
        return {
            "external_id": payload.get("fingerprint") or alertname,
            "title": alertname,
            "description": description or alertname,
            "severity": "medium",
            "environment": "prod",
            "service": None,
            "metadata": {"raw_payload": payload}
        }
    
    async def update_alert_status(
        self,
        alert_fingerprint: str,
        status: str,  # "resolved" or "acknowledged"
        alertmanager_url: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update alert status in Prometheus Alertmanager
        
        Args:
            alert_fingerprint: Prometheus alert fingerprint
            status: New status (resolved, acknowledged)
            alertmanager_url: Alertmanager API URL (e.g., http://alertmanager:9093)
            notes: Optional notes about the update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import httpx
            
            # Prometheus Alertmanager API for silencing alerts
            # We'll use the silence API to acknowledge/resolve
            silence_url = f"{alertmanager_url.rstrip('/')}/api/v2/silences"
            
            # For resolving, we can expire the alert
            # For acknowledging, we create a silence
            if status == "resolved":
                # Prometheus alerts resolve automatically when condition clears
                # We can't force resolve, but we can silence it
                logger.info(f"Prometheus alert {alert_fingerprint} - alerts resolve automatically when condition clears")
                return True
            elif status == "acknowledged":
                # Create a silence to acknowledge the alert
                silence_payload = {
                    "matchers": [
                        {
                            "name": "fingerprint",
                            "value": alert_fingerprint,
                            "isRegex": False
                        }
                    ],
                    "startsAt": datetime.utcnow().isoformat() + "Z",
                    "endsAt": (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + "Z",
                    "comment": notes or "Acknowledged via AI Agent",
                    "createdBy": "ai-agent"
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        silence_url,
                        json=silence_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"Successfully acknowledged Prometheus alert {alert_fingerprint}")
                        return True
                    else:
                        logger.error(f"Failed to acknowledge Prometheus alert: {response.status_code} - {response.text}")
                        return False
            else:
                logger.warning(f"Unknown status for Prometheus alert: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Prometheus alert status: {e}", exc_info=True)
            return False

