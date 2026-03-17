"""
TicketController — thin facade over TicketIntakeController and TicketQueryController.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.controllers.ticket_intake_controller import TicketIntakeController
from app.controllers.ticket_query_controller import TicketQueryController


class TicketController:
    """Facade: delegates to intake and query sub-controllers."""

    def __init__(self, db: Session, tenant_id: int):
        self._intake = TicketIntakeController(db, tenant_id)
        self._query = TicketQueryController(db, tenant_id)

    # ── Intake ────────────────────────────────────────────────────────────────

    async def receive_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._intake.receive_webhook(source, payload)

    async def create_demo_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._intake.create_demo_ticket(ticket_data)

    # ── Query / management ────────────────────────────────────────────────────

    def list_tickets(self, status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        return self._query.list_tickets(status, limit)

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        return await self._query.get_ticket(ticket_id)

    async def execute_ticket_runbook(self, ticket_id: int, runbook_id: int) -> Dict[str, Any]:
        return await self._query.execute_ticket_runbook(ticket_id, runbook_id)

    def cleanup_demo_tickets(self, sources: List[str]) -> Dict[str, Any]:
        return self._query.cleanup_demo_tickets(sources)
