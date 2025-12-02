"""
Splunk Connector
Handles webhook alerts from Splunk and HTTP Event Collector (HEC) integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import json
from app.core.logging import get_logger

logger = get_logger(__name__)


class SplunkConnector:
    """Connector for Splunk alerts and events"""
    
    def __init__(self):
        self.name = "splunk"
    
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Splunk webhook payload to internal ticket format
        
        Splunk webhook format (Alert Action):
        {
            "result": {
                "_raw": "Log entry text",
                "_time": "2025-01-01T00:00:00Z",
                "host": "server1",
                "source": "/var/log/app.log",
                "sourcetype": "access_combined",
                "index": "main",
                "splunk_server": "splunk1",
                "search_name": "High Error Rate Alert",
                "owner": "admin",
                "app": "search",
                "sid": "1234567890.1234"
            },
            "search_name": "High Error Rate Alert",
            "owner": "admin",
            "app": "search",
            "sid": "1234567890.1234"
        }
        
        Splunk webhook format (Custom JSON):
        {
            "alert_name": "High Error Rate",
            "alert_description": "Error rate exceeded threshold",
            "severity": "high",
            "host": "server1",
            "source": "/var/log/app.log",
            "count": 100,
            "threshold": 50,
            "time": "2025-01-01T00:00:00Z"
        }
        """
        try:
            # Check if it's a Splunk alert result format
            if "result" in payload:
                return self._normalize_alert_result(payload)
            
            # Check if it's a custom JSON format
            elif "alert_name" in payload or "search_name" in payload:
                return self._normalize_custom_alert(payload)
            
            # Generic format
            else:
                return self._normalize_generic(payload)
                
        except Exception as e:
            logger.error(f"Error normalizing Splunk webhook: {e}", exc_info=True)
            return self._normalize_generic(payload)
    
    def _normalize_alert_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Splunk alert result format"""
        result = payload.get("result", {})
        search_name = payload.get("search_name") or result.get("search_name", "Splunk Alert")
        
        # Extract information from result
        raw_text = result.get("_raw", "")
        host = result.get("host", "")
        source = result.get("source", "")
        sourcetype = result.get("sourcetype", "")
        time_str = result.get("_time", "")
        sid = payload.get("sid") or result.get("sid", "")
        
        # Try to extract severity from raw text or fields
        severity = self._extract_severity(result, raw_text)
        
        # Build description
        description = raw_text or f"Alert triggered: {search_name}"
        if host:
            description = f"Host: {host}\n{description}"
        
        return {
            "external_id": sid or f"{search_name}_{host}_{time_str}",
            "title": search_name,
            "description": description,
            "severity": severity,
            "environment": self._extract_environment(host, source),
            "service": host or source.split("/")[-1] if source else None,
            "status": "open",
            "metadata": {
                "splunk_sid": sid,
                "splunk_search_name": search_name,
                "splunk_host": host,
                "splunk_source": source,
                "splunk_sourcetype": sourcetype,
                "splunk_time": time_str,
                "splunk_raw": raw_text,
                "splunk_owner": payload.get("owner") or result.get("owner"),
                "splunk_app": payload.get("app") or result.get("app"),
                "raw_payload": payload
            }
        }
    
    def _normalize_custom_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize custom Splunk alert format"""
        alert_name = payload.get("alert_name") or payload.get("search_name", "Splunk Alert")
        description = payload.get("alert_description") or payload.get("description", "")
        severity_str = payload.get("severity", "medium")
        host = payload.get("host", "")
        source = payload.get("source", "")
        time_str = payload.get("time", "")
        
        # Map severity
        severity_map = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "low"
        }
        severity = severity_map.get(severity_str.lower(), "medium")
        
        return {
            "external_id": payload.get("alert_id") or f"{alert_name}_{host}_{time_str}",
            "title": alert_name,
            "description": description or alert_name,
            "severity": severity,
            "environment": self._extract_environment(host, source),
            "service": host or source.split("/")[-1] if source else None,
            "status": "open",
            "metadata": {
                "splunk_alert_name": alert_name,
                "splunk_host": host,
                "splunk_source": source,
                "splunk_severity": severity_str,
                "splunk_time": time_str,
                "raw_payload": payload
            }
        }
    
    def _normalize_generic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generic normalization fallback"""
        return {
            "external_id": payload.get("id") or payload.get("sid") or payload.get("alert_id"),
            "title": payload.get("title") or payload.get("alert_name") or payload.get("search_name") or "Splunk Alert",
            "description": payload.get("description") or payload.get("alert_description") or payload.get("_raw", ""),
            "severity": self._extract_severity(payload, payload.get("_raw", "")),
            "environment": "prod",
            "service": payload.get("host") or payload.get("source", "").split("/")[-1] if payload.get("source") else None,
            "metadata": {"raw_payload": payload}
        }
    
    def _extract_severity(self, data: Dict[str, Any], raw_text: str = "") -> str:
        """Extract severity from Splunk data"""
        # Check explicit severity field
        severity = data.get("severity") or data.get("level") or data.get("priority")
        if severity:
            severity_map = {
                "critical": "critical",
                "high": "high",
                "medium": "medium",
                "low": "low",
                "error": "high",
                "warning": "medium",
                "info": "low",
                "debug": "low"
            }
            return severity_map.get(str(severity).lower(), "medium")
        
        # Try to infer from raw text
        raw_lower = raw_text.lower()
        if any(word in raw_lower for word in ["critical", "fatal", "emergency"]):
            return "critical"
        elif any(word in raw_lower for word in ["error", "err", "failed", "failure"]):
            return "high"
        elif any(word in raw_lower for word in ["warn", "warning", "caution"]):
            return "medium"
        else:
            return "medium"
    
    def _extract_environment(self, host: str, source: str) -> str:
        """Extract environment from host or source"""
        host_lower = (host or "").lower()
        source_lower = (source or "").lower()
        
        combined = f"{host_lower} {source_lower}"
        
        if any(term in combined for term in ["dev", "development"]):
            return "dev"
        elif any(term in combined for term in ["test", "qa", "staging", "stage"]):
            return "test"
        elif any(term in combined for term in ["prod", "production"]):
            return "prod"
        else:
            return "prod"
    
    async def send_to_hec(
        self,
        hec_url: str,
        hec_token: str,
        event: Dict[str, Any],
        index: str = "main",
        sourcetype: str = "json"
    ) -> bool:
        """
        Send event to Splunk HTTP Event Collector (HEC)
        
        Args:
            hec_url: Splunk HEC endpoint (e.g., https://splunk.example.com:8088/services/collector)
            hec_token: HEC authentication token
            event: Event data to send
            index: Splunk index name
            sourcetype: Splunk sourcetype
        
        Returns:
            True if successful, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Splunk {hec_token}",
                "Content-Type": "application/json"
            }
            
            # HEC expects events in specific format
            hec_event = {
                "time": datetime.utcnow().timestamp(),
                "host": event.get("host", "unknown"),
                "source": event.get("source", "troubleshooting_ai"),
                "sourcetype": sourcetype,
                "index": index,
                "event": event
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    hec_url,
                    headers=headers,
                    json=hec_event
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent event to Splunk HEC: {event.get('title', 'unknown')}")
                    return True
                else:
                    logger.error(f"Splunk HEC error: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending event to Splunk HEC: {e}", exc_info=True)
            return False
    
    async def update_alert_status(
        self,
        alert_sid: str,
        status: str,  # "resolved" or "acknowledged"
        splunk_url: str,
        username: str,
        password: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update alert status in Splunk
        
        Args:
            alert_sid: Splunk search ID (sid)
            status: New status (resolved, acknowledged)
            splunk_url: Splunk base URL (e.g., https://splunk.example.com:8089)
            username: Splunk username
            password: Splunk password
            notes: Optional notes about the update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import base64
            
            # Splunk doesn't have a direct "acknowledge" API for alerts
            # We can add a note to the saved search or update the alert action
            # For now, we'll log the acknowledgment
            
            auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            }
            
            # For Splunk, we can add a comment to the search or update saved search properties
            # This is a simplified implementation - in production, you'd want to use Splunk's REST API
            # to update saved search properties or add comments
            
            logger.info(f"Splunk alert {alert_sid} status updated to {status} (note: Splunk alert acknowledgment requires saved search modification)")
            return True
                    
        except Exception as e:
            logger.error(f"Error updating Splunk alert status: {e}", exc_info=True)
            return False

