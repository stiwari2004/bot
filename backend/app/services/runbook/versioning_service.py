"""
Versioning Service for runbook version management
Handles version creation, comparison, promotion, and rollback
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.runbook import Runbook
from app.models.runbook_version import RunbookVersion
from app.core.logging import get_logger
import difflib
import json

logger = get_logger(__name__)


class VersioningService:
    """Service for managing runbook versions"""
    
    def create_version(
        self,
        db: Session,
        runbook_id: int,
        change_summary: str,
        change_type: str,
        created_by: int,
        tenant_id: int
    ) -> RunbookVersion:
        """
        Create a new version of a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            change_summary: Human-readable summary of changes
            change_type: Type of change ('major', 'minor', 'patch', 'custom')
            created_by: User ID who created the version
            tenant_id: Tenant ID
            
        Returns:
            RunbookVersion object
        """
        # Get runbook
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Get current version
        current_version = self.get_current_version(db, runbook_id, tenant_id)
        
        # Calculate next version number
        if current_version:
            version_number = self._calculate_next_version(
                current_version.version_number,
                change_type
            )
            parent_version_id = current_version.id
        else:
            version_number = "1.0.0"
            parent_version_id = None
        
        # Generate diff if parent version exists
        diff_summary = None
        if current_version:
            diff_summary = self._generate_diff_summary(
                old_content=current_version.body_md or "",
                new_content=runbook.body_md or ""
            )
        
        # Create version
        version = RunbookVersion(
            tenant_id=tenant_id,
            runbook_id=runbook_id,
            version_number=version_number,
            parent_version_id=parent_version_id,
            title=runbook.title,
            body_md=runbook.body_md,
            body_yaml=self._extract_yaml_from_markdown(runbook.body_md) if runbook.body_md else None,
            change_summary=change_summary,
            change_type=change_type,
            diff_summary=diff_summary,
            created_by=created_by,
            is_current='false'  # New versions are not current until promoted
        )
        
        db.add(version)
        db.commit()
        db.refresh(version)
        
        logger.info(
            f"Created version {version_number} for runbook {runbook_id} "
            f"(type: {change_type})"
        )
        
        return version
    
    def compare_versions(
        self,
        db: Session,
        version_id_1: int,
        version_id_2: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Compare two versions and generate diff
        
        Args:
            db: Database session
            version_id_1: First version ID
            version_id_2: Second version ID
            tenant_id: Tenant ID
            
        Returns:
            Comparison dictionary with diff details
        """
        version1 = db.query(RunbookVersion).filter(
            RunbookVersion.id == version_id_1,
            RunbookVersion.tenant_id == tenant_id
        ).first()
        
        version2 = db.query(RunbookVersion).filter(
            RunbookVersion.id == version_id_2,
            RunbookVersion.tenant_id == tenant_id
        ).first()
        
        if not version1 or not version2:
            raise ValueError("One or both versions not found")
        
        if version1.runbook_id != version2.runbook_id:
            raise ValueError("Versions must belong to the same runbook")
        
        # Generate diff
        diff_summary = self._generate_diff_summary(
            old_content=version1.body_md or "",
            new_content=version2.body_md or ""
        )
        
        return {
            "version1": {
                "id": version1.id,
                "version_number": version1.version_number,
                "created_at": version1.created_at.isoformat() if version1.created_at else None,
                "change_summary": version1.change_summary
            },
            "version2": {
                "id": version2.id,
                "version_number": version2.version_number,
                "created_at": version2.created_at.isoformat() if version2.created_at else None,
                "change_summary": version2.change_summary
            },
            "diff": diff_summary
        }
    
    def promote_version(
        self,
        db: Session,
        runbook_id: int,
        version_id: int,
        target_environment: str,
        approved_by: int,
        approval_id: Optional[int],
        tenant_id: int
    ) -> Runbook:
        """
        Promote a version to target environment
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            version_id: Version ID to promote
            target_environment: Target environment ('production', 'staging', etc.)
            approved_by: User ID who approved
            approval_id: Optional deployment approval ID
            tenant_id: Tenant ID
            
        Returns:
            Updated Runbook object
        """
        # Get version
        version = db.query(RunbookVersion).filter(
            RunbookVersion.id == version_id,
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id
        ).first()
        
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        # Get runbook
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Update runbook to match version
        runbook.title = version.title
        runbook.body_md = version.body_md
        runbook.environment = target_environment
        
        # Update version links
        if target_environment == "production":
            runbook.promoted_from_id = runbook_id if runbook.runbook_id != runbook_id else None
            runbook.promoted_at = datetime.now(timezone.utc)
        
        # Mark this version as current for the environment
        # Unmark other versions
        db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id
        ).update({"is_current": "false"})
        
        version.is_current = "true"
        version.deployment_approval_id = approval_id
        
        db.commit()
        db.refresh(runbook)
        
        logger.info(
            f"Promoted version {version.version_number} of runbook {runbook_id} "
            f"to {target_environment}"
        )
        
        return runbook
    
    def rollback_version(
        self,
        db: Session,
        runbook_id: int,
        version_id: int,
        reason: str,
        rolled_back_by: int,
        tenant_id: int
    ) -> Runbook:
        """
        Rollback to a previous version
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            version_id: Version ID to rollback to
            reason: Reason for rollback
            rolled_back_by: User ID who initiated rollback
            tenant_id: Tenant ID
            
        Returns:
            Updated Runbook object
        """
        # Get target version
        target_version = db.query(RunbookVersion).filter(
            RunbookVersion.id == version_id,
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id
        ).first()
        
        if not target_version:
            raise ValueError(f"Version {version_id} not found")
        
        # Get current version
        current_version = self.get_current_version(db, runbook_id, tenant_id)
        
        # Create new version from target (rollback creates a new version)
        rollback_version = RunbookVersion(
            tenant_id=tenant_id,
            runbook_id=runbook_id,
            version_number=self._calculate_next_version(
                current_version.version_number if current_version else "1.0.0",
                "patch"
            ),
            parent_version_id=current_version.id if current_version else None,
            title=target_version.title,
            body_md=target_version.body_md,
            body_yaml=target_version.body_yaml,
            change_summary=f"Rollback to version {target_version.version_number}: {reason}",
            change_type="rollback",
            rollback_reason=reason,
            created_by=rolled_back_by,
            is_current="true"
        )
        
        # Unmark current version
        if current_version:
            current_version.is_current = "false"
        
        # Update runbook
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if runbook:
            runbook.title = target_version.title
            runbook.body_md = target_version.body_md
        
        db.add(rollback_version)
        db.commit()
        db.refresh(runbook)
        
        logger.info(
            f"Rolled back runbook {runbook_id} to version {target_version.version_number}"
        )
        
        return runbook
    
    def get_version_history(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        limit: int = 50
    ) -> List[RunbookVersion]:
        """
        Get version history for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            limit: Maximum number of versions
            
        Returns:
            List of RunbookVersion objects
        """
        return db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id
        ).order_by(RunbookVersion.created_at.desc()).limit(limit).all()
    
    def get_current_version(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        environment: Optional[str] = None
    ) -> Optional[RunbookVersion]:
        """
        Get current version for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            environment: Optional environment filter
            
        Returns:
            Current RunbookVersion or None
        """
        query = db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.tenant_id == tenant_id,
            RunbookVersion.is_current == "true"
        )
        
        return query.first()
    
    def _calculate_next_version(self, current_version: str, change_type: str) -> str:
        """Calculate next version number based on change type"""
        try:
            parts = current_version.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            if change_type == "major":
                return f"{major + 1}.0.0"
            elif change_type == "minor":
                return f"{major}.{minor + 1}.0"
            elif change_type == "patch":
                return f"{major}.{minor}.{patch + 1}"
            else:
                return f"{major}.{minor}.{patch + 1}"  # Default to patch
        except Exception:
            return "1.0.0"
    
    def _generate_diff_summary(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """Generate structured diff summary"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=3
        ))
        
        # Count changes
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return {
            "diff_lines": diff[:100],  # Limit to first 100 lines
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions,
            "has_changes": additions > 0 or deletions > 0
        }
    
    def _extract_yaml_from_markdown(self, markdown: str) -> Optional[str]:
        """Extract YAML block from markdown"""
        import re
        yaml_match = re.search(r'```yaml\n(.*?)\n```', markdown, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1)
        return None
