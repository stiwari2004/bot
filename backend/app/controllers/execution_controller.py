"""
ExecutionController — thin facade delegating to focused sub-controllers.

Consumers that import ExecutionController directly continue to work unchanged.
"""
from typing import Dict, Any, List, Optional, Literal
from sqlalchemy.orm import Session

from app.controllers.execution_session_controller import ExecutionSessionController
from app.controllers.execution_step_controller import ExecutionStepController
from app.controllers.agent_session_controller import AgentSessionController
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionController:
    """Facade: composes session, step, and agent sub-controllers."""

    def __init__(self, db: Session, tenant_id: int = 1):
        self._session_ctrl = ExecutionSessionController(db, tenant_id)
        self._step_ctrl = ExecutionStepController(db, tenant_id)
        self._agent_ctrl = AgentSessionController(db, tenant_id)

    # ── Session lifecycle ─────────────────────────────────────────────────────

    async def create_execution_session(self, **kwargs) -> Dict[str, Any]:
        return await self._session_ctrl.create_execution_session(**kwargs)

    def get_execution_session(self, session_id: int) -> Dict[str, Any]:
        return self._session_ctrl.get_execution_session(session_id)

    def list_session_events(self, session_id: int, since_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return self._session_ctrl.list_session_events(session_id, since_id, limit)

    def complete_execution_session(self, session_id: int, was_successful: bool, issue_resolved: bool,
                                   rating: int, feedback_text: Optional[str] = None,
                                   suggestions: Optional[str] = None) -> Dict[str, Any]:
        return self._session_ctrl.complete_execution_session(
            session_id, was_successful, issue_resolved, rating, feedback_text, suggestions
        )

    def abandon_execution_session(self, session_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        return self._session_ctrl.abandon_execution_session(session_id, reason)

    def get_runbook_execution_history(self, runbook_id: int) -> Dict[str, Any]:
        return self._session_ctrl.get_runbook_execution_history(runbook_id)

    def list_all_executions(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self._session_ctrl.list_all_executions(limit, offset)

    def get_pending_approvals(self) -> Dict[str, Any]:
        return self._session_ctrl.get_pending_approvals()

    # ── Step operations ───────────────────────────────────────────────────────

    async def update_execution_step(self, session_id: int, step_number: int, step_type: str,
                                    completed: bool, success: Optional[bool] = None,
                                    output: Optional[str] = None, notes: Optional[str] = None,
                                    approved: Optional[bool] = None) -> Dict[str, Any]:
        return await self._step_ctrl.update_execution_step(
            session_id, step_number, step_type, completed, success, output, notes, approved
        )

    async def approve_step(self, session_id: int, step_number: int, user_id: Optional[int],
                           approve: bool, notes: Optional[str] = None) -> Dict[str, Any]:
        return await self._step_ctrl.approve_step(session_id, step_number, user_id, approve, notes)

    async def submit_manual_command(self, session_id: int, command: str,
                                    shell: Optional[str] = "bash", run_as: Optional[str] = None,
                                    reason: Optional[str] = None, timeout_seconds: Optional[int] = 600,
                                    user_id: Optional[int] = None,
                                    idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        return await self._step_ctrl.submit_manual_command(
            session_id, command, shell, run_as, reason, timeout_seconds, user_id, idempotency_key
        )

    async def control_execution_session(self, session_id: int,
                                        action: Literal["pause", "resume", "rollback"],
                                        reason: Optional[str] = None,
                                        user_id: Optional[int] = None) -> Dict[str, Any]:
        return await self._step_ctrl.control_execution_session(session_id, action, reason, user_id)

    # ── Agent sessions ────────────────────────────────────────────────────────

    async def create_agent_session(self, issue_description: str, ticket_id: Optional[int] = None,
                                   user_id: Optional[int] = None,
                                   connection_id: Optional[int] = None) -> Dict[str, Any]:
        return await self._agent_ctrl.create_agent_session(
            issue_description, ticket_id, user_id, connection_id
        )

    def get_agent_session_plan(self, session_id: int) -> Dict[str, Any]:
        return self._agent_ctrl.get_agent_session_plan(session_id)

    def select_approach(self, session_id: int, approach_id: str) -> Dict[str, Any]:
        return self._agent_ctrl.select_approach(session_id, approach_id)

    def approve_agent_plan(self, session_id: int, selected_approach_id: Optional[str] = None, proposed_plan: Optional[List] = None) -> Dict[str, Any]:
        return self._agent_ctrl.approve_agent_plan(session_id, selected_approach_id, proposed_plan)

    def reject_agent_plan(self, session_id: int, feedback: str) -> Dict[str, Any]:
        return self._agent_ctrl.reject_agent_plan(session_id, feedback)

    async def review_agent_session(self, session_id: int, weed_step_numbers: List[int],
                                   save_as_runbook: bool,
                                   runbook_title: Optional[str]) -> Dict[str, Any]:
        return await self._agent_ctrl.review_agent_session(
            session_id, weed_step_numbers, save_as_runbook, runbook_title
        )

    def get_agent_session_steps_for_review(self, session_id: int) -> Dict[str, Any]:
        return self._agent_ctrl.get_agent_session_steps_for_review(session_id)

    def confirm_agent_resolution(self, session_id: int, human_resolved: bool) -> Dict[str, Any]:
        return self._agent_ctrl.confirm_resolution(session_id, human_resolved)

    def record_agent_feedback(self, session_id: int, feedback: str) -> Dict[str, Any]:
        return self._agent_ctrl.record_feedback(session_id, feedback)

    async def retry_agent_session(self, session_id: int, user_direction: Optional[str] = None) -> Dict[str, Any]:
        return await self._agent_ctrl.retry_agent_session(session_id, user_direction)
