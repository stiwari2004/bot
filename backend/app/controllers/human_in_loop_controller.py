"""
HumanInLoopController
Handles HTTP requests for human-in-the-loop workspace operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.runbook_repository import RunbookRepository
from app.services.execution.approval_service import ApprovalService
from app.core.logging import get_logger

logger = get_logger(__name__)


class HumanInLoopController(BaseController):
    """Controller for human-in-the-loop workspace operations"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)
        self.runbook_repo = RunbookRepository(db)

        from app.services.execution.step_execution_service import StepExecutionService
        from app.services.ticket.ticket_status_service import TicketStatusService
        from app.services.execution.resolution_verification_service import ResolutionVerificationService

        self.approval_service = ApprovalService(
            step_execution_service=StepExecutionService(),
            ticket_status_service=TicketStatusService(),
            resolution_verification_service=ResolutionVerificationService(),
        )

    async def get_pending_approvals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all pending approvals for the tenant"""
        try:
            sessions = self.execution_repo.get_pending_approvals(self.tenant_id, limit=limit)
            pending_approvals = []

            for session in sessions:
                step = self.execution_repo.get_step_awaiting_approval(
                    session.id, session.approval_step_number
                )
                if step:
                    runbook_title = None
                    if session.runbook_id:
                        runbook = self.runbook_repo.get_by_id_and_tenant(
                            session.runbook_id, self.tenant_id
                        )
                        if runbook:
                            runbook_title = runbook.title

                    pending_approvals.append({
                        "session_id": session.id,
                        "step_id": step.id,
                        "step_number": step.step_number,
                        "runbook_id": session.runbook_id,
                        "runbook_title": runbook_title,
                        "ticket_id": session.ticket_id,
                        "command": step.command,
                        "command_payload": step.command_payload,
                        "requires_approval": step.requires_approval,
                        "waiting_since": session.created_at.isoformat() if session.created_at else None,
                        "current_parameters": step.command_payload,
                    })

            return pending_approvals

        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            raise self.handle_error(e, "Failed to get pending approvals")

    async def approve_step(
        self,
        session_id: int,
        step_id: int,
        approve: bool,
        user_id: int,
        reason: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Approve or reject an execution step with optional parameter tuning"""
        try:
            session = self.execution_repo.get_by_id_and_tenant(session_id, self.tenant_id)
            if not session:
                raise self.not_found("Execution session", session_id)

            step = self.execution_repo.get_step_by_id_and_session(step_id, session_id)
            if not step:
                raise self.not_found("Execution step", step_id)

            if parameters:
                await self.approval_service.tune_parameters(
                    db=self.db,
                    session_id=session_id,
                    step_id=step_id,
                    parameters=parameters,
                    user_id=user_id,
                    reason=reason or "Parameter tuning before approval",
                )

            updated_session = await self.approval_service.approve_step(
                db=self.db,
                session_id=session_id,
                step_number=step.step_number,
                user_id=user_id,
                approve=approve,
            )

            return {
                "session_id": session_id,
                "step_id": step_id,
                "approved": approve,
                "status": updated_session.status,
                "message": "Step approved successfully" if approve else "Step rejected",
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error approving step {step_id} in session {session_id}: {e}")
            raise self.handle_error(e, "Failed to approve step")

    async def tune_parameters(
        self,
        session_id: int,
        step_id: int,
        parameters: Dict[str, Any],
        user_id: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tune parameters for an execution step before approval"""
        try:
            session = self.execution_repo.get_by_id_and_tenant(session_id, self.tenant_id)
            if not session:
                raise self.not_found("Execution session", session_id)

            step = self.execution_repo.get_step_by_id_and_session(step_id, session_id)
            if not step:
                raise self.not_found("Execution step", step_id)

            tunings = await self.approval_service.tune_parameters(
                db=self.db,
                session_id=session_id,
                step_id=step_id,
                parameters=parameters,
                user_id=user_id,
                reason=reason,
            )

            return {
                "session_id": session_id,
                "step_id": step_id,
                "tuned_parameters": len(tunings),
                "parameters": parameters,
                "message": "Parameters tuned successfully",
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error tuning parameters for step {step_id} in session {session_id}: {e}")
            raise self.handle_error(e, "Failed to tune parameters")

    def get_audit_trail(self, session_id: int) -> List[Dict[str, Any]]:
        """Get audit trail for an execution session"""
        try:
            session = self.execution_repo.get_by_id_and_tenant(session_id, self.tenant_id)
            if not session:
                raise self.not_found("Execution session", session_id)

            return self.approval_service.get_audit_trail(db=self.db, session_id=session_id)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting audit trail for session {session_id}: {e}")
            raise self.handle_error(e, "Failed to get audit trail")
