"""
SolarWinds API connector
Supports both SolarWinds Orion (on-premises) and SolarWinds Observability SaaS
Fetches alerts and manages alert states
"""
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from app.core.logging import get_logger
from app.services.monitoring_connectors.solarwinds_types import (
    SolarWindsAlert,
    SolarWindsNode,
    SolarWindsConnectionConfig,
)
from app.services.monitoring_connectors.solarwinds_alert_parser import SolarWindsAlertParser

logger = get_logger(__name__)


class SolarWindsConnector:
    """Connector for SolarWinds Orion (on-prem) and Observability SaaS"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.name = "solarwinds"
        self.parser = SolarWindsAlertParser()

    # ------------------------------------------------------------------
    # Webhook normalization (delegates to parser)
    # ------------------------------------------------------------------
    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.parser.normalize_webhook(payload)

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------
    def _is_observability_saas(self, api_base_url: str) -> bool:
        return "cloud.solarwinds.com" in api_base_url.lower()

    async def test_connection(self, config: SolarWindsConnectionConfig) -> Dict[str, Any]:
        try:
            headers = await self._get_auth_headers(config)
            if self._is_observability_saas(config.api_base_url):
                test_url = f"{config.api_base_url.rstrip('/')}/v1/metrics"
                response = await self.client.get(test_url, headers=headers, params={"limit": 1}, timeout=10.0)
            else:
                test_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
                response = await self.client.post(test_url, headers=headers, json={"query": "SELECT TOP 1 NodeID, Caption FROM Orion.Nodes"}, timeout=10.0)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "metricsInfo" in data:
                        return {"success": True, "message": f"Connection successful. Found {len(data.get('metricsInfo', []))} available metrics."}
                except Exception:
                    pass
                return {"success": True, "message": "Connection successful"}
            elif response.status_code == 401:
                return {"success": False, "message": "Authentication failed. Please check your API token."}
            elif response.status_code == 404:
                return {"success": False, "message": f"API endpoint not found. Please verify your API base URL is correct: {config.api_base_url}"}
            else:
                error_text = response.text[:200] if hasattr(response, "text") else str(response.status_code)
                return {"success": False, "message": f"Connection failed: {response.status_code} - {error_text}"}
        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timeout. Please check your network connection and API base URL."}
        except Exception as e:
            logger.error(f"SolarWinds connection test failed: {e}", exc_info=True)
            return {"success": False, "message": f"Connection test error: {str(e)}"}

    # ------------------------------------------------------------------
    # Fetch alerts
    # ------------------------------------------------------------------
    async def fetch_alerts(
        self,
        config: SolarWindsConnectionConfig,
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[SolarWindsAlert]:
        try:
            headers = await self._get_auth_headers(config)
            if self._is_observability_saas(config.api_base_url):
                return await self._fetch_alerts_observability_saas(config, headers, status_filter, severity_filter, limit)
            else:
                return await self._fetch_alerts_orion(config, headers, status_filter, severity_filter, limit)
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
        limit: int = 100,
    ) -> List[SolarWindsAlert]:
        try:
            base_url = config.api_base_url.rstrip("/")
            possible_endpoints = [
                f"{base_url}/v1/changeEvents",
                f"{base_url}/v1/entities",
                f"{base_url}/v1/logs",
            ]
            alerts = []

            for alerts_url in possible_endpoints:
                try:
                    response = await self.client.get(alerts_url, headers=headers, params={"limit": min(limit, 1000)}, timeout=10.0)
                    if response.status_code == 404:
                        continue
                    if response.status_code == 401:
                        raise Exception("Authentication failed. Invalid API token.")
                    response.raise_for_status()
                    data = response.json()

                    alert_items = data if isinstance(data, list) else (
                        data.get("alerts") or data.get("data") or data.get("results") or
                        data.get("items") or data.get("events") or data.get("incidents") or
                        data.get("notifications") or []
                    )

                    for item in alert_items[:limit]:
                        alert = self.parser.parse_observability_alert(item)
                        if alert:
                            if status_filter and alert.state not in status_filter:
                                continue
                            if severity_filter and alert.severity not in severity_filter:
                                continue
                            alerts.append(alert)

                    if alerts or response.status_code == 200:
                        return alerts
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        continue
                    raise
                except Exception:
                    continue

            logger.info("SolarWinds Observability SaaS does not expose alerts via REST API. Use webhooks or changeEvents.")
            return []
        except Exception as e:
            logger.error(f"Error fetching Observability SaaS alerts: {e}", exc_info=True)
            return []

    async def _fetch_alerts_orion(
        self,
        config: SolarWindsConnectionConfig,
        headers: Dict[str, str],
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[SolarWindsAlert]:
        try:
            query_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            swql_query = self.parser.build_alert_query(status_filter, severity_filter, limit)
            response = await self.client.post(query_url, headers=headers, json={"query": swql_query})
            response.raise_for_status()
            data = response.json()
            alerts = [self.parser.parse_orion_alert(r) for r in data.get("results", [])]
            alerts = [a for a in alerts if a is not None]
            logger.info(f"Fetched {len(alerts)} alerts from SolarWinds Orion")
            return alerts
        except Exception as e:
            logger.error(f"Error fetching Orion alerts: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Alert actions
    # ------------------------------------------------------------------
    async def acknowledge_alert(self, config: SolarWindsConnectionConfig, alert_id: str) -> bool:
        try:
            headers = await self._get_auth_headers(config)
            ack_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Invoke/Orion.AlertActive/Acknowledge"
            response = await self.client.post(ack_url, headers=headers, json={"ids": [alert_id]})
            response.raise_for_status()
            logger.info(f"Acknowledged SolarWinds alert: {alert_id}")
            return True
        except Exception as e:
            logger.error(f"Error acknowledging SolarWinds alert: {e}", exc_info=True)
            return False

    async def resolve_alert(self, config: SolarWindsConnectionConfig, alert_id: str) -> bool:
        try:
            headers = await self._get_auth_headers(config)
            resolve_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Invoke/Orion.AlertActive/Resolve"
            response = await self.client.post(resolve_url, headers=headers, json={"ids": [alert_id]})
            response.raise_for_status()
            logger.info(f"Resolved SolarWinds alert: {alert_id}")
            return True
        except Exception as e:
            logger.error(f"Error resolving SolarWinds alert: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Fetch nodes
    # ------------------------------------------------------------------
    async def fetch_nodes(
        self,
        config: SolarWindsConnectionConfig,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[SolarWindsNode]:
        try:
            headers = await self._get_auth_headers(config)
            query_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/Query"
            query = "SELECT TOP {limit} NodeID, Caption, IPAddress, Status, NodeType FROM Orion.Nodes WHERE 1=1"
            if status_filter:
                query += " AND (" + " OR ".join(f"Status = '{s}'" for s in status_filter) + ")"
            query += " ORDER BY Caption"
            if not isinstance(limit, int) or limit < 1 or limit > 10000:
                limit = 100
            swql_query = query.format(limit=limit)
            response = await self.client.post(query_url, headers=headers, json={"query": swql_query})
            response.raise_for_status()
            data = response.json()
            nodes = [
                SolarWindsNode(
                    node_id=str(r.get("NodeID", "")),
                    caption=r.get("Caption", "Unknown Node"),
                    ip_address=r.get("IPAddress", ""),
                    status=r.get("Status", "Unknown"),
                    node_type=r.get("NodeType", ""),
                    custom_properties={},
                )
                for r in data.get("results", [])
            ]
            logger.info(f"Fetched {len(nodes)} nodes from SolarWinds")
            return nodes
        except httpx.HTTPStatusError as e:
            logger.error(f"SolarWinds API error fetching nodes: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch nodes from SolarWinds: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching SolarWinds nodes: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    async def _get_auth_headers(self, config: SolarWindsConnectionConfig) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if config.oauth_token:
            if config.oauth_token_expires and datetime.now(timezone.utc) < config.oauth_token_expires:
                headers["Authorization"] = f"Bearer {config.oauth_token}"
                return headers
            elif config.oauth_client_id and config.oauth_client_secret:
                token = await self._refresh_oauth_token(config)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    return headers
        if config.api_key:
            if "cloud.solarwinds.com" in config.api_base_url.lower():
                headers["Authorization"] = f"Bearer {config.api_key}"
            else:
                headers["X-SolarWinds-API-Key"] = config.api_key
            return headers
        if config.username and config.password:
            encoded = base64.b64encode(f"{config.username}:{config.password}".encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            return headers
        raise Exception("No valid authentication method found for SolarWinds")

    async def _refresh_oauth_token(self, config: SolarWindsConnectionConfig) -> Optional[str]:
        try:
            token_url = f"{config.api_base_url.rstrip('/')}/SolarWinds/InformationService/v3/Json/RequestAccessToken"
            response = await self.client.post(token_url, json={"grant_type": "client_credentials", "client_id": config.oauth_client_id, "client_secret": config.oauth_client_secret})
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Error refreshing SolarWinds OAuth token: {e}", exc_info=True)
            return None

    async def close(self):
        await self.client.aclose()
