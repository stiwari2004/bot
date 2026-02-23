"""
PaaS auth endpoints (central Resolvify only).

Used by edge/jump servers to validate tenant-admin/MSP login.
Requires X-Paas-API-Key header matching PAAS_EDGE_API_KEY.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.auth import authenticate_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription

router = APIRouter()


def _require_paas_api_key(x_paas_api_key: str | None = Header(None, alias="X-Paas-API-Key")):
    """Require valid X-Paas-API-Key (central: PAAS_EDGE_API_KEY)."""
    key = (getattr(settings, "PAAS_EDGE_API_KEY", None) or "").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PaaS API key not configured on central",
        )
    if not x_paas_api_key or (x_paas_api_key or "").strip() != key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Paas-API-Key",
        )


class ValidateLoginRequest(BaseModel):
    username: str  # email
    password: str


@router.post("/validate-login")
def validate_login(
    body: ValidateLoginRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_paas_api_key),
):
    """
    Validate tenant-admin/MSP credentials. Returns user + tenant + limits on success.
    Edge calls this before creating/updating local user and issuing JWT.
    """
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    # Only allow tenant_admin, msp_admin, or legacy admin (with tenant)
    if user.role not in ("tenant_admin", "msp_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant or MSP admins can log in via PaaS",
        )
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found",
        )
    max_seats = 0
    max_nodes = 0
    sub = (
        db.query(TenantSubscription)
        .filter(
            TenantSubscription.tenant_id == user.tenant_id,
            TenantSubscription.status == "active",
        )
        .first()
    )
    if sub:
        max_seats = sub.max_seats or 0
        max_nodes = sub.max_nodes or 0
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "tenant": {"id": tenant.id, "name": tenant.name, "is_msp": bool(tenant.is_msp)},
        "limits": {"max_seats": max_seats, "max_nodes": max_nodes},
    }
