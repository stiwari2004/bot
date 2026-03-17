"""
VersioningController
Handles HTTP requests for runbook versioning operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.runbook_repository import RunbookRepository
from app.services.runbook.versioning_service import VersioningService
from app.core.logging import get_logger

logger = get_logger(__name__)


class VersioningController(BaseController):
    """Controller for runbook versioning operations"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.versioning_service = VersioningService()
    
    def create_version(
        self,
        runbook_id: int,
        change_summary: str,
        change_type: str,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new version of a runbook
        
        Args:
            runbook_id: Runbook ID
            change_summary: Summary of changes
            change_type: Type of change ('major', 'minor', 'patch', 'custom')
            created_by: User ID creating the version
            
        Returns:
            Version creation result
        """
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            version = self.versioning_service.create_version(
                db=self.db,
                runbook_id=runbook_id,
                change_summary=change_summary,
                change_type=change_type,
                created_by=created_by,
                tenant_id=self.tenant_id
            )
            
            return {
                "version_id": version.id,
                "runbook_id": runbook_id,
                "version_number": version.version_number,
                "change_summary": version.change_summary,
                "change_type": version.change_type,
                "message": "Version created successfully"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating version for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to create version")
    
    def get_version_history(
        self,
        runbook_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a runbook
        
        Args:
            runbook_id: Runbook ID
            limit: Maximum number of versions
            
        Returns:
            List of version dictionaries
        """
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            versions = self.versioning_service.get_version_history(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                limit=limit
            )
            
            return [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "change_summary": v.change_summary,
                    "change_type": v.change_type,
                    "is_current": v.is_current == "true",
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "created_by": v.created_by
                }
                for v in versions
            ]
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting version history for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get version history")
    
    def compare_versions(
        self,
        version_id_1: int,
        version_id_2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions
        
        Args:
            version_id_1: First version ID
            version_id_2: Second version ID
            
        Returns:
            Comparison result with diff
        """
        try:
            comparison = self.versioning_service.compare_versions(
                db=self.db,
                version_id_1=version_id_1,
                version_id_2=version_id_2,
                tenant_id=self.tenant_id
            )
            
            return comparison
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error comparing versions {version_id_1} and {version_id_2}: {e}")
            raise self.handle_error(e, "Failed to compare versions")
    
    def rollback_version(
        self,
        runbook_id: int,
        version_id: int,
        reason: str,
        rolled_back_by: int
    ) -> Dict[str, Any]:
        """
        Rollback to a previous version
        
        Args:
            runbook_id: Runbook ID
            version_id: Version ID to rollback to
            reason: Reason for rollback
            rolled_back_by: User ID initiating rollback
            
        Returns:
            Rollback result
        """
        try:
            runbook = self.versioning_service.rollback_version(
                db=self.db,
                runbook_id=runbook_id,
                version_id=version_id,
                reason=reason,
                rolled_back_by=rolled_back_by,
                tenant_id=self.tenant_id
            )
            
            return {
                "runbook_id": runbook_id,
                "version_id": version_id,
                "message": "Rollback completed successfully"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error rolling back runbook {runbook_id} to version {version_id}: {e}")
            raise self.handle_error(e, "Failed to rollback version")
