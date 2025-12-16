"""
Super Admin endpoints for platform-level tenant management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import re

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.super_admin import SuperAdmin
from app.models.tenant_billing_config import TenantBillingConfig
from app.services.super_admin_auth import get_current_super_admin
from app.services.auth import get_password_hash
from app.core.logging import get_logger
from decimal import Decimal

router = APIRouter()
logger = get_logger(__name__)
# Helpers
def slugify(name: str) -> str:
    """Generate a URL-friendly slug from a tenant name."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip().lower()).strip('-')
    return slug or 'tenant'

def ensure_unique_slug(db: Session, base_slug: str) -> str:
    """Ensure the slug is unique; append numeric suffix if needed."""
    candidate = base_slug
    suffix = 1
    while db.query(Tenant).filter(Tenant.subdomain_slug == candidate).first():
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate



# Schemas
class BillingConfigCreate(BaseModel):
    """Billing configuration for tenant creation"""
    fixed_monthly_cost: float = 0.0
    per_node_enabled: bool = False
    per_node_cost: float = 0.0
    node_count_override: Optional[int] = None
    per_ticket_received_enabled: bool = False
    per_ticket_received_cost: float = 0.0
    per_ticket_resolved_enabled: bool = False
    per_ticket_resolved_cost: float = 0.0
    per_execution_enabled: bool = False
    per_execution_cost: float = 0.0
    per_api_call_enabled: bool = False
    per_api_call_cost: float = 0.0
    per_llm_token_enabled: bool = False
    per_llm_token_cost: float = 0.0
    billing_cycle: str = "monthly"
    billing_day: int = 1
    is_active: bool = True


class SubscriptionConfigCreate(BaseModel):
    """Subscription configuration for tenant creation"""
    max_seats: int = Field(..., gt=0, description="Maximum number of user seats")
    max_nodes: int = Field(..., gt=0, description="Maximum number of infrastructure nodes")
    subscription_name: Optional[str] = None
    monthly_price: Decimal = Field(0.00, ge=0)
    seat_overage_rate: Decimal = Field(0.00, ge=0)
    node_overage_rate: Decimal = Field(0.00, ge=0)
    is_enforced: bool = True
    expires_at: Optional[datetime] = None
    auto_renew: bool = True
    notes: Optional[str] = None


class TenantCreate(BaseModel):
    name: str
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    deployment_type: str = "saas"  # 'saas' or 'paas'
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    # Billing configuration (optional - can be set later)
    billing_config: Optional[BillingConfigCreate] = None
    # Subscription configuration (optional - can be set later)
    subscription_config: Optional[SubscriptionConfigCreate] = None
    # White-labeling: Is this tenant an MSP that can create sub-tenants?
    is_msp: bool = False
    parent_tenant_id: Optional[int] = None  # If this is a sub-tenant, reference parent


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    deployment_type: Optional[str] = None
    is_active: Optional[bool] = None
    onboarding_status: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    config_metadata: Optional[Dict[str, Any]] = None


class TenantUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "admin"  # admin, user, viewer


class TenantUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


# Platform Overview
@router.get("/overview")
async def get_platform_overview(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get platform-wide statistics"""
    try:
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        saas_tenants = db.query(Tenant).filter(Tenant.deployment_type == "saas").count()
        paas_tenants = db.query(Tenant).filter(Tenant.deployment_type == "paas").count()
        total_users = db.query(User).count()
        
        return {
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "saas": saas_tenants,
                "paas": paas_tenants,
            },
            "users": {
                "total": total_users,
            },
            "system": {
                "status": "healthy",
            }
        }
    except Exception as e:
        logger.error(f"Error fetching platform overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch platform overview")


# Tenant Management
@router.get("/tenants", response_model=List[Dict[str, Any]])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    deployment_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all tenants with optional filters"""
    query = db.query(Tenant)
    
    if deployment_type:
        query = query.filter(Tenant.deployment_type == deployment_type)
    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)
    
    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "subdomain_slug": t.subdomain_slug,
            "description": t.description,
            "deployment_type": t.deployment_type,
            "is_active": t.is_active,
            "onboarding_status": t.onboarding_status,
            "contact_email": t.contact_email,
            "contact_name": t.contact_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tenants
    ]


