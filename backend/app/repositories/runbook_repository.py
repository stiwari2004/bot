"""
Repository for runbook data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from app.models.runbook import Runbook
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger
from app.core.performance import QueryOptimizer

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
        active_only: bool = True,
        environment: Optional[str] = None
    ) -> List[Runbook]:
        """Get all runbooks for a tenant with pagination and eager loading"""
        try:
            query = self.db.query(Runbook).filter(Runbook.tenant_id == tenant_id)
            
            # Eager load tenant relationship to prevent N+1 queries
            query = query.options(joinedload(Runbook.tenant))
            
            if active_only:
                query = query.filter(Runbook.is_active == "active")
            
            # Filter by environment if specified
            if environment:
                query = query.filter(Runbook.environment == environment)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting runbooks by tenant: {e}", exc_info=True)
            return []
    
    def get_by_id_and_tenant(
        self,
        runbook_id: int,
        tenant_id: int,
        environment: Optional[str] = None
    ) -> Optional[Runbook]:
        """Get runbook by ID and tenant with eager loading"""
        query = self.db.query(Runbook).filter(
            and_(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            )
        )
        
        # Eager load tenant relationship
        query = query.options(joinedload(Runbook.tenant))
        
        # Filter by environment if specified
        if environment:
            query = query.filter(Runbook.environment == environment)
        
        return query.first()
    
    def get_approved_by_id_and_tenant(
        self,
        runbook_id: int,
        tenant_id: int,
        environment: Optional[str] = None
    ) -> Optional[Runbook]:
        """Get approved runbook by ID and tenant with eager loading"""
        query = self.db.query(Runbook).filter(
            and_(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id,
                Runbook.status == "approved"
            )
        )
        
        # Eager load tenant relationship
        query = query.options(joinedload(Runbook.tenant))
        
        # Filter by environment if specified (default to production for approved runbooks)
        if environment:
            query = query.filter(Runbook.environment == environment)
        else:
            # Default to production for approved runbooks
            query = query.filter(Runbook.environment == "production")
        
        return query.first()
    
    def get_active_by_tenant(self, tenant_id: int, environment: Optional[str] = None) -> List[Runbook]:
        """Get all active runbooks for duplicate checking"""
        query = self.db.query(Runbook).filter(
            Runbook.tenant_id == tenant_id,
            Runbook.is_active == "active"
        )
        
        # Filter by environment if specified
        if environment:
            query = query.filter(Runbook.environment == environment)
        
        return query.all()
    
    def archive(self, runbook_id: int, tenant_id: int) -> bool:
        """Archive a runbook (soft delete)"""
        runbook = self.get_by_id_and_tenant(runbook_id, tenant_id)
        if runbook:
            runbook.is_active = "archived"
            self.db.commit()
            self.db.refresh(runbook)
            return True
        return False


