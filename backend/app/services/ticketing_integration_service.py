"""
Ticketing Integration Service — public API facade for updating tickets in external tools
"""
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
import json
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.services.ticket_status_updater import TicketStatusUpdater
from app.services.ticket_comment_service import TicketCommentService

logger = get_logger(__name__)


class TicketingIntegrationService:
    """Facade for updating and commenting on tickets in external ticketing tools"""

    def __init__(self):
        self._status_updater = TicketStatusUpdater()
        self._comment_service = TicketCommentService()

    async def close_ticket(self, db: Session, ticket: Ticket, reason: str) -> bool:
        return await self._status_updater.update_ticket_status(
            db=db, ticket=ticket, status="closed", comment=reason
        )

    async def resolve_ticket(self, db: Session, ticket: Ticket, resolution_notes: str) -> bool:
        return await self._status_updater.update_ticket_status(
            db=db, ticket=ticket, status="resolved", comment=resolution_notes
        )

    async def escalate_ticket(
        self,
        db: Session,
        ticket: Ticket,
        escalation_reason: str,
        escalation_level: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        from app.services.escalation_service import EscalationService
        escalation_service = EscalationService()
        escalation_context = escalation_service.determine_escalation_level(
            db=db, ticket=ticket, escalation_reason=escalation_reason, execution_context=execution_context
        )
        if escalation_level:
            escalation_context["escalation_level"] = escalation_level

        execution_logs = execution_context.get("execution_logs") if execution_context else None
        escalation_comment = escalation_service.build_escalation_comment(
            escalation_reason=escalation_reason,
            escalation_context=escalation_context,
            execution_logs=execution_logs,
        )

        if ticket.meta_data is None:
            ticket.meta_data = {}
        if isinstance(ticket.meta_data, str):
            ticket.meta_data = json.loads(ticket.meta_data)
        ticket.meta_data["escalation_context"] = escalation_context
        ticket.escalation_reason = escalation_reason

        return await self._status_updater.update_ticket_status(
            db=db, ticket=ticket, status="escalated",
            comment=escalation_comment, escalation_context=escalation_context,
        )

    async def mark_for_manual_review(self, db: Session, ticket: Ticket, reason: str) -> bool:
        return await self._status_updater.update_ticket_status(
            db=db, ticket=ticket, status="in_progress",
            comment=f"Requires manual review: {reason}",
        )

    async def add_ticket_comment(self, db: Session, ticket: Ticket, comment: str) -> bool:
        return await self._comment_service.add_ticket_comment(db=db, ticket=ticket, comment=comment)


# Global instance
_ticketing_integration_service: Optional[TicketingIntegrationService] = None


def get_ticketing_integration_service() -> TicketingIntegrationService:
    global _ticketing_integration_service
    if _ticketing_integration_service is None:
        _ticketing_integration_service = TicketingIntegrationService()
    return _ticketing_integration_service
