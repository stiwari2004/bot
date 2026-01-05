"""
SolarWinds API connector
Supports both SolarWinds Orion (on-premises) and SolarWinds Observability SaaS
Fetches alerts and manages alert states
"""
import base64
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from app.core.logging import get_logger
from app.services.monitoring_connectors.solarwinds_types import (
    SolarWindsAlert,
    SolarWindsNode,
    SolarWindsConnectionConfig
)

logger = get_logger(__name__)


class SolarWindsConnector:
    """Connector for SolarWinds Orion (on-prem) and Observability SaaS"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.name = "solarwinds"
    
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize SolarWinds webhook payload to internal alert format
        
        SolarWinds Observability SaaS webhook format (varies by configuration):
        {
            "alert_id": "12345",
            "alert_name": "High CPU Usage",
            "alert_message": "CPU usage exceeded threshold",
            "alert_status": "triggered|resolved|acknowledged",
            "severity": "critical|warning|info",
            "entity_name": "server-01",
            "entity_type": "host",
            "metric_name": "cpu.usage",
            "metric_value": 95.5,
            "threshold": 90.0,
            "timestamp": "2025-01-01T00:00:00Z",
            "tags": ["env:prod", "service:api"],
            "url": "https://ap-01.cloud.solarwinds.com/alerts/12345"
        }
        
        Note: Actual webhook format depends on how webhooks are configured in SolarWinds UI.
        """
        try:
            # Extract alert information
            alert_id = payload.get("alert_id") or payload.get("id") or payload.get("event_id")
            title = payload.get("alert_name") or payload.get("name") or payload.get("title", "SolarWinds Alert")
            description = payload.get("alert_message") or payload.get("message") or payload.get("description", "")
            
            # Extract status
            alert_status = payload.get("alert_status") or payload.get("status", "triggered")
            
            # Map SolarWinds severity to standard severity
            severity_map = {
                "critical": "critical",
                "error": "high",
                "warning": "medium",
                "info": "low",
                "information": "low"
            }
            raw_severity = payload.get("severity") or payload.get("level", "warning")
            severity = severity_map.get(raw_severity.lower(), "medium")
            
            # Extract entity/service information
            entity_name = payload.get("entity_name") or payload.get("entity")
            entity_type = payload.get("entity_type")
            service = None
            
            # Extract environment and service from tags
            tags = payload.get("tags", [])
            environment = "prod"
            
            for tag in tags:
                if isinstance(tag, str):
                    if tag.startswith("env:"):
                        environment = tag.split(":", 1)[1]
                    elif tag.startswith("service:"):
                        service = tag.split(":", 1)[1]
            
            # Extract metric information
            metric_name = payload.get("metric_name")
            metric_value = payload.get("metric_value")
            threshold = payload.get("threshold")
            
            return {
                "external_id": str(alert_id) if alert_id else None,
                "title": title,
                "description": description,
                "severity": severity,
                "environment": environment,
                "service": service or entity_name,
                "status": "open" if alert_status in ["triggered", "active", "firing"] else "resolved",
                "metadata": {
                    "solarwinds_alert_id": alert_id,
                    "solarwinds_alert_status": alert_status,
                    "solarwinds_entity_name": entity_name,
                    "solarwinds_entity_type": entity_type,
                    "solarwinds_metric_name": metric_name,
                    "solarwinds_metric_value": metric_value,
                    "solarwinds_threshold": threshold,
                    "solarwinds_severity": raw_severity,
                    "solarwinds_tags": tags,
                    "solarwinds_url": payload.get("url"),
                    "solarwinds_timestamp": payload.get("timestamp"),
                    "raw_payload": payload
                }
            }
        except Exception as e:
            logger.error(f"Error normalizing SolarWinds webhook: {e}", exc_info=True)
            # Return basic format on error
            return {
                "external_id": payload.get("alert_id") or payload.get("id"),
                "title": payload.get("alert_name") or payload.get("title", "SolarWinds Alert"),
                "description": payload.get("alert_message") or payload.get("message", ""),
                "severity": "medium",
                "environment": "prod",
                "service": None,
                "metadata": {"raw_payload": payload}
            }
    
    def _is_observability_saas(self, api_base_url: str) -> bool:
        """Check if this is SolarWinds Observability SaaS (not Orion on-prem)"""
        return "cloud.solarwinds.com" in api_base_url.lower()
    
    async def test_connection(self, config: SolarWindsConnectionConfig) -> Dict[str, Any]:
        """
        Test connection to SolarWinds instance
        
        Returns:
            Dict with success status and message
        """
        try:
            headers = await self._get_auth_headers(config)
            
            # Check if this is Observability SaaS or Orion on-prem
            if self._is_observability_saas(config.api_base_url):
                # Observability SaaS - test with /v1/metrics endpoint (as per official API docs)
                # API docs: https://documentation.solarwinds.com/en/success_center/observability/content/api/api-swagger.htm
                test_url = f"{config.api_base_url.rstrip('/')}/v1/metrics"
                # Use a simple GET request with limit=1 to test authentication
                params = {"limit": 1}
                response = await self.client.get(test_url, headers=headers, params=params, timeout=10.0)
            else:
                # Orion on-prem - use SWQL query
                test_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
                query = "SELECT TOP 1 NodeID, Caption FROM Orion.Nodes"
                payload = {"query": query}
                response = await self.client.post(test_url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code == 200:
                # Check if response contains metrics info (valid Observability SaaS response)
                try:
                    data = response.json()
                    if isinstance(data, dict) and "metricsInfo" in data:
                        metric_count = len(data.get("metricsInfo", []))
                        return {
                            "success": True, 
                            "message": f"Connection successful. Found {metric_count} available metrics."
                        }
                except:
                    pass
                return {"success": True, "message": "Connection successful"}
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Authentication failed. Please check your API token."
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": f"API endpoint not found. Please verify your API base URL is correct: {config.api_base_url}"
                }
            else:
                error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                return {
                    "success": False,
                    "message": f"Connection failed: {response.status_code} - {error_text}"
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Connection timeout. Please check your network connection and API base URL."
            }
        except Exception as e:
            logger.error(f"SolarWinds connection test failed: {e}", exc_info=True)
            return {"success": False, "message": f"Connection test error: {str(e)}"}
    
    async def fetch_alerts(
        self,
        config: SolarWindsConnectionConfig,
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SolarWindsAlert]:
        """
        Fetch alerts from SolarWinds
        
        Args:
            config: Connection configuration
            status_filter: Filter by alert state (Active, Acknowledged, Resolved)
            severity_filter: Filter by severity (Critical, Error, Warning, Information)
            limit: Maximum number of alerts to fetch
        
        Returns:
            List of SolarWindsAlert objects
        """
        try:
            headers = await self._get_auth_headers(config)
            
            # Check if this is Observability SaaS or Orion on-prem
            if self._is_observability_saas(config.api_base_url):
                # Observability SaaS - use REST API v1
                return await self._fetch_alerts_observability_saas(
                    config, headers, status_filter, severity_filter, limit
                )
            else:
                # Orion on-prem - use SWQL query
                return await self._fetch_alerts_orion(
                    config, headers, status_filter, severity_filter, limit
                )
        except httpx.HTTPStatusError as e:
            logger.error(f"SolarWinds API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch alerts from SolarWinds: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching SolarWinds alerts: {e}", exc_info=True)
            raise
    
    async def _fetch_alerts_observability_saas(
        self,
        config: SolarWindsConnectionConfig,
        headers: Dict[str, str],
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SolarWindsAlert]:
        """
        Fetch alerts from SolarWinds Observability SaaS using REST API v1
        
        API Documentation: https://documentation.solarwinds.com/en/success_center/observability/content/api/api-swagger.htm
        Swagger UI: https://api.xx-yy.cloud.solarwinds.com/v1/#/
        
        Note: SolarWinds Observability SaaS does not have a direct "alerts" endpoint.
        Available endpoints typically include: changeEvents, cloudAccounts, dbo, dem, 
        entities, logs, metadata, metrics, tokens.
        
        Alerts in Observability SaaS are typically:
        - Derived from metrics with thresholds (configured in UI)
        - Sent via webhooks when thresholds are breached
        - Available through changeEvents (for infrastructure changes)
        - Managed through the UI dashboard
        
        For alert integration, consider:
        1. Setting up webhooks in SolarWinds Observability UI
        2. Using changeEvents endpoint for infrastructure change notifications
        3. Monitoring metrics and deriving alerts from threshold breaches
        """
        try:
            base_url = config.api_base_url.rstrip('/')
            
            # Try endpoints that might contain alert-like data
            # Based on available endpoints: changeEvents, entities, logs, etc.
            possible_endpoints = [
                f"{base_url}/v1/changeEvents",    # Infrastructure change events (closest to alerts)
                f"{base_url}/v1/entities",        # Entities with health status
                f"{base_url}/v1/logs",            # Log entries that might indicate issues
            ]
            
            alerts = []
            last_error = None
            
            for alerts_url in possible_endpoints:
                try:
                    # Build query parameters
                    params = {"limit": min(limit, 1000)}  # API limit
                    
                    logger.info(f"Trying SolarWinds Observability endpoint: {alerts_url}")
                    
                    response = await self.client.get(alerts_url, headers=headers, params=params, timeout=10.0)
                    
                    if response.status_code == 404:
                        # Try next endpoint
                        logger.debug(f"Endpoint {alerts_url} returned 404, trying next...")
                        continue
                    
                    if response.status_code == 401:
                        raise Exception("Authentication failed. Invalid API token.")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Observability SaaS returns data in different formats
                    # Handle common response structures
                    alert_items = []
                    if isinstance(data, list):
                        alert_items = data
                    elif isinstance(data, dict):
                        alert_items = (
                            data.get("alerts", []) or 
                            data.get("data", []) or 
                            data.get("results", []) or
                            data.get("items", []) or
                            data.get("events", []) or
                            data.get("incidents", []) or
                            data.get("notifications", [])
                        )
                    
                    for item in alert_items[:limit]:
                        alert = self._parse_observability_alert(item)
                        if alert:
                            # Apply filters
                            if status_filter and alert.state not in status_filter:
                                continue
                            if severity_filter and alert.severity not in severity_filter:
                                continue
                            alerts.append(alert)
                    
                    if alerts or response.status_code == 200:
                        logger.info(f"Fetched {len(alerts)} alerts from SolarWinds Observability ({alerts_url})")
                        return alerts
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        last_error = f"Endpoint not found: {alerts_url}"
                        continue
                    else:
                        last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                        raise
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # If we get here, none of the endpoints worked or returned alert data
            # This is expected - Observability SaaS doesn't have a direct alerts API
            # Alerts are typically managed through:
            # 1. Webhooks (configured in UI)
            # 2. Metrics with thresholds (UI-based)
            # 3. changeEvents (infrastructure changes)
            logger.info(
                f"SolarWinds Observability SaaS does not expose alerts via REST API. "
                f"Available endpoints: changeEvents, cloudAccounts, dbo, dem, entities, logs, metadata, metrics, tokens. "
                f"To receive alerts, configure webhooks in the SolarWinds Observability UI or use changeEvents endpoint."
            )
            return []
            
        except Exception as e:
            logger.error(f"Error fetching Observability SaaS alerts: {e}", exc_info=True)
            # Return empty list instead of raising to allow graceful degradation
            return []
    
    async def _fetch_alerts_orion(
        self,
        config: SolarWindsConnectionConfig,
        headers: Dict[str, str],
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SolarWindsAlert]:
        """Fetch alerts from SolarWinds Orion on-prem using SWQL"""
        try:
            query_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            
            # Build SWQL query
            swql_query = self._build_alert_query(status_filter, severity_filter, limit)
            
            payload = {"query": swql_query}
            
            logger.info(f"Fetching SolarWinds Orion alerts with query: {swql_query[:100]}...")
            
            response = await self.client.post(query_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            alerts = []
            results = data.get("results", [])
            
            for result in results:
                alert = self._parse_alert(result)
                if alert:
                    alerts.append(alert)
            
            logger.info(f"Fetched {len(alerts)} alerts from SolarWinds Orion")
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching Orion alerts: {e}", exc_info=True)
            raise
    
    def _build_alert_query(
        self,
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> str:
        """
        Build SWQL query for fetching alerts
        
        SolarWinds uses SWQL (SolarWinds Query Language) which is similar to SQL
        """
        # Base query - adjust table/field names based on your SolarWinds version
        # This is a generic query - you may need to adjust for your specific SolarWinds setup
        query = """
        SELECT TOP {limit}
            AlertObjectID,
            AlertName,
            AlertMessage,
            Severity,
            AlertState,
            EntityType,
            EntityCaption,
            EntityUri,
            TriggeredDateTime,
            AcknowledgedDateTime,
            ResolvedDateTime
        FROM Orion.AlertActive
        WHERE 1=1
        """
        
        # Add filters
        if status_filter:
            status_conditions = " OR ".join([f"AlertState = '{s}'" for s in status_filter])
            query += f" AND ({status_conditions})"
        
        if severity_filter:
            severity_conditions = " OR ".join([f"Severity = '{s}'" for s in severity_filter])
            query += f" AND ({severity_conditions})"
        
        query += " ORDER BY TriggeredDateTime DESC"
        
        # Use parameterized query to prevent SQL injection
        # Note: SWQL doesn't support parameters like SQL, so we validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 10000:
            limit = 100
        return query.format(limit=limit)
    
    def _parse_alert(self, result: Dict[str, Any]) -> Optional[SolarWindsAlert]:
        """Parse SWQL query result (Orion on-prem) into SolarWindsAlert object"""
        try:
            # Map SolarWinds fields to our alert structure
            # Adjust field names based on your SolarWinds version
            alert = SolarWindsAlert(
                alert_id=str(result.get("AlertObjectID", "")),
                name=result.get("AlertName", "Unknown Alert"),
                message=result.get("AlertMessage", ""),
                severity=self._map_severity(result.get("Severity", "")),
                state=self._map_state(result.get("AlertState", "")),
                entity_type=result.get("EntityType", ""),
                entity_name=result.get("EntityCaption", ""),
                entity_id=result.get("EntityUri", ""),
                triggered_time=self._parse_datetime(result.get("TriggeredDateTime")),
                acknowledged_time=self._parse_datetime(result.get("AcknowledgedDateTime")),
                resolved_time=self._parse_datetime(result.get("ResolvedDateTime")),
                custom_properties={}
            )
            return alert
        except Exception as e:
            logger.error(f"Error parsing SolarWinds alert: {e}", exc_info=True)
            return None
    
    def _parse_observability_alert(self, result: Dict[str, Any]) -> Optional[SolarWindsAlert]:
        """Parse Observability SaaS alert into SolarWindsAlert object"""
        try:
            # Observability SaaS alert structure varies, handle common fields
            alert_id = str(result.get("id") or result.get("alert_id") or result.get("_id", ""))
            if not alert_id:
                return None
            
            # Extract name/title
            name = result.get("name") or result.get("title") or result.get("alert_name", "Unknown Alert")
            
            # Extract message/description
            message = result.get("message") or result.get("description") or result.get("alert_message", "")
            
            # Extract severity (may be numeric or string)
            severity_raw = result.get("severity") or result.get("level") or result.get("priority", "")
            severity = self._map_severity(str(severity_raw))
            
            # Extract state/status
            state_raw = result.get("state") or result.get("status") or result.get("alert_state", "active")
            state = self._map_state(str(state_raw))
            
            # Extract entity information
            entity_type = result.get("entity_type") or result.get("source_type", "")
            entity_name = result.get("entity_name") or result.get("source_name") or result.get("host", "")
            entity_id = result.get("entity_id") or result.get("source_id") or ""
            
            # Extract timestamps
            triggered_time = self._parse_datetime(
                result.get("created_at") or result.get("triggered_at") or result.get("timestamp")
            )
            acknowledged_time = self._parse_datetime(result.get("acknowledged_at"))
            resolved_time = self._parse_datetime(result.get("resolved_at") or result.get("closed_at"))
            
            # Store all original fields as custom properties
            custom_properties = {k: v for k, v in result.items() if k not in [
                "id", "alert_id", "_id", "name", "title", "alert_name",
                "message", "description", "alert_message", "severity", "level", "priority",
                "state", "status", "alert_state", "entity_type", "source_type",
                "entity_name", "source_name", "host", "entity_id", "source_id",
                "created_at", "triggered_at", "timestamp", "acknowledged_at", "resolved_at", "closed_at"
            ]}
            
            alert = SolarWindsAlert(
                alert_id=alert_id,
                name=name,
                message=message,
                severity=severity,
                state=state,
                entity_type=entity_type,
                entity_name=entity_name,
                entity_id=entity_id,
                triggered_time=triggered_time or datetime.now(timezone.utc),
                acknowledged_time=acknowledged_time,
                resolved_time=resolved_time,
                custom_properties=custom_properties
            )
            return alert
        except Exception as e:
            logger.error(f"Error parsing Observability SaaS alert: {e}", exc_info=True)
            return None
    
    def _map_severity(self, solarwinds_severity: str) -> str:
        """Map SolarWinds severity to internal format"""
        severity_map = {
            "Critical": "Critical",
            "Error": "Error",
            "Warning": "Warning",
            "Information": "Info",
            "Info": "Info",
        }
        return severity_map.get(solarwinds_severity, "Info")
    
    def _map_state(self, solarwinds_state: str) -> str:
        """Map SolarWinds alert state to internal format"""
        state_map = {
            "Active": "Active",
            "Acknowledged": "Acknowledged",
            "Resolved": "Resolved",
            "Suppressed": "Resolved",
        }
        return state_map.get(solarwinds_state, "Active")
    
    def _parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        """Parse datetime from SolarWinds format"""
        if not dt_value:
            return None
        
        if isinstance(dt_value, str):
            # Try common datetime formats
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(dt_value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        
        if isinstance(dt_value, datetime):
            return dt_value.replace(tzinfo=timezone.utc)
        
        return None
    
    async def acknowledge_alert(
        self,
        config: SolarWindsConnectionConfig,
        alert_id: str
    ) -> bool:
        """
        Acknowledge an alert in SolarWinds
        
        Args:
            config: Connection configuration
            alert_id: Alert ID to acknowledge
        
        Returns:
            True if successful
        """
        try:
            headers = await self._get_auth_headers(config)
            # SolarWinds REST API endpoint for acknowledging alerts
            # Adjust endpoint based on your SolarWinds version
            ack_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Invoke/Orion.AlertActive/Acknowledge"
            
            payload = {
                "ids": [alert_id]
            }
            
            response = await self.client.post(
                ack_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            logger.info(f"Acknowledged SolarWinds alert: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging SolarWinds alert: {e}", exc_info=True)
            return False
    
    async def resolve_alert(
        self,
        config: SolarWindsConnectionConfig,
        alert_id: str
    ) -> bool:
        """
        Resolve an alert in SolarWinds
        
        Args:
            config: Connection configuration
            alert_id: Alert ID to resolve
        
        Returns:
            True if successful
        """
        try:
            headers = await self._get_auth_headers(config)
            # SolarWinds REST API endpoint for resolving alerts
            resolve_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Invoke/Orion.AlertActive/Resolve"
            
            payload = {
                "ids": [alert_id]
            }
            
            response = await self.client.post(
                resolve_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            logger.info(f"Resolved SolarWinds alert: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving SolarWinds alert: {e}", exc_info=True)
            return False
    
    async def _get_auth_headers(self, config: SolarWindsConnectionConfig) -> Dict[str, str]:
        """
        Get authentication headers for SolarWinds API
        
        Supports:
        - Basic Auth (username/password)
        - API Key
        - OAuth 2.0
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Try OAuth first if available
        if config.oauth_token:
            # Check if token is expired
            if config.oauth_token_expires and datetime.now(timezone.utc) < config.oauth_token_expires:
                headers["Authorization"] = f"Bearer {config.oauth_token}"
                return headers
            elif config.oauth_client_id and config.oauth_client_secret:
                # Refresh token
                token = await self._refresh_oauth_token(config)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    return headers
        
        # Try API Key (for both Orion on-prem and Observability SaaS)
        if config.api_key:
            # SolarWinds Observability SaaS uses Bearer token
            # Orion on-prem uses X-SolarWinds-API-Key header
            # Check if it's Observability SaaS (api.cloud.solarwinds.com) or Orion
            if "cloud.solarwinds.com" in config.api_base_url.lower():
                # Observability SaaS - use Bearer token
                headers["Authorization"] = f"Bearer {config.api_key}"
            else:
                # Orion on-prem - use custom header
                headers["X-SolarWinds-API-Key"] = config.api_key
            return headers
        
        # Fall back to Basic Auth
        if config.username and config.password:
            credentials = f"{config.username}:{config.password}"
            encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            headers["Authorization"] = f"Basic {encoded}"
            return headers
        
        raise Exception("No valid authentication method found for SolarWinds")
    
    async def _refresh_oauth_token(self, config: SolarWindsConnectionConfig) -> Optional[str]:
        """Refresh OAuth token"""
        try:
            token_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/RequestAccessToken"
            
            payload = {
                "grant_type": "client_credentials",
                "client_id": config.oauth_client_id,
                "client_secret": config.oauth_client_secret
            }
            
            response = await self.client.post(token_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return data.get("access_token")
        except Exception as e:
            logger.error(f"Error refreshing SolarWinds OAuth token: {e}", exc_info=True)
            return None
    
    async def fetch_nodes(
        self,
        config: SolarWindsConnectionConfig,
        status_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SolarWindsNode]:
        """
        Fetch nodes/devices from SolarWinds
        
        Args:
            config: Connection configuration
            status_filter: Filter by node status (Up, Down, Unknown)
            limit: Maximum number of nodes to fetch
        
        Returns:
            List of SolarWindsNode objects
        """
        try:
            headers = await self._get_auth_headers(config)
            query_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            
            # Build SWQL query for nodes
            query = """
            SELECT TOP {limit}
                NodeID,
                Caption,
                IPAddress,
                Status,
                NodeType
            FROM Orion.Nodes
            WHERE 1=1
            """
            
            if status_filter:
                status_conditions = " OR ".join([f"Status = '{s}'" for s in status_filter])
                query += f" AND ({status_conditions})"
            
            query += " ORDER BY Caption"
            
            # Validate limit to prevent injection
            if not isinstance(limit, int) or limit < 1 or limit > 10000:
                limit = 100
            swql_query = query.format(limit=limit)
            
            payload = {"query": swql_query}
            
            logger.info(f"Fetching SolarWinds nodes with query: {swql_query[:100]}...")
            
            response = await self.client.post(
                query_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            nodes = []
            results = data.get("results", [])
            
            for result in results:
                node = SolarWindsNode(
                    node_id=str(result.get("NodeID", "")),
                    caption=result.get("Caption", "Unknown Node"),
                    ip_address=result.get("IPAddress", ""),
                    status=result.get("Status", "Unknown"),
                    node_type=result.get("NodeType", ""),
                    custom_properties={}
                )
                nodes.append(node)
            
            logger.info(f"Fetched {len(nodes)} nodes from SolarWinds")
            return nodes
            
        except httpx.HTTPStatusError as e:
            logger.error(f"SolarWinds API error fetching nodes: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch nodes from SolarWinds: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching SolarWinds nodes: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()



