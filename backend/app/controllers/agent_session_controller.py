"""
AgentSessionController — autonomous agent session lifecycle
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentSessionController(BaseController):
    """Agent-driven sessions: create, plan approval, review, crystallise"""

    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)

    async def create_agent_session(
        self,
        issue_description: str,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        import asyncio
        from app.core.database import SessionLocal
        from app.models.execution_session import ExecutionSession
        from app.services.execution.connection_service import ConnectionService
        from app.services.execution.agent_executor import get_agent_executor

        session = ExecutionSession(
            tenant_id=self.tenant_id,
            runbook_id=None,
            ticket_id=ticket_id,
            user_id=user_id,
            status="pending",
            meta_data={
                "agent_session": True,
                "issue_description": issue_description,
                "connection_id": connection_id,
            },
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # If the ticket was previously closed as false_positive, clear that
        # classification so triage does not block this explicit retry.
        if ticket_id:
            from app.models.ticket import Ticket
            ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket and ticket.classification == "false_positive":
                ticket.classification = None
                ticket.status = "open"
                self.db.commit()

        try:
            conn_service = ConnectionService()
            connection_config = await conn_service.get_connection_config(self.db, session, None)
        except Exception as conn_err:
            self.db.delete(session)
            self.db.commit()
            raise self.bad_request(f"Connection error: {conn_err}")

        agent = get_agent_executor()
        _session_id = session.id
        _conn_config = connection_config
        _issue = issue_description

        async def _run_agent_task() -> None:
            _db = SessionLocal()
            try:
                await agent.run(
                    db=_db,
                    session_id=_session_id,
                    connection_config=_conn_config,
                    issue_description=_issue,
                )
            except Exception as exc:
                logger.exception("Agent background task failed for session %d: %s", _session_id, exc)
            finally:
                _db.close()

        asyncio.create_task(_run_agent_task())

        return {
            "session_id": session.id,
            "status": "started",
            "message": (
                "Agent session started. Connect to WebSocket to stream progress: "
                f"/api/v1/executions/demo/sessions/{session.id}/ws"
            ),
            "websocket_url": f"/api/v1/executions/demo/sessions/{session.id}/ws",
        }

    def get_agent_session_plan(self, session_id: int) -> Dict[str, Any]:
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        meta = session.meta_data or {}
        return {
            "session_id":       session_id,
            "status":           session.status,
            "phase":            meta.get("phase", "unknown"),
            "diagnosis":        meta.get("diagnosis"),
            "targets":          meta.get("targets") or [],
            "approved_targets": meta.get("approved_targets") or [],
            "excluded_targets": meta.get("excluded_targets") or [],
        }

    def set_exclusions(self, session_id: int, exclusions: List[str]) -> Dict[str, Any]:
        from sqlalchemy.orm.attributes import flag_modified
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        if session.status != "awaiting_exclusions":
            raise self.bad_request(f"Session is not awaiting exclusions (current status: {session.status})")
        targets = session.meta_data.get("targets") or []
        approved = [t for t in targets if t.get("path") not in exclusions]
        session.meta_data["approved_targets"] = approved
        session.meta_data["excluded_targets"] = exclusions
        session.status = "executing"
        flag_modified(session, "meta_data")
        self.db.commit()
        return {
            "session_id":     session_id,
            "approved_count": len(approved),
            "excluded_count": len(exclusions),
            "status":         "executing",
            "message":        f"Execution starting — {len(approved)} targets approved, {len(exclusions)} excluded.",
        }

    def escalate_session(self, session_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        from sqlalchemy.orm.attributes import flag_modified
        from datetime import datetime, timezone
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        session.status = "escalated"
        session.meta_data["escalation_reason"] = reason
        session.meta_data["escalated_at"] = datetime.now(timezone.utc).isoformat()
        flag_modified(session, "meta_data")
        self.db.commit()
        if session.ticket_id:
            try:
                from app.services.ticket_status_service import get_ticket_status_service
                get_ticket_status_service().update_ticket_on_execution_complete(
                    db=self.db, ticket_id=session.ticket_id,
                    execution_status="failed", issue_resolved=False,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Could not escalate ticket %d: %s", session.ticket_id, e)
        return {"session_id": session_id, "status": "escalated", "message": "Session escalated to next level."}

    async def review_agent_session(
        self,
        session_id: int,
        weed_step_numbers: List[int],
        save_as_runbook: bool,
        runbook_title: Optional[str],
    ) -> Dict[str, Any]:
        from app.services.execution.runbook_crystalliser import get_runbook_crystalliser
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        meta = session.meta_data or {}
        if not meta.get("agent_session"):
            raise self.bad_request(
                "This endpoint is only for agent sessions (sessions without a pre-existing runbook)."
            )
        if not meta.get("pending_review"):
            raise self.bad_request(
                "Session is not pending review. It may already have been crystallised."
            )

        result: Dict[str, Any] = {
            "session_id": session_id,
            "weed_steps_marked": weed_step_numbers,
            "runbook_created": False,
        }

        if save_as_runbook:
            if not runbook_title:
                issue = meta.get("issue_description") or "Unknown issue"
                runbook_title = f"Auto: {issue[:60]}"

            crystalliser = get_runbook_crystalliser()
            try:
                cryst = await crystalliser.crystallise(
                    db=self.db,
                    session=session,
                    weed_step_numbers=weed_step_numbers,
                    runbook_title=runbook_title,
                    tenant_id=session.tenant_id,
                )
                result["runbook_created"] = True
                result.update(cryst)
            except ValueError as ve:
                raise self.bad_request(str(ve))

        return result

    def confirm_resolution(self, session_id: int, human_resolved: bool) -> Dict[str, Any]:
        """
        Human confirms whether the issue is actually fixed.
        - human_resolved=True  → ticket closed as resolved, runbook crystallised
        - human_resolved=False → ticket escalated, session flagged for retry
        """
        from sqlalchemy.orm.attributes import flag_modified
        from datetime import datetime, timezone

        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        if session.status not in ("awaiting_human_confirmation", "completed", "completed_with_errors"):
            raise self.bad_request(
                f"Session is not awaiting confirmation (current status: {session.status})"
            )

        session.meta_data["human_confirmed_resolved"] = human_resolved
        session.meta_data["pending_review"]           = False

        if human_resolved:
            session.status       = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.meta_data["phase"] = "done"
        else:
            session.status       = "completed_with_errors"
            session.completed_at = datetime.now(timezone.utc)
            session.meta_data["phase"] = "done"

        flag_modified(session, "meta_data")
        self.db.commit()

        # Update ticket
        if session.ticket_id:
            try:
                from app.services.ticket_status_service import get_ticket_status_service
                get_ticket_status_service().update_ticket_on_execution_complete(
                    db=self.db,
                    ticket_id=session.ticket_id,
                    execution_status="completed",
                    issue_resolved=human_resolved,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Could not update ticket %d on confirmation: %s", session.ticket_id, e
                )

        return {
            "session_id": session_id,
            "human_resolved": human_resolved,
            "ticket_status": "resolved" if human_resolved else "escalated",
            "message": (
                "Ticket closed as resolved. Runbook will be crystallised from this session."
                if human_resolved else
                "Ticket escalated. Consider retrying with different guidance."
            ),
        }

    def record_feedback(self, session_id: int, feedback: str) -> Dict[str, Any]:
        """Persist human feedback on a completed session without starting a retry."""
        from sqlalchemy.orm.attributes import flag_modified
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        meta = session.meta_data or {}
        feedbacks = list(meta.get("user_feedback") or [])
        from datetime import datetime, timezone
        feedbacks.append({
            "text": feedback.strip(),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        session.meta_data["user_feedback"] = feedbacks
        flag_modified(session, "meta_data")
        self.db.commit()
        return {"session_id": session_id, "feedback_recorded": True, "total_feedback": len(feedbacks)}

    async def retry_agent_session(
        self,
        session_id: int,
        user_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new agent session with the same issue, injecting directional feedback if provided."""
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        meta = session.meta_data or {}
        issue_description = meta.get("issue_description", "")
        if not issue_description:
            raise self.bad_request("Original session has no issue description to retry.")

        # Inject direction so the agent doesn't repeat the same approach
        if user_direction and user_direction.strip():
            enriched_description = (
                f"{issue_description}\n\n"
                f"[PREVIOUS ATTEMPT CONTEXT]\n"
                f"Session {session_id} already ran and did not resolve the issue.\n"
                f"User guidance for this retry: {user_direction.strip()}"
            )
        else:
            enriched_description = issue_description

        return await self.create_agent_session(
            issue_description=enriched_description,
            ticket_id=session.ticket_id,
            user_id=session.user_id,
            connection_id=meta.get("connection_id"),
        )

    def get_agent_session_steps_for_review(self, session_id: int) -> Dict[str, Any]:
        from app.services.execution.command_classifier import get_command_classifier
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)

        steps = self.execution_repo.get_steps_for_session(session_id)
        clf = get_command_classifier()
        step_review = []
        for step in steps:
            classification = clf.classify(step.command or "")
            payload = step.command_payload or {}
            step_review.append({
                "step_number": step.step_number,
                "command": step.command,
                "reasoning": payload.get("reasoning", ""),
                "output": (step.output or "")[:500],
                "error": step.error or "",
                "success": step.success,
                "completed": step.completed,
                "safety_level": classification.level,
                "safety_label": classification.label,
                "suggested_weed": (
                    not step.success
                    or payload.get("weed") is True
                    or classification.level == 4
                ),
            })

        meta = session.meta_data or {}
        return {
            "session_id": session_id,
            "steps": step_review,
            "total": len(step_review),
            "agent_summary": meta.get("agent_summary", ""),
            "resolved": meta.get("agent_resolved", False),
        }
