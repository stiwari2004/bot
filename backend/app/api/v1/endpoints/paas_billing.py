"""
PaaS billing endpoints (central Resolvify only).

Edge servers POST synced user data for billing. Requires X-Paas-API-Key.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.models.paas_synced_user import PaasSyncedUser

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


class SyncUserItem(BaseModel):
    id: int | None = None
    email: str
    full_name: str | None = None
    role: str | None = None
    tenant_id: int | None = None
    node_details: dict | None = None


class SyncUsersRequest(BaseModel):
    tenant_id: int
    users: list[SyncUserItem]


@router.post("/billing/sync-users")
def sync_users(
    body: SyncUsersRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_paas_api_key),
):
    """
    Upsert users synced from edge for billing. Keyed by (tenant_id, email).
    """
    now = datetime.now(timezone.utc)
    for u in body.users:
        existing = (
            db.query(PaasSyncedUser)
            .filter(PaasSyncedUser.tenant_id == body.tenant_id, PaasSyncedUser.email == u.email)
            .first()
        )
        if existing:
            existing.edge_user_id = u.id
            existing.full_name = u.full_name
            existing.role = u.role
            existing.node_details = u.node_details
            existing.synced_at = now
            existing.source = "paas_edge"
        else:
            row = PaasSyncedUser(
                tenant_id=body.tenant_id,
                edge_user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                node_details=u.node_details,
                synced_at=now,
                source="paas_edge",
            )
            db.add(row)
    db.commit()
    return {"synced": len(body.users)}
