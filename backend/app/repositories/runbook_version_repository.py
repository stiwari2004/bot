"""
RunbookVersionRepository
Data access layer for RunbookVersion model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.runbook_version import RunbookVersion


class RunbookVersionRepository(BaseRepository[RunbookVersion]):
    """Repository for RunbookVersion operations"""
    
    def __init__(self, db: Session):
        super().__init__(RunbookVersion, db)
    
    def get_by_runbook(
        self,
        runbook_id: int,
        tenant_id: Optional[int] = None
    ) -> List[RunbookVersion]:
        """Get all versions for a runbook, ordered by version number"""
        query = self.db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id
        )
        if tenant_id:
            query = query.filter(RunbookVersion.tenant_id == tenant_id)
        return query.order_by(RunbookVersion.created_at.desc()).all()
    
    def get_current_version(
        self,
        runbook_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[RunbookVersion]:
        """Get the current version of a runbook"""
        query = self.db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.is_current == 'true'
        )
        if tenant_id:
            query = query.filter(RunbookVersion.tenant_id == tenant_id)
        return query.first()
    
    def get_version_by_number(
        self,
        runbook_id: int,
        version_number: str,
        tenant_id: Optional[int] = None
    ) -> Optional[RunbookVersion]:
        """Get a specific version by version number"""
        query = self.db.query(RunbookVersion).filter(
            RunbookVersion.runbook_id == runbook_id,
            RunbookVersion.version_number == version_number
        )
        if tenant_id:
            query = query.filter(RunbookVersion.tenant_id == tenant_id)
        return query.first()
    
    def get_version_chain(
        self,
        version_id: int,
        tenant_id: Optional[int] = None
    ) -> List[RunbookVersion]:
        """Get the full version chain (parent -> child) for a version"""
        version = self.get(version_id)
        if not version:
            return []
        
        chain = [version]
        
        # Get parent versions
        current = version
        while current.parent_version_id:
            parent = self.get(current.parent_version_id)
            if parent and (not tenant_id or parent.tenant_id == tenant_id):
                chain.insert(0, parent)
                current = parent
            else:
                break
        
        # Get child versions
        current = version
        while True:
            children = self.db.query(RunbookVersion).filter(
                RunbookVersion.parent_version_id == current.id
            ).all()
            if children:
                child = children[0]  # Take first child (assuming linear versioning)
                if not tenant_id or child.tenant_id == tenant_id:
                    chain.append(child)
                    current = child
                else:
                    break
            else:
                break
        
        return chain








