"""
Super Admin endpoints - Platform-level management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.super_admin_auth import get_current_super_admin
from app.services.auth import get_password_hash
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class TenantCreate(BaseModel):
    name: str
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    deployment_type: str = "saas"
    is_active: bool = True
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain_slug: Optional[str]
    description: Optional[str]
    deployment_type: str
    is_active: bool
    contact_email: Optional[str]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    created_at: str
    updated_at: Optional[str]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"  # Legacy role string
    role_id: Optional[int] = None  # New RBAC role ID
    must_change_password: Optional[bool] = False  # Force password change at next login


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None  # Legacy role string
    role_id: Optional[int] = None  # New RBAC role ID
    password: Optional[str] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None  # Force password change at next login


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str  # Legacy role string
    role_id: Optional[int]  # New RBAC role ID
    role_name: Optional[str]  # Role name from RBAC
    is_active: bool
    must_change_password: Optional[bool] = False
    last_login: Optional[str]
    created_at: str


# Overview endpoint
@router.get("/overview")
async def get_overview(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get platform overview statistics"""
    try:
        # Count tenants
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        
        # Count users - use raw SQL to avoid role_id column issues
        from sqlalchemy import text
        try:
            total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
            active_users = db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true")).scalar() or 0
        except Exception as e:
            logger.warning(f"Error counting users: {e}")
            total_users = 0
            active_users = 0
        
        # Count users by role (gracefully handle if role column doesn't exist)
        role_counts = {}
        try:
            users_by_role = db.query(
                User.role,
                func.count(User.id).label('count')
            ).group_by(User.role).all()
            role_counts = {role: count for role, count in users_by_role}
        except Exception as role_error:
            logger.warning(f"Could not fetch users by role: {role_error}")
            # Continue without role breakdown
        
        return {
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "inactive": total_tenants - active_tenants
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "by_role": role_counts
            }
        }
    except Exception as e:
        logger.error(f"Error fetching overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview: {str(e)}")


