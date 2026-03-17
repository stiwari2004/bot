"""
Mixin: VM command execution for ConnectorService
"""
import json
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.credential import InfrastructureConnection
from app.services.credential_service import get_credential_service
from app.services.infrastructure import get_connector
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorCommandMixin:
    """VM command execution operations for ConnectorService."""

    async def test_command_on_vm(
        self,
        db: Session,
        connection_id: int,
        vm_resource_id: str,
        command: str,
        shell: Optional[str],
        tenant_id: int,
    ) -> Dict[str, Any]:
        """Execute a test command on an Azure VM via Run Command API"""
        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True,
        ).first()

        if not infra_conn:
            raise ValueError("Infrastructure connection not found")

        if infra_conn.connection_type not in ["cloud_account", "azure_subscription", "azure_bastion"]:
            raise ValueError(f"Test command is only supported for Azure connections. Connection type: {infra_conn.connection_type}")

        if not infra_conn.credential_id:
            raise ValueError("Connection has no associated credential")

        cred_data = get_credential_service().get_credential(db, infra_conn.credential_id, tenant_id)
        if not cred_data:
            raise ValueError("Credential not found")

        subscription_id = cred_data.get("subscription_id")
        if not subscription_id and infra_conn.meta_data:
            try:
                conn_meta = json.loads(infra_conn.meta_data)
                subscription_id = conn_meta.get("subscription_id")
            except Exception as e:
                logger.debug(f"Failed to parse connection metadata: {e}")

        if not subscription_id:
            raise ValueError("Subscription ID not found in credential or connection metadata")

        tenant_id_cred = cred_data.get("tenant_id")
        client_id = cred_data.get("client_id")
        client_secret = cred_data.get("client_secret")

        if not (tenant_id_cred and client_id and client_secret):
            raise ValueError("Azure credentials (tenant_id, client_id, client_secret) are required")

        parts = vm_resource_id.strip("/").split("/")
        if len(parts) < 9 or "subscriptions" not in parts or "virtualMachines" not in parts:
            raise ValueError(f"Invalid VM resource ID format: {vm_resource_id}")

        vm_idx = parts.index("virtualMachines")
        vm_name = parts[vm_idx + 1]
        rg_idx = parts.index("resourceGroups")
        resource_group = parts[rg_idx + 1]

        if not shell:
            try:
                from azure.identity import ClientSecretCredential
                from azure.mgmt.compute import ComputeManagementClient

                credential = ClientSecretCredential(tenant_id=tenant_id_cred, client_id=client_id, client_secret=client_secret)
                compute_client = ComputeManagementClient(credential, subscription_id)
                vm = compute_client.virtual_machines.get(resource_group_name=resource_group, vm_name=vm_name)

                if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                    os_type_val = vm.storage_profile.os_disk.os_type
                    os_type = os_type_val.value if hasattr(os_type_val, "value") else str(os_type_val)
                    shell = "powershell" if os_type and "windows" in os_type.lower() else "bash"
                else:
                    shell = "powershell"
            except Exception as e:
                logger.warning(f"Could not detect OS type for VM {vm_name}, defaulting to PowerShell: {e}")
                shell = "powershell"

        connection_config = {
            "resource_id": vm_resource_id,
            "subscription_id": subscription_id,
            "shell": shell,
            "azure_credentials": {"tenant_id": tenant_id_cred, "client_id": client_id, "client_secret": client_secret},
            "tenant_id": tenant_id_cred,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        connector = get_connector("azure_bastion")
        logger.info(f"Executing test command on VM {vm_name} (RG: {resource_group}): {command[:50]}")
        result = await connector.execute_command(command=command, connection_config=connection_config, timeout=60)

        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error", ""),
            "exit_code": result.get("exit_code", -1),
            "vm_name": vm_name,
            "resource_group": resource_group,
            "shell": shell,
            "command": command,
        }
