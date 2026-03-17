"""
Agent execution — session query, cancel, delete, and step listing endpoints
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_optional
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sessions")
async def list_execution_sessions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all execution sessions for the authenticated user's tenant"""
    try:
        tenant_id = current_user.tenant_id
        query = db.query(ExecutionSession).filter(ExecutionSession.tenant_id == tenant_id)
        if status:
            query = query.filter(ExecutionSession.status == status)
        sessions = query.order_by(ExecutionSession.created_at.desc()).limit(limit).all()

        runbook_ids = [s.runbook_id for s in sessions]
        runbooks = {r.id: r.title for r in db.query(Runbook).filter(Runbook.id.in_(runbook_ids)).all()}

        return {"sessions": [
            {
                "id": s.id, "runbook_id": s.runbook_id,
                "runbook_title": runbooks.get(s.runbook_id, "Unknown"),
                "ticket_id": s.ticket_id, "status": s.status,
                "current_step": s.current_step, "waiting_for_approval": s.waiting_for_approval,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "total_duration_minutes": s.total_duration_minutes,
            }
            for s in sessions
        ]}
    except Exception as e:
        logger.error(f"Error listing execution sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}")
async def get_execution_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution session status"""
    try:
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == current_user.tenant_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")

        steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id
        ).order_by(ExecutionStep.step_number).all()

        return {
            "session_id": session.id, "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id, "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": [
                {
                    "step_number": s.step_number, "step_type": s.step_type,
                    "command": s.command, "requires_approval": s.requires_approval,
                    "approved": s.approved, "completed": s.completed,
                    "success": s.success, "output": s.output, "error": s.error,
                }
                for s in steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.post("/{session_id}/cancel")
async def cancel_execution(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Cancel a running execution session"""
    try:
        tenant_id = current_user.tenant_id if current_user else 1
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        if session.status in ("completed", "failed", "abandoned"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel session with status '{session.status}'")

        session.status = "abandoned"
        session.completed_at = func.now()
        db.commit()
        db.refresh(session)
        logger.info(f"Session {session_id} cancelled by user")
        return {"session_id": session.id, "status": session.status, "message": "Session cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel session: {str(e)}")


@router.delete("/{session_id}")
async def delete_execution_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete an execution session"""
    try:
        tenant_id = current_user.tenant_id if current_user else 1
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        if session.status in ("pending", "waiting_approval", "in_progress"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete session with status '{session.status}'. Cancel it first."
            )
        db.delete(session)
        db.commit()
        logger.info(f"Session {session_id} deleted by user")
        return {"session_id": session_id, "message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting execution session: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/{session_id}/steps")
async def get_session_steps(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get all steps for a session with their execution status"""
    try:
        tenant_id = current_user.tenant_id if current_user else 1
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")

        steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id
        ).order_by(ExecutionStep.step_number).all()

        return {
            "session_id": session_id, "status": session.status,
            "current_step": session.current_step,
            "steps": [
                {
                    "id": s.id, "step_number": s.step_number, "step_type": s.step_type,
                    "command": s.command, "notes": s.notes,
                    "requires_approval": s.requires_approval, "approved": s.approved,
                    "completed": s.completed, "success": s.success,
                    "output": s.output, "error": s.error,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session steps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session steps: {str(e)}")
