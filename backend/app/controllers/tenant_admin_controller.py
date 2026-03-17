"""
Tenant Admin Controller — MSP customer and subscription management
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.logging import get_logger
from app.repositories.tenant_repository import TenantRepository, UserRepository, SubscriptionRepository
from app.services.tenant_admin_auth import verify_tenant_access
from app.controllers.tenant_admin_customer_mixin import TenantAdminCustomerMixin
from app.controllers.tenant_admin_users_mixin import TenantAdminUsersMixin

logger = get_logger(__name__)


class TenantAdminController(TenantAdminCustomerMixin, TenantAdminUsersMixin):
    def __init__(self, db: Session, msp_tenant_id: int, admin_email: str = None):
        self.db = db
        self.msp_tenant_id = msp_tenant_id
        self.admin_email = admin_email
        self.tenant_repo = TenantRepository(db)
        self.user_repo = UserRepository(db)
        self.subscription_repo = SubscriptionRepository(db)

    def _check_access(self, customer_id: int):
        if not verify_tenant_access(self.msp_tenant_id, customer_id, self.db):
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only manage your own MSP tenant and its customers.",
            )

    def _format_customer(self, t) -> dict:
        return {
            "id": t.id, "name": t.name, "subdomain_slug": t.subdomain_slug,
            "description": t.description, "contact_email": t.contact_email,
            "is_active": t.is_active, "onboarding_status": t.onboarding_status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }


def get_tenant_admin_controller(db: Session, msp_tenant_id: int, admin_email: str = None) -> TenantAdminController:
    return TenantAdminController(db, msp_tenant_id, admin_email)
