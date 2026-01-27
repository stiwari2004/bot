"""
Deployment Approval Service
Handles approval workflow for runbook promotions
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.deployment_approval import DeploymentApproval
from app.models.runbook import Runbook
from app.models.runbook_version import RunbookVersion
from app.services.runbook.versioning_service import VersioningService
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeploymentApprovalService:
    """Service for managing deployment approvals"""
    
    def __init__(self):
        self.versioning_service = VersioningService()
    
    def request_promotion(
        self,
        db: Session,
        runbook_id: int,
        version_id: int,
        requested_by: int,
        tenant_id: int,
        target_environment: str = "production"
    ) -> DeploymentApproval:
        """
        Request promotion of a runbook version
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            version_id: Version ID to promote
            requested_by: User ID requesting promotion
            tenant_id: Tenant ID
            target_environment: Target environment
            
        Returns:
            DeploymentApproval object
        """
        # Verify runbook and version
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        version = db.query(RunbookVersion).filter(
            RunbookVersion.id == version_id,
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id
        ).first()
        
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        # Check if there's already a pending approval
        existing = db.query(DeploymentApproval).filter(
            DeploymentApproval.deployment_type == "runbook",
            DeploymentApproval.reference_id == runbook_id,
            DeploymentApproval.status == "pending",
            DeploymentApproval.target_environment == target_environment
        ).first()
        
        if existing:
            raise ValueError("Pending approval already exists for this runbook")
        
        # Create approval request
        approval = DeploymentApproval(
            deployment_type="runbook",
            target_environment=target_environment,
            reference_id=runbook_id,
            reference_name=runbook.title,
            status="pending",
            requested_by=requested_by,
            approval_metadata={
                "version_id": version_id,
                "version_number": version.version_number,
                "change_summary": version.change_summary,
                "change_type": version.change_type
            }
        )
        
        db.add(approval)
        db.commit()
        db.refresh(approval)
        
        logger.info(
            f"Created promotion request {approval.id} for runbook {runbook_id} "
            f"version {version.version_number}"
        )
        
        return approval
    
    def approve_promotion(
        self,
        db: Session,
        approval_id: int,
        approved_by: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Approve and execute promotion
        
        Args:
            db: Database session
            approval_id: Approval ID
            approved_by: User ID approving
            tenant_id: Tenant ID
            
        Returns:
            Result dictionary
        """
        approval = db.query(DeploymentApproval).filter(
            DeploymentApproval.id == approval_id
        ).first()
        
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "pending":
            raise ValueError(f"Approval {approval_id} is not pending")
        
        # Get metadata
        metadata = approval.approval_metadata or {}
        runbook_id = approval.reference_id
        version_id = metadata.get("version_id")
        
        if not version_id:
            raise ValueError("Version ID not found in approval metadata")
        
        # Verify runbook belongs to tenant
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Promote version
        promoted_runbook = self.versioning_service.promote_version(
            db=db,
            runbook_id=runbook_id,
            version_id=version_id,
            target_environment=approval.target_environment,
            approved_by=approved_by,
            approval_id=approval_id,
            tenant_id=tenant_id
        )
        
        # Update approval
        approval.status = "approved"
        approval.approved_by = approved_by
        approval.approved_at = datetime.now(timezone.utc)
        approval.deployed_at = datetime.now(timezone.utc)
        approval.deployment_log = f"Promoted to {approval.target_environment} successfully"
        
        db.commit()
        
        logger.info(
            f"Approved and deployed promotion {approval_id} for runbook {runbook_id}"
        )
        
        return {
            "approval_id": approval.id,
            "runbook_id": runbook_id,
            "version_id": version_id,
            "status": "deployed",
            "deployed_at": approval.deployed_at.isoformat() if approval.deployed_at else None
        }
    
    def reject_promotion(
        self,
        db: Session,
        approval_id: int,
        rejected_by: int,
        reason: str,
        tenant_id: int
    ) -> DeploymentApproval:
        """
        Reject promotion request
        
        Args:
            db: Database session
            approval_id: Approval ID
            rejected_by: User ID rejecting
            reason: Rejection reason
            tenant_id: Tenant ID
            
        Returns:
            Updated DeploymentApproval object
        """
        approval = db.query(DeploymentApproval).filter(
            DeploymentApproval.id == approval_id
        ).first()
        
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "pending":
            raise ValueError(f"Approval {approval_id} is not pending")
        
        # Update approval
        approval.status = "rejected"
        approval.approved_by = rejected_by  # Using approved_by field for rejector
        approval.rejected_at = datetime.now(timezone.utc)
        approval.rejection_reason = reason
        
        db.commit()
        db.refresh(approval)
        
        logger.info(
            f"Rejected promotion {approval_id}: {reason}"
        )
        
        return approval
    
    def get_pending_approvals(
        self,
        db: Session,
        tenant_id: int,
        limit: int = 50
    ) -> List[DeploymentApproval]:
        """
        Get pending approval requests
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            limit: Maximum number of results
            
        Returns:
            List of DeploymentApproval objects
        """
        # Get runbook IDs for tenant
        runbook_ids = [r.id for r in db.query(Runbook.id).filter(
            Runbook.tenant_id == tenant_id
        ).all()]
        
        if not runbook_ids:
            return []
        
        return db.query(DeploymentApproval).filter(
            DeploymentApproval.deployment_type == "runbook",
            DeploymentApproval.reference_id.in_(runbook_ids),
            DeploymentApproval.status == "pending"
        ).order_by(DeploymentApproval.created_at.desc()).limit(limit).all()
