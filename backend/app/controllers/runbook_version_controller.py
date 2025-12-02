"""
RunbookVersionController
Handles HTTP requests for runbook versioning operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.runbook.runbook_versioning_service import RunbookVersioningService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookVersionController(BaseController):
    """Controller for runbook versioning operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.versioning_service = RunbookVersioningService()
    
    async def create_version(
        self,
        runbook_id: int,
        title: Optional[str] = None,
        body_md: Optional[str] = None,
        body_yaml: Optional[str] = None,
        change_summary: Optional[str] = None,
        change_type: str = 'minor',
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new version of a runbook
        
        Args:
            runbook_id: Runbook ID
            title: Runbook title
            body_md: Markdown content
            body_yaml: YAML content
            change_summary: Summary of changes
            change_type: Type of change ('major', 'minor', 'patch')
            created_by: User ID
            
        Returns:
            Created version information
        """
        try:
            version = await self.versioning_service.create_version(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                title=title or "",
                body_md=body_md,
                body_yaml=body_yaml,
                change_summary=change_summary,
                change_type=change_type,
                created_by=created_by
            )
            
            return {
                "id": version.id,
                "version_number": version.version_number,
                "title": version.title,
                "change_summary": version.change_summary,
                "change_type": version.change_type,
                "is_current": version.is_current == 'true',
                "created_at": version.created_at.isoformat() if version.created_at else None,
            }
        
        except Exception as e:
            logger.error(f"Error creating version for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to create version")
    
    async def get_version_history(
        self,
        runbook_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a runbook
        
        Args:
            runbook_id: Runbook ID
            
        Returns:
            List of versions
        """
        try:
            history = await self.versioning_service.get_version_history(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id
            )
            return history
        
        except Exception as e:
            logger.error(f"Error getting version history for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get version history")
    
    async def get_version_diff(
        self,
        runbook_id: int,
        version_id_1: int,
        version_id_2: int
    ) -> Dict[str, Any]:
        """
        Get diff between two versions
        
        Args:
            runbook_id: Runbook ID
            version_id_1: First version ID
            version_id_2: Second version ID
            
        Returns:
            Diff information
        """
        try:
            diff = await self.versioning_service.get_version_diff(
                db=self.db,
                runbook_id=runbook_id,
                version_id_1=version_id_1,
                version_id_2=version_id_2,
                tenant_id=self.tenant_id
            )
            return diff
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error getting version diff: {e}")
            raise self.handle_error(e, "Failed to get version diff")
    
    async def set_current_version(
        self,
        version_id: int
    ) -> Dict[str, Any]:
        """
        Set a version as current
        
        Args:
            version_id: Version ID
            
        Returns:
            Updated version information
        """
        try:
            version = await self.versioning_service.set_current_version(
                db=self.db,
                version_id=version_id,
                tenant_id=self.tenant_id
            )
            
            return {
                "id": version.id,
                "version_number": version.version_number,
                "is_current": version.is_current == 'true',
                "message": "Version set as current"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error setting current version: {e}")
            raise self.handle_error(e, "Failed to set current version")

