"""
Resolution orchestration API endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.resolution_controller import ResolutionController
from app.core.rate_limiting import rate_limit
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/demo/tickets/{ticket_id}/auto-resolve")
@rate_limit("30/minute")
async def auto_resolve_ticket(
    ticket_id: int,
    runbook_id: int,
    confidence: float = Query(..., ge=0.0, le=1.0, description="Confidence score for auto-resolution"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatically resolve a ticket with high confidence
    
    Creates a resolution flow and initiates auto-resolution if confidence meets threshold
    """
    try:
        controller = ResolutionController(db, current_user.tenant_id)
        result = await controller.auto_resolve_ticket(
            ticket_id=ticket_id,
            runbook_id=runbook_id,
            confidence=confidence
        )
        return result
    
    except Exception as e:
        logger.error(f"Error auto-resolving ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/tickets/{ticket_id}/create-flow")
@rate_limit("30/minute")
async def create_resolution_flow(
    ticket_id: int,
    runbook_id: Optional[int] = None,
    auto_resolution_enabled: bool = False,
    confidence_threshold: float = Query(0.8, ge=0.0, le=1.0),
    max_iterations: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a resolution flow for a ticket
    
    Sets up the orchestration workflow for end-to-end resolution
    """
    try:
        controller = ResolutionController(db, current_user.tenant_id)
        result = await controller.create_resolution_flow(
            ticket_id=ticket_id,
            runbook_id=runbook_id,
            auto_resolution_enabled=auto_resolution_enabled,
            confidence_threshold=confidence_threshold,
            max_iterations=max_iterations
        )
        return result
    
    except Exception as e:
        logger.error(f"Error creating resolution flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/flows/{flow_id}")
@rate_limit("60/minute")
async def get_flow_status(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a resolution flow
    
    Returns current phase, workflow status, and progress information
    """
    try:
        controller = ResolutionController(db, current_user.tenant_id)
        status = await controller.get_flow_status(flow_id)
        return status
    
    except Exception as e:
        logger.error(f"Error getting flow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/flows/{flow_id}/advance")
@rate_limit("30/minute")
async def advance_flow_phase(
    flow_id: int,
    new_phase: str = Query(..., regex="^(precheck|fix|verification|closure|escalated)$"),
    phase_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advance resolution flow to next phase
    
    Moves the workflow to the specified phase and stores phase-specific data
    """
    try:
        controller = ResolutionController(db, current_user.tenant_id)
        result = await controller.advance_phase(
            flow_id=flow_id,
            new_phase=new_phase,
            phase_data=phase_data
        )
        return result
    
    except Exception as e:
        logger.error(f"Error advancing flow phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/flows/{flow_id}/complete")
@rate_limit("30/minute")
async def complete_resolution_flow(
    flow_id: int,
    success: bool,
    verification_result: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete a resolution flow
    
    Marks the flow as completed or escalated based on success
    """
    try:
        controller = ResolutionController(db, current_user.tenant_id)
        result = await controller.complete_flow(
            flow_id=flow_id,
            success=success,
            verification_result=verification_result
        )
        return result
    
    except Exception as e:
        logger.error(f"Error completing flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

