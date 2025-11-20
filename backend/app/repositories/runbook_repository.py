"""
Repository for runbook data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.runbook import Runbook
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookRepository(BaseRepository[Runbook]):
    """Repository for runbook CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(Runbook, db)
    
    def get_by_tenant(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[Runbook]:
        """Get all runbooks for a tenant with pagination"""
        try:
            query = self.db.query(Runbook).filter(Runbook.tenant_id == tenant_id)
            
            if active_only:
                query = query.filter(Runbook.is_active == "active")
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting runbooks by tenant: {e}", exc_info=True)
            return []
    
    def get_by_id_and_tenant(
        self,
        runbook_id: int,
        tenant_id: int
    ) -> Optional[Runbook]:
        """Get runbook by ID and tenant"""
        return self.db.query(Runbook).filter(
            and_(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            )
        ).first()
    
    def get_active_by_tenant(self, tenant_id: int) -> List[Runbook]:
        """Get all active runbooks for duplicate checking"""
        return self.db.query(Runbook).filter(
            Runbook.tenant_id == tenant_id,
            Runbook.is_active == "active"
        ).all()
    
    def archive(self, runbook_id: int, tenant_id: int) -> bool:
        """Archive a runbook (soft delete)"""
        runbook = self.get_by_id_and_tenant(runbook_id, tenant_id)
        if runbook:
            runbook.is_active = "archived"
            self.db.commit()
            self.db.refresh(runbook)
            return True
        return False


