"""
Discovery API: runs, assets, current run, adopt into infrastructure, ingest (gateway/agent).
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.discovery_run import DiscoveryRun
from app.models.discovery_asset import DiscoveryAsset
from app.models.credential import InfrastructureConnection, Credential
from app.services.auth import get_current_user
from app.services.discovery.discovery_run_service import DiscoveryRunService
from app.services.discovery.discovery_ingest_service import DiscoveryIngestService, get_tenant_id_by_ingest_token
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


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


@router.post("/run")
async def start_discovery_run(
    body: DiscoveryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a discovery run from a VM manager (e.g. Azure)."""
    service = DiscoveryRunService(db, tenant_id=current_user.tenant_id)
    run_config = {
        "manager_type": body.manager_type,
        "connection_id": body.connection_id,
        "subscription_id": body.subscription_id,
        "scope": body.scope,
    }
    result = await service.run_discovery_from_vm_manager(run_config)
    return result


@router.get("/runs")
async def list_discovery_runs(
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """Get current run id and summary (for 'current' vs 'history' lifecycle)."""
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
    current_user: User = Depends(get_current_user),
):
    """List discovered assets. If run_id omitted, use current run."""
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
    current_user: User = Depends(get_current_user),
):
    """Create InfrastructureConnection from a discovered asset (adopt into infrastructure)."""
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


@router.post("/ingest")
async def ingest_discovery_payload(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    x_discovery_token: Optional[str] = Header(None, alias="X-Discovery-Token"),
    authorization: Optional[str] = Header(None),
):
    """
    Ingest payload from scanner gateway/agent. Auth via X-Discovery-Token (or Bearer in Authorization).
    Token must match tenant.config_metadata["discovery_ingest_token"].
    Payload: { asset: { source, source_native_id, ... }, components?: [], outbound_connections?: [] }
    """
    token = x_discovery_token or (authorization.replace("Bearer ", "").strip() if authorization else None)
    tenant_id = get_tenant_id_by_ingest_token(db, token) if token else None
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or missing discovery ingest token")
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id required in payload")
    run = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id, DiscoveryRun.tenant_id == tenant_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Discovery run not found")
    asset_data = payload.get("asset") or payload
    if isinstance(asset_data, dict):
        ingest_svc = DiscoveryIngestService(db, tenant_id=tenant_id)
        result = ingest_svc.ingest_asset_payload(run_id=run_id, payload=asset_data)
        return result
    raise HTTPException(status_code=400, detail="payload.asset required")
