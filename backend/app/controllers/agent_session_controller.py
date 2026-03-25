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
            "session_id": session_id,
            "status": session.status,
            "phase": meta.get("phase", "unknown"),
            "diagnosis": meta.get("diagnosis"),
            "approaches": meta.get("approaches") or [],
            "proposed_plan": meta.get("proposed_plan"),
            "plan_approved": meta.get("plan_approved"),
            "plan_rejection_count": meta.get("plan_rejection_count", 0),
            "plan_rejection_feedback": meta.get("plan_rejection_feedback", []),
        }

    async def select_approach(self, session_id: int, approach_id: str) -> Dict[str, Any]:
        """
        Human selected an approach — call the LLM to generate the detailed plan for it.
        Returns the generated steps so the UI can render them for editing.
        """
        from app.services.execution.agent_executor import get_agent_executor
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        if session.status != "awaiting_plan_approval":
            raise self.bad_request(
                f"Session is not awaiting plan approval (current status: {session.status})"
            )
        executor = get_agent_executor()
        steps = await executor.generate_plan_for_approach(
            db          = self.db,
            session_id  = session_id,
            approach_id = approach_id,
        )
        return {
            "session_id":  session_id,
            "approach_id": approach_id,
            "steps":       steps,
        }

    def approve_agent_plan(
        self,
        session_id: int,
        selected_approach_id: Optional[str] = None,
        proposed_plan: Optional[List] = None,
    ) -> Dict[str, Any]:
        from sqlalchemy.orm.attributes import flag_modified
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        if session.status != "awaiting_plan_approval":
            raise self.bad_request(
                f"Session is not awaiting plan approval (current status: {session.status})"
            )

        # Use human-edited steps if provided, otherwise use the LLM-generated plan
        if proposed_plan is not None:
            session.meta_data["proposed_plan"] = proposed_plan
        elif session.meta_data.get("generated_plan"):
            session.meta_data["proposed_plan"] = session.meta_data["generated_plan"]
        else:
            raise self.bad_request(
                "No plan to approve. Select an approach first to generate the plan."
            )

        if selected_approach_id:
            session.meta_data["selected_approach_id"] = selected_approach_id

        session.meta_data["plan_approved"] = True
        session.meta_data["plan_rejected"] = False
        flag_modified(session, "meta_data")
        self.db.commit()
        return {
            "session_id": session_id,
            "approved": True,
            "selected_approach_id": selected_approach_id,
            "message": "Plan approved — execution will begin shortly.",
        }

    def reject_agent_plan(self, session_id: int, feedback: str) -> Dict[str, Any]:
        from sqlalchemy.orm.attributes import flag_modified
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Session", session_id)
        if session.status != "awaiting_plan_approval":
            raise self.bad_request(
                f"Session is not awaiting plan approval (current status: {session.status})"
            )
        feedbacks = list(session.meta_data.get("plan_rejection_feedback") or [])
        feedbacks.append(feedback)
        session.meta_data["plan_rejection_feedback"] = feedbacks
        session.meta_data["plan_rejection_count"] = len(feedbacks)
        session.meta_data["plan_rejected"] = True
        session.meta_data["plan_approved"] = None
        flag_modified(session, "meta_data")
        self.db.commit()
        return {
            "session_id": session_id,
            "rejected": True,
            "feedback_recorded": feedback,
            "rejection_count": len(feedbacks),
            "message": "Feedback recorded — agent is revising the plan.",
        }

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
