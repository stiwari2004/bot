"""
ExecutionStepController — step-level operations within a session
"""
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.services.execution_orchestrator import execution_orchestrator
from app.services.idempotency import idempotency_manager
from app.services.execution import ExecutionEngine
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionStepController(BaseController):
    """Step-level operations: update, approve, manual command, control"""

    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)
        self.execution_engine = ExecutionEngine()

    async def update_execution_step(
        self,
        session_id: int,
        step_number: int,
        step_type: str,
        completed: bool,
        success: Optional[bool] = None,
        output: Optional[str] = None,
        notes: Optional[str] = None,
        approved: Optional[bool] = None,
    ) -> Dict[str, Any]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)

            step = self.execution_repo.get_step(session_id, step_number, step_type)
            if not step:
                raise self.not_found("Execution step", step_number)

            step.completed = completed
            if success is not None:
                step.success = success
            elif not completed:
                step.success = None

            if output is not None:
                step.output = output
            if notes is not None:
                step.notes = notes

            if completed:
                step.completed_at = datetime.now(timezone.utc)
            else:
                step.completed_at = None

            if approved is not None:
                if approved and step.requires_approval and step.approved is None:
                    session = await self.execution_engine.approve_step(
                        db=self.db,
                        session_id=session_id,
                        step_number=step_number,
                        user_id=None,
                        approve=True,
                    )
                    session = self.execution_repo.get_by_id(session_id)
                    logger.info(f"Step {step_number} approved and executed. Session status: {session.status}")
                    return {"message": "Step approved and execution triggered", "session": session}
                else:
                    step.approved = approved
                    step.approved_at = datetime.now(timezone.utc) if approved else None
                    if not approved:
                        session.status = "failed"
                        session.waiting_for_approval = False
                        session.completed_at = datetime.now(timezone.utc)
            elif step.requires_approval and step.approved is None:
                session.waiting_for_approval = True

            if approved is None or not approved or not step.requires_approval:
                remaining_steps = [s for s in session.steps if not s.completed]
                current_step = (
                    remaining_steps[0].step_number
                    if remaining_steps
                    else (session.steps[-1].step_number if session.steps else None)
                )
                waiting_for_approval = any(s.requires_approval and s.approved is None for s in session.steps)
                new_status = (
                    "waiting_approval"
                    if waiting_for_approval
                    else ("in_progress" if session.status != "failed" else session.status)
                )
                self.execution_repo.update_session(
                    session_id=session_id,
                    current_step=current_step,
                    waiting_for_approval=waiting_for_approval,
                    status=new_status,
                )
            return {"message": "Step updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise self.handle_error(e, "Failed to update step")

    async def approve_step(
        self,
        session_id: int,
        step_number: int,
        user_id: Optional[int],
        approve: bool,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)

            if session.tenant_id != self.tenant_id:
                raise self.not_found("Execution session", session_id)

            updated_session = await self.execution_engine.approve_step(
                db=self.db,
                session_id=session_id,
                step_number=step_number,
                user_id=user_id,
                approve=approve,
            )
            return execution_orchestrator.serialize_session(updated_session)
        except HTTPException:
            raise
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving step: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to approve step")

    async def submit_manual_command(
        self,
        session_id: int,
        command: str,
        shell: Optional[str] = "bash",
        run_as: Optional[str] = None,
        reason: Optional[str] = None,
        timeout_seconds: Optional[int] = 600,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        idempotency_key = (idempotency_key or "").strip() or None
        reservation_committed = False
        try:
            if idempotency_key:
                existing = await idempotency_manager.reserve("manual-command", idempotency_key)
                if existing:
                    if existing == "__PENDING__":
                        raise HTTPException(
                            status_code=409,
                            detail="Manual command processing already in progress for provided idempotency key.",
                        )
                    raise HTTPException(
                        status_code=409,
                        detail="Duplicate manual command detected for provided idempotency key.",
                    )

            event_record = await execution_orchestrator.submit_manual_command(
                self.db,
                session_id=session_id,
                command=command,
                shell=shell,
                run_as=run_as,
                reason=reason,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                idempotency_key=idempotency_key,
            )

            if idempotency_key:
                await idempotency_manager.commit(
                    "manual-command", idempotency_key, event_record.get("stream_id") or ""
                )
                reservation_committed = True

            return event_record
        except ValueError as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("manual-command", idempotency_key)
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("manual-command", idempotency_key)
            logger.exception("Failed to submit manual command: %s", e)
            raise self.handle_error(e, "Failed to submit manual command")

    async def control_execution_session(
        self,
        session_id: int,
        action: Literal["pause", "resume", "rollback"],
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            session = await execution_orchestrator.control_session(
                self.db,
                session_id=session_id,
                action=action,
                reason=reason,
                user_id=user_id,
            )
            return execution_orchestrator.serialize_session(session)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Failed to perform session control action: %s", e)
            raise self.handle_error(e, "Failed to control session")
