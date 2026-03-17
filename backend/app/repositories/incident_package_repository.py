"""
Repository for incident package data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.incident_package import IncidentPackage
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class IncidentPackageRepository(BaseRepository[IncidentPackage]):
    """Repository for IncidentPackage CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(IncidentPackage, db)

    def get_latest_for_ticket(self, ticket_id: int, tenant_id: int) -> Optional[IncidentPackage]:
        """Get the most recently generated package for a ticket"""
        return self.db.query(IncidentPackage).filter(
            IncidentPackage.ticket_id == ticket_id,
            IncidentPackage.tenant_id == tenant_id,
        ).order_by(IncidentPackage.generated_at.desc()).first()

    def list_for_tenant(self, tenant_id: int, limit: int = 50) -> List[IncidentPackage]:
        """List all incident packages for a tenant"""
        return self.db.query(IncidentPackage).filter(
            IncidentPackage.tenant_id == tenant_id,
        ).order_by(IncidentPackage.generated_at.desc()).limit(limit).all()
