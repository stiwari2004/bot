"""
License endpoints for token-based activation and validation.
Used by worker registration and session create for enforcement.
Unauthenticated for activation; token in body.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.services.license.license_service import LicenseService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ActivateRequest(BaseModel):
    """Request for token activation (worker startup or backend bootstrap)"""
    token: str


class ActivateResponse(BaseModel):
    """Response from token activation"""
    success: bool
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    is_active: bool = False
    max_nodes: Optional[int] = None
    max_seats: Optional[int] = None
    current_nodes: Optional[int] = None
    current_seats: Optional[int] = None
    error: Optional[str] = None


class ValidateRequest(BaseModel):
    """Request for tenant license re-validation"""
    tenant_id: int


class ValidateResponse(BaseModel):
    """Response from tenant validation"""
    is_valid: bool
    tenant_id: Optional[int] = None
    is_active: bool = False
    max_nodes: Optional[int] = None
    current_nodes: Optional[int] = None
    nodes_remaining: Optional[int] = None
    has_subscription: Optional[bool] = None
    unlimited: Optional[bool] = None
    error: Optional[str] = None


class CheckNodeRequest(BaseModel):
    """Request to check if tenant can add node"""
    tenant_id: int


class CheckNodeResponse(BaseModel):
    """Response from node limit check"""
    allowed: bool
    error: Optional[str] = None


@router.post("/activate", response_model=ActivateResponse)
async def activate(
    request: ActivateRequest,
    db: Session = Depends(get_db),
):
    """
    Validate activation token and return tenant_id + activation info.
    Called at worker startup or backend bootstrap.
    Unauthenticated; token provided in body.
    """
    service = LicenseService(db)
    success, error, info = service.activate(request.token)
    if not success:
        return ActivateResponse(success=False, error=error)
    return ActivateResponse(
        success=True,
        tenant_id=info["tenant_id"],
        tenant_name=info.get("tenant_name"),
        is_active=info.get("is_active", True),
        max_nodes=info.get("max_nodes"),
        max_seats=info.get("max_seats"),
        current_nodes=info.get("current_nodes"),
        current_seats=info.get("current_seats"),
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate(
    request: ValidateRequest,
    db: Session = Depends(get_db),
):
    """
    Re-validate license for a tenant (e.g. periodic worker heartbeat).
    """
    service = LicenseService(db)
    is_valid, error, info = service.validate(request.tenant_id)
    if not is_valid:
        return ValidateResponse(is_valid=False, error=error)
    if info and info.get("has_subscription") is False:
        return ValidateResponse(
            is_valid=True,
            has_subscription=False,
            unlimited=info.get("unlimited", True),
        )
    return ValidateResponse(
        is_valid=True,
        tenant_id=info.get("tenant_id"),
        is_active=info.get("is_active", True),
        max_nodes=info.get("max_nodes"),
        current_nodes=info.get("current_nodes"),
        nodes_remaining=info.get("nodes_remaining"),
        has_subscription=True,
    )


@router.post("/check-node", response_model=CheckNodeResponse)
async def check_node(
    request: CheckNodeRequest,
    db: Session = Depends(get_db),
):
    """
    Check if tenant can add another node (infrastructure connection).
    """
    service = LicenseService(db)
    allowed, error = service.check_node_limit(request.tenant_id)
    return CheckNodeResponse(allowed=allowed, error=error)
