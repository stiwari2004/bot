"""
Tenant Admin Discovery: staging, approval, create assets. Token for agent.
Only tenant_admin / msp_admin / super_admin. Ingest is token-only (no session).
"""
import io
import json
import os
import secrets
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.models.tenant import Tenant
from app.models.discovery_run import DiscoveryRun
from app.models.discovery_asset import DiscoveryAsset
from app.models.credential import InfrastructureConnection, Credential
from app.services.discovery.discovery_run_service import DiscoveryRunService
from app.services.discovery.discovery_ingest_service import (
    DiscoveryIngestService,
    get_tenant_id_by_ingest_token,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Role check for tenant admin discovery (management endpoints)
TENANT_ADMIN_ROLES = ("tenant_admin", "msp_admin", "super_admin")


def get_current_tenant_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in TENANT_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    return current_user


# --- Request/Response models ---
class DiscoveryRunRequest(BaseModel):
    manager_type: str = "azure"
    connection_id: int
    subscription_id: Optional[str] = None
    scope: Optional[Dict[str, Any]] = None


class AdoptAssetRequest(BaseModel):
    asset_id: int
    credential_id: int
    connection_type: str = "ssh"
    name: Optional[str] = None
    environment: str = "prod"


class AdoptBulkRequest(BaseModel):
    assets: List[AdoptAssetRequest]


# --- Management endpoints (tenant admin only) ---
@router.post("/run")
async def start_discovery_run(
    body: DiscoveryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Start a discovery run from a VM manager (e.g. Azure). Tenant admin only."""
    service = DiscoveryRunService(db, tenant_id=current_user.tenant_id)
    run_config = {
        "manager_type": body.manager_type,
        "connection_id": body.connection_id,
        "subscription_id": body.subscription_id,
        "scope": body.scope,
    }
    return await service.run_discovery_from_vm_manager(run_config)


@router.get("/runs")
async def list_discovery_runs(
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """List discovery runs for the tenant."""
    q = db.query(DiscoveryRun).filter(DiscoveryRun.tenant_id == current_user.tenant_id)
    if status:
        q = q.filter(DiscoveryRun.status == status)
    runs = q.order_by(DiscoveryRun.started_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "run_config": r.run_config,
        }
        for r in runs
    ]


@router.get("/current")
async def get_current_discovery(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Get current run id and summary."""
    service = DiscoveryRunService(db, tenant_id=current_user.tenant_id)
    run_id = service.get_current_run_id()
    if not run_id:
        return {"current_run_id": None, "assets_count": 0}
    count = db.query(DiscoveryAsset).filter(
        DiscoveryAsset.tenant_id == current_user.tenant_id,
        DiscoveryAsset.current_run_id == run_id,
    ).count()
    return {"current_run_id": run_id, "assets_count": count}


@router.get("/assets")
async def list_discovery_assets(
    run_id: Optional[int] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """List discovered (staged) assets. If run_id omitted, use current run."""
    q = db.query(DiscoveryAsset).filter(DiscoveryAsset.tenant_id == current_user.tenant_id)
    if run_id is None:
        service = DiscoveryRunService(db, tenant_id=current_user.tenant_id)
        run_id = service.get_current_run_id()
    if run_id is not None:
        q = q.filter(DiscoveryAsset.current_run_id == run_id)
    if source:
        q = q.filter(DiscoveryAsset.source == source)
    assets = q.all()
    return [
        {
            "id": a.id,
            "source": a.source,
            "source_native_id": a.source_native_id,
            "name": a.name,
            "primary_ip": a.primary_ip,
            "tags": a.tags,
        }
        for a in assets
    ]


@router.post("/adopt")
async def adopt_asset_into_infrastructure(
    body: AdoptAssetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Create one InfrastructureConnection from a discovered asset (Create assets)."""
    asset = (
        db.query(DiscoveryAsset)
        .filter(
            DiscoveryAsset.id == body.asset_id,
            DiscoveryAsset.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Discovery asset not found")
    cred = (
        db.query(Credential)
        .filter(
            Credential.id == body.credential_id,
            Credential.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    name = body.name or asset.name or (asset.primary_ip or asset.source_native_id)
    if not name:
        name = f"asset-{asset.id}"
    meta = {"discovery_asset_id": asset.id}
    conn = InfrastructureConnection(
        tenant_id=current_user.tenant_id,
        credential_id=body.credential_id,
        name=name,
        connection_type=body.connection_type,
        target_host=asset.primary_ip or asset.name,
        environment=body.environment,
        meta_data=json.dumps(meta),
        is_active=True,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"infrastructure_connection_id": conn.id, "name": conn.name}


@router.post("/adopt-bulk")
async def adopt_bulk_into_infrastructure(
    body: AdoptBulkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Create InfrastructureConnection for multiple discovered assets."""
    results = []
    for item in body.assets:
        asset = (
            db.query(DiscoveryAsset)
            .filter(
                DiscoveryAsset.id == item.asset_id,
                DiscoveryAsset.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not asset:
            results.append({"asset_id": item.asset_id, "ok": False, "error": "Asset not found"})
            continue
        cred = (
            db.query(Credential)
            .filter(
                Credential.id == item.credential_id,
                Credential.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not cred:
            results.append({"asset_id": item.asset_id, "ok": False, "error": "Credential not found"})
            continue
        name = item.name or asset.name or (asset.primary_ip or asset.source_native_id) or f"asset-{asset.id}"
        meta = {"discovery_asset_id": asset.id}
        conn = InfrastructureConnection(
            tenant_id=current_user.tenant_id,
            credential_id=item.credential_id,
            name=name,
            connection_type=item.connection_type,
            target_host=asset.primary_ip or asset.name,
            environment=item.environment,
            meta_data=json.dumps(meta),
            is_active=True,
        )
        db.add(conn)
        results.append({"asset_id": item.asset_id, "ok": True, "infrastructure_connection_id": conn.id})
    db.commit()
    return {"results": results}


# --- Token management (tenant admin only) ---
@router.post("/token")
async def create_discovery_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Generate a new discovery ingest token for the agent. Shown once. Tenant admin only."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    token = secrets.token_urlsafe(32)
    config = dict(tenant.config_metadata) if tenant.config_metadata else {}
    config["discovery_ingest_token"] = token
    tenant.config_metadata = config
    db.add(tenant)
    db.commit()
    return {"token": token, "message": "Copy this token; it will not be shown again. Use it in the agent config."}


@router.post("/token/rotate")
async def rotate_discovery_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Rotate discovery ingest token. New token shown once. Tenant admin only."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    token = secrets.token_urlsafe(32)
    config = dict(tenant.config_metadata) if tenant.config_metadata else {}
    config["discovery_ingest_token"] = token
    tenant.config_metadata = config
    db.add(tenant)
    db.commit()
    return {"token": token, "message": "New token generated. Update the agent config. Old token is invalid."}


@router.get("/token/status")
async def get_discovery_token_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin),
):
    """Return whether a discovery token is configured. Does not return the token. Tenant admin only."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    config = tenant.config_metadata or {}
    configured = bool(config.get("discovery_ingest_token"))
    return {"configured": configured}


# --- One-step run script (no auth; user passes URL + token when running the script) ---
@router.get("/run", response_class=PlainTextResponse)
async def get_run_script():
    """
    Returns the one_step.py script so users can run:
      curl -sSL "https://YOUR_APP/api/v1/tenant-admin/discovery/run" -o run.py && python3 run.py "INGEST_URL" "TOKEN"
    One command: install + full discovery (agent + network + storage).
    """
    try:
        # discovery-agent is sibling of backend (bot/discovery-agent, bot/backend)
        this_file = Path(__file__).resolve()
        # endpoints -> v1 -> api -> app -> backend
        backend = this_file.parent.parent.parent.parent.parent
        repo_root = backend.parent
        script_path = repo_root / "discovery-agent" / "one_step.py"
        if script_path.is_file():
            return PlainTextResponse(script_path.read_text(encoding="utf-8"), media_type="text/plain")
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Discovery run script not available")


@router.get("/agent.zip", response_class=Response)
async def get_agent_zip():
    """
    Returns discovery-agent folder as a zip so one_step.py can download and run
    full discovery when not run from inside the repo.
    """
    try:
        this_file = Path(__file__).resolve()
        backend = this_file.parent.parent.parent.parent.parent
        repo_root = backend.parent
        agent_dir = repo_root / "discovery-agent"
        if not agent_dir.is_dir():
            raise HTTPException(status_code=404, detail="Discovery agent package not available")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in agent_dir.rglob("*"):
                if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
                    arcname = f.relative_to(agent_dir.parent)
                    zf.write(f, arcname)
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="application/zip")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Discovery agent package not available")


# --- Ingest (token-only; agent calls this, no session) ---
@router.post("/ingest")
async def ingest_discovery_payload(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    x_discovery_token: Optional[str] = Header(None, alias="X-Discovery-Token"),
    authorization: Optional[str] = Header(None),
):
    """
    Ingest payload from scanner/agent. Auth via X-Discovery-Token or Authorization: Bearer.
    Token must have been created in Tenant Admin → Discovery → Generate token.
    """
    token = x_discovery_token or (authorization.replace("Bearer ", "").strip() if authorization else None)
    tenant_id = get_tenant_id_by_ingest_token(db, token) if token else None
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or missing discovery ingest token")
    run_id = payload.get("run_id")
    if not run_id:
        # Agent-friendly: create an "agent" run and set as current so agent can omit run_id
        service = DiscoveryRunService(db, tenant_id=tenant_id)
        run = service.create_run({"source": "agent", "created_by": "ingest"})
        run_id = run.id
        service._set_current_run(run_id)
    run = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id, DiscoveryRun.tenant_id == tenant_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Discovery run not found")
    asset_data = payload.get("asset") or payload
    if isinstance(asset_data, dict):
        ingest_svc = DiscoveryIngestService(db, tenant_id=tenant_id)
        result = ingest_svc.ingest_asset_payload(run_id=run_id, payload=asset_data)
        return result
    raise HTTPException(status_code=400, detail="payload.asset required")
