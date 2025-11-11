"""
Agent execution endpoints with human validation
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.models.user import User
from app.services.auth import get_current_user
from app.services.execution_engine import ExecutionEngine
from app.services.runbook_search import RunbookSearchService
from app.services.ticket_status_service import get_ticket_status_service
from app.core.logging import get_logger
from pydantic import BaseModel
import json

router = APIRouter()
logger = get_logger(__name__)

# Store active WebSocket connections
active_connections: dict = {}


class ExecutionRequest(BaseModel):
    runbook_id: int
    ticket_id: Optional[int] = None
    issue_description: Optional[str] = None


class StepApprovalRequest(BaseModel):
    approve: bool
    notes: Optional[str] = None


@router.get("/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db)
):
    """Get all sessions waiting for approval"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
        sessions = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.waiting_for_approval == True,
            ExecutionSession.status == "waiting_approval"
        ).all()
        
        result = []
        for session in sessions:
            step = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.step_number == session.approval_step_number
            ).first()
            
            runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
            
            result.append({
                "session_id": session.id,
                "runbook_id": session.runbook_id,
                "runbook_title": runbook.title if runbook else "Unknown",
                "step_number": session.approval_step_number,
                "step_type": step.step_type if step else None,
                "command": step.command if step else None,
                "issue_description": session.issue_description,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        return {"pending_approvals": result}
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")


@router.post("/execute")
async def start_execution(
    request: ExecutionRequest,
    db: Session = Depends(get_db)
):
    """Start execution of a runbook"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        user_id = None
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
            user_id = current_user.id
        except:
            pass  # Use defaults for demo
        
        # Verify runbook exists
        runbook = db.query(Runbook).filter(
            Runbook.id == request.runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        if runbook.status != "approved":
            raise HTTPException(status_code=400, detail="Runbook must be approved before execution")
        
        # Create execution session
        engine = ExecutionEngine()
        session = await engine.create_execution_session(
            db=db,
            runbook_id=request.runbook_id,
            tenant_id=tenant_id,
            ticket_id=request.ticket_id,
            issue_description=request.issue_description,
            user_id=user_id
        )
        
        # Update ticket status when execution starts (if ticket_id provided)
        if request.ticket_id:
            ticket_status_service = get_ticket_status_service()
            ticket_status_service.update_ticket_on_execution_start(db, request.ticket_id)
        
        # Start execution if no approval needed
        if session.status == "pending":
            session = await engine.start_execution(db, session.id)
        
        db.refresh(session)
        
        return {
            "session_id": session.id,
            "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/{session_id}/approve-step")
async def approve_step(
    session_id: int,
    step_number: int,
    request: StepApprovalRequest,
    db: Session = Depends(get_db)
):
    """Approve or reject a step"""
    try:
        # Use demo user for POC
        user_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            user_id = current_user.id
        except:
            pass  # Use default for demo
        
        engine = ExecutionEngine()
        session = await engine.approve_step(
            db=db,
            session_id=session_id,
            step_number=step_number,
            user_id=user_id,
            approve=request.approve
        )
        
        db.refresh(session)
        
        # Get current step details
        current_step = None
        if session.current_step:
            current_step = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id,
                ExecutionStep.step_number == session.current_step
            ).first()
        
        return {
            "session_id": session.id,
            "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step,
            "step_details": {
                "step_number": current_step.step_number if current_step else None,
                "command": current_step.command if current_step else None,
                "output": current_step.output if current_step else None,
                "success": current_step.success if current_step else None
            } if current_step else None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving step: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve step: {str(e)}")


@router.get("/{session_id}")
async def get_execution_status(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get execution session status"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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


@router.websocket("/ws/approvals/{session_id}")
async def websocket_approvals(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time approval updates"""
    await websocket.accept()
    
    try:
        # Store connection
        if session_id not in active_connections:
            active_connections[session_id] = []
        active_connections[session_id].append(websocket)
        
        # Send initial status
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if session:
                await websocket.send_json({
                    "type": "status",
                    "session_id": session_id,
                    "status": session.status,
                    "waiting_for_approval": session.waiting_for_approval
                })
        finally:
            db.close()
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "approval":
                # Handle approval
                approve = data.get("approve", False)
                step_number = data.get("step_number")
                
                # Process approval (this would call the approval endpoint logic)
                await websocket.send_json({
                    "type": "approval_received",
                    "approved": approve,
                    "step_number": step_number
                })
            
    except WebSocketDisconnect:
        # Remove connection
        if session_id in active_connections:
            active_connections[session_id].remove(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


async def notify_approval_needed(session_id: int, step_number: int):
    """Notify WebSocket clients that approval is needed"""
    if session_id in active_connections:
        message = {
            "type": "approval_needed",
            "session_id": session_id,
            "step_number": step_number
        }
        # Send to all connected clients
        for ws in active_connections[session_id]:
            try:
                await ws.send_json(message)
            except:
                pass

