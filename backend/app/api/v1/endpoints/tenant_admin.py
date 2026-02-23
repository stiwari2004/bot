"""
Tenant Admin endpoints - For MSPs/white-label tenants to manage their own customers
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from decimal import Decimal

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.tenant_billing_config import TenantBillingConfig
from app.services.auth import get_current_user, get_password_hash
from app.services.tenant_admin_auth import (
    get_current_msp_admin,
    get_allowed_tenant_ids_for_msp,
    verify_tenant_access
)
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class CustomerCreate(BaseModel):
    """Create a customer (sub-tenant) for MSP"""
    name: str
    subdomain_slug: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    # Admin user for this customer
    admin_email: EmailStr
    admin_password: str
    admin_full_name: Optional[str] = None
    # Billing configuration
    billing_config: Optional[Dict[str, Any]] = None
    # Subscription configuration
    subscription_config: Optional[Dict[str, Any]] = None


class CustomerResponse(BaseModel):
    """Customer (sub-tenant) response"""
    id: int
    name: str
    subdomain_slug: Optional[str]
    description: Optional[str]
    contact_email: Optional[str]
    is_active: bool
    onboarding_status: str
    created_at: str


# Note: Using get_current_msp_admin from tenant_admin_auth.py instead


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """List all customers (sub-tenants) for this MSP"""
    customers = db.query(Tenant).filter(
        Tenant.parent_tenant_id == current_user.tenant_id,
        Tenant.is_msp == False  # Only show sub-tenants, not other MSPs
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


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create a new customer (sub-tenant) for this MSP"""
    # Validate MSP tenant
    msp_tenant = current_user.tenant
    if not msp_tenant.is_msp:
        raise HTTPException(status_code=403, detail="Your tenant is not an MSP")
    
    # Check if customer name already exists
    existing = db.query(Tenant).filter(Tenant.name == customer_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenant with name '{customer_data.name}' already exists")
    
    # Check subdomain if provided
    if customer_data.subdomain_slug:
        existing_slug = db.query(Tenant).filter(Tenant.subdomain_slug == customer_data.subdomain_slug).first()
        if existing_slug:
            raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{customer_data.subdomain_slug}' already exists")
    
    # Check if admin email already exists
    # Case-insensitive email lookup
    from sqlalchemy import func
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(customer_data.admin_email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"User with email '{customer_data.admin_email}' already exists")
    
    # Note: For MSP creating customers, we don't check MSP's seat limit
    # because the customer will have their own subscription
    # But we should check if MSP has subscription to create customers (future enhancement)
    
    # Create customer tenant
    customer_tenant = Tenant(
        name=customer_data.name,
        subdomain_slug=customer_data.subdomain_slug,
        description=customer_data.description,
        deployment_type="saas",  # Customers are always SaaS
        platform_managed=True,
        contact_email=customer_data.contact_email,
        contact_name=customer_data.contact_name,
        contact_phone=customer_data.contact_phone,
        onboarding_status="pending",
        is_active=True,
        is_msp=False,
        parent_tenant_id=msp_tenant.id,
    )
    
    db.add(customer_tenant)
    db.flush()  # Get customer_tenant.id
    
    # Check subscription seat limit for the customer tenant (if they have a subscription)
    # Note: New customer tenants won't have subscription yet, so this will pass
    # Subscription should be assigned separately by MSP or Super Admin
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    tracker = SubscriptionTracker(db)
    allowed, error_msg = tracker.check_seat_limit(customer_tenant.id)
    if not allowed:
        # If limit reached, rollback customer creation
        db.rollback()
        raise HTTPException(status_code=403, detail=error_msg or "Seat limit reached for customer tenant")
    
    # Create admin user for customer (tenant_admin role, not msp_admin)
    admin_user = User(
        tenant_id=customer_tenant.id,
        email=customer_data.admin_email,
        password_hash=get_password_hash(customer_data.admin_password),
        full_name=customer_data.admin_full_name or customer_data.contact_name,
        role="tenant_admin",  # Tenant admin role for customer tenants
        is_active=True,
    )
    db.add(admin_user)
    
    # Create billing configuration if provided
    if customer_data.billing_config:
        billing_config = TenantBillingConfig(
            tenant_id=customer_tenant.id,
            fixed_monthly_cost=Decimal(str(customer_data.billing_config.get("fixed_monthly_cost", 0))),
            per_node_enabled=customer_data.billing_config.get("per_node_enabled", False),
            per_node_cost=Decimal(str(customer_data.billing_config.get("per_node_cost", 0))),
            node_count_override=customer_data.billing_config.get("node_count_override"),
            per_ticket_received_enabled=customer_data.billing_config.get("per_ticket_received_enabled", False),
            per_ticket_received_cost=Decimal(str(customer_data.billing_config.get("per_ticket_received_cost", 0))),
            per_ticket_resolved_enabled=customer_data.billing_config.get("per_ticket_resolved_enabled", False),
            per_ticket_resolved_cost=Decimal(str(customer_data.billing_config.get("per_ticket_resolved_cost", 0))),
            per_execution_enabled=customer_data.billing_config.get("per_execution_enabled", False),
            per_execution_cost=Decimal(str(customer_data.billing_config.get("per_execution_cost", 0))),
            per_api_call_enabled=customer_data.billing_config.get("per_api_call_enabled", False),
            per_api_call_cost=Decimal(str(customer_data.billing_config.get("per_api_call_cost", 0))),
            per_llm_token_enabled=customer_data.billing_config.get("per_llm_token_enabled", False),
            per_llm_token_cost=Decimal(str(customer_data.billing_config.get("per_llm_token_cost", 0))),
            billing_cycle=customer_data.billing_config.get("billing_cycle", "monthly"),
            billing_day=customer_data.billing_config.get("billing_day", 1),
            is_active=customer_data.billing_config.get("is_active", True),
        )
        db.add(billing_config)
    
    # Create subscription if provided
    if customer_data.subscription_config:
        from app.models.tenant_subscription import TenantSubscription
        from app.services.subscription.subscription_tracker import SubscriptionTracker
        
        subscription = TenantSubscription(
            tenant_id=customer_tenant.id,
            max_seats=customer_data.subscription_config.get("max_seats", 5),
            max_nodes=customer_data.subscription_config.get("max_nodes", 20),
            subscription_name=customer_data.subscription_config.get("subscription_name"),
            monthly_price=Decimal(str(customer_data.subscription_config.get("monthly_price", 0))),
            seat_overage_rate=Decimal(str(customer_data.subscription_config.get("seat_overage_rate", 0))),
            node_overage_rate=Decimal(str(customer_data.subscription_config.get("node_overage_rate", 0))),
            is_enforced=customer_data.subscription_config.get("is_enforced", True),
            expires_at=None,  # MSP can set this later
            auto_renew=customer_data.subscription_config.get("auto_renew", True),
            notes=customer_data.subscription_config.get("notes"),
            created_by=None,  # MSP created, not super admin
            status="active"
        )
        db.add(subscription)
        logger.info(f"Created subscription for customer {customer_tenant.name}")
    
    db.commit()
    db.refresh(customer_tenant)
    
    # Update subscription usage if subscription was created
    if customer_data.subscription_config:
        tracker = SubscriptionTracker(db)
        tracker.update_usage(customer_tenant.id)
    
    logger.info(f"Tenant admin {current_user.email} created customer {customer_tenant.name} (id={customer_tenant.id})")
    
    return {
        "id": customer_tenant.id,
        "name": customer_tenant.name,
        "subdomain_slug": customer_tenant.subdomain_slug,
        "description": customer_tenant.description,
        "contact_email": customer_tenant.contact_email,
        "is_active": customer_tenant.is_active,
        "onboarding_status": customer_tenant.onboarding_status,
        "created_at": customer_tenant.created_at.isoformat() if customer_tenant.created_at else None,
    }


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get customer details"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    customer = db.query(Tenant).filter(
        Tenant.id == customer_id,
        Tenant.parent_tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "id": customer.id,
        "name": customer.name,
        "subdomain_slug": customer.subdomain_slug,
        "description": customer.description,
        "contact_email": customer.contact_email,
        "is_active": customer.is_active,
        "onboarding_status": customer.onboarding_status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Update customer details"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    customer = db.query(Tenant).filter(
        Tenant.id == customer_id,
        Tenant.parent_tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update fields
    if "name" in customer_data:
        # Check if name is already taken by another tenant
        existing = db.query(Tenant).filter(
            Tenant.name == customer_data["name"],
            Tenant.id != customer_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with name '{customer_data['name']}' already exists")
        customer.name = customer_data["name"]
    
    if "subdomain_slug" in customer_data:
        if customer_data["subdomain_slug"]:
            existing = db.query(Tenant).filter(
                Tenant.subdomain_slug == customer_data["subdomain_slug"],
                Tenant.id != customer_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Tenant with subdomain '{customer_data['subdomain_slug']}' already exists")
        customer.subdomain_slug = customer_data.get("subdomain_slug")
    
    if "description" in customer_data:
        customer.description = customer_data["description"]
    if "contact_email" in customer_data:
        customer.contact_email = customer_data["contact_email"]
    if "contact_name" in customer_data:
        customer.contact_name = customer_data["contact_name"]
    if "contact_phone" in customer_data:
        customer.contact_phone = customer_data["contact_phone"]
    if "is_active" in customer_data:
        customer.is_active = customer_data["is_active"]
    if "onboarding_status" in customer_data:
        customer.onboarding_status = customer_data["onboarding_status"]
    
    db.commit()
    db.refresh(customer)
    
    logger.info(f"MSP admin {current_user.email} updated customer {customer.name} (id={customer.id})")
    
    return {
        "id": customer.id,
        "name": customer.name,
        "subdomain_slug": customer.subdomain_slug,
        "description": customer.description,
        "contact_email": customer.contact_email,
        "is_active": customer.is_active,
        "onboarding_status": customer.onboarding_status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Deactivate a customer (soft delete)"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    customer = db.query(Tenant).filter(
        Tenant.id == customer_id,
        Tenant.parent_tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.is_active = False
    db.commit()
    
    logger.info(f"MSP admin {current_user.email} deactivated customer {customer.name} (id={customer.id})")
    
    return {"message": f"Customer {customer_id} deactivated successfully"}


# Customer User Management
@router.get("/customers/{customer_id}/users")
async def list_customer_users(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """List users for a customer"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    users = db.query(User).filter(User.tenant_id == customer_id).all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/customers/{customer_id}/users")
async def create_customer_user(
    customer_id: int,
    user_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create a user for a customer (sub-tenant)"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    # IMPORTANT: Prevent creating users under the MSP tenant itself
    # MSP admins should only create users for customer tenants (sub-tenants), not for their own MSP tenant
    customer_tenant = db.query(Tenant).filter(Tenant.id == customer_id).first()
    if not customer_tenant:
        raise HTTPException(status_code=404, detail=f"Customer tenant {customer_id} not found")
    
    if customer_tenant.id == current_user.tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Cannot create users under MSP tenant. Please select a customer (sub-tenant) to create users for."
        )
    
    if customer_tenant.is_msp:
        raise HTTPException(
            status_code=403,
            detail="Cannot create users under another MSP tenant. Please select a customer (sub-tenant)."
        )
    
    # Check if user already exists
        # Case-insensitive email lookup
        from sqlalchemy import func
        existing = db.query(User).filter(func.lower(User.email) == func.lower(user_data["email"])).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"User with email '{user_data['email']}' already exists")
    
    # Check subscription seat limit
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    tracker = SubscriptionTracker(db)
    allowed, error_msg = tracker.check_seat_limit(customer_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=error_msg or "Seat limit reached")
    
    # Determine role: if admin role is requested, use tenant_admin for customer tenants
    requested_role = user_data.get("role", "user")
    if requested_role == "admin":
        final_role = "tenant_admin"  # Customer tenant admins use tenant_admin role
    else:
        final_role = requested_role
    
    # Create user
    user = User(
        tenant_id=customer_id,
        email=user_data["email"],
        password_hash=get_password_hash(user_data["password"]),
        full_name=user_data.get("full_name"),
        role=final_role,
        is_active=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # PaaS: sync to central for billing
    try:
        from app.services.central_client import sync_users_for_billing
        sync_users_for_billing(customer_id, [{
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "node_details": None,
        }])
    except Exception as e:
        logger.warning("PaaS sync_users_for_billing failed: %s", e)
    
    logger.info(f"MSP admin {current_user.email} created user {user.email} for customer {customer_id}")
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.put("/customers/{customer_id}/users/{user_id}")
async def update_customer_user(
    customer_id: int,
    user_id: int,
    user_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Update a user for a customer"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    user = db.query(User).filter(User.id == user_id, User.tenant_id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found for customer {customer_id}")
    
    if "role" in user_data:
        if user_data["role"] not in ["admin", "user", "viewer"]:
            raise HTTPException(status_code=400, detail="role must be 'admin', 'user', or 'viewer'")
        # Convert "admin" role to "tenant_admin" for customer tenants
        if user_data["role"] == "admin":
            user.role = "tenant_admin"
        else:
            user.role = user_data["role"]
    
    if "full_name" in user_data:
        user.full_name = user_data["full_name"]
    
    if "is_active" in user_data:
        user.is_active = user_data["is_active"]
    
    if "password" in user_data and user_data["password"]:
        user.password_hash = get_password_hash(user_data["password"])
    
    db.commit()
    db.refresh(user)
    
    # PaaS: sync to central for billing
    try:
        from app.services.central_client import sync_users_for_billing
        sync_users_for_billing(customer_id, [{
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "node_details": None,
        }])
    except Exception as e:
        logger.warning("PaaS sync_users_for_billing failed: %s", e)
    
    logger.info(f"MSP admin {current_user.email} updated user {user.email} for customer {customer_id}")
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.delete("/customers/{customer_id}/users/{user_id}")
async def delete_customer_user(
    customer_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Deactivate a user for a customer (soft delete)"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    user = db.query(User).filter(User.id == user_id, User.tenant_id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found for customer {customer_id}")
    
    user.is_active = False
    db.commit()
    
    logger.info(f"MSP admin {current_user.email} deactivated user {user.email} for customer {customer_id}")
    
    return {"message": f"User {user_id} deactivated successfully"}


# Subscription Management for Customers
@router.get("/customers/{customer_id}/subscription")
async def get_customer_subscription(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get subscription for a customer"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    from app.models.tenant_subscription import TenantSubscription
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == customer_id
    ).first()
    
    if not subscription:
        return {"has_subscription": False}
    
    # Update usage
    tracker = SubscriptionTracker(db)
    tracker.update_usage(customer_id)
    db.refresh(subscription)
    
    return {
        "id": subscription.id,
        "max_seats": subscription.max_seats,
        "max_nodes": subscription.max_nodes,
        "current_seats": subscription.current_seats,
        "current_nodes": subscription.current_nodes,
        "seats_remaining": subscription.seats_remaining,
        "nodes_remaining": subscription.nodes_remaining,
        "seats_exceeded": subscription.seats_exceeded,
        "nodes_exceeded": subscription.nodes_exceeded,
        "subscription_name": subscription.subscription_name,
        "monthly_price": float(subscription.monthly_price),
        "status": subscription.status,
        "is_enforced": subscription.is_enforced,
        "is_active": subscription.is_active,
    }


@router.post("/customers/{customer_id}/subscription")
async def create_customer_subscription(
    customer_id: int,
    subscription_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create or update subscription for a customer"""
    # Verify access
    if not verify_tenant_access(current_user.tenant_id, customer_id, db):
        raise HTTPException(status_code=403, detail="Access denied. You can only manage your own MSP tenant and its customers.")
    
    from app.models.tenant_subscription import TenantSubscription
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    
    # Check if subscription already exists
    existing = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == customer_id
    ).first()
    
    if existing:
        # Update existing
        existing.max_seats = subscription_data.get("max_seats", existing.max_seats)
        existing.max_nodes = subscription_data.get("max_nodes", existing.max_nodes)
        if "subscription_name" in subscription_data:
            existing.subscription_name = subscription_data["subscription_name"]
        if "monthly_price" in subscription_data:
            existing.monthly_price = Decimal(str(subscription_data["monthly_price"]))
        if "seat_overage_rate" in subscription_data:
            existing.seat_overage_rate = Decimal(str(subscription_data["seat_overage_rate"]))
        if "node_overage_rate" in subscription_data:
            existing.node_overage_rate = Decimal(str(subscription_data["node_overage_rate"]))
        if "is_enforced" in subscription_data:
            existing.is_enforced = subscription_data["is_enforced"]
        if "auto_renew" in subscription_data:
            existing.auto_renew = subscription_data["auto_renew"]
        if "notes" in subscription_data:
            existing.notes = subscription_data["notes"]
        
        db.commit()
        db.refresh(existing)
        
        tracker = SubscriptionTracker(db)
        tracker.update_usage(customer_id)
        db.refresh(existing)
        
        logger.info(f"MSP admin {current_user.email} updated subscription for customer {customer_id}")
        
        return {
            "id": existing.id,
            "max_seats": existing.max_seats,
            "max_nodes": existing.max_nodes,
            "current_seats": existing.current_seats,
            "current_nodes": existing.current_nodes,
            "message": "Subscription updated successfully"
        }
    else:
        # Create new
        subscription = TenantSubscription(
            tenant_id=customer_id,
            max_seats=subscription_data.get("max_seats", 5),
            max_nodes=subscription_data.get("max_nodes", 20),
            subscription_name=subscription_data.get("subscription_name"),
            monthly_price=Decimal(str(subscription_data.get("monthly_price", 0))),
            seat_overage_rate=Decimal(str(subscription_data.get("seat_overage_rate", 0))),
            node_overage_rate=Decimal(str(subscription_data.get("node_overage_rate", 0))),
            is_enforced=subscription_data.get("is_enforced", True),
            expires_at=None,
            auto_renew=subscription_data.get("auto_renew", True),
            notes=subscription_data.get("notes"),
            created_by=None,  # MSP created
            status="active"
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        tracker = SubscriptionTracker(db)
        tracker.update_usage(customer_id)
        db.refresh(subscription)
        
        logger.info(f"MSP admin {current_user.email} created subscription for customer {customer_id}")
        
        return {
            "id": subscription.id,
            "max_seats": subscription.max_seats,
            "max_nodes": subscription.max_nodes,
            "current_seats": subscription.current_seats,
            "current_nodes": subscription.current_nodes,
            "message": "Subscription created successfully"
        }


# Dashboard/Overview
@router.get("/dashboard")
async def get_msp_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get MSP dashboard overview"""
    msp_tenant_id = current_user.tenant_id
    
    # Get customer count
    customer_count = db.query(Tenant).filter(
        Tenant.parent_tenant_id == msp_tenant_id,
        Tenant.is_msp == False,
        Tenant.is_active == True
    ).count()
    
    # Get total users across all customers
    allowed_tenant_ids = get_allowed_tenant_ids_for_msp(msp_tenant_id, db)
    total_users = db.query(User).filter(
        User.tenant_id.in_(allowed_tenant_ids),
        User.is_active == True
    ).count()
    
    # Get total nodes across all customers
    from app.models.credential import InfrastructureConnection
    total_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id.in_(allowed_tenant_ids),
        InfrastructureConnection.is_active == True
    ).count()
    
    # Get subscription summaries
    from app.models.tenant_subscription import TenantSubscription
    subscriptions = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id.in_(allowed_tenant_ids),
        TenantSubscription.status == "active"
    ).all()
    
    total_seats = sum(s.max_seats for s in subscriptions)
    total_nodes_limit = sum(s.max_nodes for s in subscriptions)
    current_seats = sum(s.current_seats for s in subscriptions)
    current_nodes = sum(s.current_nodes for s in subscriptions)
    
    return {
        "msp_tenant": {
            "id": current_user.tenant.id,
            "name": current_user.tenant.name,
        },
        "customers": {
            "total": customer_count,
            "active": customer_count,
        },
        "users": {
            "total": total_users,
            "seats_used": current_seats,
            "seats_limit": total_seats,
        },
        "nodes": {
            "total": total_nodes,
            "nodes_used": current_nodes,
            "nodes_limit": total_nodes_limit,
        },
        "subscriptions": {
            "total": len(subscriptions),
            "active": len([s for s in subscriptions if s.is_active]),
        }
    }

