"""
Tenant Admin endpoints - For MSPs/white-label tenants to manage their own customers
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.user import User
from app.services.tenant_admin_auth import get_current_msp_admin
from app.core.logging import get_logger
from app.controllers.tenant_admin_controller import get_tenant_admin_controller

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
    admin_email: EmailStr
    admin_password: str
    admin_full_name: Optional[str] = None
    billing_config: Optional[Dict[str, Any]] = None
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


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """List all customers (sub-tenants) for this MSP"""
    return get_tenant_admin_controller(db, current_user.tenant_id).list_customers()


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create a new customer (sub-tenant) for this MSP"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).create_customer(
        customer_data, msp_tenant=current_user.tenant
    )


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get customer details"""
    return get_tenant_admin_controller(db, current_user.tenant_id).get_customer(customer_id)


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Update customer details"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).update_customer(
        customer_id, customer_data
    )


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Deactivate a customer (soft delete)"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).delete_customer(customer_id)


@router.get("/customers/{customer_id}/users")
async def list_customer_users(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """List users for a customer"""
    return get_tenant_admin_controller(db, current_user.tenant_id).list_customer_users(customer_id)


@router.post("/customers/{customer_id}/users")
async def create_customer_user(
    customer_id: int,
    user_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create a user for a customer (sub-tenant)"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).create_customer_user(
        customer_id, user_data
    )


@router.put("/customers/{customer_id}/users/{user_id}")
async def update_customer_user(
    customer_id: int,
    user_id: int,
    user_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Update a user for a customer"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).update_customer_user(
        customer_id, user_id, user_data
    )


@router.delete("/customers/{customer_id}/users/{user_id}")
async def delete_customer_user(
    customer_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Deactivate a user for a customer (soft delete)"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).delete_customer_user(
        customer_id, user_id
    )


@router.get("/customers/{customer_id}/subscription")
async def get_customer_subscription(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get subscription for a customer"""
    return get_tenant_admin_controller(db, current_user.tenant_id).get_customer_subscription(customer_id)


@router.post("/customers/{customer_id}/subscription")
async def create_customer_subscription(
    customer_id: int,
    subscription_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Create or update subscription for a customer"""
    return get_tenant_admin_controller(db, current_user.tenant_id, current_user.email).create_customer_subscription(
        customer_id, subscription_data
    )


@router.get("/dashboard")
async def get_msp_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_msp_admin)
):
    """Get MSP dashboard overview"""
    return get_tenant_admin_controller(db, current_user.tenant_id).get_msp_dashboard(current_user)
