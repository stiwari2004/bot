"""
Infrastructure State Management Service
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.provisioning_project import ProvisioningProject
from app.models.provisioned_resource import ProvisionedResource

logger = get_logger(__name__)


class StateService:
    """Service for managing infrastructure state"""
    
    def __init__(self):
        pass
    
    async def save_state(
        self,
        project_id: int,
        state_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Save infrastructure state"""
        try:
            project = db.query(ProvisioningProject).filter(
                ProvisioningProject.id == project_id
            ).first()
            
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            project.terraform_state = state_data
            db.commit()
            
            return {
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_state(
        self,
        project_id: int,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Get infrastructure state"""
        try:
            project = db.query(ProvisioningProject).filter(
                ProvisioningProject.id == project_id
            ).first()
            
            if not project:
                return None
            
            return project.terraform_state
            
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return None
    
    async def detect_drift(
        self,
        project_id: int,
        current_state: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Detect drift between expected state and current state
        
        Args:
            project_id: Project ID
            current_state: Current infrastructure state
            db: Database session
            
        Returns:
            Dict with drift information
        """
        try:
            expected_state = await self.get_state(project_id, db)
            
            if not expected_state:
                return {
                    "success": False,
                    "error": "No expected state found"
                }
            
            # Simple drift detection - compare resource IDs
            expected_resources = set()
            current_resources = set()
            
            # Extract resource IDs from expected state (Terraform format)
            if isinstance(expected_state, dict):
                resources = expected_state.get("resources", [])
                for resource in resources:
                    if isinstance(resource, dict):
                        resource_id = resource.get("id") or resource.get("resource_id")
                        if resource_id:
                            expected_resources.add(str(resource_id))
            
            # Extract resource IDs from current state
            if isinstance(current_state, dict):
                resources = current_state.get("resources", [])
                for resource in resources:
                    if isinstance(resource, dict):
                        resource_id = resource.get("id") or resource.get("resource_id")
                        if resource_id:
                            current_resources.add(str(resource_id))
            
            # Find differences
            missing_resources = expected_resources - current_resources
            extra_resources = current_resources - expected_resources
            
            has_drift = len(missing_resources) > 0 or len(extra_resources) > 0
            
            return {
                "success": True,
                "has_drift": has_drift,
                "missing_resources": list(missing_resources),
                "extra_resources": list(extra_resources),
                "drift_summary": {
                    "missing_count": len(missing_resources),
                    "extra_count": len(extra_resources)
                }
            }
            
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def lock_state(
        self,
        project_id: int,
        lock_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Lock state for exclusive access"""
        # TODO: Implement state locking mechanism
        # This would typically use a distributed lock (Redis, etc.)
        logger.info(f"State lock requested for project {project_id} with lock_id {lock_id}")
        return {
            "success": True,
            "locked": True
        }
    
    async def unlock_state(
        self,
        project_id: int,
        lock_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Unlock state"""
        # TODO: Implement state unlocking
        logger.info(f"State unlock requested for project {project_id} with lock_id {lock_id}")
        return {
            "success": True,
            "locked": False
        }

