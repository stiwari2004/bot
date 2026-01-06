"""
License activation endpoints for PaaS deployments
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.services.license.license_activation_service import LicenseActivationService
from app.models.tenant_subscription import TenantSubscription
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class LicenseActivationRequest(BaseModel):
    """Request model for license activation"""
    license_key: str


class LicenseActivationResponse(BaseModel):
    """Response model for license activation"""
    success: bool
    message: Optional[str] = None
    license_key: Optional[str] = None
    activated_at: Optional[str] = None
    server_fingerprint: Optional[str] = None
    server_hostname: Optional[str] = None
    max_seats: Optional[int] = None
    max_nodes: Optional[int] = None


class LicenseStatusResponse(BaseModel):
    """Response model for license status"""
    is_paas_mode: bool
    is_activated: bool
    error: Optional[str] = None
    activation: Optional[dict] = None
    server_info: Optional[dict] = None


@router.post("/activate", response_model=LicenseActivationResponse)
async def activate_license(
    request: LicenseActivationRequest,
    db: Session = Depends(get_db)
):
    """
    Activate a license key on this server instance (PaaS only)
    
    This endpoint binds a license key to the current server's fingerprint.
    Once activated, the license key cannot be used on another server.
    """
    activation_service = LicenseActivationService(db)
    
    if not activation_service.is_paas_mode():
        raise HTTPException(
            status_code=400,
            detail="License activation is only available in PaaS deployment mode"
        )
    
    # Activate license (client IP is optional and not critical)
    success, error, info = activation_service.activate_license(
        license_key=request.license_key,
        activation_ip=None  # IP tracking is optional
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error or "License activation failed")
    
    return LicenseActivationResponse(
        success=True,
        message="License activated successfully",
        license_key=info.get("license_key"),
        activated_at=info.get("activated_at"),
        server_fingerprint=info.get("server_fingerprint"),
        server_hostname=info.get("server_hostname"),
        max_seats=info.get("max_seats"),
        max_nodes=info.get("max_nodes"),
    )


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    db: Session = Depends(get_db)
):
    """
    Get current license activation status
    
    Returns activation status, server info, and license details.
    """
    activation_service = LicenseActivationService(db)
    status = activation_service.get_activation_status()
    
    return LicenseStatusResponse(
        is_paas_mode=status["is_paas_mode"],
        is_activated=status["is_activated"],
        error=status.get("error"),
        activation=status.get("activation"),
        server_info=status.get("server_info"),
    )


@router.get("/telemetry")
async def get_license_telemetry(
    db: Session = Depends(get_db)
):
    """
    Get license usage telemetry (seats, nodes, limits)
    
    This endpoint provides usage statistics for license monitoring.
    """
    activation_service = LicenseActivationService(db)
    
    if not activation_service.is_paas_mode():
        raise HTTPException(
            status_code=400,
            detail="License telemetry is only available in PaaS deployment mode"
        )
    
    # Validate activation
    is_valid, error, info = activation_service.validate_activation()
    if not is_valid:
        raise HTTPException(status_code=403, detail=error or "License not activated")
    
    # Get usage details
    from app.services.subscription.subscription_tracker import SubscriptionTracker
    tracker = SubscriptionTracker(db)
    
    # Find subscription
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.server_fingerprint == info["server_fingerprint"]
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update usage
    current_seats, current_nodes = tracker.update_usage(subscription.tenant_id)
    
    return {
        "license_key": subscription.license_key,
        "activated_at": subscription.activated_at.isoformat() if subscription.activated_at else None,
        "subscription": {
            "max_seats": subscription.max_seats,
            "max_nodes": subscription.max_nodes,
            "current_seats": current_seats,
            "current_nodes": current_nodes,
            "seats_remaining": subscription.seats_remaining,
            "nodes_remaining": subscription.nodes_remaining,
            "seats_usage_percent": round((current_seats / subscription.max_seats * 100) if subscription.max_seats > 0 else 0, 2),
            "nodes_usage_percent": round((current_nodes / subscription.max_nodes * 100) if subscription.max_nodes > 0 else 0, 2),
        },
        "server_info": activation_service.get_activation_status().get("server_info"),
    }

