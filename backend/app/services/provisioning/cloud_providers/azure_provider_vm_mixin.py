"""
Mixin: VM creation for AzureProvider
"""
from typing import Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureProviderVMMixin:
    """VM creation helpers for AzureProvider."""

    async def create_vm(
        self,
        resource_group: str,
        vm_name: str,
        location: str,
        vm_size: str,
        image_publisher: str = "Canonical",
        image_offer: str = "0001-com-ubuntu-server-jammy",
        image_sku: str = "22_04-lts",
        image_version: str = "latest",
        admin_username: str = "azureuser",
        admin_password: Optional[str] = None,
        ssh_public_key: Optional[str] = None,
        subscription_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        network_interface_id: Optional[str] = None,
        os_disk_size_gb: int = 30
    ) -> Dict[str, Any]:
        """Create an Azure VM"""
        try:
            from azure.mgmt.compute import ComputeManagementClient
            from azure.mgmt.compute.models import (
                VirtualMachine,
                NetworkProfile,
                NetworkInterfaceReference,
                OSProfile,
                LinuxConfiguration,
                SshConfiguration,
                SshPublicKey,
                WindowsConfiguration,
                StorageProfile,
                ImageReference,
                OSDisk,
                DiskCreateOptionTypes
            )
            from azure.core.exceptions import HttpResponseError

            credential = self._get_credential(tenant_id, client_id, client_secret)
            compute_client = ComputeManagementClient(credential, subscription_id)

            image_reference = ImageReference(
                publisher=image_publisher,
                offer=image_offer,
                sku=image_sku,
                version=image_version
            )

            os_profile = None
            if ssh_public_key:
                os_profile = OSProfile(
                    computer_name=vm_name,
                    admin_username=admin_username,
                    linux_configuration=LinuxConfiguration(
                        disable_password_authentication=True,
                        ssh=SshConfiguration(
                            public_keys=[
                                SshPublicKey(
                                    path=f"/home/{admin_username}/.ssh/authorized_keys",
                                    key_data=ssh_public_key
                                )
                            ]
                        )
                    )
                )
            elif admin_password:
                os_profile = OSProfile(
                    computer_name=vm_name,
                    admin_username=admin_username,
                    admin_password=admin_password,
                    windows_configuration=WindowsConfiguration(enable_automatic_updates=True)
                )
            else:
                return {
                    "success": False,
                    "error": "Either ssh_public_key (for Linux) or admin_password (for Windows) must be provided"
                }

            storage_profile = StorageProfile(
                image_reference=image_reference,
                os_disk=OSDisk(
                    create_option=DiskCreateOptionTypes.from_image,
                    disk_size_gb=os_disk_size_gb,
                    name=f"{vm_name}-osdisk"
                )
            )

            network_profile = None
            if network_interface_id:
                network_profile = NetworkProfile(
                    network_interfaces=[NetworkInterfaceReference(id=network_interface_id)]
                )

            vm_parameters = VirtualMachine(
                location=location,
                hardware_profile={"vm_size": vm_size},
                storage_profile=storage_profile,
                os_profile=os_profile,
                network_profile=network_profile
            )

            poller = compute_client.virtual_machines.begin_create_or_update(
                resource_group_name=resource_group,
                vm_name=vm_name,
                parameters=vm_parameters
            )
            vm_result = poller.result()

            return {
                "success": True,
                "vm_id": vm_result.id,
                "vm_name": vm_result.name,
                "location": vm_result.location,
                "provisioning_state": vm_result.provisioning_state,
                "resource_group": resource_group
            }

        except HttpResponseError as e:
            logger.error(f"Error creating Azure VM: {e}")
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure VM: {e}")
            return {"success": False, "error": str(e)}
