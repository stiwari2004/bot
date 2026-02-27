"""
ManageEngine OpManager API connector

This connector uses the OpManager REST API to fetch alarms for polling-based
integrations. It is focused on the /api/json/alarm/listAlarms endpoint.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class OpManagerConnector:
    """Connector for ManageEngine OpManager alarms via REST API."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        self.name = "opmanager"

    async def close(self) -> None:
        await self.client.aclose()

    async def test_connection(self, base_url: str, api_key: str) -> Dict[str, Any]:
        """
        Test connection to OpManager by calling listAlarms with a small limit.
        """
        try:
            if not base_url:
                return {"success": False, "message": "API base URL is required"}
            if not api_key:
                return {"success": False, "message": "API key is required"}

            url = f"{base_url.rstrip('/')}/api/json/alarm/listAlarms"
            headers = {"apiKey": api_key}
            params = {
                "alertType": "ActiveAlarms",
                "page": 1,
                "pageLength": 1,
            }

            logger.info(f"Testing OpManager connection to {url}")
            resp = await self.client.get(url, headers=headers, params=params)

            if resp.status_code != 200:
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {resp.status_code} - {resp.text[:200]}",
                }

            # Accept both list and dict responses
            try:
                data = resp.json()
            except Exception:
                return {
                    "success": False,
                    "message": "Received non-JSON response from OpManager",
                }

            return {
                "success": True,
                "message": "Connection to OpManager successful",
                "sample": data if isinstance(data, list) else None,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Connection timeout. Please check network and OpManager URL.",
            }
        except Exception as e:
            logger.error(f"OpManager connection test failed: {e}", exc_info=True)
            return {"success": False, "message": f"Connection test error: {str(e)}"}

    async def fetch_alarms(
        self,
        base_url: str,
        api_key: str,
        alert_type: str = "ActiveAlarms",
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch alarms from OpManager.

        Returns a list of raw alarm dictionaries as returned by OpManager.
        """
        if not base_url or not api_key:
            raise ValueError("OpManager base_url and api_key are required")

        url = f"{base_url.rstrip('/')}/api/json/alarm/listAlarms"
        headers = {"apiKey": api_key}

        params: Dict[str, Any] = {
            "alertType": alert_type or "ActiveAlarms",
            "page": 1,
            "pageLength": min(limit, 1000),
        }
        if severity is not None:
            params["severity"] = severity

        logger.info(
            f"Fetching OpManager alarms from {url} (alertType={params['alertType']}, "
            f"severity={params.get('severity')}, limit={params['pageLength']})"
        )

        resp = await self.client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        # The OpManager docs show an object with fields like rows, but
        # some deployments may return a bare list of alarms (as in the user's example).
        if isinstance(data, list):
            alarms = data
        elif isinstance(data, dict):
            # Try common shapes
            if "rows" in data and isinstance(data["rows"], list):
                alarms = data["rows"]
            elif "Alarms" in data and isinstance(data["Alarms"], list):
                alarms = data["Alarms"]
            else:
                # Fallback: if it looks like a single alarm dict, wrap it
                alarms = [data]
        else:
            alarms = []

        # Ensure each alarm has a parsed timestamp where possible
        for alarm in alarms:
            try:
                # Prefer modTimeLong (epoch ms) if present
                ts_ms = alarm.get("modTimeLong")
                if ts_ms is not None:
                    alarm["_parsed_mod_time"] = datetime.fromtimestamp(
                        int(ts_ms) / 1000.0, tz=timezone.utc
                    )
                else:
                    # Fallback: modTime string like "06/03/2025 12:47:38 PM PDT"
                    mod_time_str = alarm.get("modTime")
                    if isinstance(mod_time_str, str):
                        alarm["_parsed_mod_time"] = mod_time_str
            except Exception:
                # Best-effort only; ignore timestamp parsing errors
                continue

        logger.info(f"Fetched {len(alarms)} alarms from OpManager")
        return alarms

