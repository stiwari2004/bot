"""
Repository for credential data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.credential import Credential
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class CredentialRepository(BaseRepository[Credential]):
    """Repository for credential CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(Credential, db)
    
    def get_by_tenant(self, tenant_id: int, environment: Optional[str] = None) -> List[Credential]:
        """Get all credentials for a tenant, optionally filtered by environment"""
        query = self.db.query(Credential).filter(Credential.tenant_id == tenant_id)
        if environment:
            query = query.filter(Credential.environment == environment)
        return query.all()
    
    def get_by_id_and_tenant(self, credential_id: int, tenant_id: int) -> Optional[Credential]:
        """Get credential by ID and tenant"""
        return self.db.query(Credential).filter(
            Credential.id == credential_id,
            Credential.tenant_id == tenant_id
        ).first()




