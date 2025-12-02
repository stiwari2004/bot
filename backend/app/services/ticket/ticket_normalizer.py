"""
Service for normalizing ticket data from various sources
"""
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketNormalizer:
    """Service for normalizing ticket data from various monitoring sources"""
    
    def __init__(self):
        # Import monitoring connectors
        try:
            from app.services.monitoring_connectors.datadog import DatadogConnector
            from app.services.monitoring_connectors.azure_monitor import AzureMonitorConnector
            from app.services.monitoring_connectors.prometheus import PrometheusConnector
            from app.services.monitoring_connectors.splunk import SplunkConnector
            
            self.datadog_connector = DatadogConnector()
            self.azure_monitor_connector = AzureMonitorConnector()
            self.prometheus_connector = PrometheusConnector()
            self.splunk_connector = SplunkConnector()
        except ImportError as e:
            logger.warning(f"Could not import monitoring connectors: {e}")
            self.datadog_connector = None
            self.azure_monitor_connector = None
            self.prometheus_connector = None
            self.splunk_connector = None
    
    def normalize(self, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Normalize ticket data from various sources"""
        # Use connector-specific normalization if available
        if source == "datadog" and self.datadog_connector:
            try:
                return self.datadog_connector.normalize_webhook(payload)
            except Exception as e:
                logger.error(f"Error in Datadog connector normalization: {e}", exc_info=True)
        
        elif source == "azure_monitor" and self.azure_monitor_connector:
            try:
                return self.azure_monitor_connector.normalize_webhook(payload)
            except Exception as e:
                logger.error(f"Error in Azure Monitor connector normalization: {e}", exc_info=True)
        
        elif source == "prometheus" and self.prometheus_connector:
            try:
                return self.prometheus_connector.normalize_webhook(payload)
            except Exception as e:
                logger.error(f"Error in Prometheus connector normalization: {e}", exc_info=True)
        
        elif source == "splunk" and self.splunk_connector:
            try:
                return self.splunk_connector.normalize_webhook(payload)
            except Exception as e:
                logger.error(f"Error in Splunk connector normalization: {e}", exc_info=True)
        
        # Fallback to legacy normalization
        return self._legacy_normalize(payload, source)
    
    def _legacy_normalize(self, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Legacy normalization for sources without connectors"""
        normalized = {
            "external_id": None,
            "title": "",
            "description": "",
            "severity": "medium",
            "environment": "prod",
            "service": None,
            "metadata": {}
        }
        
        if source == "prometheus":
            normalized["title"] = payload.get("groupLabels", {}).get("alertname", "Alert")
            normalized["description"] = payload.get("annotations", {}).get("description", "")
            normalized["severity"] = payload.get("labels", {}).get("severity", "medium")
            normalized["external_id"] = payload.get("fingerprint")
        
        elif source == "datadog":
            normalized["title"] = payload.get("title", "Datadog Alert")
            normalized["description"] = payload.get("text", "")
            normalized["severity"] = payload.get("priority", "normal")
            normalized["external_id"] = payload.get("id")
        
        elif source == "pagerduty":
            normalized["title"] = payload.get("summary", "PagerDuty Incident")
            normalized["description"] = payload.get("description", "")
            normalized["severity"] = payload.get("urgency", "medium")
            normalized["external_id"] = payload.get("id")
        
        elif source == "servicenow":
            # ServiceNow webhook format - can be from incident table or event
            # Check for different webhook formats
            incident = payload.get("result", payload.get("incident", payload))
            
            normalized["title"] = incident.get("short_description") or incident.get("title", "ServiceNow Incident")
            normalized["description"] = incident.get("description") or incident.get("comments", "")
            normalized["external_id"] = incident.get("number") or incident.get("sys_id")
            
            # Map ServiceNow priority/urgency to severity
            priority = incident.get("priority", "3")
            urgency = incident.get("urgency", "3")
            
            priority_map = {
                "1": "critical",
                "2": "high",
                "3": "medium",
                "4": "low",
                "5": "low"
            }
            normalized["severity"] = priority_map.get(str(priority), priority_map.get(str(urgency), "medium"))
            
            # Map ServiceNow state to status
            state = incident.get("state", "1")
            state_map = {
                "1": "open",  # New
                "2": "in_progress",  # In Progress
                "3": "open",  # On Hold
                "4": "resolved",  # Resolved
                "5": "resolved",  # Closed
                "6": "resolved"  # Canceled
            }
            normalized["status"] = state_map.get(str(state), "open")
            
            # Store ServiceNow metadata
            normalized["metadata"] = {
                "servicenow_sys_id": incident.get("sys_id"),
                "servicenow_number": incident.get("number"),
                "servicenow_state": state,
                "servicenow_urgency": urgency,
                "servicenow_impact": incident.get("impact"),
                "servicenow_priority": priority,
                "servicenow_category": incident.get("category"),
                "servicenow_subcategory": incident.get("subcategory"),
                "servicenow_assigned_to": incident.get("assigned_to"),
                "servicenow_caller": incident.get("caller_id"),
                "raw_payload": payload  # Keep original payload
            }
        
        else:
            # Generic format
            normalized["title"] = payload.get("title", payload.get("summary", "Alert"))
            normalized["description"] = payload.get("description", payload.get("body", ""))
            normalized["severity"] = payload.get("severity", payload.get("priority", "medium"))
            normalized["external_id"] = payload.get("id", payload.get("external_id"))
            normalized["metadata"] = payload
        
        return normalized




