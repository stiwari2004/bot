"""
Quarantine API endpoints
Provides endpoints for managing runbook quarantines
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.quarantine_controller import QuarantineController
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class QuarantineStatusResponse(BaseModel):
    """Response model for quarantine status"""
    is_quarantined: bool
    quarantine_id: Optional[int] = None
    reason: Optional[str] = None
    failure_count: Optional[int] = None
    quarantined_at: Optional[str] = None
    review_status: Optional[str] = None


class QuarantineRequest(BaseModel):
    """Request model for manual quarantine"""
    runbook_version_id: Optional[int] = None
    reason: str = "manual"
    auto_release_hours: Optional[int] = None


class ReleaseRequest(BaseModel):
    """Request model for releasing quarantine"""
    runbook_version_id: Optional[int] = None
    review_notes: Optional[str] = None


class FailurePatternResponse(BaseModel):
    """Response model for failure pattern analysis"""
    has_pattern: bool
    failure_count: Optional[int] = None
    error_types: Optional[List[str]] = None
    same_error: Optional[bool] = None
    varied_errors: Optional[bool] = None
    recent_errors: Optional[List[Dict[str, Any]]] = None
    quarantine_reason: Optional[str] = None
    quarantined_at: Optional[str] = None
    message: Optional[str] = None


@router.get("/demo/quarantine/status/{runbook_id}", response_model=QuarantineStatusResponse)
async def get_quarantine_status(
    runbook_id: int,
    runbook_version_id: Optional[int] = Query(None, description="Optional runbook version ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quarantine status for a runbook
    
    Returns whether the runbook is quarantined and details
    """
    try:
        controller = QuarantineController(db, current_user.tenant_id)
        status = controller.get_quarantine_status(
            runbook_id=runbook_id,
            runbook_version_id=runbook_version_id
        )
        return QuarantineStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quarantine status for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/quarantine/quarantine/{runbook_id}")
async def quarantine_runbook(
    runbook_id: int,
    request: QuarantineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually quarantine a runbook
    
    Allows admins to quarantine runbooks for review or safety reasons
    """
    try:
        controller = QuarantineController(db, current_user.tenant_id)
        result = controller.quarantine_runbook(
            runbook_id=runbook_id,
            runbook_version_id=request.runbook_version_id,
            reason=request.reason,
            quarantined_by=current_user.id,
            auto_release_hours=request.auto_release_hours
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error quarantining runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/quarantine/release/{runbook_id}")
async def release_quarantine(
    runbook_id: int,
    request: ReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Release a runbook from quarantine
    
    Allows admins to release runbooks after review
    """
    try:
        quarantine_service = QuarantineService()
        
        quarantine = quarantine_service.release_quarantine(
            db=db,
            runbook_id=runbook_id,
            runbook_version_id=request.runbook_version_id,
            reviewed_by=current_user.id,
            review_notes=request.review_notes,
            tenant_id=current_user.tenant_id
        )
        
        return {
            "quarantine_id": quarantine.id,
            "runbook_id": runbook_id,
            "runbook_version_id": request.runbook_version_id,
            "message": "Quarantine released successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error releasing quarantine for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/quarantine/pending-review")
async def get_pending_reviews(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get runbooks pending review
    
    Returns list of quarantined runbooks that need review
    """
    try:
        controller = QuarantineController(db, current_user.tenant_id)
        results = controller.get_pending_reviews(limit=limit)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/quarantine/failure-patterns/{runbook_id}", response_model=FailurePatternResponse)
async def get_failure_patterns(
    runbook_id: int,
    runbook_version_id: Optional[int] = Query(None, description="Optional runbook version ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get failure pattern analysis for a runbook
    
    Returns analysis of failure patterns including error types and consistency
    """
    try:
        controller = QuarantineController(db, current_user.tenant_id)
        analysis = controller.get_failure_patterns(
            runbook_id=runbook_id,
            runbook_version_id=runbook_version_id
        )
        return FailurePatternResponse(**analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting failure patterns for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
