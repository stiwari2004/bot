"""
DeploymentApprovalController
Handles HTTP requests for deployment approval operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.models.deployment_approval import DeploymentApproval
from app.services.deployment.deployment_approval_service import DeploymentApprovalService
from app.core.logging import get_logger

logger = get_logger(__name__)


class DeploymentApprovalController(BaseController):
    """Controller for deployment approval operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.approval_service = DeploymentApprovalService()
    
    def request_promotion(
        self,
        runbook_id: int,
        version_id: int,
        requested_by: int,
        target_environment: str = "production"
    ) -> Dict[str, Any]:
        """
        Request promotion of a runbook version
        
        Args:
            runbook_id: Runbook ID
            version_id: Version ID to promote
            requested_by: User ID requesting
            target_environment: Target environment
            
        Returns:
            Approval request result
        """
        try:
            approval = self.approval_service.request_promotion(
                db=self.db,
                runbook_id=runbook_id,
                version_id=version_id,
                requested_by=requested_by,
                tenant_id=self.tenant_id,
                target_environment=target_environment
            )
            
            return {
                "approval_id": approval.id,
                "runbook_id": runbook_id,
                "version_id": version_id,
                "status": approval.status,
                "target_environment": approval.target_environment,
                "message": "Promotion request created successfully"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error requesting promotion for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to request promotion")
    
    def approve_promotion(
        self,
        approval_id: int,
        approved_by: int
    ) -> Dict[str, Any]:
        """
        Approve and execute promotion
        
        Args:
            approval_id: Approval ID
            approved_by: User ID approving
            
        Returns:
            Approval result
        """
        try:
            result = self.approval_service.approve_promotion(
                db=self.db,
                approval_id=approval_id,
                approved_by=approved_by,
                tenant_id=self.tenant_id
            )
            
            return result
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error approving promotion {approval_id}: {e}")
            raise self.handle_error(e, "Failed to approve promotion")
    
    def reject_promotion(
        self,
        approval_id: int,
        rejected_by: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Reject promotion request
        
        Args:
            approval_id: Approval ID
            rejected_by: User ID rejecting
            reason: Rejection reason
            
        Returns:
            Rejection result
        """
        try:
            approval = self.approval_service.reject_promotion(
                db=self.db,
                approval_id=approval_id,
                rejected_by=rejected_by,
                reason=reason,
                tenant_id=self.tenant_id
            )
            
            return {
                "approval_id": approval.id,
                "status": approval.status,
                "rejection_reason": approval.rejection_reason,
                "message": "Promotion rejected successfully"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error rejecting promotion {approval_id}: {e}")
            raise self.handle_error(e, "Failed to reject promotion")
    
    def get_pending_approvals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get pending approval requests
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of approval dictionaries
        """
        try:
            approvals = self.approval_service.get_pending_approvals(
                db=self.db,
                tenant_id=self.tenant_id,
                limit=limit
            )
            
            return [
                {
                    "id": a.id,
                    "runbook_id": a.reference_id,
                    "runbook_name": a.reference_name,
                    "target_environment": a.target_environment,
                    "status": a.status,
                    "requested_by": a.requested_by,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "metadata": a.approval_metadata
                }
                for a in approvals
            ]
        
        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            raise self.handle_error(e, "Failed to get pending approvals")
