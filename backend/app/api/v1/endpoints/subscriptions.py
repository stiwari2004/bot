"""
Subscription management endpoints (Super Admin only)
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from decimal import Decimal

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Request/Response Models
class SubscriptionCreate(BaseModel):
    """Request model for creating subscription"""
    tenant_id: int = Field(..., description="Tenant ID to assign subscription to")
    license_plan_id: Optional[int] = Field(None, description="License plan ID (Free, Starter, Professional, Enterprise). If provided, will use plan defaults.")
    max_seats: int = Field(..., gt=0, description="Maximum number of user seats")
    max_nodes: int = Field(..., gt=0, description="Maximum number of infrastructure nodes")
    subscription_name: Optional[str] = Field(None, description="Custom subscription name")
    monthly_price: Decimal = Field(0.00, ge=0, description="Monthly subscription price")
    seat_overage_rate: Decimal = Field(0.00, ge=0, description="Cost per additional seat per month")
    node_overage_rate: Decimal = Field(0.00, ge=0, description="Cost per additional node per month")
    is_enforced: bool = Field(True, description="Enforce limits and block when exceeded")
    expires_at: Optional[datetime] = Field(None, description="Subscription expiration date (NULL = never expires)")
    auto_renew: bool = Field(True, description="Auto-renew subscription")
    notes: Optional[str] = Field(None, description="Admin notes")


class SubscriptionUpdate(BaseModel):
    """Request model for updating subscription"""
    license_plan_id: Optional[int] = Field(None, description="License plan ID. If provided, will update limits to plan defaults.")
    max_seats: Optional[int] = Field(None, gt=0, description="Maximum number of user seats")
    max_nodes: Optional[int] = Field(None, gt=0, description="Maximum number of infrastructure nodes")
    subscription_name: Optional[str] = None
    monthly_price: Optional[Decimal] = Field(None, ge=0)
    seat_overage_rate: Optional[Decimal] = Field(None, ge=0)
    node_overage_rate: Optional[Decimal] = Field(None, ge=0)
    is_enforced: Optional[bool] = None
    status: Optional[str] = Field(None, description="active, suspended, expired, cancelled")
    expires_at: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    notes: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Response model for subscription"""
    id: int
    tenant_id: int
    tenant_name: str
    license_plan_id: Optional[int]
    license_plan_name: Optional[str]
    max_seats: int
    max_nodes: int
    current_seats: int
    current_nodes: int
    seats_remaining: int
    nodes_remaining: int
    seats_exceeded: bool
    nodes_exceeded: bool
    subscription_name: Optional[str]
    monthly_price: float
    seat_overage_rate: float
    node_overage_rate: float
    status: str
    is_enforced: bool
    is_active: bool
    started_at: datetime
    expires_at: Optional[datetime]
    auto_renew: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new subscription for a tenant"""
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == subscription_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if subscription already exists
    existing = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == subscription_data.tenant_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenant already has a subscription. Update existing subscription instead.")
    
    # If license_plan_id is provided, load plan and use defaults
    license_plan = None
    if subscription_data.license_plan_id:
        license_plan = db.query(LicensePlan).filter(
            LicensePlan.id == subscription_data.license_plan_id,
            LicensePlan.is_active == True
        ).first()
        if not license_plan:
            raise HTTPException(status_code=404, detail="License plan not found or inactive")
    
    # Use plan defaults if license plan is provided, otherwise use provided values
    max_seats = license_plan.default_max_seats if license_plan else subscription_data.max_seats
    max_nodes = license_plan.default_max_nodes if license_plan else subscription_data.max_nodes
    monthly_price = Decimal(license_plan.default_monthly_price) if license_plan and license_plan.default_monthly_price and license_plan.default_monthly_price != "custom" else subscription_data.monthly_price
    
    # Create subscription
    subscription = TenantSubscription(
        tenant_id=subscription_data.tenant_id,
        license_plan_id=subscription_data.license_plan_id,
        max_seats=max_seats,
        max_nodes=max_nodes,
        subscription_name=subscription_data.subscription_name or (license_plan.plan_name if license_plan else None),
        monthly_price=monthly_price,
        seat_overage_rate=subscription_data.seat_overage_rate,
        node_overage_rate=subscription_data.node_overage_rate,
        is_enforced=subscription_data.is_enforced,
        expires_at=subscription_data.expires_at,
        auto_renew=subscription_data.auto_renew,
        notes=subscription_data.notes,
        created_by=current_admin.id,
        status="active"
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Update initial usage
    tracker = SubscriptionTracker(db)
    tracker.update_usage(subscription_data.tenant_id)
    db.refresh(subscription)
    
    logger.info(f"Super admin {current_admin.email} created subscription for tenant {tenant.name}: {subscription_data.max_seats} seats, {subscription_data.max_nodes} nodes")
    
    # Get license plan name if available
    license_plan_name = None
    if subscription.license_plan_id:
        plan = db.query(LicensePlan).filter(LicensePlan.id == subscription.license_plan_id).first()
        license_plan_name = plan.plan_name if plan else None
    
    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        tenant_name=tenant.name,
        license_plan_id=subscription.license_plan_id,
        license_plan_name=license_plan_name,
        max_seats=subscription.max_seats,
        max_nodes=subscription.max_nodes,
        current_seats=subscription.current_seats,
        current_nodes=subscription.current_nodes,
        seats_remaining=subscription.seats_remaining,
        nodes_remaining=subscription.nodes_remaining,
        seats_exceeded=subscription.seats_exceeded,
        nodes_exceeded=subscription.nodes_exceeded,
        subscription_name=subscription.subscription_name,
        monthly_price=float(subscription.monthly_price),
        seat_overage_rate=float(subscription.seat_overage_rate),
        node_overage_rate=float(subscription.node_overage_rate),
        status=subscription.status,
        is_enforced=subscription.is_enforced,
        is_active=subscription.is_active,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew,
        notes=subscription.notes,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at
    )


@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    tenant_id: Optional[int] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all subscriptions"""
    try:
        query = db.query(TenantSubscription)
        
        if tenant_id:
            query = query.filter(TenantSubscription.tenant_id == tenant_id)
        if status:
            query = query.filter(TenantSubscription.status == status)
        
        subscriptions = query.all()
        
        # Update usage for all subscriptions
        tracker = SubscriptionTracker(db)
        results = []
        for sub in subscriptions:
            try:
                tracker.update_usage(sub.tenant_id)
                db.refresh(sub)
            except Exception as e:
                logger.warning(f"Error updating usage for tenant {sub.tenant_id}: {e}")
            
            tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
            
            # Get license plan name if available (gracefully handle if LicensePlan table doesn't exist)
            license_plan_name = None
            try:
                if sub.license_plan_id:
                    plan = db.query(LicensePlan).filter(LicensePlan.id == sub.license_plan_id).first()
                    license_plan_name = plan.plan_name if plan else None
            except Exception as e:
                logger.warning(f"Could not fetch license plan {sub.license_plan_id}: {e}")
                license_plan_name = None
        
        results.append(SubscriptionResponse(
            id=sub.id,
            tenant_id=sub.tenant_id,
            tenant_name=tenant.name if tenant else "Unknown",
            license_plan_id=sub.license_plan_id,
            license_plan_name=license_plan_name,
            max_seats=sub.max_seats,
            max_nodes=sub.max_nodes,
            current_seats=sub.current_seats,
            current_nodes=sub.current_nodes,
            seats_remaining=sub.seats_remaining,
            nodes_remaining=sub.nodes_remaining,
            seats_exceeded=sub.seats_exceeded,
            nodes_exceeded=sub.nodes_exceeded,
            subscription_name=sub.subscription_name,
            monthly_price=float(sub.monthly_price),
            seat_overage_rate=float(sub.seat_overage_rate),
            node_overage_rate=float(sub.node_overage_rate),
            status=sub.status,
            is_enforced=sub.is_enforced,
            is_active=sub.is_active,
            started_at=sub.started_at,
            expires_at=sub.expires_at,
            auto_renew=sub.auto_renew,
            notes=sub.notes,
            created_at=sub.created_at,
            updated_at=sub.updated_at
            ))
        
        return results
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list subscriptions: {str(e)}")


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get subscription details"""
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update usage
    tracker = SubscriptionTracker(db)
    tracker.update_usage(subscription.tenant_id)
    db.refresh(subscription)
    
    tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
    
    # Get license plan name if available
    license_plan_name = None
    if subscription.license_plan_id:
        plan = db.query(LicensePlan).filter(LicensePlan.id == subscription.license_plan_id).first()
        license_plan_name = plan.plan_name if plan else None
    
    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        license_plan_id=subscription.license_plan_id,
        license_plan_name=license_plan_name,
        max_seats=subscription.max_seats,
        max_nodes=subscription.max_nodes,
        current_seats=subscription.current_seats,
        current_nodes=subscription.current_nodes,
        seats_remaining=subscription.seats_remaining,
        nodes_remaining=subscription.nodes_remaining,
        seats_exceeded=subscription.seats_exceeded,
        nodes_exceeded=subscription.nodes_exceeded,
        subscription_name=subscription.subscription_name,
        monthly_price=float(subscription.monthly_price),
        seat_overage_rate=float(subscription.seat_overage_rate),
        node_overage_rate=float(subscription.node_overage_rate),
        status=subscription.status,
        is_enforced=subscription.is_enforced,
        is_active=subscription.is_active,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew,
        notes=subscription.notes,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at
    )


@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update subscription"""
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # If license_plan_id is provided, load plan and update defaults
    if subscription_data.license_plan_id is not None:
        license_plan = db.query(LicensePlan).filter(
            LicensePlan.id == subscription_data.license_plan_id,
            LicensePlan.is_active == True
        ).first()
        if not license_plan:
            raise HTTPException(status_code=404, detail="License plan not found or inactive")
        
        subscription.license_plan_id = subscription_data.license_plan_id
        # Update limits to plan defaults if not explicitly provided
        if subscription_data.max_seats is None:
            subscription.max_seats = license_plan.default_max_seats
        if subscription_data.max_nodes is None:
            subscription.max_nodes = license_plan.default_max_nodes
        if subscription_data.monthly_price is None and license_plan.default_monthly_price and license_plan.default_monthly_price != "custom":
            subscription.monthly_price = Decimal(license_plan.default_monthly_price)
    
    # Update fields
    if subscription_data.max_seats is not None:
        subscription.max_seats = subscription_data.max_seats
    if subscription_data.max_nodes is not None:
        subscription.max_nodes = subscription_data.max_nodes
    if subscription_data.subscription_name is not None:
        subscription.subscription_name = subscription_data.subscription_name
    if subscription_data.monthly_price is not None:
        subscription.monthly_price = subscription_data.monthly_price
    if subscription_data.seat_overage_rate is not None:
        subscription.seat_overage_rate = subscription_data.seat_overage_rate
    if subscription_data.node_overage_rate is not None:
        subscription.node_overage_rate = subscription_data.node_overage_rate
    if subscription_data.is_enforced is not None:
        subscription.is_enforced = subscription_data.is_enforced
    if subscription_data.status is not None:
        subscription.status = subscription_data.status
    if subscription_data.expires_at is not None:
        subscription.expires_at = subscription_data.expires_at
    if subscription_data.auto_renew is not None:
        subscription.auto_renew = subscription_data.auto_renew
    if subscription_data.notes is not None:
        subscription.notes = subscription_data.notes
    
    db.commit()
    db.refresh(subscription)
    
    # Update usage
    tracker = SubscriptionTracker(db)
    tracker.update_usage(subscription.tenant_id)
    db.refresh(subscription)
    
    tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
    
    # Get license plan name if available
    license_plan_name = None
    if subscription.license_plan_id:
        plan = db.query(LicensePlan).filter(LicensePlan.id == subscription.license_plan_id).first()
        license_plan_name = plan.plan_name if plan else None
    
    logger.info(f"Super admin {current_admin.email} updated subscription {subscription_id}")
    
    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        license_plan_id=subscription.license_plan_id,
        license_plan_name=license_plan_name,
        max_seats=subscription.max_seats,
        max_nodes=subscription.max_nodes,
        current_seats=subscription.current_seats,
        current_nodes=subscription.current_nodes,
        seats_remaining=subscription.seats_remaining,
        nodes_remaining=subscription.nodes_remaining,
        seats_exceeded=subscription.seats_exceeded,
        nodes_exceeded=subscription.nodes_exceeded,
        subscription_name=subscription.subscription_name,
        monthly_price=float(subscription.monthly_price),
        seat_overage_rate=float(subscription.seat_overage_rate),
        node_overage_rate=float(subscription.node_overage_rate),
        status=subscription.status,
        is_enforced=subscription.is_enforced,
        is_active=subscription.is_active,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew,
        notes=subscription.notes,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at
    )


@router.get("/tenant/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get usage summary for a tenant"""
    tracker = SubscriptionTracker(db)
    return tracker.get_usage_summary(tenant_id)


