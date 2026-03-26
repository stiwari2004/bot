"""
TriageService — shared gate called before any execution session starts.

Checks whether an incoming ticket/session should be acted on or suppressed
due to an active change window.  Called by both:
  - AgentExecutor._precheck_phase()   (no-runbook sessions)
  - ExecutionEngine at session start  (runbook sessions)

Suppression behaviour:
  - Ticket is marked suppressed via ChangeWindowService (sets ticket.suppressed)
  - Session status is set to "suppressed" with full context in meta_data so
    the ChangeWindowMonitor can retrigger after the window ends
  - A new session is created (referencing original_suppressed_session_id) when
    the change window expires and the alert is still firing

Returns: "proceed" | "suppressed"
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession

logger = get_logger(__name__)


class TriageService:
    """
    Shared pre-execution gate that evaluates whether a session should run
    or be held because an active change window covers the affected service.
    """

    def evaluate(
        self,
        db: Session,
        session: ExecutionSession,
    ) -> str:
        """
        Evaluate whether execution should proceed or be suppressed.

        Updates the session in-place if suppressed (status, meta_data,
        completed_at) and commits the change.

        Returns "proceed" or "suppressed".
        """
        if not session.ticket_id:
            # No linked ticket — agent was started manually, always proceed
            return "proceed"

        from app.models.ticket import Ticket
        ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
        if not ticket:
            return "proceed"

        # ── Already suppressed at ticket level ───────────────────────────────
        if ticket.suppressed:
            self._mark_session_suppressed(
                db, session,
                change_ticket_id=ticket.suppressed_by_change_ticket_id,
                change_ticket_ext=None,
                reason=ticket.suppression_reason or "Ticket already suppressed by change window",
            )
            return "suppressed"

        # ── Already classified as false positive — skip unless manually reopened ─
        if ticket.classification == "false_positive":
            if ticket.status == "open":
                # Human explicitly reopened it — clear the stale classification
                # so the agent re-evaluates with fresh eyes
                ticket.classification = None
                db.commit()
            else:
                self._mark_session_suppressed(
                    db, session,
                    change_ticket_id=None,
                    change_ticket_ext=None,
                    reason="Ticket already classified as false positive",
                )
                return "suppressed"

        # ── Active change window check ─────────────────────────────────────────
        from app.services.change_window_service import get_change_window_service
        cw_service = get_change_window_service()
        should_suppress, change_ticket, reason = cw_service.should_suppress_ticket(db, ticket)

        if should_suppress and change_ticket:
            cw_service.suppress_ticket(db, ticket, change_ticket, reason)
            self._mark_session_suppressed(
                db, session,
                change_ticket_id=change_ticket.id,
                change_ticket_ext=change_ticket.external_id,
                reason=reason,
            )
            logger.info(
                "Session %d suppressed — active change window '%s' (%s). "
                "Monitor will retrigger after window ends if alert still fires.",
                session.id, change_ticket.title, change_ticket.external_id,
            )
            return "suppressed"

        return "proceed"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mark_session_suppressed(
        self,
        db: Session,
        session: ExecutionSession,
        change_ticket_id: Optional[int],
        change_ticket_ext: Optional[str],
        reason: str,
    ) -> None:
        """Persist suppression context onto the session and commit."""
        session.status       = "suppressed"
        session.completed_at = datetime.now(timezone.utc)
        existing = session.meta_data or {}
        session.meta_data = {
            **existing,
            "suppressed_by_change_ticket_id":  change_ticket_id,
            "suppressed_by_change_ticket_ext": change_ticket_ext,
            "suppression_reason":              reason,
        }
        flag_modified(session, "meta_data")
        db.commit()


# ── Singleton ──────────────────────────────────────────────────────────────────

_triage_service: Optional[TriageService] = None


def get_triage_service() -> TriageService:
    global _triage_service
    if _triage_service is None:
        _triage_service = TriageService()
    return _triage_service
