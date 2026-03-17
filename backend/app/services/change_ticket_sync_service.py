"""
Change Ticket Sync Service
Polls ticketing tools (ServiceNow, ManageEngine) for change tickets and syncs them to database
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.ticketing_tool_connection import TicketingToolConnection
from app.models.change_ticket import ChangeTicket
from app.services.change_ticket_sync_fetchers_mixin import ChangeTicketFetchersMixin
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChangeTicketSyncService(ChangeTicketFetchersMixin):
    """Service for syncing change tickets from ticketing tools"""

    async def sync_change_tickets(self, connection: TicketingToolConnection, db: Session) -> Dict[str, int]:
        """Sync change tickets for a specific connection."""
        logger.info(f"Syncing change tickets from {connection.tool_name} connection {connection.id}")

        try:
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}

            change_tickets = []

            if connection.tool_name == "servicenow":
                change_tickets = await self._fetch_servicenow_changes(connection, meta_data)
            elif connection.tool_name == "manageengine":
                change_tickets = await self._fetch_manageengine_changes(connection, meta_data)
            else:
                logger.warning(f"Change ticket sync not supported for {connection.tool_name}")
                return {"created_count": 0, "updated_count": 0, "error_count": 0}

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

                    existing = db.query(ChangeTicket).filter(
                        ChangeTicket.tenant_id == connection.tenant_id,
                        ChangeTicket.source == connection.tool_name,
                        ChangeTicket.external_id == external_id
                    ).first()

                    if existing:
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


# Global instance
_change_ticket_sync_service: Optional[ChangeTicketSyncService] = None


def get_change_ticket_sync_service() -> ChangeTicketSyncService:
    """Get or create change ticket sync service instance"""
    global _change_ticket_sync_service
    if _change_ticket_sync_service is None:
        _change_ticket_sync_service = ChangeTicketSyncService()
    return _change_ticket_sync_service
