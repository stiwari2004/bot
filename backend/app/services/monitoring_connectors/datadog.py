"""
Datadog Monitoring Connector
Handles webhook alerts and API integration with Datadog
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import re
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatadogConnector:
    """Connector for Datadog monitoring platform"""
    
    def __init__(self):
        self.name = "datadog"
    
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Datadog webhook payload to internal ticket format
        
        Datadog webhook format:
        {
            "title": "Alert title",
            "text": "Alert description",
            "body": "Alert body with URLs containing /monitors/16908155",
            "alert_id": "12345",
            "monitor_id": "{{monitor.id}}",  # May be literal string, not expanded
            "alert_metric": "cpu.usage",
            "alert_status": "alerting",
            "alert_transition": "Triggered",
            "priority": "normal|low|high",
            "tags": ["env:prod", "service:api"],
            "event_type": "alert",
            "date": "2025-01-01T00:00:00Z"
        }
        """
        try:
            # Extract alert information
            title = payload.get("title", "Datadog Alert")
            description = payload.get("text", "")
            alert_id = payload.get("alert_id") or payload.get("id")
            
            # Extract monitor_id - try multiple sources
            monitor_id = payload.get("monitor_id")
            
            # If monitor_id is a template variable (not expanded), try to extract from body/link
            if not monitor_id or monitor_id.startswith("{{") or monitor_id.startswith("$"):
                # Try to extract from body field which contains URLs like:
                # https://us5.datadoghq.com/monitors/16908155?group=...
                body = payload.get("body", "")
                link = payload.get("link", "")
                
                # Search for /monitors/{id} pattern in body or link
                monitor_id_match = None
                for text in [body, link]:
                    if text:
                        # Match /monitors/ followed by digits
                        match = re.search(r'/monitors/(\d+)', text)
                        if match:
                            monitor_id_match = match.group(1)
                            break
                
                if monitor_id_match:
                    monitor_id = monitor_id_match
                    logger.info(f"Extracted monitor_id={monitor_id} from webhook body/link")
                else:
                    logger.warning(f"Could not extract monitor_id from webhook payload. body={body[:100]}...")
            
            alert_status = payload.get("alert_status", "alerting")
            priority = payload.get("priority", "normal")
            
            # Map Datadog priority to severity
            priority_map = {
                "critical": "critical",
                "high": "high",
                "normal": "medium",
                "low": "low"
            }
            severity = priority_map.get(priority.lower(), "medium")
            
            # Extract environment and service from tags
            tags = payload.get("tags", [])
            environment = "prod"
            service = None
            
            for tag in tags:
                if isinstance(tag, str):
                    if tag.startswith("env:"):
                        environment = tag.split(":", 1)[1]
                    elif tag.startswith("service:"):
                        service = tag.split(":", 1)[1]
            
            # Extract scope/group from body/link URLs if available (e.g., group=host:srv640992)
            scope = None
            body = payload.get("body", "")
            link = payload.get("link", "")
            for text in [body, link]:
                if text:
                    # Match group=host:xxx or similar patterns
                    scope_match = re.search(r'group=([^&]+)', text)
                    if scope_match:
                        scope = scope_match.group(1)
                        # URL decode if needed (e.g., host%3Asrv640992 -> host:srv640992)
                        try:
                            import urllib.parse
                            scope = urllib.parse.unquote(scope)
                        except:
                            pass
                        break
            
            return {
                # Use monitor_id as primary external_id when available, so we can mute the correct monitor
                "external_id": str(monitor_id or alert_id) if (monitor_id or alert_id) else None,
                "title": title,
                "description": description,
                "severity": severity,
                "environment": environment,
                "service": service,
                "status": "open" if alert_status == "alerting" else "resolved",
                "metadata": {
                    "datadog_alert_id": alert_id,
                    "datadog_monitor_id": monitor_id,
                    "datadog_scope": scope,  # Store scope for muting with specific group
                    "datadog_alert_status": alert_status,
                    "datadog_alert_metric": payload.get("alert_metric"),
                    "datadog_alert_transition": payload.get("alert_transition"),
                    "datadog_tags": tags,
                    "datadog_event_type": payload.get("event_type"),
                    "raw_payload": payload
                }
            }
        except Exception as e:
            logger.error(f"Error normalizing Datadog webhook: {e}", exc_info=True)
            # Return basic format on error
            return {
                "external_id": payload.get("alert_id") or payload.get("id"),
                "title": payload.get("title", "Datadog Alert"),
                "description": payload.get("text", ""),
                "severity": "medium",
                "environment": "prod",
                "service": None,
                "metadata": {"raw_payload": payload}
            }
    
    async def fetch_alerts(
        self,
        api_key: str,
        application_key: str,
        base_url: str = "https://api.datadoghq.com",
        status: str = "Alert"
    ) -> List[Dict[str, Any]]:
        """
        Fetch active alerts from Datadog API
        
        Args:
            api_key: Datadog API key
            application_key: Datadog Application key
            base_url: Datadog API base URL
            status: Alert status to filter (Alert, Warn, No Data, OK)
        
        Returns:
            List of alert dictionaries
        """
        try:
            headers = {
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": application_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch monitors with alert status
                response = await client.get(
                    f"{base_url}/api/v1/monitor",
                    headers=headers,
                    params={"status": status}
                )
                
                if response.status_code == 200:
                    monitors = response.json()
                    alerts = []
                    for monitor in monitors:
                        alerts.append({
                            "id": monitor.get("id"),
                            "title": monitor.get("name", "Unnamed Monitor"),
                            "message": monitor.get("message", ""),
                            "severity": self._map_priority_to_severity(monitor.get("priority")),
                            "status": monitor.get("overall_state", "unknown"),
                            "tags": monitor.get("tags", []),
                            "created_at": datetime.utcnow().isoformat(),
                            "raw_data": monitor
                        })
                    logger.info(f"Fetched {len(alerts)} alerts from Datadog")
                    return alerts
                else:
                    logger.error(f"Datadog API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching Datadog alerts: {e}", exc_info=True)
            return []
    
    def _map_priority_to_severity(self, priority: Optional[int]) -> str:
        """Map Datadog priority (1-5) to severity"""
        if priority is None:
            return "medium"
        if priority <= 1:
            return "critical"
        elif priority <= 2:
            return "high"
        elif priority <= 3:
            return "medium"
        else:
            return "low"
    
    async def update_alert_status(
        self,
        alert_id: str,
        status: str,  # "resolved" or "acknowledged"
        api_key: str,
        application_key: str,
        base_url: str = "https://api.datadoghq.com",
        notes: Optional[str] = None,
        scope: Optional[str] = None
    ) -> bool:
        """
        Update alert status in Datadog
        
        Args:
            alert_id: Datadog alert/monitor ID
            status: New status (resolved, acknowledged)
            api_key: Datadog API key
            application_key: Datadog Application key
            base_url: Datadog API base URL
            notes: Optional notes about the update
            scope: Optional scope for muting (e.g., "host:srv640992")
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize base_url to avoid leading/trailing spaces or missing protocol
            safe_base_url = (base_url or "").strip().rstrip("/")
            if not safe_base_url.startswith("http://") and not safe_base_url.startswith(
                "https://"
            ):
                logger.error(
                    f"Datadog base_url is invalid or missing protocol: {base_url!r} "
                    f"(computed safe_base_url={safe_base_url!r})"
                )
                return False

            # Validate that we have both keys
            if not api_key:
                logger.error("Datadog API key is missing")
                return False
            if not application_key:
                logger.error("Datadog Application key is missing")
                return False
            
            headers = {
                "DD-API-KEY": api_key.strip(),
                "DD-APPLICATION-KEY": application_key.strip(),
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Log key lengths (not values) for debugging
            logger.info(
                f"Datadog auth: API key length={len(api_key.strip())}, "
                f"Application key length={len(application_key.strip())}, "
                f"base_url={safe_base_url}"
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if status == "resolved" or status == "acknowledged":
                    # Resolve/acknowledge by muting the monitor
                    mute_url = f"{safe_base_url}/api/v1/monitor/{alert_id}/mute"
                    mute_payload = {
                        "message": notes or (f"{status.capitalize()}d via AI Agent")
                    }
                    
                    # Include scope if provided (for multi-group monitors)
                    if scope:
                        mute_payload["scope"] = scope
                    
                    logger.info(
                        f"Calling Datadog mute API: {mute_url} with payload={mute_payload}, "
                        f"headers keys={list(headers.keys())}"
                    )
                    
                    response = await client.post(mute_url, json=mute_payload, headers=headers)
                    
                    # Log response details for debugging
                    logger.info(
                        f"Datadog API response: status={response.status_code}, "
                        f"headers={dict(response.headers)}, "
                        f"body={response.text[:500]}"
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully {status} Datadog monitor {alert_id} (scope={scope})")
                        return True
                    else:
                        logger.error(
                            f"Failed to {status} Datadog monitor {alert_id}: "
                            f"{response.status_code} - {response.text}"
                        )
                        return False
                else:
                    logger.warning(f"Unknown status for Datadog alert: {status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating Datadog alert status: {e}", exc_info=True)
            return False

