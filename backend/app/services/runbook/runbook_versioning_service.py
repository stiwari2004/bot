"""
RunbookVersioningService
Business logic for runbook versioning and version management
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import re

from app.core.logging import get_logger
from app.models.runbook import Runbook
from app.models.runbook_version import RunbookVersion
from app.repositories.runbook_version_repository import RunbookVersionRepository

logger = get_logger(__name__)


class RunbookVersioningService:
    """Service for managing runbook versions"""
    
    def __init__(self):
        pass
    
    def _parse_version_number(self, version_str: str) -> tuple[int, int, int]:
        """Parse semantic version string (e.g., '1.2.3') into (major, minor, patch)"""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return 1, 0, 0
    
    def _increment_version(
        self,
        current_version: Optional[str],
        change_type: str = 'minor'
    ) -> str:
        """
        Increment version number based on change type
        
        Args:
            current_version: Current version string (e.g., '1.2.3')
            change_type: 'major', 'minor', 'patch'
            
        Returns:
            New version string
        """
        if not current_version:
            return "1.0.0"
        
        major, minor, patch = self._parse_version_number(current_version)
        
        if change_type == 'major':
            return f"{major + 1}.0.0"
        elif change_type == 'minor':
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    
    async def create_version(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        title: str,
        body_md: Optional[str] = None,
        body_yaml: Optional[str] = None,
        change_summary: Optional[str] = None,
        change_type: str = 'minor',
        created_by: Optional[int] = None
    ) -> RunbookVersion:
        """
        Create a new version of a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            title: Runbook title
            body_md: Markdown content
            body_yaml: YAML content
            change_summary: Summary of changes
            change_type: Type of change ('major', 'minor', 'patch')
            created_by: User ID who created the version
            
        Returns:
            Created RunbookVersion object
        """
        # Get current version
        repo = RunbookVersionRepository(db)
        current_version_obj = repo.get_current_version(runbook_id, tenant_id)
        
        # Determine parent version and version number
        if current_version_obj:
            parent_version_id = current_version_obj.id
            new_version_number = self._increment_version(
                current_version_obj.version_number,
                change_type
            )
            # Mark old version as not current
            current_version_obj.is_current = 'false'
            db.add(current_version_obj)
        else:
            # First version
            parent_version_id = None
            new_version_number = "1.0.0"
        
        # Get runbook to copy content if not provided
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Use provided content or copy from runbook
        version_body_md = body_md or runbook.body_md
        version_title = title or runbook.title
        
        # Create new version
        new_version = RunbookVersion(
            tenant_id=tenant_id,
            runbook_id=runbook_id,
            version_number=new_version_number,
            parent_version_id=parent_version_id,
            title=version_title,
            body_md=version_body_md,
            body_yaml=body_yaml,
            change_summary=change_summary,
            change_type=change_type,
            created_by=created_by,
            is_current='true',
        )
        
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        
        logger.info(
            f"Created version {new_version_number} for runbook {runbook_id} "
            f"(change_type={change_type})"
        )
        
        return new_version
    
    async def get_version_history(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a runbook
        
        Returns:
            List of version dictionaries
        """
        repo = RunbookVersionRepository(db)
        versions = repo.get_by_runbook(runbook_id, tenant_id)
        
        return [
            {
                "id": v.id,
                "version_number": v.version_number,
                "title": v.title,
                "change_summary": v.change_summary,
                "change_type": v.change_type,
                "is_current": v.is_current == 'true',
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": v.created_by,
                "parent_version_id": v.parent_version_id,
            }
            for v in versions
        ]
    
    async def get_version_diff(
        self,
        db: Session,
        runbook_id: int,
        version_id_1: int,
        version_id_2: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Get diff between two versions
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            version_id_1: First version ID
            version_id_2: Second version ID
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with diff information
        """
        repo = RunbookVersionRepository(db)
        version1 = repo.get(version_id_1)
        version2 = repo.get(version_id_2)
        
        if not version1 or not version2:
            raise ValueError("One or both versions not found")
        
        if version1.runbook_id != runbook_id or version2.runbook_id != runbook_id:
            raise ValueError("Versions do not belong to the specified runbook")
        
        if version1.tenant_id != tenant_id or version2.tenant_id != tenant_id:
            raise ValueError("Versions do not belong to the specified tenant")
        
        # Simple diff (can be enhanced with proper diff algorithm)
        body1 = version1.body_md or ""
        body2 = version2.body_md or ""
        
        # Calculate simple differences
        lines1 = body1.split('\n')
        lines2 = body2.split('\n')
        
        added_lines = [line for line in lines2 if line not in lines1]
        removed_lines = [line for line in lines1 if line not in lines2]
        
        return {
            "version1": {
                "id": version1.id,
                "version_number": version1.version_number,
                "title": version1.title,
            },
            "version2": {
                "id": version2.id,
                "version_number": version2.version_number,
                "title": version2.title,
            },
            "changes": {
                "added_lines": added_lines[:50],  # Limit to first 50
                "removed_lines": removed_lines[:50],
                "total_lines_v1": len(lines1),
                "total_lines_v2": len(lines2),
            },
            "summary": {
                "lines_added": len(added_lines),
                "lines_removed": len(removed_lines),
                "net_change": len(lines2) - len(lines1),
            }
        }
    
    async def set_current_version(
        self,
        db: Session,
        version_id: int,
        tenant_id: int
    ) -> RunbookVersion:
        """
        Set a version as the current version
        
        Args:
            db: Database session
            version_id: Version ID to set as current
            tenant_id: Tenant ID
            
        Returns:
            Updated RunbookVersion
        """
        repo = RunbookVersionRepository(db)
        version = repo.get(version_id)
        
        if not version or version.tenant_id != tenant_id:
            raise ValueError("Version not found or access denied")
        
        # Unset current flag on all versions for this runbook
        all_versions = repo.get_by_runbook(version.runbook_id, tenant_id)
        for v in all_versions:
            if v.is_current == 'true':
                v.is_current = 'false'
                db.add(v)
        
        # Set this version as current
        version.is_current = 'true'
        db.add(version)
        db.commit()
        db.refresh(version)
        
        logger.info(f"Set version {version.version_number} as current for runbook {version.runbook_id}")
        
        return version








