"""
Super Admin endpoints - Platform-level management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.services.super_admin_auth import get_current_super_admin
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger
from app.controllers.super_admin_controller import get_super_admin_controller

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class TenantCreate(BaseModel):
    name: str
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    deployment_type: str = "saas"
    is_active: bool = True
    is_msp: bool = False
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_msp: Optional[bool] = None
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
    is_msp: bool
    contact_email: Optional[str]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    created_at: str
    updated_at: Optional[str]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"
    role_id: Optional[int] = None
    must_change_password: Optional[bool] = False


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    role_id: Optional[int]
    role_name: Optional[str]
    is_active: bool
    must_change_password: Optional[bool] = False
    last_login: Optional[str]
    created_at: str


@router.get("/overview")
async def get_overview(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get platform overview statistics"""
    try:
        return get_super_admin_controller(db).get_overview()
    except Exception as e:
        logger.error(f"Error fetching overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview: {str(e)}")


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
        return get_super_admin_controller(db).list_tenants(skip, limit, is_active, deployment_type)
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
        return get_super_admin_controller(db).get_tenant(tenant_id)
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
        return get_super_admin_controller(db, current_admin.email).create_tenant(tenant_data)
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
        return get_super_admin_controller(db, current_admin.email).update_tenant(tenant_id, tenant_data)
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
        return get_super_admin_controller(db, current_admin.email).delete_tenant(tenant_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete tenant: {str(e)}")


@router.get("/tenants/{tenant_id}/users", response_model=List[UserResponse])
async def list_tenant_users(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all users for a tenant"""
    try:
        return get_super_admin_controller(db).list_tenant_users(tenant_id)
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
        return get_super_admin_controller(db, current_admin.email).create_tenant_user(tenant_id, user_data)
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
        return get_super_admin_controller(db, current_admin.email).update_tenant_user(tenant_id, user_id, user_data)
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
        return get_super_admin_controller(db, current_admin.email).delete_tenant_user(tenant_id, user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.post("/tenants/{tenant_id}/users/{user_id}/unlock")
async def unlock_user(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Unlock a user account"""
    try:
        return get_super_admin_controller(db, current_admin.email).unlock_user(tenant_id, user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlocking user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to unlock user: {str(e)}")
