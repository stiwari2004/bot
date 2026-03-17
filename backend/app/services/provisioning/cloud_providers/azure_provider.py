"""
Azure provider for infrastructure provisioning
"""
from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.services.provisioning.cloud_providers.azure_provider_vm_mixin import AzureProviderVMMixin
from app.services.provisioning.cloud_providers.azure_provider_network_mixin import AzureProviderNetworkMixin

logger = get_logger(__name__)


class AzureProvider(AzureProviderVMMixin, AzureProviderNetworkMixin):
    """Azure cloud provider integration for provisioning resources"""

    def __init__(self):
        pass

    def _get_credential(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        """Get Azure credential object"""
        try:
            from azure.identity import ClientSecretCredential, DefaultAzureCredential

            if tenant_id and client_id and client_secret:
                return ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                return DefaultAzureCredential()
        except ImportError:
            raise ImportError("Azure SDK not installed. Install: pip install azure-identity azure-mgmt-compute azure-mgmt-network azure-mgmt-resource")

    async def create_resource_group(
        self,
        resource_group_name: str,
        location: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create an Azure resource group"""
        try:
            from azure.mgmt.resource import ResourceManagementClient
            from azure.core.exceptions import HttpResponseError

            credential = self._get_credential(tenant_id, client_id, client_secret)
            resource_client = ResourceManagementClient(credential, subscription_id)

            rg_result = resource_client.resource_groups.create_or_update(
                resource_group_name,
                {
                    "location": location,
                    "tags": tags or {}
                }
            )

            return {
                "success": True,
                "resource_group_name": rg_result.name,
                "location": rg_result.location,
                "id": rg_result.id
            }

        except HttpResponseError as e:
            logger.error(f"Error creating resource group: {e}")
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure resource group: {e}")
            return {"success": False, "error": str(e)}
