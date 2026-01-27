"""
Human-in-the-Loop Workspace API endpoints
Provides endpoints for approval management, parameter tuning, and audit trails
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.human_in_loop_controller import HumanInLoopController
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ParameterTuningRequest(BaseModel):
    """Request model for parameter tuning"""
    parameters: Dict[str, Any]
    reason: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request model for approval"""
    approve: bool
    reason: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None  # Optional parameter tuning


class PendingApprovalResponse(BaseModel):
    """Response model for pending approval"""
    session_id: int
    step_id: int
    step_number: int
    runbook_id: int
    runbook_title: Optional[str]
    ticket_id: Optional[int]
    command: Optional[str]
    command_payload: Optional[Dict[str, Any]]
    requires_approval: bool
    waiting_since: Optional[str]
    current_parameters: Optional[Dict[str, Any]]


class AuditTrailResponse(BaseModel):
    """Response model for audit trail"""
    id: int
    action: str
    user_id: Optional[int]
    timestamp: str
    reason: Optional[str]
    modified_parameters: Optional[Dict[str, Any]]
    original_parameters: Optional[Dict[str, Any]]
    outcome: Optional[str]
    outcome_notes: Optional[str]
    step_id: Optional[int]


@router.get("/demo/workspace/pending-approvals", response_model=List[PendingApprovalResponse])
async def get_pending_approvals(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of approvals"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending approvals for the tenant
    
    Returns list of execution steps waiting for approval
    """
    try:
        controller = HumanInLoopController(db, current_user.tenant_id)
        approvals = await controller.get_pending_approvals(limit=limit)
        return [PendingApprovalResponse(**approval) for approval in approvals]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/workspace/approve/{session_id}/{step_id}")
async def approve_step(
    session_id: int,
    step_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject an execution step with optional parameter tuning
    
    If parameters are provided, they will be tuned before approval
    """
    try:
        controller = HumanInLoopController(db, current_user.tenant_id)
        result = await controller.approve_step(
            session_id=session_id,
            step_id=step_id,
            approve=request.approve,
            user_id=current_user.id,
            reason=request.reason,
            parameters=request.parameters
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving step {step_id} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/workspace/tune-parameters/{session_id}/{step_id}")
async def tune_step_parameters(
    session_id: int,
    step_id: int,
    request: ParameterTuningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tune parameters for an execution step before approval
    
    This allows modifying step parameters without changing the runbook code
    """
    try:
        controller = HumanInLoopController(db, current_user.tenant_id)
        result = await controller.tune_parameters(
            session_id=session_id,
            step_id=step_id,
            parameters=request.parameters,
            user_id=current_user.id,
            reason=request.reason
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tuning parameters for step {step_id} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/workspace/audit-trail/{session_id}", response_model=List[AuditTrailResponse])
async def get_audit_trail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit trail for an execution session
    
    Returns chronological list of all approval actions, parameter tunings, and decisions
    """
    try:
        controller = HumanInLoopController(db, current_user.tenant_id)
        audit_trail = controller.get_audit_trail(session_id=session_id)
        return [AuditTrailResponse(**record) for record in audit_trail]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit trail for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
