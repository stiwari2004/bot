"""
VM Manager Connector interface and implementations.
Returns normalized asset list (L1) for discovery runs.
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Normalized VM/asset shape returned by any VM manager connector
NORMALIZED_ASSET_KEYS = (
    "source",
    "source_native_id",
    "name",
    "primary_ip",
    "ips",
    "tags",
    "meta",
)


def normalize_asset(
    source: str,
    source_native_id: str,
    name: Optional[str] = None,
    primary_ip: Optional[str] = None,
    ips: Optional[List[str]] = None,
    tags: Optional[Dict[str, str]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a normalized asset dict for discovery_asset upsert."""
    return {
        "source": source,
        "source_native_id": source_native_id,
        "name": name,
        "primary_ip": primary_ip or None,
        "ips": ips or [],
        "tags": tags or {},
        "meta": meta or {},
    }


class VMManagerConnector(ABC):
    """Abstract VM manager connector. Implementations: Azure, vCenter, AWS, GCP, etc."""

    @property
    @abstractmethod
    def source(self) -> str:
        """Source identifier (e.g. 'azure', 'vcenter')."""
        pass

    @abstractmethod
    async def list_vms(
        self,
        connection_id: int,
        subscription_id: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List VMs from this manager. Returns list of normalized asset dicts.
        scope: optional filter (e.g. folder IDs, tag filter) per connector.
        """
        pass


class AzureVMManagerConnector(VMManagerConnector):
    """VM manager connector for Azure. Uses existing CloudDiscoveryService."""

    def __init__(self, db, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    @property
    def source(self) -> str:
        return "azure"

    async def list_vms(
        self,
        connection_id: int,
        subscription_id: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        from app.services.cloud_discovery import CloudDiscoveryService

        vms = await CloudDiscoveryService.list_azure_vms(
            db=self.db,
            subscription_id=subscription_id,
            tenant_id=self.tenant_id,
        )
        # Filter to this connection if we have connection_id
        if connection_id is not None:
            vms = [v for v in vms if v.get("connection_id") == connection_id]
        normalized = []
        for v in vms:
            resource_id = v.get("resource_id") or ""
            name = v.get("name")
            meta = {
                "resource_group": v.get("resource_group"),
                "location": v.get("location"),
                "vm_size": v.get("vm_size"),
                "os_type": v.get("os_type"),
                "power_state": v.get("power_state"),
                "provisioning_state": v.get("provisioning_state"),
                "subscription_id": v.get("subscription_id"),
            }
            # Azure list_all does not include private IP; would need network API for that
            primary_ip = None
            ips = []
            normalized.append(
                normalize_asset(
                    source=self.source,
                    source_native_id=resource_id,
                    name=name,
                    primary_ip=primary_ip,
                    ips=ips,
                    tags={},
                    meta=meta,
                )
            )
        return normalized


def get_vm_manager_connector(
    db,
    tenant_id: int,
    manager_type: str,
) -> Optional[VMManagerConnector]:
    """Factory: return connector for manager_type (azure, vcenter, ...)."""
    if manager_type in ("azure", "azure_subscription", "cloud_account"):
        return AzureVMManagerConnector(db=db, tenant_id=tenant_id)
    # vcenter, aws, gcp: add when implemented
    return None
