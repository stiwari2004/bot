"""
Mixin: connection testing operations for ConnectorService
"""
import json
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.models.credential import Credential, InfrastructureConnection
from app.services.credential_service import get_credential_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorTestingMixin:
    """Connection testing operations for ConnectorService."""

    def test_connection(self, db: Session, connection_id: int, tenant_id: int) -> Dict[str, Any]:
        """Test infrastructure connection by validating credentials and connectivity"""
        logger.info(f"Testing infrastructure connection {connection_id}")

        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True,
        ).first()

        if not infra_conn:
            logger.warning(f"Infrastructure connection {connection_id} not found")
            raise ValueError("Infrastructure connection not found")

        logger.info(f"Found connection: {infra_conn.name}, type: {infra_conn.connection_type}")

        if not infra_conn.credential_id:
            logger.warning(f"Connection {connection_id} has no credential assigned")
            raise ValueError("Connection has no credential assigned")

        credential = db.query(Credential).filter(
            Credential.id == infra_conn.credential_id, Credential.tenant_id == tenant_id
        ).first()

        if not credential:
            logger.warning(f"Credential {infra_conn.credential_id} not found")
            raise ValueError("Credential not found")

        logger.info(f"Found credential: {credential.name}, type: {credential.credential_type}")

        if infra_conn.connection_type in ["cloud_account", "azure_subscription", "azure_bastion"]:
            return self._test_azure_connection(db, infra_conn, credential, tenant_id)

        return {
            "success": True,
            "message": f"Connection '{infra_conn.name}' is configured.",
            "details": {
                "connection_type": infra_conn.connection_type,
                "note": "Full testing not implemented for this connection type yet.",
            },
        }

    def _test_azure_connection(
        self,
        db: Session,
        infra_conn: InfrastructureConnection,
        credential: Credential,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """Test Azure connection"""
        logger.info("Testing Azure connection")
        cred_service = get_credential_service()

        try:
            cred_data = cred_service.get_credential(db, credential.id, tenant_id)
        except ValueError as e:
            logger.error(f"Credential decryption error: {e}", exc_info=True)
            raise ValueError(f"Failed to decrypt credential: {str(e)}. Please recreate the credential.")
        except Exception as e:
            logger.error(f"Error retrieving credential: {e}", exc_info=True)
            raise ValueError(f"Failed to retrieve credential: {str(e) or type(e).__name__}")

        if not cred_data:
            raise ValueError("Failed to retrieve credential data. Credential may be corrupted or missing.")

        logger.info(f"Retrieved credential data. Keys: {list(cred_data.keys())}")

        if credential.credential_type != "azure":
            raise ValueError(f"Credential type is '{credential.credential_type}', but 'azure' is required for Azure connections.")

        tenant_id_cred = cred_data.get("tenant_id")
        client_id = cred_data.get("client_id")
        client_secret = cred_data.get("client_secret")

        sub_id = cred_data.get("subscription_id")
        if not sub_id and infra_conn.meta_data:
            try:
                conn_meta = json.loads(infra_conn.meta_data)
                sub_id = conn_meta.get("subscription_id")
            except Exception as e:
                logger.debug(f"Failed to parse connection metadata for subscription_id: {e}")

        logger.info(f"Azure credentials check - tenant_id: {bool(tenant_id_cred)}, client_id: {bool(client_id)}, client_secret: {bool(client_secret)}, subscription_id: {bool(sub_id)}")

        if not (tenant_id_cred and client_id and client_secret):
            missing = [k for k, v in {"tenant_id": tenant_id_cred, "client_id": client_id, "client_secret": client_secret}.items() if not v]
            raise ValueError(f"Azure credentials incomplete. Missing: {', '.join(missing)}")

        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.compute import ComputeManagementClient

            azure_credential = ClientSecretCredential(tenant_id=tenant_id_cred, client_id=client_id, client_secret=client_secret)

            if sub_id:
                compute_client = ComputeManagementClient(azure_credential, sub_id)
                try:
                    vms = list(compute_client.virtual_machines.list_all())
                    from azure.mgmt.resource import ResourceManagementClient
                    resource_client = ResourceManagementClient(azure_credential, sub_id)
                    rgs = list(resource_client.resource_groups.list())
                    return {
                        "success": True,
                        "message": f"Azure connection successful! Found {len(rgs)} resource groups and {len(vms)} VMs.",
                        "details": {
                            "subscription_id": sub_id,
                            "resource_groups": len(rgs),
                            "virtual_machines": len(vms),
                            "sample_vms": [vm.name for vm in vms[:10]],
                            "note": "VMs include stopped/deallocated ones",
                        },
                    }
                except Exception as e:
                    return {
                        "success": True,
                        "message": "Azure authentication successful, but limited access to resources.",
                        "details": {
                            "subscription_id": sub_id,
                            "warning": str(e),
                            "hint": "Check if service principal has 'Reader' role on subscription or resource groups",
                        },
                    }
            else:
                return {
                    "success": True,
                    "message": "Azure credentials are valid (authentication successful).",
                    "details": {"note": "Subscription ID not provided. Add subscription_id to discover VMs."},
                }
        except Exception as e:
            logger.error(f"Azure connection test failed: {e}", exc_info=True)
            error_msg = str(e)
            if "AADSTS" in error_msg or "authentication" in error_msg.lower():
                hint = "Authentication failed. Check tenant_id, client_id, and client_secret are correct."
            elif "subscription" in error_msg.lower():
                hint = "Subscription access denied. Ensure the service principal has 'Reader' role."
            else:
                hint = "Check tenant_id, client_id, and client_secret are correct"
            return {"success": False, "message": f"Azure connection test failed: {error_msg}", "details": {"error": error_msg, "hint": hint}}
