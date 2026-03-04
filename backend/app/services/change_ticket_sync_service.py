"""
Change Ticket Sync Service
Polls ticketing tools (ServiceNow, ManageEngine) for change tickets and syncs them to database
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.models.change_ticket import ChangeTicket
from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChangeTicketSyncService:
    """Service for syncing change tickets from ticketing tools"""
    
    def __init__(self):
        self.servicenow_fetcher = ServiceNowTicketFetcher()
        self.manageengine_fetcher = ManageEngineTicketFetcher()
    
    async def sync_change_tickets(self, connection: TicketingToolConnection, db: Session) -> Dict[str, int]:
        """
        Sync change tickets for a specific connection
        
        Args:
            connection: TicketingToolConnection to sync from
            db: Database session
            
        Returns:
            Dictionary with created_count, updated_count, error_count
        """
        logger.info(f"Syncing change tickets from {connection.tool_name} connection {connection.id}")
        
        try:
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
            
            # Fetch change tickets based on tool
            change_tickets = []
            
            if connection.tool_name == "servicenow":
                change_tickets = await self._fetch_servicenow_changes(
                    connection, meta_data
                )
            elif connection.tool_name == "manageengine":
                change_tickets = await self._fetch_manageengine_changes(
                    connection, meta_data
                )
            else:
                logger.warning(f"Change ticket sync not supported for {connection.tool_name}")
                return {"created_count": 0, "updated_count": 0, "error_count": 0}
            
            # Sync to database
            created_count = 0
            updated_count = 0
            error_count = 0
            
            for change_data in change_tickets:
                try:
                    external_id = change_data.get("external_id")
                    if not external_id:
                        logger.warning(f"Skipping change ticket without external_id: {change_data}")
                        error_count += 1
                        continue
                    
                    # Check if change ticket already exists
                    existing = db.query(ChangeTicket).filter(
                        ChangeTicket.tenant_id == connection.tenant_id,
                        ChangeTicket.source == connection.tool_name,
                        ChangeTicket.external_id == external_id
                    ).first()
                    
                    if existing:
                        # Update existing change ticket
                        existing.title = change_data.get("title", existing.title)
                        existing.description = change_data.get("description", existing.description)
                        existing.change_type = change_data.get("change_type", existing.change_type)
                        existing.status = change_data.get("status", existing.status)
                        existing.start_time = change_data.get("start_time", existing.start_time)
                        existing.end_time = change_data.get("end_time", existing.end_time)
                        existing.affected_services = change_data.get("affected_services", existing.affected_services)
                        existing.affected_environments = change_data.get("affected_environments", existing.affected_environments)
                        existing.suppression_enabled = change_data.get("suppression_enabled", True)
                        existing.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                        logger.debug(f"Updated change ticket: {external_id}")
                    else:
                        # Create new change ticket
                        new_change = ChangeTicket(
                            tenant_id=connection.tenant_id,
                            external_id=external_id,
                            source=connection.tool_name,
                            title=change_data.get("title", "Change Ticket"),
                            description=change_data.get("description"),
                            change_type=change_data.get("change_type"),
                            status=change_data.get("status", "scheduled"),
                            start_time=change_data.get("start_time"),
                            end_time=change_data.get("end_time"),
                            affected_services=change_data.get("affected_services", []),
                            affected_environments=change_data.get("affected_environments", []),
                            suppression_enabled=change_data.get("suppression_enabled", True)
                        )
                        db.add(new_change)
                        created_count += 1
                        logger.info(f"Created change ticket: {external_id} - {new_change.title[:50]}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing change ticket {change_data.get('external_id')}: {e}", exc_info=True)
                    continue
            
            db.commit()
            
            logger.info(
                f"Change ticket sync complete for {connection.tool_name} connection {connection.id}: "
                f"{created_count} created, {updated_count} updated, {error_count} errors"
            )
            
            return {
                "created_count": created_count,
                "updated_count": updated_count,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing change tickets for {connection.tool_name} connection {connection.id}: {e}", exc_info=True)
            db.rollback()
            return {"created_count": 0, "updated_count": 0, "error_count": 1}
    
    async def _fetch_servicenow_changes(
        self,
        connection: TicketingToolConnection,
        meta_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch change tickets from ServiceNow"""
        import httpx
        import base64
        
        try:
            # ServiceNow Change Request table: change_request
            # States: 1=New, 2=Assess, 3=Authorize, 4=Scheduled, 5=Implement, 6=Review, 7=Closed, 8=Canceled
            # We want states 4 (Scheduled), 5 (Implement), 6 (Review) - active changes
            status_filter = ["4", "5", "6"]  # Scheduled, Implement, Review
            
            # Build query: state IN (4,5,6) AND start_date >= today - 7 days
            # Fetch changes from last 7 days and future changes
            since = datetime.now(timezone.utc) - timedelta(days=7)
            
            username = meta_data.get("username") or connection.api_username
            password = meta_data.get("password") or connection.api_password
            
            # Normalize API base URL
            api_url = connection.api_base_url or meta_data.get("api_base_url", "")
            if not api_url.startswith("http"):
                api_url = f"https://{api_url}"
            api_url = api_url.rstrip("/")
            
            # Build auth headers (Basic Auth)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if username and password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                headers["Authorization"] = f"Basic {encoded}"
            
            # Query change_request table
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
            
            # Transform ServiceNow change tickets to our format
            result = []
            for change in changes:
                # Parse start_date and end_date
                start_time = self._parse_servicenow_date(change.get("start_date"))
                end_time = self._parse_servicenow_date(change.get("end_date"))
                
                if not start_time or not end_time:
                    logger.warning(f"Skipping change {change.get('number')} - missing start_date or end_date")
                    continue
                
                # Map state to status
                state_map = {
                    "4": "scheduled",
                    "5": "in_progress",
                    "6": "review"
                }
                status = state_map.get(change.get("state"), "scheduled")
                
                # Extract affected services/environments from cmdb_ci (configuration items)
                # This is a simplified extraction - in production, you'd query the CI table
                affected_services = []
                affected_environments = []
                
                # Try to extract from description or other fields
                description = change.get("description", "") or change.get("short_description", "")
                if description:
                    # Simple extraction - look for common patterns
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
                    "affected_environments": affected_environments if affected_environments else ["prod", "staging", "dev"],  # Default to all if not specified
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
        """
        Fetch change tickets from ManageEngine ServiceDesk Plus (v3 API).
        
        MVP implementation:
        - Uses the v3 `/api/v3/changes` list endpoint
        - Filters to changes whose scheduled start is within the last 7 days (or in the future)
        - Maps a small, robust subset of fields into our internal change ticket format
        """
        import httpx
        
        try:
            # Time window: last 7 days and upcoming changes
            since = datetime.now(timezone.utc) - timedelta(days=7)
            since_ms = str(int(since.timestamp() * 1000))

            # Normalize API base URL
            api_base_url = connection.api_base_url or meta_data.get("api_base_url", "")
            if not api_base_url:
                logger.warning("ManageEngine change sync: api_base_url is not set; skipping.")
                return []
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")

            api_url = f"{api_base_url}/api/v3/changes"

            # Authentication: use v3 API key/authtoken (same as ticket fetcher)
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

            # Build list_info for Get List Changes.
            # We keep this intentionally simple and conservative for MVP.
            list_info: Dict[str, Any] = {
                "row_count": 100,
                "start_index": 1,
                # Use scheduled_start_time when available; fall back to created_time
                "sort_field": "scheduled_start_time",
                "sort_order": "asc",
                "search_criteria": [
                    {
                        "field": "scheduled_start_time.value",
                        "condition": "greater than",
                        "value": since_ms,
                    }
                ],
            }

            input_data = {"list_info": list_info}
            params = {"input_data": json.dumps(input_data)}

            # Respect SSL flags from meta_data, same pattern as request fetcher
            ssl_verify = meta_data.get("ssl_verify", True)
            if meta_data.get("skip_ssl_verify") is True:
                ssl_verify = False

            logger.info(
                f"Fetching ManageEngine changes from {api_url} "
                f"with list_info={list_info}"
            )

            if ssl_verify:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(api_url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    response = await client.get(api_url, headers=headers, params=params)

            if response.status_code != 200:
                snippet = response.text[:500] if hasattr(response, "text") else ""
                logger.error(
                    f"ManageEngine change API error {response.status_code}: {snippet}"
                )
                return []

            data = response.json()

            # Response shape: typically { "changes": [ ... ] }, but be tolerant.
            changes_raw: List[Dict[str, Any]]
            if isinstance(data, dict) and "changes" in data and isinstance(
                data["changes"], list
            ):
                changes_raw = data["changes"]
            elif isinstance(data, list):
                changes_raw = data
            else:
                logger.warning(
                    f"Unexpected ManageEngine change list response shape: {type(data)}"
                )
                return []

            result: List[Dict[str, Any]] = []

            for ch in changes_raw:
                try:
                    external_id = str(ch.get("id") or ch.get("change_id") or "")
                    if not external_id:
                        logger.debug(f"Skipping change without id: {ch}")
                        continue

                    title = (
                        ch.get("subject")
                        or ch.get("title")
                        or "Change Request"
                    )
                    description = ch.get("description") or ""

                    # Status mapping – keep it simple and robust
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

                    # Parse scheduled start / end times
                    def _parse_me_datetime(field_name: str) -> Optional[datetime]:
                        val = ch.get(field_name)
                        # Many v3 datetime fields are objects with {"value": <ms>, "display_value": "..."}
                        if isinstance(val, dict) and "value" in val:
                            try:
                                ms = int(val["value"])
                                return datetime.fromtimestamp(
                                    ms / 1000.0, tz=timezone.utc
                                )
                            except Exception:
                                return None
                        # Fallback: ISO/string timestamp
                        if isinstance(val, str) and val:
                            try:
                                # Try a few common formats; if all fail, ignore
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
                        # Without a sane window, suppression behaviour is ambiguous – skip for MVP
                        logger.debug(
                            f"Skipping change {external_id} - missing start/end time"
                        )
                        continue

                    # For now we don't have structured affected services/environments from SDP change.
                    # Default environments follow ServiceNow behaviour.
                    affected_services: List[str] = []
                    affected_environments: List[str] = ["prod", "staging", "dev"]

                    result.append(
                        {
                            "external_id": external_id,
                            "title": title,
                            "description": description,
                            "change_type": None,  # SDP change type mapping can be added later
                            "status": status,
                            "start_time": start_time,
                            "end_time": end_time,
                            "affected_services": affected_services,
                            "affected_environments": affected_environments,
                            "suppression_enabled": True,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Error normalizing ManageEngine change record: {e}", exc_info=True
                    )
                    continue

            logger.info(
                f"Fetched {len(result)} change tickets from ManageEngine for connection {connection.id}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error fetching ManageEngine change tickets: {e}", exc_info=True
            )
            return []
    
    def _parse_servicenow_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ServiceNow date string to datetime"""
        if not date_str:
            return None
        
        try:
            # ServiceNow dates are typically in format: "2025-01-07 10:00:00" or ISO format
            # Try multiple formats
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
                    # Make timezone-aware if not already
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
            
            # If all formats fail, try parsing as ISO format with dateutil
            try:
                from dateutil import parser
                dt = parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
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


# Global instance
_change_ticket_sync_service: Optional[ChangeTicketSyncService] = None


def get_change_ticket_sync_service() -> ChangeTicketSyncService:
    """Get or create change ticket sync service instance"""
    global _change_ticket_sync_service
    if _change_ticket_sync_service is None:
        _change_ticket_sync_service = ChangeTicketSyncService()
    return _change_ticket_sync_service

