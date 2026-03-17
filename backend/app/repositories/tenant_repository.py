"""
Repository for tenant and user data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(Tenant, db)

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_customers_for_msp(self, msp_tenant_id: int) -> List[Tenant]:
        """Get all non-MSP customer tenants under an MSP"""
        return self.db.query(Tenant).filter(
            Tenant.parent_tenant_id == msp_tenant_id,
            Tenant.is_msp == False,
        ).all()

    def get_customer_by_id(self, customer_id: int, msp_tenant_id: int) -> Optional[Tenant]:
        """Get a customer tenant scoped to an MSP parent"""
        return self.db.query(Tenant).filter(
            Tenant.id == customer_id,
            Tenant.parent_tenant_id == msp_tenant_id,
        ).first()


class UserRepository(BaseRepository[User]):
    """Repository for User CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def list_for_tenant(self, tenant_id: int) -> List[User]:
        return self.db.query(User).filter(User.tenant_id == tenant_id).all()


class SubscriptionRepository:
    """Thin repository for TenantSubscription lookups"""

    def __init__(self, db: Session):
        self.db = db

    def get_for_tenant(self, tenant_id: int):
        """Get subscription for a tenant (returns None if not found)"""
        from app.models.tenant_subscription import TenantSubscription
        return self.db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == tenant_id,
        ).first()
