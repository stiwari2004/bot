"""
Super Admin Controller — platform-level tenant and user management
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from fastapi import HTTPException

from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository
from app.services.auth import get_password_hash

logger = get_logger(__name__)


class SuperAdminController:
    def __init__(self, db: Session, admin_email: str = None):
        self.db = db
        self.admin_email = admin_email
        self.tenant_repo = TenantRepository(db)

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------
    def get_overview(self) -> dict:
        db = self.db
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()

        try:
            total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
            active_users = db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true")).scalar() or 0
        except Exception as e:
            logger.warning(f"Error counting users: {e}")
            total_users = 0
            active_users = 0

        role_counts = {}
        try:
            users_by_role = db.query(User.role, func.count(User.id).label("count")).group_by(User.role).all()
            role_counts = {role: count for role, count in users_by_role}
        except Exception as role_error:
            logger.warning(f"Could not fetch users by role: {role_error}")

        return {
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "inactive": total_tenants - active_tenants,
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "by_role": role_counts,
            },
        }

    # ------------------------------------------------------------------
    # Tenant management
    # ------------------------------------------------------------------
    def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        deployment_type: Optional[str] = None,
    ) -> List[dict]:
        db = self.db
        query = db.query(Tenant)
        if is_active is not None:
            query = query.filter(Tenant.is_active == is_active)
        if deployment_type:
            query = query.filter(Tenant.deployment_type == deployment_type)
        tenants = query.offset(skip).limit(limit).all()
        return [self._format_tenant(t) for t in tenants]

    def get_tenant(self, tenant_id: int) -> dict:
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return self._format_tenant(tenant)

    def create_tenant(self, tenant_data) -> dict:
        db = self.db
        existing = db.query(Tenant).filter(func.lower(Tenant.name) == func.lower(tenant_data.name)).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Tenant with name '{tenant_data.name}' already exists (ID: {existing.id})",
            )
        if tenant_data.subdomain_slug:
            existing_slug = db.query(Tenant).filter(
                func.lower(Tenant.subdomain_slug) == func.lower(tenant_data.subdomain_slug)
            ).first()
            if existing_slug:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists (ID: {existing_slug.id}, Name: {existing_slug.name})",
                )

        tenant = Tenant(
            name=tenant_data.name,
            subdomain_slug=tenant_data.subdomain_slug,
            description=tenant_data.description,
            deployment_type=tenant_data.deployment_type,
            is_active=tenant_data.is_active,
            is_msp=tenant_data.is_msp,
            contact_email=tenant_data.contact_email,
            contact_name=tenant_data.contact_name,
            contact_phone=tenant_data.contact_phone,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        logger.info(f"Super admin {self.admin_email} created tenant: {tenant.name} (ID: {tenant.id})")
        return self._format_tenant(tenant)

    def update_tenant(self, tenant_id: int, tenant_data) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if tenant_data.name is not None:
            conflict = db.query(Tenant).filter(Tenant.name == tenant_data.name, Tenant.id != tenant_id).first()
            if conflict:
                raise HTTPException(status_code=400, detail=f"Tenant with name '{tenant_data.name}' already exists")
            tenant.name = tenant_data.name

        if tenant_data.subdomain_slug is not None:
            conflict = db.query(Tenant).filter(
                Tenant.subdomain_slug == tenant_data.subdomain_slug, Tenant.id != tenant_id
            ).first()
            if conflict:
                raise HTTPException(
                    status_code=400, detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists"
                )
            tenant.subdomain_slug = tenant_data.subdomain_slug

        if tenant_data.description is not None:
            tenant.description = tenant_data.description
        if tenant_data.is_active is not None:
            tenant.is_active = tenant_data.is_active
        if tenant_data.contact_email is not None:
            tenant.contact_email = tenant_data.contact_email
        if tenant_data.contact_name is not None:
            tenant.contact_name = tenant_data.contact_name
        if tenant_data.contact_phone is not None:
            tenant.contact_phone = tenant_data.contact_phone
        if tenant_data.is_msp is not None:
            tenant.is_msp = tenant_data.is_msp

        db.commit()
        db.refresh(tenant)
        logger.info(f"Super admin {self.admin_email} updated tenant: {tenant.name} (ID: {tenant.id})")
        return self._format_tenant(tenant)

    def delete_tenant(self, tenant_id: int) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant.is_active = False
        db.commit()
        logger.info(f"Super admin {self.admin_email} deactivated tenant: {tenant.name} (ID: {tenant.id})")
        return {"message": f"Tenant '{tenant.name}' has been deactivated"}

    # ------------------------------------------------------------------
    # Tenant user management
    # ------------------------------------------------------------------
    def list_tenant_users(self, tenant_id: int) -> List[dict]:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        try:
            users = db.query(User).filter(User.tenant_id == tenant_id).all()
        except Exception as e:
            logger.warning(f"Error querying users (possibly missing role_id column): {e}")
            db.rollback()
            user_rows = db.execute(
                text("SELECT id, email, full_name, role, is_active, last_login, created_at FROM users WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).fetchall()

            class _SimpleUser:
                def __init__(self, row):
                    self.id = row[0]
                    self.email = row[1]
                    self.full_name = row[2]
                    self.role = row[3]
                    self.role_id = None
                    self.is_active = row[4]
                    self.last_login = row[5]
                    self.created_at = row[6]

            users = [_SimpleUser(r) for r in user_rows]

        return [self._format_user(u) for u in users]

    def create_tenant_user(self, tenant_id: int, user_data) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        existing = db.query(User).filter(func.lower(User.email) == func.lower(user_data.email)).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"User with email '{user_data.email}' already exists")

        if user_data.role_id:
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise HTTPException(status_code=400, detail=f"Role with ID {user_data.role_id} not found")

        user = User(
            tenant_id=tenant_id,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            role_id=user_data.role_id,
            is_active=True,
            must_change_password=user_data.must_change_password or False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Super admin {self.admin_email} created user: {user.email} for tenant: {tenant.name}")
        return self._format_user(user)

    def update_tenant_user(self, tenant_id: int, user_id: int, user_data) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.role_id is not None:
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise HTTPException(status_code=400, detail=f"Role with ID {user_data.role_id} not found")
            user.role_id = user_data.role_id
        if user_data.password is not None:
            user.password_hash = get_password_hash(user_data.password)
            user.must_change_password = False
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.must_change_password is not None:
            user.must_change_password = user_data.must_change_password

        db.commit()
        db.refresh(user)
        logger.info(f"Super admin {self.admin_email} updated user: {user.email} for tenant: {tenant.name}")
        return self._format_user(user)

    def delete_tenant_user(self, tenant_id: int, user_id: int) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = False
        db.commit()
        logger.info(f"Super admin {self.admin_email} deactivated user: {user.email} for tenant: {tenant.name}")
        return {"message": f"User '{user.email}' has been deactivated"}

    def unlock_user(self, tenant_id: int, user_id: int) -> dict:
        db = self.db
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.locked_until = None
        user.failed_login_attempts = 0
        user.last_failed_login_at = None
        db.commit()
        logger.info(f"Super admin {self.admin_email} unlocked user: {user.email} for tenant: {tenant.name}")
        return {"message": f"User '{user.email}' has been unlocked successfully"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _format_tenant(self, t) -> dict:
        return {
            "id": t.id,
            "name": t.name,
            "subdomain_slug": t.subdomain_slug,
            "description": t.description,
            "deployment_type": t.deployment_type,
            "is_active": t.is_active,
            "is_msp": getattr(t, "is_msp", False),
            "contact_email": t.contact_email,
            "contact_name": t.contact_name,
            "contact_phone": t.contact_phone,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    def _format_user(self, u) -> dict:
        role_name = None
        try:
            if hasattr(u, "role_id") and u.role_id and hasattr(u, "role_obj") and u.role_obj:
                role_name = u.role_obj.name
        except Exception:
            pass
        return {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "role_id": getattr(u, "role_id", None),
            "role_name": role_name,
            "is_active": u.is_active,
            "must_change_password": getattr(u, "must_change_password", False) or False,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }


def get_super_admin_controller(db: Session, admin_email: str = None) -> SuperAdminController:
    return SuperAdminController(db, admin_email)
