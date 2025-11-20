"""
Repository for infrastructure connection data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.credential import InfrastructureConnection
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class InfrastructureRepository(BaseRepository[InfrastructureConnection]):
    """Repository for infrastructure connection CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(InfrastructureConnection, db)
    
    def get_by_tenant(self, tenant_id: int, environment: Optional[str] = None) -> List[InfrastructureConnection]:
        """Get all infrastructure connections for a tenant, optionally filtered by environment"""
        query = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        )
        if environment:
            query = query.filter(InfrastructureConnection.environment == environment)
        return query.all()
    
    def get_by_id_and_tenant(self, connection_id: int, tenant_id: int) -> Optional[InfrastructureConnection]:
        """Get infrastructure connection by ID and tenant"""
        return self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id
        ).first()




