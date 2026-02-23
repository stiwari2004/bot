"""
Client Admin (Tenant Admin) endpoints for managing their own tenant
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_billing_config import TenantBillingConfig
from app.models.tenant_subscription import TenantSubscription
from app.models.credential import InfrastructureConnection
from app.services.auth import get_current_user, get_password_hash
from app.core.logging import get_logger
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter()
logger = get_logger(__name__)


def get_current_tenant_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Ensure the current user is a tenant admin (role='tenant_admin' or role='admin' with non-MSP tenant)"""
    # Refresh tenant relationship
    db.refresh(current_user, ['tenant'])
    tenant = current_user.tenant
    
    if not tenant:
        raise HTTPException(
            status_code=403,
            detail="User has no associated tenant"
        )
    
    # Check if user is tenant admin (not MSP admin)
    # Allow both 'tenant_admin' role and legacy 'admin' role with non-MSP tenant
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


# Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"  # user, viewer (admin can only create users/viewers, not other admins)


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


class BillingViewResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    billing_config: Optional[dict] = None
    subscription: Optional[dict] = None
    current_usage: Optional[dict] = None


class NodeResponse(BaseModel):
    id: int
    name: str
    connection_type: str
    target_host: Optional[str] = None
    environment: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_nodes: int
    active_nodes: int
    pending_nodes: int  # Discovered but not yet approved/activated


# User Management Endpoints
@router.get("/users", response_model=List[UserResponse])
async def list_tenant_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """List all users in the tenant"""
    users = db.query(User).filter(
        User.tenant_id == current_admin.tenant_id
    ).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login,
        }
        for u in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_tenant_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Create a new user in the tenant"""
    # Check if user already exists
    # Case-insensitive email lookup
    from sqlalchemy import func
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate role (tenant admin can only create users/viewers, not other admins)
    if user_data.role in ["admin", "tenant_admin", "msp_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Tenant admins cannot create other admin users"
        )
    
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
    # PaaS: sync to central for billing
    try:
        from app.services.central_client import sync_users_for_billing
        sync_users_for_billing(current_admin.tenant_id, [{
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "tenant_id": new_user.tenant_id,
            "node_details": None,
        }])
    except Exception as e:
        logger.warning("PaaS sync_users_for_billing failed: %s", e)
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at,
        "last_login": new_user.last_login,
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_tenant_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get a specific user in the tenant"""
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_tenant_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Update a user in the tenant"""
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent changing own role or deactivating self
    if user_id == current_admin.id:
        if user_data.role and user_data.role != user.role:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        if user_data.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    # Prevent creating other admins
    if user_data.role in ["admin", "tenant_admin", "msp_admin"] and user.id != current_admin.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot change user role to admin"
        )
    
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
    # PaaS: sync to central for billing
    try:
        from app.services.central_client import sync_users_for_billing
        sync_users_for_billing(current_admin.tenant_id, [{
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "node_details": None,
        }])
    except Exception as e:
        logger.warning("PaaS sync_users_for_billing failed: %s", e)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


@router.delete("/users/{user_id}")
async def delete_tenant_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Deactivate a user (soft delete)"""
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_admin.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    user.is_active = False
    db.commit()
    return {"message": "User deactivated successfully"}


# Billing Endpoints
@router.get("/billing", response_model=BillingViewResponse)
async def get_tenant_billing(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get billing information for the tenant (read-only)"""
    tenant = db.query(Tenant).filter(Tenant.id == current_admin.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    billing_config = db.query(TenantBillingConfig).filter(
        TenantBillingConfig.tenant_id == current_admin.tenant_id
    ).first()
    
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == current_admin.tenant_id
    ).first()
    
    # Get current usage
    current_usage = {}
    if subscription:
        current_usage = {
            "seats_used": subscription.current_seats,
            "seats_limit": subscription.max_seats,
            "nodes_used": subscription.current_nodes,
            "nodes_limit": subscription.max_nodes,
        }
    
    billing_data = None
    if billing_config:
        billing_data = {
            "fixed_monthly_cost": float(billing_config.fixed_monthly_cost) if billing_config.fixed_monthly_cost else 0.0,
            "per_node_enabled": billing_config.per_node_enabled,
            "per_node_cost": float(billing_config.per_node_cost) if billing_config.per_node_cost else 0.0,
            "billing_cycle": billing_config.billing_cycle,
            "is_active": billing_config.is_active,
        }
    
    sub_data = None
    if subscription:
        sub_data = {
            "subscription_name": subscription.subscription_name,
            "max_seats": subscription.max_seats,
            "max_nodes": subscription.max_nodes,
            "monthly_price": float(subscription.monthly_price) if subscription.monthly_price else 0.0,
            "status": subscription.status,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }
    
    return BillingViewResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        billing_config=billing_data,
        subscription=sub_data,
        current_usage=current_usage
    )


# Node Management Endpoints
@router.get("/nodes", response_model=List[NodeResponse])
async def list_tenant_nodes(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """List all infrastructure connections (nodes) for the tenant"""
    query = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    )
    
    if is_active is not None:
        query = query.filter(InfrastructureConnection.is_active == is_active)
    
    nodes = query.all()
    return [
        {
            "id": n.id,
            "name": n.name,
            "connection_type": n.connection_type,
            "target_host": n.target_host,
            "environment": n.environment,
            "is_active": n.is_active,
            "created_at": n.created_at,
        }
        for n in nodes
    ]


@router.put("/nodes/{node_id}/activate")
async def activate_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Activate a node (approve for billing and execution)"""
    node = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.id == node_id,
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_active = True
    db.commit()
    return {
        "message": "Node activated successfully",
        "node": {
            "id": node.id,
            "name": node.name,
            "connection_type": node.connection_type,
            "target_host": node.target_host,
            "environment": node.environment,
            "is_active": node.is_active,
            "created_at": node.created_at,
        }
    }


@router.put("/nodes/{node_id}/deactivate")
async def deactivate_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Deactivate a node (remove from billing and execution)"""
    node = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.id == node_id,
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_active = False
    db.commit()
    return {
        "message": "Node deactivated successfully",
        "node": {
            "id": node.id,
            "name": node.name,
            "connection_type": node.connection_type,
            "target_host": node.target_host,
            "environment": node.environment,
            "is_active": node.is_active,
            "created_at": node.created_at,
        }
    }


# Dashboard Endpoint
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get dashboard statistics for the tenant"""
    # User stats
    total_users = db.query(User).filter(
        User.tenant_id == current_admin.tenant_id
    ).count()
    active_users = db.query(User).filter(
        User.tenant_id == current_admin.tenant_id,
        User.is_active == True
    ).count()
    
    # Node stats
    total_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).count()
    active_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id,
        InfrastructureConnection.is_active == True
    ).count()
    pending_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id,
        InfrastructureConnection.is_active == False
    ).count()
    
    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_nodes=total_nodes,
        active_nodes=active_nodes,
        pending_nodes=pending_nodes
    )

