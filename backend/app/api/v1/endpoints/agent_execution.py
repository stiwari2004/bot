"""
Agent execution endpoints with human validation
Main execution CRUD endpoints - WebSocket and debug endpoints are in separate modules
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from app.core.database import get_db
from app.core.tenant_utils import get_tenant_id
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_optional
from app.controllers.execution_controller import ExecutionController
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)


class ExecutionRequest(BaseModel):
    runbook_id: int
    ticket_id: Optional[int] = None
    issue_description: Optional[str] = None
    metadata: Optional[dict] = None  # Accept metadata from frontend


class StepApprovalRequest(BaseModel):
    approve: bool
    step_number: Optional[int] = None  # Optional - will use session's approval_step_number if not provided
    notes: Optional[str] = None


@router.get("/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sessions waiting for approval"""
    try:
        tenant_id = get_tenant_id(current_user)
        controller = ExecutionController(db, tenant_id)
        return controller.get_pending_approvals()
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")


@router.post("/execute")
@rate_limit("100/minute")  # High limit for dev/test
async def start_execution(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Start execution of a runbook"""
    import time
    start_time = time.time()
    logger.info(f"[START_EXECUTION] Received execution request: runbook_id={request.runbook_id}, ticket_id={request.ticket_id}, issue_description={request.issue_description[:50] if request.issue_description else None}")
    try:
        # Get tenant_id and user_id from current user or defaults
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None
        
        # Delegate to controller - all business logic is now in ExecutionController
        controller = ExecutionController(db, tenant_id)
        payload = await controller.create_execution_session(
            runbook_id=request.runbook_id,
            issue_description=request.issue_description,
            ticket_id=request.ticket_id,
            user_id=user_id,
            metadata=request.metadata,  # Metadata is stored in AgentWorkerAssignment.details and used for context
            auto_start=False  # Don't auto-start here - we'll do it in background
        )
        
        elapsed = time.time() - start_time
        logger.info(f"[START_EXECUTION] Session created in {elapsed:.2f}s, returning session {payload.get('id')}")
        
        # Start execution in background (non-blocking)
        session_id = payload.get('id')
        if session_id:
            async def start_execution_background():
                """Background task to start execution"""
                from app.core.database import SessionLocal
                from app.services.execution import ExecutionEngine
                from app.models.execution_session import ExecutionSession
                import asyncio
                
                # Small delay to ensure response is sent first
                await asyncio.sleep(0.1)
                
                background_db = SessionLocal()
                try:
                    logger.info(f"[BACKGROUND] Starting execution for session {session_id}")
                    
                    # Check session status and update if needed
                    session = background_db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
                    if not session:
                        logger.error(f"[BACKGROUND] Session {session_id} not found")
                        return
                    
                    # If session is queued, change it to pending to allow execution
                    if session.status == "queued":
                        logger.info(f"[BACKGROUND] Session {session_id} is queued, changing to pending")
                        session.status = "pending"
                        background_db.commit()
                        background_db.refresh(session)
                    
                    engine = ExecutionEngine()
                    session = await engine.start_execution(background_db, session_id)
                    logger.info(f"[BACKGROUND] Execution started for session {session_id}, status: {session.status}")
                    
                    # Ensure events are published by committing
                    background_db.commit()
                except Exception as e:
                    logger.error(f"[BACKGROUND] Failed to start execution for session {session_id}: {e}", exc_info=True)
                    import traceback
                    logger.error(f"[BACKGROUND] Traceback: {traceback.format_exc()}")
                    background_db.rollback()
                finally:
                    background_db.close()
            
            # FastAPI BackgroundTasks supports async functions
            background_tasks.add_task(start_execution_background)
            logger.info(f"[START_EXECUTION] Queued background execution for session {session_id}")
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/{session_id}/approve-step")
@rate_limit("200/minute")  # High limit for dev/test
async def approve_step(
    session_id: int,
    request: StepApprovalRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Approve or reject a step"""
    try:
        # Get tenant_id and user_id from current user or defaults
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None
        
        # If step_number not provided, use session's approval_step_number
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
        
        # Delegate to controller
        from app.controllers.execution_controller import ExecutionController
        controller = ExecutionController(db, tenant_id=tenant_id)
        result = await controller.approve_step(
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


@router.get("/sessions")
async def list_execution_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all execution sessions for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        
        query = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(ExecutionSession.status == status)
        
        sessions = query.order_by(ExecutionSession.created_at.desc()).limit(limit).all()
        
        # Get runbook titles
        from app.models.runbook import Runbook
        runbook_ids = [s.runbook_id for s in sessions]
        runbooks = {r.id: r.title for r in db.query(Runbook).filter(Runbook.id.in_(runbook_ids)).all()}
        
        return {
            "sessions": [
                {
                    "id": s.id,
                    "runbook_id": s.runbook_id,
                    "runbook_title": runbooks.get(s.runbook_id, "Unknown"),
                    "ticket_id": s.ticket_id,
                    "status": s.status,
                    "current_step": s.current_step,
                    "waiting_for_approval": s.waiting_for_approval,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "total_duration_minutes": s.total_duration_minutes,
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error(f"Error listing execution sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}")
async def get_execution_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution session status for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Get all steps
        steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id
        ).order_by(ExecutionStep.step_number).all()
        
        return {
            "session_id": session.id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "command": s.command,
                    "requires_approval": s.requires_approval,
                    "approved": s.approved,
                    "completed": s.completed,
                    "success": s.success,
                    "output": s.output,
                    "error": s.error
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
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
        tenant_id = current_user.tenant_id if current_user else 1
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Only allow canceling if session is in a cancellable state
        if session.status in ["completed", "failed", "abandoned"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel session with status '{session.status}'"
            )
        
        # Update session status to abandoned
        session.status = "abandoned"
        session.completed_at = func.now()
        db.commit()
        db.refresh(session)
        
        logger.info(f"Session {session_id} cancelled by user")
        
        return {
            "session_id": session.id,
            "status": session.status,
            "message": "Session cancelled successfully"
        }
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
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
        tenant_id = current_user.tenant_id if current_user else 1
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Don't allow deleting running sessions - cancel them first
        if session.status in ["pending", "waiting_approval", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete session with status '{session.status}'. Cancel it first."
            )
        
        db.delete(session)
        db.commit()
        
        logger.info(f"Session {session_id} deleted by user")
        
        return {
            "session_id": session_id,
            "message": "Session deleted successfully"
        }
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
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
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
            "session_id": session_id,
            "status": session.status,
            "current_step": session.current_step,
            "steps": [
                {
                    "id": s.id,
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "command": s.command,
                    "notes": s.notes,
                    "requires_approval": s.requires_approval,
                    "approved": s.approved,
                    "completed": s.completed,
                    "success": s.success,
                    "output": s.output,
                    "error": s.error,
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


# WebSocket and debug endpoints are now in separate modules:
# - execution_websocket.py: WebSocket endpoints
# - azure_debug.py: Azure-specific debug endpoints
# - execution_debug.py: General debug endpoints

