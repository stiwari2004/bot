"""
Discovery ingest: accept payloads from scanner gateway/agent.
Validates token -> tenant; stores or normalizes payload (L2/L3 in later phases).
"""
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.discovery_run import DiscoveryRun
from app.models.discovery_asset import DiscoveryAsset

logger = logging.getLogger(__name__)


def get_tenant_id_by_ingest_token(db: Session, token: str) -> Optional[int]:
    """
    Resolve tenant_id from ingest token.
    Token can be stored in tenant.config_metadata["discovery_ingest_token"] or a dedicated table later.
    """
    if not token:
        return None
    tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
    for t in tenants:
        config = t.config_metadata or {}
        if isinstance(config, dict) and config.get("discovery_ingest_token") == token:
            return t.id
    return None


class DiscoveryIngestService:
    """Process ingest payloads from gateway/agent."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def ingest_asset_payload(
        self,
        run_id: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ingest a single asset payload (e.g. from agent).
        Payload: { source, source_native_id, name?, primary_ip?, ips?, tags?, components?, outbound_connections? }
        For Phase 1 we only upsert L1 asset; components/edges in Phase 2.
        """
        source = payload.get("source") or "discovered_via_connection"
        source_native_id = payload.get("source_native_id") or ""
        if not source_native_id:
            return {"ok": False, "error": "source_native_id required"}
        fingerprint = payload.get("fingerprint")
        name = payload.get("name")
        primary_ip = payload.get("primary_ip")
        ips = payload.get("ips") or []
        tags = payload.get("tags") or {}
        existing = (
            self.db.query(DiscoveryAsset)
            .filter(
                DiscoveryAsset.tenant_id == self.tenant_id,
                DiscoveryAsset.source == source,
                DiscoveryAsset.source_native_id == source_native_id,
            )
            .first()
        )
        if existing:
            existing.primary_ip = primary_ip
            existing.ips = json.dumps(ips)
            existing.name = name
            existing.tags = json.dumps(tags)
            existing.fingerprint = fingerprint
            existing.current_run_id = run_id
            self.db.add(existing)
        else:
            asset = DiscoveryAsset(
                tenant_id=self.tenant_id,
                source=source,
                source_native_id=source_native_id,
                fingerprint=fingerprint,
                primary_ip=primary_ip,
                ips=json.dumps(ips),
                name=name,
                tags=json.dumps(tags),
                current_run_id=run_id,
            )
            self.db.add(asset)
        self.db.commit()
        return {"ok": True}
