"""
Controller for decision endpoints — recommendation, pattern matching, and ticket annotations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.base_controller import BaseController
from app.repositories.ticket_repository import TicketRepository
from app.repositories.execution_pattern_repository import ExecutionPatternRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class DecisionController(BaseController):
    """Handles decision logic: recommendations, patterns, ticket annotations."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.ticket_repo = TicketRepository(db)
        self.pattern_repo = ExecutionPatternRepository(db)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_ticket(self, ticket_id: int):
        ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
        if not ticket:
            raise self.not_found("Ticket", ticket_id)
        return ticket

    # ── Runbook feedback ──────────────────────────────────────────────────────

    def submit_runbook_feedback(
        self,
        ticket_id: int,
        runbook_id: int,
        matches: bool,
        user_email: str,
    ) -> Dict[str, Any]:
        ticket = self._get_ticket(ticket_id)
        meta = ticket.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}
        feedback = meta.get("runbook_feedback") or {}
        if not isinstance(feedback, dict):
            feedback = {}
        feedback[str(runbook_id)] = {
            "matches": matches,
            "at": datetime.now(timezone.utc).isoformat(),
            "by": user_email,
        }
        meta["runbook_feedback"] = feedback
        ticket.meta_data = meta
        self.db.commit()
        return {
            "ticket_id": ticket.id,
            "runbook_id": runbook_id,
            "matches": matches,
            "message": (
                "Runbook marked as matching this ticket."
                if matches
                else "Runbook marked as not matching this ticket."
            ),
        }

    # ── Recommendation ────────────────────────────────────────────────────────

    def get_recommendation(self, ticket_id: int) -> Dict[str, Any]:
        from app.services.decision import RecommendationEngine
        ticket = self._get_ticket(ticket_id)
        engine = RecommendationEngine()
        rec = engine.recommend_runbook(ticket, self.db)
        return rec.to_dict()

    # ── Problem candidate ─────────────────────────────────────────────────────

    def mark_problem_candidate(
        self,
        ticket_id: int,
        note: Optional[str],
        user_email: str,
    ) -> Dict[str, Any]:
        ticket = self._get_ticket(ticket_id)
        meta = ticket.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}
        recurring = meta.get("recurring") or {}
        problem_candidate = meta.get("problem_candidate") or {}
        now = datetime.now(timezone.utc)
        problem_candidate.update({
            "created_at": now.isoformat(),
            "created_by": user_email,
            "note": note,
            "recurring": recurring,
        })
        meta["problem_candidate"] = problem_candidate
        ticket.meta_data = meta
        self.db.commit()
        return {"ticket_id": ticket.id, "problem_candidate": problem_candidate}

    # ── Pattern matching ──────────────────────────────────────────────────────

    def get_matching_patterns(
        self,
        ticket_id: int,
        pattern_type: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        from app.services.decision import PatternMatchingService
        ticket = self._get_ticket(ticket_id)
        context = {
            "tenant_id": ticket.tenant_id,
            "environment": ticket.environment,
            "service": ticket.service,
            "severity": ticket.severity,
        }
        issue_description = ticket.description or ticket.title
        svc = PatternMatchingService()
        matching = svc.find_matching_patterns(
            issue_description, context, self.db,
            pattern_type=pattern_type, limit=limit
        )
        return [
            {
                "pattern_id": p.id,
                "pattern_type": p.pattern_type,
                "runbook_id": p.runbook_id,
                "issue_signature": p.issue_signature,
                "match_score": score,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count,
            }
            for p, score in matching
        ]

    # ── Ticket context ────────────────────────────────────────────────────────

    def get_ticket_context(
        self,
        ticket_id: int,
        time_window_hours: int,
    ) -> Dict[str, Any]:
        from app.services.decision import ContextCorrelationService
        self._get_ticket(ticket_id)  # existence + tenant check
        svc = ContextCorrelationService()
        data = svc.correlate_ticket_context(ticket_id, self.db, time_window_hours)
        return {
            "ticket_id": ticket_id,
            "alert_count": len(data["alerts"]),
            "execution_count": len(data["executions"]),
            "signals": data["signals"],
            "correlated_at": data["correlated_at"].isoformat(),
        }

    # ── Pattern list ──────────────────────────────────────────────────────────

    def list_patterns(
        self,
        pattern_type: Optional[str],
        runbook_id: Optional[int],
        min_success_rate: Optional[float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        patterns = self.pattern_repo.list_with_filters(
            tenant_id=self.tenant_id,
            pattern_type=pattern_type,
            runbook_id=runbook_id,
            min_success_rate=min_success_rate,
            limit=limit,
        )
        return [
            {
                "pattern_id": p.id,
                "pattern_type": p.pattern_type,
                "runbook_id": p.runbook_id,
                "issue_signature": p.issue_signature,
                "match_score": 0.0,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count,
            }
            for p in patterns
        ]

    # ── Pattern create ────────────────────────────────────────────────────────

    async def create_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.decision import PatternStorageService
        svc = PatternStorageService()
        pattern = await svc.store_pattern(
            tenant_id=self.tenant_id,
            pattern_type=pattern_data.get("pattern_type", "execution"),
            runbook_id=pattern_data.get("runbook_id"),
            ticket_id=pattern_data.get("ticket_id"),
            session_id=pattern_data.get("session_id"),
            issue_signature=pattern_data.get("issue_signature"),
            context=pattern_data.get("context", {}),
            pattern_data=pattern_data.get("pattern_data", {}),
            db=self.db,
        )
        return {"pattern_id": pattern.id, "message": "Pattern created successfully"}

    # ── Explanation ───────────────────────────────────────────────────────────

    async def get_explanation(
        self,
        ticket_id: int,
        recommendation_id: Optional[int],
    ) -> Dict[str, Any]:
        from app.services.decision import RecommendationEngine
        self._get_ticket(ticket_id)
        engine = RecommendationEngine()
        return await engine.generate_explanation(
            ticket_id=ticket_id,
            recommendation_id=recommendation_id,
            db=self.db,
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_decision_controller: Optional[DecisionController] = None


def get_decision_controller(db: Session, tenant_id: int) -> DecisionController:
    return DecisionController(db, tenant_id)
