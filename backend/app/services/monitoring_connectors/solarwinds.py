"""
SolarWinds Orion API connector
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
    """Connector for SolarWinds Orion API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_connection(self, config: SolarWindsConnectionConfig) -> Dict[str, Any]:
        """
        Test connection to SolarWinds instance
        
        Returns:
            Dict with success status and message
        """
        try:
            # Try to authenticate and get a simple query
            headers = await self._get_auth_headers(config)
            test_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            
            # Simple SWQL query to test connection
            query = "SELECT TOP 1 NodeID, Caption FROM Orion.Nodes"
            payload = {
                "query": query
            }
            
            response = await self.client.post(
                test_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {response.status_code} - {response.text[:200]}"
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
        Fetch alerts from SolarWinds using SWQL query
        
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
            query_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            
            # Build SWQL query
            swql_query = self._build_alert_query(status_filter, severity_filter, limit)
            
            payload = {"query": swql_query}
            
            logger.info(f"Fetching SolarWinds alerts with query: {swql_query[:100]}...")
            
            response = await self.client.post(
                query_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            alerts = []
            results = data.get("results", [])
            
            for result in results:
                alert = self._parse_alert(result)
                if alert:
                    alerts.append(alert)
            
            logger.info(f"Fetched {len(alerts)} alerts from SolarWinds")
            return alerts
            
        except httpx.HTTPStatusError as e:
            logger.error(f"SolarWinds API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch alerts from SolarWinds: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching SolarWinds alerts: {e}", exc_info=True)
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
        """Parse SWQL query result into SolarWindsAlert object"""
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



