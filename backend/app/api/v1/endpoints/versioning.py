"""
Versioning API endpoints
Provides endpoints for runbook versioning and promotion workflow
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.versioning_controller import VersioningController
from app.controllers.deployment_approval_controller import DeploymentApprovalController
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class CreateVersionRequest(BaseModel):
    """Request model for creating a version"""
    change_summary: str
    change_type: str = "minor"  # 'major', 'minor', 'patch', 'custom'


class RollbackRequest(BaseModel):
    """Request model for rollback"""
    version_id: int
    reason: str


class PromotionRequest(BaseModel):
    """Request model for promotion"""
    version_id: int
    target_environment: str = "production"


class ApprovePromotionRequest(BaseModel):
    """Request model for approving promotion"""
    approval_id: int


class RejectPromotionRequest(BaseModel):
    """Request model for rejecting promotion"""
    approval_id: int
    reason: str


@router.post("/demo/runbooks/{runbook_id}/versions")
async def create_version(
    runbook_id: int,
    request: CreateVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of a runbook"""
    try:
        controller = VersioningController(db, current_user.tenant_id)
        result = controller.create_version(
            runbook_id=runbook_id,
            change_summary=request.change_summary,
            change_type=request.change_type,
            created_by=current_user.id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating version for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/runbooks/{runbook_id}/versions")
async def get_version_history(
    runbook_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get version history for a runbook"""
    try:
        controller = VersioningController(db, current_user.tenant_id)
        history = controller.get_version_history(runbook_id=runbook_id, limit=limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version history for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/versions/{version_id_1}/compare/{version_id_2}")
async def compare_versions(
    version_id_1: int,
    version_id_2: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare two versions"""
    try:
        controller = VersioningController(db, current_user.tenant_id)
        comparison = controller.compare_versions(
            version_id_1=version_id_1,
            version_id_2=version_id_2
        )
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing versions {version_id_1} and {version_id_2}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/runbooks/{runbook_id}/rollback")
async def rollback_version(
    runbook_id: int,
    request: RollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rollback to a previous version"""
    try:
        controller = VersioningController(db, current_user.tenant_id)
        result = controller.rollback_version(
            runbook_id=runbook_id,
            version_id=request.version_id,
            reason=request.reason,
            rolled_back_by=current_user.id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/runbooks/{runbook_id}/promote")
async def request_promotion(
    runbook_id: int,
    request: PromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request promotion of a runbook version"""
    try:
        controller = DeploymentApprovalController(db, current_user.tenant_id)
        result = controller.request_promotion(
            runbook_id=runbook_id,
            version_id=request.version_id,
            requested_by=current_user.id,
            target_environment=request.target_environment
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting promotion for runbook {runbook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/deployment-approvals/approve")
async def approve_promotion(
    request: ApprovePromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve and execute promotion"""
    try:
        controller = DeploymentApprovalController(db, current_user.tenant_id)
        result = controller.approve_promotion(
            approval_id=request.approval_id,
            approved_by=current_user.id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving promotion {request.approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/deployment-approvals/reject")
async def reject_promotion(
    request: RejectPromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject promotion request"""
    try:
        controller = DeploymentApprovalController(db, current_user.tenant_id)
        result = controller.reject_promotion(
            approval_id=request.approval_id,
            rejected_by=current_user.id,
            reason=request.reason
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting promotion {request.approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/deployment-approvals/pending")
async def get_pending_approvals(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending deployment approvals"""
    try:
        controller = DeploymentApprovalController(db, current_user.tenant_id)
        approvals = controller.get_pending_approvals(limit=limit)
        return approvals
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