@router.post("/tenants", response_model=Dict[str, Any])
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new tenant"""
    # Validate deployment_type
    if tenant_data.deployment_type not in ["saas", "paas"]:
        raise HTTPException(status_code=400, detail="deployment_type must be 'saas' or 'paas'")
    
    # Check if tenant name already exists
    existing = db.query(Tenant).filter(Tenant.name == tenant_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenant with name '{tenant_data.name}' already exists")
    
    # Check subdomain_slug if provided
    if tenant_data.subdomain_slug:
        existing_slug = db.query(Tenant).filter(Tenant.subdomain_slug == tenant_data.subdomain_slug).first()
        if existing_slug:
            raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists")
        final_slug = tenant_data.subdomain_slug
    else:
        # Auto-generate slug from name if not provided
        base_slug = slugify(tenant_data.name)
        final_slug = ensure_unique_slug(db, base_slug)
    
    # Validate parent_tenant_id if provided
    if tenant_data.parent_tenant_id:
        parent = db.query(Tenant).filter(Tenant.id == tenant_data.parent_tenant_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail=f"Parent tenant {tenant_data.parent_tenant_id} not found")
        if not parent.is_msp:
            raise HTTPException(status_code=400, detail=f"Parent tenant {parent.name} is not an MSP")
    
    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
            subdomain_slug=final_slug,
        description=tenant_data.description,
        deployment_type=tenant_data.deployment_type,
        platform_managed=(tenant_data.deployment_type == "saas"),
        contact_email=tenant_data.contact_email,
        contact_name=tenant_data.contact_name,
        contact_phone=tenant_data.contact_phone,
        onboarding_status="pending",
        is_active=True,
        is_msp=tenant_data.is_msp,
        parent_tenant_id=tenant_data.parent_tenant_id,
    )
    
    db.add(tenant)
    db.flush()  # Flush to get tenant.id
    
    # Create billing configuration if provided
    if tenant_data.billing_config:
        billing_config = TenantBillingConfig(
            tenant_id=tenant.id,
            fixed_monthly_cost=Decimal(str(tenant_data.billing_config.fixed_monthly_cost)),
            per_node_enabled=tenant_data.billing_config.per_node_enabled,
            per_node_cost=Decimal(str(tenant_data.billing_config.per_node_cost)),
            node_count_override=tenant_data.billing_config.node_count_override,
            per_ticket_received_enabled=tenant_data.billing_config.per_ticket_received_enabled,
            per_ticket_received_cost=Decimal(str(tenant_data.billing_config.per_ticket_received_cost)),
            per_ticket_resolved_enabled=tenant_data.billing_config.per_ticket_resolved_enabled,
            per_ticket_resolved_cost=Decimal(str(tenant_data.billing_config.per_ticket_resolved_cost)),
            per_execution_enabled=tenant_data.billing_config.per_execution_enabled,
            per_execution_cost=Decimal(str(tenant_data.billing_config.per_execution_cost)),
            per_api_call_enabled=tenant_data.billing_config.per_api_call_enabled,
            per_api_call_cost=Decimal(str(tenant_data.billing_config.per_api_call_cost)),
            per_llm_token_enabled=tenant_data.billing_config.per_llm_token_enabled,
            per_llm_token_cost=Decimal(str(tenant_data.billing_config.per_llm_token_cost)),
            billing_cycle=tenant_data.billing_config.billing_cycle,
            billing_day=tenant_data.billing_config.billing_day,
            is_active=tenant_data.billing_config.is_active,
        )
        db.add(billing_config)
        logger.info(f"Created billing config for tenant {tenant.name}")
    
    # Create subscription if provided
    subscription_created = False
    if tenant_data.subscription_config:
        from app.models.tenant_subscription import TenantSubscription
        from app.services.subscription.subscription_tracker import SubscriptionTracker
        
        subscription = TenantSubscription(
            tenant_id=tenant.id,
            max_seats=tenant_data.subscription_config.max_seats,
            max_nodes=tenant_data.subscription_config.max_nodes,
            subscription_name=tenant_data.subscription_config.subscription_name,
            monthly_price=tenant_data.subscription_config.monthly_price,
            seat_overage_rate=tenant_data.subscription_config.seat_overage_rate,
            node_overage_rate=tenant_data.subscription_config.node_overage_rate,
            is_enforced=tenant_data.subscription_config.is_enforced,
            expires_at=tenant_data.subscription_config.expires_at,
            auto_renew=tenant_data.subscription_config.auto_renew,
            notes=tenant_data.subscription_config.notes,
            created_by=current_admin.id,
            status="active"
        )
        db.add(subscription)
        subscription_created = True
        logger.info(f"Created subscription for tenant {tenant.name}: {tenant_data.subscription_config.max_seats} seats, {tenant_data.subscription_config.max_nodes} nodes")
    
    db.commit()
    db.refresh(tenant)
    
    # Update initial usage if subscription was created
    if subscription_created:
        tracker = SubscriptionTracker(db)
        tracker.update_usage(tenant.id)
    
    logger.info(f"Super admin {current_admin.email} created tenant {tenant.name} (id={tenant.id})")
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "subdomain_slug": tenant.subdomain_slug,
        "deployment_type": tenant.deployment_type,
        "onboarding_status": tenant.onboarding_status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "billing_configured": tenant_data.billing_config is not None,
        "subscription_configured": subscription_created,
    }


@router.get("/tenants/{tenant_id}", response_model=Dict[str, Any])
async def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get tenant details"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    # Get user count for this tenant
    user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    
    # Get customer count if MSP
    customer_count = 0
    if tenant.is_msp:
        customer_count = db.query(Tenant).filter(
            Tenant.parent_tenant_id == tenant_id,
            Tenant.is_msp == False
        ).count()
    
    # Get parent MSP if this is a customer
    parent_msp = None
    if tenant.parent_tenant_id:
        parent = db.query(Tenant).filter(Tenant.id == tenant.parent_tenant_id).first()
        if parent:
            parent_msp = {
                "id": parent.id,
                "name": parent.name
            }
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "subdomain_slug": tenant.subdomain_slug,
        "description": tenant.description,
        "deployment_type": tenant.deployment_type,
        "platform_managed": tenant.platform_managed,
        "is_active": tenant.is_active,
        "onboarding_status": tenant.onboarding_status,
        "contact_email": tenant.contact_email,
        "contact_name": tenant.contact_name,
        "contact_phone": tenant.contact_phone,
        "config_metadata": tenant.config_metadata,
        "is_msp": tenant.is_msp,
        "parent_tenant_id": tenant.parent_tenant_id,
        "parent_msp": parent_msp,
        "user_count": user_count,
        "customer_count": customer_count,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }


@router.get("/tenants/{tenant_id}/customers", response_model=List[Dict[str, Any]])
async def get_tenant_customers(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get all customers (sub-tenants) for an MSP tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    if not tenant.is_msp:
        raise HTTPException(status_code=400, detail=f"Tenant {tenant_id} is not an MSP")
    
    customers = db.query(Tenant).filter(
        Tenant.parent_tenant_id == tenant_id,
        Tenant.is_msp == False
    ).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "subdomain_slug": t.subdomain_slug,
            "description": t.description,
            "contact_email": t.contact_email,
            "is_active": t.is_active,
            "onboarding_status": t.onboarding_status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in customers
    ]


@router.put("/tenants/{tenant_id}", response_model=Dict[str, Any])
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    # Update fields
    if tenant_data.name is not None:
        # Check if name is already taken by another tenant
        existing = db.query(Tenant).filter(Tenant.name == tenant_data.name, Tenant.id != tenant_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with name '{tenant_data.name}' already exists")
        tenant.name = tenant_data.name
    
    if tenant_data.subdomain_slug is not None:
        # Check if subdomain is already taken
        existing = db.query(Tenant).filter(Tenant.subdomain_slug == tenant_data.subdomain_slug, Tenant.id != tenant_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{tenant_data.subdomain_slug}' already exists")
        tenant.subdomain_slug = tenant_data.subdomain_slug
    
    if tenant_data.description is not None:
        tenant.description = tenant_data.description
    if tenant_data.deployment_type is not None:
        if tenant_data.deployment_type not in ["saas", "paas"]:
            raise HTTPException(status_code=400, detail="deployment_type must be 'saas' or 'paas'")
        tenant.deployment_type = tenant_data.deployment_type
        tenant.platform_managed = (tenant_data.deployment_type == "saas")
    if tenant_data.is_active is not None:
        tenant.is_active = tenant_data.is_active
    if tenant_data.onboarding_status is not None:
        tenant.onboarding_status = tenant_data.onboarding_status
    if tenant_data.contact_email is not None:
        tenant.contact_email = tenant_data.contact_email
    if tenant_data.contact_name is not None:
        tenant.contact_name = tenant_data.contact_name
    if tenant_data.contact_phone is not None:
        tenant.contact_phone = tenant_data.contact_phone
    if tenant_data.config_metadata is not None:
        tenant.config_metadata = tenant_data.config_metadata
    
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Super admin {current_admin.email} updated tenant {tenant.name} (id={tenant.id})")
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "deployment_type": tenant.deployment_type,
        "is_active": tenant.is_active,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Deactivate a tenant (soft delete)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    tenant.is_active = False
    db.commit()
    
    logger.info(f"Super admin {current_admin.email} deactivated tenant {tenant.name} (id={tenant.id})")
    
    return {"message": f"Tenant {tenant_id} deactivated successfully"}


# Tenant User Management
@router.get("/tenants/{tenant_id}/users", response_model=List[Dict[str, Any]])
async def list_tenant_users(
    tenant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List users for a specific tenant"""
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    users = db.query(User).filter(User.tenant_id == tenant_id).offset(skip).limit(limit).all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/tenants/{tenant_id}/users", response_model=Dict[str, Any])
async def create_tenant_user(
    tenant_id: int,
    user_data: TenantUserCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a user for a tenant"""
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"User with email '{user_data.email}' already exists")
    
    # Validate role
    if user_data.role not in ["admin", "user", "viewer"]:
        raise HTTPException(status_code=400, detail="role must be 'admin', 'user', or 'viewer'")
    
    # Check subscription seat limit
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    tracker = SubscriptionTracker(db)
    allowed, error_msg = tracker.check_seat_limit(tenant_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=error_msg or "Seat limit reached")
    
    # Determine final role based on tenant type
    # If "admin" role is requested:
    # - For MSP tenants: use "msp_admin"
    # - For regular tenants: use "tenant_admin"
    requested_role = user_data.role
    if requested_role == "admin":
        if tenant.is_msp:
            final_role = "msp_admin"
        else:
            final_role = "tenant_admin"
    else:
        final_role = requested_role
    
    # Create user
    from app.services.auth import get_password_hash
    user = User(
        tenant_id=tenant_id,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=final_role,
        is_active=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Super admin {current_admin.email} created user {user.email} for tenant {tenant.name}")
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": user.tenant_id,
    }


@router.put("/tenants/{tenant_id}/users/{user_id}", response_model=Dict[str, Any])
async def update_tenant_user(
    tenant_id: int,
    user_id: int,
    user_data: TenantUserUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a user for a tenant"""
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found for tenant {tenant_id}")
    
    if user_data.role is not None:
        if user_data.role not in ["admin", "user", "viewer"]:
            raise HTTPException(status_code=400, detail="role must be 'admin', 'user', or 'viewer'")
        # Determine final role based on tenant type
        # If "admin" role is requested:
        # - For MSP tenants: use "msp_admin"
        # - For regular tenants: use "tenant_admin"
        if user_data.role == "admin":
            if tenant.is_msp:
                user.role = "msp_admin"
            else:
                user.role = "tenant_admin"
        else:
            user.role = user_data.role
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Super admin {current_admin.email} updated user {user.email} (id={user.id}) for tenant {tenant.name}")
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "tenant_id": user.tenant_id,
    }


@router.delete("/tenants/{tenant_id}/users/{user_id}", response_model=Dict[str, Any])
async def delete_tenant_user(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Deactivate (soft delete) a user for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found for tenant {tenant_id}")
    
    user.is_active = False
    db.commit()
    
    logger.info(f"Super admin {current_admin.email} deactivated user {user.email} (id={user.id}) for tenant {tenant.name}")
    
    return {"message": f"User {user_id} deactivated successfully"}





