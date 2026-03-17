"""
Client Admin — user management endpoints
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_current_user, get_password_hash
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ── Shared auth dependency ────────────────────────────────────────────────────

def get_current_tenant_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Ensure the current user is a tenant admin."""
    db.refresh(current_user, ['tenant'])
    tenant = current_user.tenant
    if not tenant:
        raise HTTPException(status_code=403, detail="User has no associated tenant")
    is_tenant_admin = (
        current_user.role == "tenant_admin" or
        (current_user.role == "admin" and not tenant.is_msp)
    )
    if not is_tenant_admin:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Tenant admin role required. MSP admins should use /tenant-admin."
        )
    return current_user


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_nodes: int
    active_nodes: int
    pending_nodes: int


def _user_dict(u: User) -> dict:
    return {
        "id": u.id, "email": u.email, "full_name": u.full_name,
        "role": u.role, "is_active": u.is_active,
        "created_at": u.created_at, "last_login": u.last_login,
    }


def _sync_paas(tenant_id: int, user: User) -> None:
    try:
        from app.services.central_client import sync_users_for_billing
        sync_users_for_billing(tenant_id, [{
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "tenant_id": user.tenant_id, "node_details": None,
        }])
    except Exception as e:
        logger.warning("PaaS sync_users_for_billing failed: %s", e)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserResponse])
async def list_tenant_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """List all users in the tenant"""
    users = db.query(User).filter(User.tenant_id == current_admin.tenant_id).all()
    return [_user_dict(u) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_tenant_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Create a new user in the tenant"""
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    if user_data.role in ("admin", "tenant_admin", "msp_admin"):
        raise HTTPException(status_code=403, detail="Tenant admins cannot create other admin users")

    new_user = User(
        tenant_id=current_admin.tenant_id,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    _sync_paas(current_admin.tenant_id, new_user)
    return _user_dict(new_user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_tenant_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get a specific user in the tenant"""
    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_dict(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_tenant_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Update a user in the tenant"""
    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == current_admin.id:
        if user_data.role and user_data.role != user.role:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        if user_data.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    if user_data.role in ("admin", "tenant_admin", "msp_admin") and user.id != current_admin.id:
        raise HTTPException(status_code=403, detail="Cannot change user role to admin")

    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)
    _sync_paas(current_admin.tenant_id, user)
    return _user_dict(user)


@router.delete("/users/{user_id}")
async def delete_tenant_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Deactivate a user (soft delete)"""
    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    db.commit()
    return {"message": "User deactivated successfully"}
