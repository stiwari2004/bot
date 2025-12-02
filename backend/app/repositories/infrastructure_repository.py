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
    
    def create_connection(
        self,
        tenant_id: int,
        credential_id: Optional[int],
        name: str,
        connection_type: str,
        target_host: Optional[str],
        target_port: Optional[int],
        target_service: Optional[str],
        environment: str,
        meta_data: Optional[str],
        is_active: bool = True
    ) -> InfrastructureConnection:
        """Create a new infrastructure connection"""
        connection = InfrastructureConnection(
            tenant_id=tenant_id,
            credential_id=credential_id,
            name=name,
            connection_type=connection_type,
            target_host=target_host,
            target_port=target_port,
            target_service=target_service,
            environment=environment,
            meta_data=meta_data,
            is_active=is_active
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection
    
    def update_connection(
        self,
        connection_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[InfrastructureConnection]:
        """Update infrastructure connection fields"""
        connection = self.get_by_id_and_tenant(connection_id, tenant_id)
        if connection:
            for key, value in kwargs.items():
                setattr(connection, key, value)
            self.db.commit()
            self.db.refresh(connection)
        return connection




