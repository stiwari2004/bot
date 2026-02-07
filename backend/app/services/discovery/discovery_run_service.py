"""
Discovery run orchestration: create run, call VM manager, upsert assets, set current run.
Lifecycle: current vs history; deterministic run_config.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.discovery_run import DiscoveryRun
from app.models.discovery_asset import DiscoveryAsset
from app.models.tenant import Tenant
from app.services.discovery.vm_manager_connector import get_vm_manager_connector, normalize_asset

logger = logging.getLogger(__name__)


class DiscoveryRunService:
    """Orchestrates discovery runs: VM manager fetch, asset upsert, current run promotion."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def create_run(self, run_config: Dict[str, Any]) -> DiscoveryRun:
        """Create a new discovery run (status=running)."""
        run = DiscoveryRun(
            tenant_id=self.tenant_id,
            run_config=json.dumps(run_config) if run_config else None,
            status="running",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _append_stage(self, run: DiscoveryRun, stage: str, status: str, detail: Optional[str] = None) -> None:
        """Append a stage to stage_log JSON."""
        try:
            log = json.loads(run.stage_log) if run.stage_log else []
        except (json.JSONDecodeError, TypeError):
            log = []
        log.append({"stage": stage, "status": status, "detail": detail, "at": datetime.now(timezone.utc).isoformat()})
        run.stage_log = json.dumps(log)
        self.db.add(run)
        self.db.commit()

    def complete_run(self, run: DiscoveryRun, status: str = "success", error_detail: Optional[str] = None) -> None:
        """Mark run completed and optionally set as current."""
        run.completed_at = datetime.now(timezone.utc)
        run.status = status
        if error_detail:
            self._append_stage(run, "complete", status, error_detail)
        self.db.add(run)
        self.db.commit()
        if status == "success":
            self._set_current_run(run.id)

    def _set_current_run(self, run_id: int) -> None:
        """Set tenant.current_discovery_run_id to this run."""
        tenant = self.db.query(Tenant).filter(Tenant.id == self.tenant_id).first()
        if tenant:
            tenant.current_discovery_run_id = run_id
            self.db.add(tenant)
            self.db.commit()

    def upsert_assets_from_normalized(
        self,
        run_id: int,
        normalized_assets: List[Dict[str, Any]],
    ) -> int:
        """Upsert discovery_asset from normalized VM list; set current_run_id. Returns count upserted."""
        count = 0
        for na in normalized_assets:
            source = na.get("source") or "azure"
            source_native_id = na.get("source_native_id") or ""
            if not source_native_id:
                continue
            existing = (
                self.db.query(DiscoveryAsset)
                .filter(
                    DiscoveryAsset.tenant_id == self.tenant_id,
                    DiscoveryAsset.source == source,
                    DiscoveryAsset.source_native_id == source_native_id,
                )
                .first()
            )
            meta = na.get("meta") or {}
            tags = na.get("tags") or {}
            if existing:
                existing.primary_ip = na.get("primary_ip")
                existing.ips = json.dumps(na.get("ips") or [])
                existing.name = na.get("name")
                existing.tags = json.dumps(tags)
                existing.current_run_id = run_id
                existing.updated_at = datetime.now(timezone.utc)
                self.db.add(existing)
            else:
                asset = DiscoveryAsset(
                    tenant_id=self.tenant_id,
                    source=source,
                    source_native_id=source_native_id,
                    primary_ip=na.get("primary_ip"),
                    ips=json.dumps(na.get("ips") or []),
                    name=na.get("name"),
                    tags=json.dumps(tags),
                    current_run_id=run_id,
                )
                self.db.add(asset)
            count += 1
        self.db.commit()
        return count

    async def run_discovery_from_vm_manager(
        self,
        run_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Start a discovery run: create run, call VM manager connector, upsert assets, complete run.
        run_config must include: manager_type (e.g. 'azure'), connection_id; optional: subscription_id, scope.
        """
        run = self.create_run(run_config)
        run_id = run.id
        manager_type = run_config.get("manager_type") or "azure"
        connection_id = run_config.get("connection_id")
        subscription_id = run_config.get("subscription_id")
        scope = run_config.get("scope")

        try:
            self._append_stage(run, "vm_manager_fetch", "started")
            connector = get_vm_manager_connector(self.db, self.tenant_id, manager_type)
            if not connector:
                self.complete_run(run, status="failed", error_detail=f"Unsupported manager_type: {manager_type}")
                return {"run_id": run_id, "status": "failed", "error": f"Unsupported manager_type: {manager_type}"}

            normalized = await connector.list_vms(
                connection_id=connection_id,
                subscription_id=subscription_id,
                scope=scope,
            )
            self._append_stage(run, "vm_manager_fetch", "success", detail=f"{len(normalized)} VMs")
            count = self.upsert_assets_from_normalized(run_id, normalized)
            self._append_stage(run, "merge", "success", detail=f"{count} assets upserted")
            self.complete_run(run, status="success")
            return {
                "run_id": run_id,
                "status": "success",
                "assets_count": count,
            }
        except Exception as e:
            logger.exception("Discovery run failed")
            self._append_stage(run, "vm_manager_fetch", "failed", detail=str(e))
            self.complete_run(run, status="failed", error_detail=str(e))
            return {"run_id": run_id, "status": "failed", "error": str(e)}

    def get_current_run_id(self) -> Optional[int]:
        """Return tenant.current_discovery_run_id or latest successful run."""
        tenant = self.db.query(Tenant).filter(Tenant.id == self.tenant_id).first()
        if tenant and tenant.current_discovery_run_id:
            return tenant.current_discovery_run_id
        run = (
            self.db.query(DiscoveryRun)
            .filter(DiscoveryRun.tenant_id == self.tenant_id, DiscoveryRun.status == "success")
            .order_by(DiscoveryRun.completed_at.desc())
            .first()
        )
        return run.id if run else None
