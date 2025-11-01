"""
Seed data for development
"""
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_password_hash
from app.core.logging import get_logger

logger = get_logger(__name__)


def seed_default_data(db: Session):
    """Create default tenant and user for development"""
    
    # Create default tenant
    default_tenant = db.query(Tenant).filter(Tenant.name == "default").first()
    if not default_tenant:
        default_tenant = Tenant(
            name="default",
            description="Default tenant for development",
            is_active=True
        )
        db.add(default_tenant)
        db.commit()
        db.refresh(default_tenant)
        logger.info(f"Created default tenant: {default_tenant.id}")
    
    # Create default user
    default_user = db.query(User).filter(User.email == "admin@example.com").first()
    if not default_user:
        default_user = User(
            tenant_id=default_tenant.id,
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        logger.info(f"Created default user: {default_user.email}")
    
    return default_tenant, default_user
