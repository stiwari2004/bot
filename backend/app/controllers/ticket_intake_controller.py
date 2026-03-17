"""
TicketIntakeController — webhook ingestion, analysis, and runbook matching
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.controllers.base_controller import BaseController
from app.repositories.ticket_repository import TicketRepository
from app.repositories.runbook_repository import RunbookRepository
from app.models.ticket import Ticket
from app.services.ticket_analysis_service import TicketAnalysisService
from app.services.ticket_status_service import get_ticket_status_service
from app.services.ticket.ticket_normalizer import TicketNormalizer
from app.services.ticket.runbook_matching_service import RunbookMatchingService
from app.services.execution import ExecutionEngine
from app.services.config_service import ConfigService
from app.services.decision import RecommendationEngine
from app.services.change_window_service import get_change_window_service
from app.services.recurring_incident_service import update_recurring_metadata
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketIntakeController(BaseController):
    """Ticket ingestion: webhooks, demo creation, analysis, matching, auto-execute"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.ticket_repo = TicketRepository(db)
        self.runbook_repo = RunbookRepository(db)
        self.normalizer = TicketNormalizer()
        self.matching_service = RunbookMatchingService()
        self.analysis_service = TicketAnalysisService()
        self.ticket_status_service = get_ticket_status_service()
        self.execution_engine = ExecutionEngine()
        self.recommendation_engine = RecommendationEngine()

    async def receive_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ticket_data = self.normalizer.normalize(payload, source)
            ticket = self.ticket_repo.create_ticket(
                tenant_id=self.tenant_id,
                source=source,
                external_id=ticket_data.get("external_id"),
                title=ticket_data.get("title", "Untitled Alert"),
                description=ticket_data.get("description", ""),
                severity=ticket_data.get("severity", "medium"),
                environment=ticket_data.get("environment", "prod"),
                service=ticket_data.get("service"),
                status="open",
                raw_payload=payload,
                meta_data=ticket_data.get("metadata", {}),
                received_at=datetime.utcnow(),
            )

            change_window_service = get_change_window_service()
            if change_window_service.check_and_suppress_ticket(self.db, ticket):
                logger.info(f"Ticket {ticket.id} suppressed due to active change window")
                return {
                    "ticket_id": ticket.id,
                    "status": "suppressed",
                    "message": "Ticket received but suppressed due to active change window",
                }

            try:
                update_recurring_metadata(self.db, ticket)
            except Exception as e:
                logger.warning(f"Failed to update recurring metadata for webhook ticket {ticket.id}: {e}")

            analysis_result = await self._analyze_ticket(ticket)

            try:
                recommendation = self.recommendation_engine.recommend_runbook(ticket, self.db)
                self.ticket_repo.update_ticket_metadata(
                    ticket_id=ticket.id,
                    tenant_id=self.tenant_id,
                    meta_data={"recommendation": recommendation.to_dict()},
                )
            except Exception as e:
                logger.warning(f"Failed to generate recommendation for ticket {ticket.id}: {e}")

            return {
                "ticket_id": ticket.id,
                "status": ticket.status,
                "classification": ticket.classification,
                "confidence": analysis_result["confidence"],
                "message": "Ticket received and analyzed",
            }
        except Exception as e:
            logger.error(f"Error receiving webhook: {e}")
            raise self.handle_error(e, "Failed to process webhook")

    async def create_demo_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ticket = self.ticket_repo.create_ticket(
                tenant_id=self.tenant_id,
                source=ticket_data.get("source", "custom"),
                external_id=ticket_data.get("external_id"),
                title=ticket_data.get("title", "Demo Ticket"),
                description=ticket_data.get("description", ""),
                severity=ticket_data.get("severity", "medium"),
                environment=ticket_data.get("environment", "prod"),
                service=ticket_data.get("service"),
                status="open",
                raw_payload=ticket_data,
                meta_data=ticket_data.get("metadata", {}),
                received_at=datetime.utcnow(),
            )

            change_window_service = get_change_window_service()
            if change_window_service.check_and_suppress_ticket(self.db, ticket):
                logger.info(f"Ticket {ticket.id} suppressed due to active change window")
                return {
                    "ticket_id": ticket.id,
                    "status": "suppressed",
                    "message": "Ticket received but suppressed due to active change window",
                }

            try:
                update_recurring_metadata(self.db, ticket)
            except Exception as e:
                logger.warning(f"Failed to update recurring metadata for demo ticket {ticket.id}: {e}")

            analysis_result = await self._analyze_ticket(ticket)

            try:
                recommendation = self.recommendation_engine.recommend_runbook(ticket, self.db)
                self.ticket_repo.update_ticket_metadata(
                    ticket_id=ticket.id,
                    tenant_id=self.tenant_id,
                    meta_data={"recommendation": recommendation.to_dict()},
                )
            except Exception as e:
                logger.warning(f"Failed to generate recommendation for ticket {ticket.id}: {e}")

            await self._find_and_store_matched_runbooks(ticket, analysis_result)
            await self._auto_execute_if_eligible(ticket)

            return {
                "ticket_id": ticket.id,
                "status": ticket.status,
                "classification": ticket.classification,
                "confidence": analysis_result["confidence"],
                "reasoning": analysis_result.get("reasoning"),
            }
        except Exception as e:
            logger.error(f"Error creating demo ticket: {e}")
            raise self.handle_error(e, "Failed to create ticket")

    async def _analyze_ticket(self, ticket: Ticket) -> Dict[str, Any]:
        analysis_result = await self.analysis_service.analyze_ticket({
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity,
            "source": ticket.source,
        })
        confidence = analysis_result["confidence"]
        classification_confidence = "high" if confidence >= 0.8 else ("medium" if confidence >= 0.5 else "low")
        self.ticket_repo.update_ticket(
            ticket_id=ticket.id,
            tenant_id=self.tenant_id,
            classification=analysis_result["classification"],
            classification_confidence=classification_confidence,
            analyzed_at=datetime.utcnow(),
            status="analyzing",
        )
        ticket = self.ticket_repo.get_by_id_and_tenant(ticket.id, self.tenant_id)
        if analysis_result["classification"] == "false_positive" and confidence >= 0.8:
            self.ticket_status_service.update_ticket_on_false_positive(self.db, ticket.id)
        return analysis_result

    async def _find_and_store_matched_runbooks(self, ticket: Ticket, analysis_result: Dict[str, Any]):
        if analysis_result["classification"] != "false_positive":
            matched_runbooks = await self.matching_service.find_matching_runbooks(
                self.db,
                ticket.description or "",
                ticket.title,
                self.tenant_id,
                analysis_result["classification"],
            )
            meta = getattr(ticket, "meta_data", None) or {}
            if isinstance(meta, dict):
                feedback = meta.get("runbook_feedback") or {}
                if isinstance(feedback, dict):
                    matched_runbooks = [
                        rb for rb in matched_runbooks
                        if feedback.get(str(rb.get("id")), {}).get("matches", True) is not False
                    ]
            if matched_runbooks:
                self.ticket_repo.update_ticket_metadata(
                    ticket_id=ticket.id,
                    tenant_id=self.tenant_id,
                    meta_data={"matched_runbooks": matched_runbooks},
                )
                logger.info(f"Found {len(matched_runbooks)} matching runbooks for ticket {ticket.id}")
            else:
                self.ticket_repo.update_ticket_metadata(
                    ticket_id=ticket.id,
                    tenant_id=self.tenant_id,
                    meta_data={
                        "matched_runbooks": [],
                        "no_match_suggestion": "No matching runbook found. Consider generating a new runbook for this issue.",
                    },
                )
                logger.info(f"No matching runbooks for ticket {ticket.id}; stored no_match_suggestion")

    async def _auto_execute_if_eligible(self, ticket: Ticket):
        if not ticket.meta_data or not isinstance(ticket.meta_data, dict):
            return
        matched_runbooks = self.matching_service.get_matched_runbooks_from_meta(
            self.db, ticket.meta_data, self.tenant_id
        )
        if not matched_runbooks:
            return

        best_match = matched_runbooks[0]
        runbook_id = best_match.get("id")
        match_confidence = best_match.get("confidence_score", 0.0)
        execution_mode = ConfigService.get_execution_mode(self.db, self.tenant_id)

        if execution_mode == "auto" and match_confidence >= 0.8 and runbook_id:
            try:
                runbook = self.runbook_repo.get_approved_by_id_and_tenant(
                    runbook_id=runbook_id, tenant_id=self.tenant_id
                )
                if runbook:
                    session = await self.execution_engine.create_execution_session(
                        db=self.db,
                        runbook_id=runbook_id,
                        tenant_id=self.tenant_id,
                        ticket_id=ticket.id,
                        issue_description=ticket.description or ticket.title,
                        user_id=None,
                    )
                    self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket.id)
                    if session.status == "pending":
                        session = await self.execution_engine.start_execution(self.db, session.id)
                    logger.info(
                        f"Auto-started execution session {session.id} for ticket {ticket.id} "
                        f"with runbook {runbook_id} (confidence: {match_confidence:.2f})"
                    )
            except Exception as e:
                logger.error(f"Failed to auto-start execution for ticket {ticket.id}: {e}")
