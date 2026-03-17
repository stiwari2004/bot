"""
Mixin: cloud resource discovery and save operations for ConnectorService
"""
import json
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from app.models.credential import InfrastructureConnection
from app.services.credential_service import get_credential_service
from app.services.cloud_discovery import CloudDiscoveryService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorDiscoveryMixin:
    """Cloud resource discovery operations for ConnectorService."""

    async def discover_cloud_resources(
        self, db: Session, connection_id: int, tenant_id: int
    ) -> Dict[str, Any]:
        """Discover resources (VMs, instances) from a cloud account connection"""
        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True,
        ).first()

        if not infra_conn:
            raise ValueError("Infrastructure connection not found")

        if infra_conn.connection_type not in ["cloud_account", "azure_subscription", "azure_bastion"]:
            raise ValueError(f"Connection type '{infra_conn.connection_type}' does not support resource discovery.")

        subscription_id = None
        if infra_conn.meta_data:
            try:
                conn_meta = json.loads(infra_conn.meta_data)
                subscription_id = conn_meta.get("subscription_id")
            except Exception as e:
                logger.debug(f"Failed to parse connection metadata for subscription_id: {e}")

        if not subscription_id and infra_conn.credential_id:
            try:
                cred_data = get_credential_service().get_credential(db, infra_conn.credential_id, tenant_id)
                if cred_data:
                    subscription_id = cred_data.get("subscription_id")
            except Exception as e:
                logger.warning(f"Could not get subscription_id from credential: {e}")

        logger.info(f"Discovering VMs for connection {connection_id} (name: {infra_conn.name}), subscription_id: {subscription_id}")

        vms = await CloudDiscoveryService.list_azure_vms(db=db, subscription_id=subscription_id, tenant_id=tenant_id)
        logger.info(f"list_azure_vms returned {len(vms)} total VMs")

        connection_vms = [vm for vm in vms if vm.get("connection_id") == connection_id]
        logger.info(f"Filtered to {len(connection_vms)} VMs for connection {connection_id}")

        if not connection_vms:
            if not subscription_id:
                return {
                    "connection_id": connection_id, "connection_name": infra_conn.name,
                    "resources": [], "total": 0,
                    "warning": "Subscription ID not set in connection metadata. Please add subscription_id to the connection.",
                }
            return {
                "connection_id": connection_id, "connection_name": infra_conn.name,
                "resources": [], "total": 0,
                "warning": f"No VMs found in subscription {subscription_id}. Check if service principal has 'Reader' role.",
            }

        return {"connection_id": connection_id, "connection_name": infra_conn.name, "resources": connection_vms, "total": len(connection_vms)}

    async def save_discovered_resources(
        self,
        db: Session,
        connection_id: int,
        tenant_id: int,
        resource_ids: List[str],
        environment: str = "prod",
    ) -> Dict[str, Any]:
        """Save discovered resources as InfrastructureConnection entries."""
        from app.repositories.infrastructure_repository import InfrastructureRepository

        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True,
        ).first()

        if not infra_conn:
            raise ValueError("Infrastructure connection not found")

        discovery_result = await self.discover_cloud_resources(db, connection_id, tenant_id)
        discovered_resources = discovery_result.get("resources", [])
        resources_to_save = [r for r in discovered_resources if r.get("resource_id") in resource_ids]

        if not resources_to_save:
            return {"created_count": 0, "skipped_count": 0, "created_connections": [], "message": "No matching resources found in discovery results"}

        infra_repo = InfrastructureRepository(db)
        created_count = 0
        skipped_count = 0
        created_connections = []

        for resource in resources_to_save:
            resource_id = resource.get("resource_id")
            vm_name = resource.get("name") or resource.get("vm_name")
            resource_group = resource.get("resource_group")

            if not vm_name:
                logger.warning(f"Skipping resource {resource_id}: missing name")
                skipped_count += 1
                continue

            existing = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.tenant_id == tenant_id,
                InfrastructureConnection.name == vm_name,
                InfrastructureConnection.is_active == True,
            ).first()

            if existing:
                logger.info(f"Skipping {vm_name}: already exists as connection {existing.id}")
                skipped_count += 1
                continue

            meta_data = {
                "resource_id": resource_id,
                "subscription_id": resource.get("subscription_id"),
                "resource_group": resource_group,
                "vm_name": vm_name,
                "os_type": resource.get("os_type"),
                "discovered_from_connection_id": connection_id,
                "discovered_at": datetime.utcnow().isoformat(),
            }

            try:
                new_connection = infra_repo.create_connection(
                    tenant_id=tenant_id,
                    credential_id=infra_conn.credential_id,
                    name=vm_name,
                    connection_type="azure_bastion",
                    target_host=None,
                    target_port=None,
                    target_service=None,
                    environment=environment,
                    meta_data=json.dumps(meta_data),
                    is_active=True,
                )
                db.flush()
                created_count += 1
                created_connections.append({"id": new_connection.id, "name": new_connection.name, "resource_id": resource_id})
                logger.info(f"Created InfrastructureConnection {new_connection.id} for discovered resource {vm_name}")
            except Exception as e:
                logger.error(f"Error creating connection for {vm_name}: {e}", exc_info=True)
                skipped_count += 1

        db.commit()

        if created_count > 0:
            from app.services.subscription.subscription_tracker import SubscriptionTracker
            SubscriptionTracker(db).update_usage(tenant_id)

        return {
            "created_count": created_count,
            "skipped_count": skipped_count,
            "created_connections": created_connections,
            "message": f"Created {created_count} connection(s), skipped {skipped_count}",
        }