# Tenant management endpoints
@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    deployment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all tenants"""
    try:
        query = db.query(Tenant)
        
        if is_active is not None:
            query = query.filter(Tenant.is_active == is_active)
        if deployment_type:
            query = query.filter(Tenant.deployment_type == deployment_type)
        
        tenants = query.offset(skip).limit(limit).all()
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "subdomain_slug": t.subdomain_slug,
                "description": t.description,
                "deployment_type": t.deployment_type,
                "is_active": t.is_active,
                "contact_email": t.contact_email,
                "contact_name": t.contact_name,
                "contact_phone": t.contact_phone,
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tenants
        ]
    except Exception as e:
        logger.error(f"Error listing tenants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {str(e)}")


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get a specific tenant"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        return {
            "id": tenant.id,
            "name": tenant.name,
            "subdomain_slug": tenant.subdomain_slug,
            "description": tenant.description,
            "deployment_type": tenant.deployment_type,
            "is_active": tenant.is_active,
            "contact_email": tenant.contact_email,
            "contact_name": tenant.contact_name,
            "contact_phone": tenant.contact_phone,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tenant: {str(e)}")


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new tenant"""
    try:
        # Check if tenant name already exists
        existing = db.query(Tenant).filter(Tenant.name == tenant_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with name '{tenant_data.name}' already exists")
        
        # Check subdomain slug if provided
        if tenant_data.subdomain_slug:
            existing_slug = db.query(Tenant).filter(Tenant.subdomain_slug == tenant_data.subdomain_slug).first()
            if existing_slug:
                raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists")
        
        # Create tenant
        tenant = Tenant(
            name=tenant_data.name,
            subdomain_slug=tenant_data.subdomain_slug,
            description=tenant_data.description,
            deployment_type=tenant_data.deployment_type,
            is_active=tenant_data.is_active,
            contact_email=tenant_data.contact_email,
            contact_name=tenant_data.contact_name,
            contact_phone=tenant_data.contact_phone,
        )
        
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        logger.info(f"Super admin {current_admin.email} created tenant: {tenant.name} (ID: {tenant.id})")
        
        return {
            "id": tenant.id,
            "name": tenant.name,
            "subdomain_slug": tenant.subdomain_slug,
            "description": tenant.description,
            "deployment_type": tenant.deployment_type,
            "is_active": tenant.is_active,
            "contact_email": tenant.contact_email,
            "contact_name": tenant.contact_name,
            "contact_phone": tenant.contact_phone,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create tenant: {str(e)}")


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a tenant"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Update fields
        if tenant_data.name is not None:
            # Check if new name conflicts
            existing = db.query(Tenant).filter(
                Tenant.name == tenant_data.name,
                Tenant.id != tenant_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Tenant with name '{tenant_data.name}' already exists")
            tenant.name = tenant_data.name
        
        if tenant_data.subdomain_slug is not None:
            # Check if new slug conflicts
            existing = db.query(Tenant).filter(
                Tenant.subdomain_slug == tenant_data.subdomain_slug,
                Tenant.id != tenant_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists")
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
        
        db.commit()
        db.refresh(tenant)
        
        logger.info(f"Super admin {current_admin.email} updated tenant: {tenant.name} (ID: {tenant.id})")
        
        return {
            "id": tenant.id,
            "name": tenant.name,
            "subdomain_slug": tenant.subdomain_slug,
            "description": tenant.description,
            "deployment_type": tenant.deployment_type,
            "is_active": tenant.is_active,
            "contact_email": tenant.contact_email,
            "contact_name": tenant.contact_name,
            "contact_phone": tenant.contact_phone,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update tenant: {str(e)}")


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Delete (deactivate) a tenant"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Soft delete - deactivate instead of hard delete
        tenant.is_active = False
        db.commit()
        
        logger.info(f"Super admin {current_admin.email} deactivated tenant: {tenant.name} (ID: {tenant.id})")
        
        return {"message": f"Tenant '{tenant.name}' has been deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete tenant: {str(e)}")


# Tenant user management endpoints
@router.get("/tenants/{tenant_id}/users", response_model=List[UserResponse])
async def list_tenant_users(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all users for a tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Use raw SQL to avoid role_id column issues
        from sqlalchemy import text
        try:
            # Try to query with role_id column
            users = db.query(User).filter(User.tenant_id == tenant_id).all()
        except Exception as e:
            # If role_id doesn't exist, rollback the transaction and use raw SQL
            logger.warning(f"Error querying users (possibly missing role_id column): {e}")
            db.rollback()  # Rollback the aborted transaction
            user_rows = db.execute(
                text("SELECT id, email, full_name, role, is_active, last_login, created_at FROM users WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            ).fetchall()
            users = []
            for row in user_rows:
                # Create a simple object-like structure
                class SimpleUser:
                    def __init__(self, row):
                        self.id = row[0]
                        self.email = row[1]
                        self.full_name = row[2]
                        self.role = row[3]
                        self.role_id = None  # Not available
                        self.is_active = row[4]
                        self.last_login = row[5]
                        self.created_at = row[6]
                users.append(SimpleUser(row))
        
        result = []
        for u in users:
            # Load role relationship (gracefully handle if Role table doesn't exist)
            role_name = None
            try:
                if hasattr(u, 'role_id') and u.role_id and hasattr(u, 'role_obj') and u.role_obj:
                    role_name = u.role_obj.name
            except Exception:
                # Role relationship not available (table might not exist)
                pass
            
            result.append({
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "role_id": getattr(u, 'role_id', None),
                "role_name": role_name,
                "is_active": u.is_active,
                "must_change_password": getattr(u, 'must_change_password', False) or False,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tenant users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.post("/tenants/{tenant_id}/users", response_model=UserResponse)
async def create_tenant_user(
    tenant_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new user for a tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Check if user email already exists
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"User with email '{user_data.email}' already exists")
        
        # Validate role_id if provided
        if user_data.role_id:
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise HTTPException(status_code=400, detail=f"Role with ID {user_data.role_id} not found")
        
        # Create user
        user = User(
            tenant_id=tenant_id,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            role_id=user_data.role_id,
            is_active=True,
            must_change_password=user_data.must_change_password or False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Load role relationship
        role_name = None
        if user.role_obj:
            role_name = user.role_obj.name
        
        logger.info(f"Super admin {current_admin.email} created user: {user.email} for tenant: {tenant.name}")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "role_id": user.role_id,
            "role_name": role_name,
            "is_active": user.is_active,
            "must_change_password": user.must_change_password or False,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.put("/tenants/{tenant_id}/users/{user_id}", response_model=UserResponse)
async def update_tenant_user(
    tenant_id: int,
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a user for a tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get user
        user = db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.role_id is not None:
            # Validate role_id if provided
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                raise HTTPException(status_code=400, detail=f"Role with ID {user_data.role_id} not found")
            user.role_id = user_data.role_id
        if user_data.password is not None:
            user.password_hash = get_password_hash(user_data.password)
            # Clear must_change_password flag when password is manually changed by admin
            user.must_change_password = False
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.must_change_password is not None:
            user.must_change_password = user_data.must_change_password
        
        db.commit()
        db.refresh(user)
        
        # Load role relationship
        role_name = None
        if user.role_obj:
            role_name = user.role_obj.name
        
        logger.info(f"Super admin {current_admin.email} updated user: {user.email} for tenant: {tenant.name}")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "role_id": user.role_id,
            "role_name": role_name,
            "is_active": user.is_active,
            "must_change_password": user.must_change_password or False,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def delete_tenant_user(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Delete (deactivate) a user"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get user
        user = db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Soft delete - deactivate instead of hard delete
        user.is_active = False
        db.commit()
        
        logger.info(f"Super admin {current_admin.email} deactivated user: {user.email} for tenant: {tenant.name}")
        
        return {"message": f"User '{user.email}' has been deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

