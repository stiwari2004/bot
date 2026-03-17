"""
TicketQueryController — ticket read, execute, and cleanup operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.ticket_repository import TicketRepository
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.execution_repository import ExecutionRepository
from app.services.ticket_status_service import get_ticket_status_service
from app.services.ticket.runbook_matching_service import RunbookMatchingService
from app.services.execution import ExecutionEngine
from app.services.config_service import ConfigService
from app.services.decision import RecommendationEngine
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketQueryController(BaseController):
    """Ticket queries: list, get, execute runbook, cleanup"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.ticket_repo = TicketRepository(db)
        self.runbook_repo = RunbookRepository(db)
        self.execution_repo = ExecutionRepository(db)
        self.matching_service = RunbookMatchingService()
        self.ticket_status_service = get_ticket_status_service()
        self.execution_engine = ExecutionEngine()
        self.recommendation_engine = RecommendationEngine()

    def list_tickets(self, status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        try:
            tickets = self.ticket_repo.get_by_tenant(self.tenant_id, status=status, limit=limit)
            return {
                "tickets": [
                    {
                        "id": t.id,
                        "source": t.source,
                        "title": t.title,
                        "description": t.description,
                        "severity": t.severity,
                        "status": t.status,
                        "classification": t.classification,
                        "classification_confidence": t.classification_confidence,
                        "environment": t.environment,
                        "service": t.service,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "analyzed_at": t.analyzed_at.isoformat() if t.analyzed_at else None,
                        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                    }
                    for t in tickets
                ]
            }
        except Exception as e:
            logger.error(f"Error listing tickets: {e}", exc_info=True)
            return {"tickets": []}

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            if not ticket:
                raise self.not_found("Ticket", ticket_id)

            matched_runbooks = self.matching_service.get_matched_runbooks_from_meta(
                self.db, ticket.meta_data or {}, self.tenant_id
            )

            if not ticket.classification or ticket.classification != "false_positive":
                semantic_matches = await self.matching_service.find_matching_runbooks(
                    self.db,
                    ticket.description or "",
                    ticket.title,
                    self.tenant_id,
                    ticket.classification,
                )
                existing_ids = {rb["id"] for rb in matched_runbooks}
                for rb in semantic_matches:
                    if rb["id"] not in existing_ids:
                        matched_runbooks.append(rb)

            execution_sessions = self.execution_repo.get_by_ticket_id(ticket_id)

            recommendation = None
            if ticket.meta_data and isinstance(ticket.meta_data, dict):
                recommendation = ticket.meta_data.get("recommendation")

            if not recommendation:
                try:
                    rec = self.recommendation_engine.recommend_runbook(ticket, self.db)
                    recommendation = rec.to_dict()
                    self.ticket_repo.update_ticket_metadata(
                        ticket_id=ticket_id,
                        tenant_id=self.tenant_id,
                        meta_data={"recommendation": recommendation},
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate recommendation for ticket {ticket_id}: {e}")

            return {
                "id": ticket.id,
                "source": ticket.source,
                "title": ticket.title,
                "description": ticket.description,
                "severity": ticket.severity,
                "status": ticket.status,
                "classification": ticket.classification,
                "classification_confidence": ticket.classification_confidence,
                "environment": ticket.environment,
                "service": ticket.service,
                "meta_data": ticket.meta_data,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "analyzed_at": ticket.analyzed_at.isoformat() if ticket.analyzed_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "matched_runbooks": matched_runbooks,
                "recommendation": recommendation,
                "execution_sessions": [
                    {
                        "id": es.id,
                        "status": es.status,
                        "created_at": es.created_at.isoformat() if es.created_at else None,
                    }
                    for es in execution_sessions
                ],
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to get ticket")

    async def execute_ticket_runbook(self, ticket_id: int, runbook_id: int) -> Dict[str, Any]:
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            if not ticket:
                raise self.not_found("Ticket", ticket_id)

            runbook = self.runbook_repo.get_approved_by_id_and_tenant(
                runbook_id=runbook_id, tenant_id=self.tenant_id
            )
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            session = await self.execution_engine.create_execution_session(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                ticket_id=ticket.id,
                issue_description=ticket.description or ticket.title,
                user_id=None,
            )
            self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket.id)

            execution_mode = ConfigService.get_execution_mode(self.db, self.tenant_id)
            if execution_mode == "auto" and session.status == "pending":
                try:
                    session = await self.execution_engine.start_execution(self.db, session.id)
                except Exception as e:
                    logger.error(
                        f"Error auto-starting execution for ticket {ticket_id}, session {session.id}: {e}",
                        exc_info=True,
                    )

            return {
                "session_id": session.id,
                "status": session.status,
                "message": "Execution session created"
                + (" and started" if execution_mode == "auto" else " - waiting for approval"),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing runbook for ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to execute runbook")

    def cleanup_demo_tickets(self, sources: List[str]) -> Dict[str, Any]:
        try:
            deleted = self.ticket_repo.delete_by_source(self.tenant_id, sources)
            logger.info(f"Deleted {deleted} demo tickets")
            return {"message": f"Deleted {deleted} demo tickets", "deleted_count": deleted}
        except Exception as e:
            logger.error(f"Error cleaning up demo tickets: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to clean up demo tickets")
