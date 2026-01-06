"""
Deployment Approval Endpoints
Endpoints for managing code and runbook deployment approvals
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.deployment_approval import DeploymentApproval
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class DeploymentApprovalRequest(BaseModel):
    deployment_type: str  # 'code' or 'runbook'
    reference_id: Optional[int] = None
    reference_name: Optional[str] = None
    metadata: Optional[dict] = None


class DeploymentApprovalResponse(BaseModel):
    id: int
    deployment_type: str
    target_environment: str
    reference_id: Optional[int]
    reference_name: Optional[str]
    status: str
    requested_by: Optional[int]
    approved_by: Optional[int]
    approved_at: Optional[str]
    rejected_at: Optional[str]
    rejection_reason: Optional[str]
    deployed_at: Optional[str]
    created_at: str


@router.get("/deployment-approvals")
async def list_deployment_approvals(
    status_filter: Optional[str] = None,
    deployment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List deployment approvals
    
    Args:
        status_filter: Filter by status (pending, approved, rejected, deployed)
        deployment_type: Filter by type (code, runbook)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of deployment approvals
    """
    try:
        query = db.query(DeploymentApproval)
        
        if status_filter:
            query = query.filter(DeploymentApproval.status == status_filter)
        
        if deployment_type:
            query = query.filter(DeploymentApproval.deployment_type == deployment_type)
        
        approvals = query.order_by(DeploymentApproval.created_at.desc()).limit(100).all()
        
        return {
            "approvals": [
                {
                    "id": a.id,
                    "deployment_type": a.deployment_type,
                    "target_environment": a.target_environment,
                    "reference_id": a.reference_id,
                    "reference_name": a.reference_name,
                    "status": a.status,
                    "requested_by": a.requested_by,
                    "approved_by": a.approved_by,
                    "approved_at": a.approved_at.isoformat() if a.approved_at else None,
                    "rejected_at": a.rejected_at.isoformat() if a.rejected_at else None,
                    "rejection_reason": a.rejection_reason,
                    "deployed_at": a.deployed_at.isoformat() if a.deployed_at else None,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in approvals
            ],
            "total": len(approvals)
        }
    except Exception as e:
        logger.error(f"Error listing deployment approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deployment approvals: {str(e)}"
        )


@router.get("/deployment-approvals/{approval_id}")
async def get_deployment_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific deployment approval
    
    Args:
        approval_id: Approval ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Deployment approval details
    """
    try:
        approval = db.query(DeploymentApproval).filter(
            DeploymentApproval.id == approval_id
        ).first()
        
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment approval not found"
            )
        
        return {
            "id": approval.id,
            "deployment_type": approval.deployment_type,
            "target_environment": approval.target_environment,
            "reference_id": approval.reference_id,
            "reference_name": approval.reference_name,
            "status": approval.status,
            "requested_by": approval.requested_by,
            "approved_by": approval.approved_by,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
            "deployed_at": approval.deployed_at.isoformat() if approval.deployed_at else None,
            "deployment_log": approval.deployment_log,
            "metadata": approval.approval_metadata,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment approval {approval_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment approval: {str(e)}"
        )


@router.post("/deployment-approvals")
async def create_deployment_approval(
    request: DeploymentApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a deployment approval request
    
    Args:
        request: Deployment approval request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created deployment approval
    """
    try:
        # Check if user has permission (super admin required)
        from app.services.auth import get_current_super_admin_user
        # Verify user is super admin
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin permission required to create deployment approvals"
            )
        
        approval = DeploymentApproval(
            deployment_type=request.deployment_type,
            target_environment="production",
            reference_id=request.reference_id,
            reference_name=request.reference_name,
            status="pending",
            requested_by=current_user.id,
            approval_metadata=request.metadata
        )
        
        db.add(approval)
        db.commit()
        db.refresh(approval)
        
        logger.info(f"Created deployment approval {approval.id} for {request.deployment_type}")
        
        return {
            "id": approval.id,
            "deployment_type": approval.deployment_type,
            "status": approval.status,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
        }
    except Exception as e:
        logger.error(f"Error creating deployment approval: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deployment approval: {str(e)}"
        )


@router.post("/deployment-approvals/{approval_id}/approve")
async def approve_deployment(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a deployment request
    
    Args:
        approval_id: Approval ID
        db: Database session
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Updated approval
    """
    try:
        # Check if user has super admin permissions
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin permission required to update deployment approvals"
            )
        
        approval = db.query(DeploymentApproval).filter(
            DeploymentApproval.id == approval_id,
            DeploymentApproval.status == "pending"
        ).first()
        
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending deployment approval not found"
            )
        
        approval.status = "approved"
        approval.approved_by = current_user.id
        approval.approved_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(approval)
        
        logger.info(f"Deployment approval {approval_id} approved by user {current_user.id}")
        
        return {
            "id": approval.id,
            "status": approval.status,
            "approved_by": approval.approved_by,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving deployment {approval_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve deployment: {str(e)}"
        )


@router.post("/deployment-approvals/{approval_id}/reject")
async def reject_deployment(
    approval_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a deployment request
    
    Args:
        approval_id: Approval ID
        reason: Rejection reason
        db: Database session
        current_user: Current authenticated user (must be admin)
        
    Returns:
        Updated approval
    """
    try:
        # Check if user has super admin permissions
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin permission required to update deployment approvals"
            )
        
        approval = db.query(DeploymentApproval).filter(
            DeploymentApproval.id == approval_id,
            DeploymentApproval.status == "pending"
        ).first()
        
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending deployment approval not found"
            )
        
        approval.status = "rejected"
        approval.rejected_at = datetime.now(timezone.utc)
        approval.rejection_reason = reason
        
        db.commit()
        db.refresh(approval)
        
        logger.info(f"Deployment approval {approval_id} rejected by user {current_user.id}: {reason}")
        
        return {
            "id": approval.id,
            "status": approval.status,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting deployment {approval_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject deployment: {str(e)}"
        )

