"""
Subscriptions — CRUD endpoints (Super Admin only)
"""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.services.license.license_activation_service import LicenseActivationService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SubscriptionCreate(BaseModel):
    tenant_id: int = Field(..., description="Tenant ID to assign subscription to")
    license_plan_id: Optional[int] = Field(None)
    max_seats: int = Field(..., gt=0)
    max_nodes: int = Field(..., gt=0)
    subscription_name: Optional[str] = None
    monthly_price: Decimal = Field(0.00, ge=0)
    seat_overage_rate: Decimal = Field(0.00, ge=0)
    node_overage_rate: Decimal = Field(0.00, ge=0)
    is_enforced: bool = Field(True)
    expires_at: Optional[datetime] = None
    auto_renew: bool = Field(True)
    notes: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    license_plan_id: Optional[int] = None
    max_seats: Optional[int] = Field(None, gt=0)
    max_nodes: Optional[int] = Field(None, gt=0)
    subscription_name: Optional[str] = None
    monthly_price: Optional[Decimal] = Field(None, ge=0)
    seat_overage_rate: Optional[Decimal] = Field(None, ge=0)
    node_overage_rate: Optional[Decimal] = Field(None, ge=0)
    is_enforced: Optional[bool] = None
    status: Optional[str] = None
    expires_at: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    notes: Optional[str] = None


class SubscriptionResponse(BaseModel):
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
    license_key: Optional[str] = None
    is_activated: bool = False
    started_at: datetime
    expires_at: Optional[datetime]
    auto_renew: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


def _build_response(sub: TenantSubscription, tenant: Tenant, license_plan_name: Optional[str]) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id, tenant_id=sub.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        license_plan_id=sub.license_plan_id, license_plan_name=license_plan_name,
        max_seats=sub.max_seats, max_nodes=sub.max_nodes,
        current_seats=sub.current_seats, current_nodes=sub.current_nodes,
        seats_remaining=sub.seats_remaining, nodes_remaining=sub.nodes_remaining,
        seats_exceeded=sub.seats_exceeded, nodes_exceeded=sub.nodes_exceeded,
        subscription_name=sub.subscription_name,
        monthly_price=float(sub.monthly_price),
        seat_overage_rate=float(sub.seat_overage_rate),
        node_overage_rate=float(sub.node_overage_rate),
        status=sub.status, is_enforced=sub.is_enforced, is_active=sub.is_active,
        license_key=sub.license_key, is_activated=sub.is_activated,
        started_at=sub.started_at, expires_at=sub.expires_at,
        auto_renew=sub.auto_renew, notes=sub.notes,
        created_at=sub.created_at, updated_at=sub.updated_at,
    )


def _get_plan_name(db: Session, license_plan_id: Optional[int]) -> Optional[str]:
    if not license_plan_id:
        return None
    try:
        plan = db.query(LicensePlan).filter(LicensePlan.id == license_plan_id).first()
        return plan.plan_name if plan else None
    except Exception as e:
        logger.warning(f"Could not fetch license plan {license_plan_id}: {e}")
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new subscription for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == subscription_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == subscription_data.tenant_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant already has a subscription. Update existing subscription instead.")

    license_plan = None
    if subscription_data.license_plan_id:
        license_plan = db.query(LicensePlan).filter(
            LicensePlan.id == subscription_data.license_plan_id,
            LicensePlan.is_active == True
        ).first()
        if not license_plan:
            raise HTTPException(status_code=404, detail="License plan not found or inactive")

    max_seats = license_plan.default_max_seats if license_plan else subscription_data.max_seats
    max_nodes = license_plan.default_max_nodes if license_plan else subscription_data.max_nodes
    monthly_price = (
        Decimal(license_plan.default_monthly_price)
        if license_plan and license_plan.default_monthly_price and license_plan.default_monthly_price != "custom"
        else subscription_data.monthly_price
    )

    license_key = None
    if (tenant.deployment_type or "").lower() == "paas":
        license_key = LicenseActivationService(db).generate_license_key()
        logger.info(f"Generated license key for PaaS tenant {tenant.name}: {license_key}")

    subscription = TenantSubscription(
        tenant_id=subscription_data.tenant_id,
        license_plan_id=subscription_data.license_plan_id,
        max_seats=max_seats, max_nodes=max_nodes,
        subscription_name=subscription_data.subscription_name or (license_plan.plan_name if license_plan else None),
        monthly_price=monthly_price,
        seat_overage_rate=subscription_data.seat_overage_rate,
        node_overage_rate=subscription_data.node_overage_rate,
        is_enforced=subscription_data.is_enforced,
        expires_at=subscription_data.expires_at,
        auto_renew=subscription_data.auto_renew,
        notes=subscription_data.notes,
        created_by=current_admin.id,
        status="active",
        license_key=license_key,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    SubscriptionTracker(db).update_usage(subscription_data.tenant_id)
    db.refresh(subscription)

    logger.info(f"Super admin {current_admin.email} created subscription for tenant {tenant.name}")
    return _build_response(subscription, tenant, _get_plan_name(db, subscription.license_plan_id))


@router.get("", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    tenant_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
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

        tracker = SubscriptionTracker(db)
        results = []
        for sub in subscriptions:
            try:
                tracker.update_usage(sub.tenant_id)
                db.refresh(sub)
            except Exception as e:
                logger.warning(f"Error updating usage for tenant {sub.tenant_id}: {e}")
            tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
            results.append(_build_response(sub, tenant, _get_plan_name(db, sub.license_plan_id)))
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

    SubscriptionTracker(db).update_usage(subscription.tenant_id)
    db.refresh(subscription)

    tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
    return _build_response(subscription, tenant, _get_plan_name(db, subscription.license_plan_id))
