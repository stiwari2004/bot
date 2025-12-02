"""
Azure Monitor Connector
Handles webhook alerts from Azure Monitor and Azure Log Analytics
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureMonitorConnector:
    """Connector for Azure Monitor and Azure Log Analytics"""
    
    def __init__(self):
        self.name = "azure_monitor"
    
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Azure Monitor webhook payload to internal ticket format
        
        Azure Monitor webhook format (Activity Log Alert):
        {
            "schemaId": "Microsoft.Insights/activityLogs",
            "data": {
                "status": "Activated|Resolved",
                "context": {
                    "activityLog": {
                        "authorization": {...},
                        "channels": "Operation",
                        "claims": {...},
                        "caller": "user@example.com",
                        "correlationId": "guid",
                        "description": "Alert description",
                        "eventSource": "Administrative",
                        "eventTimestamp": "2025-01-01T00:00:00Z",
                        "eventDataId": "guid",
                        "level": "Critical|Error|Warning|Informational|Verbose",
                        "operationName": "Microsoft.Compute/virtualMachines/restart/action",
                        "operationId": "guid",
                        "properties": {...},
                        "resourceGroupName": "myResourceGroup",
                        "resourceProviderName": "Microsoft.Compute",
                        "resourceId": "/subscriptions/.../resourceGroups/.../providers/...",
                        "resourceType": "Microsoft.Compute/virtualMachines",
                        "status": "Succeeded|Failed|Started",
                        "subStatus": {...},
                        "subscriptionId": "guid",
                        "submissionTimestamp": "2025-01-01T00:00:00Z"
                    }
                },
                "properties": {...}
            }
        }
        
        Azure Monitor webhook format (Metric Alert):
        {
            "schemaId": "AzureMonitorMetricAlert",
            "data": {
                "essentials": {
                    "alertId": "guid",
                    "alertRule": "Alert rule name",
                    "severity": "Sev0|Sev1|Sev2|Sev3|Sev4",
                    "signalType": "Metric",
                    "monitorCondition": "Fired|Resolved",
                    "monitoringService": "Platform",
                    "firedDateTime": "2025-01-01T00:00:00Z",
                    "description": "Alert description",
                    "essentialsVersion": "1.0",
                    "alertContextVersion": "1.0"
                },
                "alertContext": {
                    "properties": {...},
                    "conditionType": "StaticThreshold",
                    "condition": {...}
                }
            }
        }
        """
        try:
            schema_id = payload.get("schemaId", "")
            data = payload.get("data", {})
            
            # Handle Activity Log Alert
            if "activityLogs" in schema_id or "activityLog" in str(data):
                return self._normalize_activity_log(data)
            
            # Handle Metric Alert
            elif "MetricAlert" in schema_id or "essentials" in data:
                return self._normalize_metric_alert(data)
            
            # Handle Log Alert
            elif "LogAlert" in schema_id or "SearchResult" in str(data):
                return self._normalize_log_alert(data)
            
            # Generic fallback
            else:
                return self._normalize_generic(payload)
                
        except Exception as e:
            logger.error(f"Error normalizing Azure Monitor webhook: {e}", exc_info=True)
            return self._normalize_generic(payload)
    
    def _normalize_activity_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Activity Log Alert"""
        context = data.get("context", {})
        activity_log = context.get("activityLog", {})
        
        status = data.get("status", activity_log.get("status", "Activated"))
        level = activity_log.get("level", "Informational")
        operation_name = activity_log.get("operationName", "Unknown Operation")
        description = activity_log.get("description", "")
        resource_id = activity_log.get("resourceId", "")
        resource_group = activity_log.get("resourceGroupName", "")
        
        # Extract resource name from resource ID
        resource_name = resource_id.split("/")[-1] if resource_id else None
        
        # Map Azure level to severity
        severity_map = {
            "Critical": "critical",
            "Error": "high",
            "Warning": "medium",
            "Informational": "low",
            "Verbose": "low"
        }
        severity = severity_map.get(level, "medium")
        
        return {
            "external_id": activity_log.get("eventDataId") or activity_log.get("correlationId"),
            "title": f"{operation_name} - {resource_name or 'Azure Resource'}",
            "description": description or operation_name,
            "severity": severity,
            "environment": self._extract_environment(resource_group),
            "service": resource_name,
            "status": "open" if status == "Activated" else "resolved",
            "metadata": {
                "azure_resource_id": resource_id,
                "azure_resource_group": resource_group,
                "azure_operation": operation_name,
                "azure_level": level,
                "azure_status": status,
                "azure_correlation_id": activity_log.get("correlationId"),
                "raw_payload": data
            }
        }
    
    def _normalize_metric_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Metric Alert"""
        essentials = data.get("essentials", {})
        alert_context = data.get("alertContext", {})
        
        alert_id = essentials.get("alertId")
        alert_rule = essentials.get("alertRule", "Azure Metric Alert")
        severity_str = essentials.get("severity", "Sev2")
        condition = essentials.get("monitorCondition", "Fired")
        description = essentials.get("description", "")
        fired_time = essentials.get("firedDateTime", "")
        
        # Map Azure severity to internal severity
        severity_map = {
            "Sev0": "critical",
            "Sev1": "high",
            "Sev2": "medium",
            "Sev3": "low",
            "Sev4": "low"
        }
        severity = severity_map.get(severity_str, "medium")
        
        # Extract resource information
        resource_id = essentials.get("alertTargetIDs", [""])[0] if essentials.get("alertTargetIDs") else ""
        resource_name = resource_id.split("/")[-1] if resource_id else None
        
        return {
            "external_id": alert_id,
            "title": alert_rule,
            "description": description or f"Metric alert fired: {alert_rule}",
            "severity": severity,
            "environment": "prod",  # Azure doesn't always provide this
            "service": resource_name,
            "status": "open" if condition == "Fired" else "resolved",
            "metadata": {
                "azure_alert_id": alert_id,
                "azure_severity": severity_str,
                "azure_condition": condition,
                "azure_fired_time": fired_time,
                "azure_resource_id": resource_id,
                "azure_condition_type": alert_context.get("conditionType"),
                "raw_payload": data
            }
        }
    
    def _normalize_log_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Log Alert"""
        # Similar structure to metric alert
        essentials = data.get("essentials", {})
        
        alert_id = essentials.get("alertId")
        alert_rule = essentials.get("alertRule", "Azure Log Alert")
        severity_str = essentials.get("severity", "Sev2")
        condition = essentials.get("monitorCondition", "Fired")
        description = essentials.get("description", "")
        
        severity_map = {
            "Sev0": "critical",
            "Sev1": "high",
            "Sev2": "medium",
            "Sev3": "low",
            "Sev4": "low"
        }
        severity = severity_map.get(severity_str, "medium")
        
        return {
            "external_id": alert_id,
            "title": alert_rule,
            "description": description or f"Log alert fired: {alert_rule}",
            "severity": severity,
            "environment": "prod",
            "service": None,
            "status": "open" if condition == "Fired" else "resolved",
            "metadata": {
                "azure_alert_id": alert_id,
                "azure_severity": severity_str,
                "azure_condition": condition,
                "raw_payload": data
            }
        }
    
    def _normalize_generic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generic normalization fallback"""
        return {
            "external_id": payload.get("id") or payload.get("alertId"),
            "title": payload.get("title") or payload.get("alertRule") or "Azure Monitor Alert",
            "description": payload.get("description") or payload.get("text", ""),
            "severity": "medium",
            "environment": "prod",
            "service": None,
            "metadata": {"raw_payload": payload}
        }
    
    def _extract_environment(self, resource_group: str) -> str:
        """Extract environment from resource group name"""
        if not resource_group:
            return "prod"
        
        resource_group_lower = resource_group.lower()
        if "dev" in resource_group_lower:
            return "dev"
        elif "test" in resource_group_lower or "qa" in resource_group_lower:
            return "test"
        elif "staging" in resource_group_lower or "stage" in resource_group_lower:
            return "staging"
        else:
            return "prod"
    
    async def update_alert_status(
        self,
        alert_id: str,
        status: str,  # "resolved" or "acknowledged"
        subscription_id: str,
        resource_group: str,
        access_token: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update alert status in Azure Monitor
        
        Args:
            alert_id: Azure alert ID
            status: New status (resolved, acknowledged)
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            access_token: Azure AD access token
            notes: Optional notes about the update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Azure Monitor alerts are typically managed through Action Groups
            # For resolving, we can update the alert rule state
            # For acknowledging, we can add a comment or update the alert state
            
            # Note: Azure Monitor doesn't have a direct "acknowledge" API
            # We can mute/resolve the alert rule instead
            alert_rule_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Insights/metricAlerts/{alert_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if status == "resolved":
                    # Get current alert rule
                    get_response = await client.get(alert_rule_url, headers=headers)
                    if get_response.status_code != 200:
                        logger.error(f"Failed to get Azure alert rule: {get_response.status_code}")
                        return False
                    
                    alert_rule = get_response.json()
                    
                    # Disable the alert rule (effectively resolving it)
                    alert_rule["properties"]["enabled"] = False
                    
                    put_response = await client.put(alert_rule_url, json=alert_rule, headers=headers)
                    
                    if put_response.status_code in [200, 201]:
                        logger.info(f"Successfully resolved Azure Monitor alert {alert_id}")
                        return True
                    else:
                        logger.error(f"Failed to resolve Azure alert: {put_response.status_code} - {put_response.text}")
                        return False
                else:
                    # For acknowledge, we can add a note via Activity Log or just log it
                    logger.info(f"Azure Monitor alert {alert_id} acknowledged (note: Azure doesn't have direct acknowledge API)")
                    return True
                    
        except Exception as e:
            logger.error(f"Error updating Azure Monitor alert status: {e}", exc_info=True)
            return False

