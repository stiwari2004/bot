"""
Mixin: ticket-fetching helpers for ChangeTicketSyncService
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from app.models.ticketing_tool_connection import TicketingToolConnection
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChangeTicketFetchersMixin:
    """Ticket-fetching helpers for ChangeTicketSyncService."""

    async def _fetch_servicenow_changes(
        self,
        connection: TicketingToolConnection,
        meta_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch change tickets from ServiceNow"""
        import httpx
        import base64

        try:
            status_filter = ["4", "5", "6"]  # Scheduled, Implement, Review
            since = datetime.now(timezone.utc) - timedelta(days=7)

            username = meta_data.get("username") or connection.api_username
            password = meta_data.get("password") or connection.api_password

            api_url = connection.api_base_url or meta_data.get("api_base_url", "")
            if not api_url.startswith("http"):
                api_url = f"https://{api_url}"
            api_url = api_url.rstrip("/")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            if username and password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                headers["Authorization"] = f"Basic {encoded}"

            query_url = f"{api_url}/api/now/table/change_request"
            params = {
                "sysparm_query": f"stateIN{','.join(status_filter)}^start_date>={since.strftime('%Y-%m-%d')}",
                "sysparm_fields": "number,sys_id,short_description,description,type,state,start_date,end_date,cmdb_ci",
                "sysparm_limit": 100,
                "sysparm_display_value": "true"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(query_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                changes = data.get("result", [])

            result = []
            for change in changes:
                start_time = self._parse_servicenow_date(change.get("start_date"))
                end_time = self._parse_servicenow_date(change.get("end_date"))

                if not start_time or not end_time:
                    logger.warning(f"Skipping change {change.get('number')} - missing start_date or end_date")
                    continue

                state_map = {
                    "4": "scheduled",
                    "5": "in_progress",
                    "6": "review"
                }
                status = state_map.get(change.get("state"), "scheduled")

                affected_services = []
                affected_environments = []

                description = change.get("description", "") or change.get("short_description", "")
                if description:
                    desc_lower = description.lower()
                    if "production" in desc_lower or "prod" in desc_lower:
                        affected_environments.append("prod")
                    if "staging" in desc_lower:
                        affected_environments.append("staging")
                    if "dev" in desc_lower or "development" in desc_lower:
                        affected_environments.append("dev")

                result.append({
                    "external_id": change.get("number"),
                    "title": change.get("short_description", "Change Request"),
                    "description": change.get("description"),
                    "change_type": self._map_servicenow_change_type(change.get("type")),
                    "status": status,
                    "start_time": start_time,
                    "end_time": end_time,
                    "affected_services": affected_services,
                    "affected_environments": affected_environments if affected_environments else ["prod", "staging", "dev"],
                    "suppression_enabled": True
                })

            logger.info(f"Fetched {len(result)} change tickets from ServiceNow")
            return result

        except Exception as e:
            logger.error(f"Error fetching ServiceNow change tickets: {e}", exc_info=True)
            return []

    async def _fetch_manageengine_changes(
        self,
        connection: TicketingToolConnection,
        meta_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch change tickets from ManageEngine ServiceDesk Plus (v3 API)."""
        import httpx

        try:
            since = datetime.now(timezone.utc) - timedelta(days=7)

            api_base_url = connection.api_base_url or meta_data.get("api_base_url", "")
            if not api_base_url:
                logger.warning("ManageEngine change sync: api_base_url is not set; skipping.")
                return []
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")

            api_url = f"{api_base_url}/api/v3/changes"

            key = (
                connection.api_key
                or meta_data.get("api_key")
                or meta_data.get("authtoken")
            )
            if not key:
                logger.warning(
                    f"ManageEngine change sync for connection {connection.id} "
                    f"skipped: missing api_key/authtoken"
                )
                return []

            headers = {
                "authtoken": key,
                "Accept": "application/vnd.manageengine.sdp.v3+json",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            list_info: Dict[str, Any] = {
                "row_count": 100,
                "start_index": 1,
                "sort_field": "scheduled_start_time",
                "sort_order": "asc",
            }

            input_data = {"list_info": list_info}
            params = {"input_data": json.dumps(input_data)}

            ssl_verify = meta_data.get("ssl_verify", True)
            if meta_data.get("skip_ssl_verify") is True:
                ssl_verify = False

            logger.info(f"Fetching ManageEngine changes from {api_url} with list_info={list_info}")

            if ssl_verify:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(api_url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    response = await client.get(api_url, headers=headers, params=params)

            if response.status_code != 200:
                snippet = response.text[:500] if hasattr(response, "text") else ""
                logger.error(f"ManageEngine change API error {response.status_code}: {snippet}")
                return []

            data = response.json()

            changes_raw: List[Dict[str, Any]]
            if isinstance(data, dict) and "changes" in data and isinstance(data["changes"], list):
                changes_raw = data["changes"]
            elif isinstance(data, list):
                changes_raw = data
            else:
                logger.warning(f"Unexpected ManageEngine change list response shape: {type(data)}")
                return []

            result: List[Dict[str, Any]] = []

            for ch in changes_raw:
                try:
                    external_id = str(ch.get("id") or ch.get("change_id") or "")
                    if not external_id:
                        logger.debug(f"Skipping change without id: {ch}")
                        continue

                    title = ch.get("subject") or ch.get("title") or "Change Request"
                    description = ch.get("description") or ""

                    raw_status = ch.get("status", {})
                    if isinstance(raw_status, dict):
                        status_name = raw_status.get("name") or ""
                    else:
                        status_name = str(raw_status or "")
                    status_name_lower = status_name.lower()
                    status_map = {
                        "scheduled": "scheduled",
                        "in progress": "in_progress",
                        "in-progress": "in_progress",
                        "implementing": "in_progress",
                        "completed": "completed",
                        "closed": "completed",
                        "canceled": "cancelled",
                        "cancelled": "cancelled",
                    }
                    status = status_map.get(status_name_lower, "scheduled")

                    def _parse_me_datetime(field_name: str) -> Optional[datetime]:
                        val = ch.get(field_name)
                        if isinstance(val, dict) and "value" in val:
                            try:
                                ms = int(val["value"])
                                return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
                            except Exception:
                                return None
                        if isinstance(val, str) and val:
                            try:
                                from dateutil import parser  # type: ignore
                                dt = parser.parse(val)
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                return dt
                            except Exception:
                                return None
                        return None

                    start_time = (
                        _parse_me_datetime("scheduled_start_time")
                        or _parse_me_datetime("planned_start_time")
                    )
                    end_time = (
                        _parse_me_datetime("scheduled_end_time")
                        or _parse_me_datetime("planned_end_time")
                    )

                    if not start_time or not end_time:
                        logger.debug(f"Skipping change {external_id} - missing start/end time")
                        continue
                    if start_time < since:
                        continue

                    result.append({
                        "external_id": external_id,
                        "title": title,
                        "description": description,
                        "change_type": None,
                        "status": status,
                        "start_time": start_time,
                        "end_time": end_time,
                        "affected_services": [],
                        "affected_environments": ["prod", "staging", "dev"],
                        "suppression_enabled": True,
                    })
                except Exception as e:
                    logger.warning(f"Error normalizing ManageEngine change record: {e}", exc_info=True)
                    continue

            logger.info(
                f"Fetched {len(result)} change tickets from ManageEngine for connection {connection.id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error fetching ManageEngine change tickets: {e}", exc_info=True)
            return []

    def _parse_servicenow_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ServiceNow date string to datetime"""
        if not date_str:
            return None
        try:
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
            try:
                from dateutil import parser
                dt = parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
            logger.warning(f"Could not parse date: {date_str}")
            return None
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None

    def _map_servicenow_change_type(self, change_type: Optional[str]) -> str:
        """Map ServiceNow change type to our format"""
        if not change_type:
            return "normal"
        type_map = {
            "standard": "standard",
            "emergency": "emergency",
            "normal": "normal"
        }
        return type_map.get(change_type.lower(), "normal")
