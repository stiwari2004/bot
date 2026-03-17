"""
Subscriptions — admin operations: update, license key regeneration, usage (Super Admin only)
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.services.license.license_activation_service import LicenseActivationService
from app.core.logging import get_logger
from app.api.v1.endpoints.subscriptions_crud import (
    SubscriptionUpdate, SubscriptionResponse, _build_response, _get_plan_name,
)

router = APIRouter()
logger = get_logger(__name__)


class RegenerateLicenseKeyResponse(BaseModel):
    license_key: str
    subscription_id: int


@router.post("/{subscription_id}/regenerate-license-key", response_model=RegenerateLicenseKeyResponse)
async def regenerate_subscription_license_key(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Generate a new license key for this subscription (PaaS only, not yet activated)."""
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.id == subscription_id
    ).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
    if not tenant or (tenant.deployment_type or "").lower() != "paas":
        raise HTTPException(
            status_code=400,
            detail="License key is only for PaaS (on-prem) tenants. This subscription's tenant is not PaaS.",
        )
    if subscription.is_activated:
        raise HTTPException(
            status_code=400,
            detail="Cannot regenerate license key: subscription is already activated on a server",
        )

    activation_service = LicenseActivationService(db)
    for _ in range(50):
        key = activation_service.generate_license_key()
        if not db.query(TenantSubscription).filter(TenantSubscription.license_key == key).first():
            subscription.license_key = key
            db.commit()
            db.refresh(subscription)
            logger.info(
                "Super admin %s regenerated license key for subscription %s (tenant_id=%s)",
                current_admin.email, subscription_id, subscription.tenant_id,
            )
            return RegenerateLicenseKeyResponse(license_key=key, subscription_id=subscription_id)

    raise HTTPException(status_code=500, detail="Could not generate a unique license key; try again")


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

    if subscription_data.license_plan_id is not None:
        license_plan = db.query(LicensePlan).filter(
            LicensePlan.id == subscription_data.license_plan_id,
            LicensePlan.is_active == True
        ).first()
        if not license_plan:
            raise HTTPException(status_code=404, detail="License plan not found or inactive")
        subscription.license_plan_id = subscription_data.license_plan_id
        if subscription_data.max_seats is None:
            subscription.max_seats = license_plan.default_max_seats
        if subscription_data.max_nodes is None:
            subscription.max_nodes = license_plan.default_max_nodes
        if (subscription_data.monthly_price is None
                and license_plan.default_monthly_price
                and license_plan.default_monthly_price != "custom"):
            subscription.monthly_price = Decimal(license_plan.default_monthly_price)

    for field in ("max_seats", "max_nodes", "subscription_name", "monthly_price",
                  "seat_overage_rate", "node_overage_rate", "is_enforced",
                  "status", "expires_at", "auto_renew", "notes"):
        value = getattr(subscription_data, field, None)
        if value is not None:
            setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)

    SubscriptionTracker(db).update_usage(subscription.tenant_id)
    db.refresh(subscription)

    tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
    logger.info(f"Super admin {current_admin.email} updated subscription {subscription_id}")
    return _build_response(subscription, tenant, _get_plan_name(db, subscription.license_plan_id))


@router.get("/tenant/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get usage summary for a tenant"""
    return SubscriptionTracker(db).get_usage_summary(tenant_id)
