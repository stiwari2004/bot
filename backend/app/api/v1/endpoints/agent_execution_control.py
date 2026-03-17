"""
Agent execution — start execution and step approval endpoints
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant_utils import get_tenant_id
from app.models.execution_session import ExecutionSession
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_optional
from app.controllers.execution_controller import ExecutionController
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit

router = APIRouter()
logger = get_logger(__name__)


class ExecutionRequest(BaseModel):
    runbook_id: int
    ticket_id: Optional[int] = None
    issue_description: Optional[str] = None
    metadata: Optional[dict] = None


class StepApprovalRequest(BaseModel):
    approve: bool
    step_number: Optional[int] = None
    notes: Optional[str] = None


@router.get("/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sessions waiting for approval"""
    try:
        return ExecutionController(db, get_tenant_id(current_user)).get_pending_approvals()
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")


@router.post("/execute")
@rate_limit("100/minute")
async def start_execution(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Start execution of a runbook"""
    import time
    start_time = time.time()
    logger.info(f"[START_EXECUTION] runbook_id={request.runbook_id}, ticket_id={request.ticket_id}")
    try:
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None

        payload = await ExecutionController(db, tenant_id).create_execution_session(
            runbook_id=request.runbook_id,
            issue_description=request.issue_description,
            ticket_id=request.ticket_id,
            user_id=user_id,
            metadata=request.metadata,
            auto_start=False
        )

        elapsed = time.time() - start_time
        logger.info(f"[START_EXECUTION] Session created in {elapsed:.2f}s, id={payload.get('id')}")

        session_id = payload.get('id')
        if session_id:
            async def _start_bg():
                from app.core.database import SessionLocal
                from app.services.execution import ExecutionEngine
                await asyncio.sleep(0.1)
                background_db = SessionLocal()
                try:
                    session = background_db.query(ExecutionSession).filter(
                        ExecutionSession.id == session_id
                    ).first()
                    if not session:
                        logger.error(f"[BACKGROUND] Session {session_id} not found")
                        return
                    if session.status == "queued":
                        session.status = "pending"
                        background_db.commit()
                        background_db.refresh(session)
                    session = await ExecutionEngine().start_execution(background_db, session_id)
                    logger.info(f"[BACKGROUND] Execution started, status: {session.status}")
                    background_db.commit()
                except Exception as e:
                    logger.error(f"[BACKGROUND] Failed for session {session_id}: {e}", exc_info=True)
                    background_db.rollback()
                finally:
                    background_db.close()

            background_tasks.add_task(_start_bg)
            logger.info(f"[START_EXECUTION] Queued background execution for session {session_id}")

        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/{session_id}/approve-step")
@rate_limit("200/minute")
async def approve_step(
    session_id: int,
    request: StepApprovalRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Approve or reject a step"""
    try:
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None

        step_number = request.step_number
        if step_number is None:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"Execution session {session_id} not found")
            if session.tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail=f"Execution session {session_id} not found")
            step_number = session.approval_step_number
            if step_number is None:
                raise HTTPException(status_code=400, detail="Step number not provided and session has no pending approval step")

        result = await ExecutionController(db, tenant_id=tenant_id).approve_step(
            session_id=session_id,
            step_number=step_number,
            user_id=user_id,
            approve=request.approve,
            notes=request.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving step: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve step: {str(e)}")
