"""
Azure provider for infrastructure provisioning
"""
from typing import Dict, Any, Optional, List
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureProvider:
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
                # Try default credential (for local development)
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
            
            # Create resource group
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
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure resource group: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
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
        """
        Create an Azure VM
        
        Args:
            resource_group: Resource group name
            vm_name: VM name
            location: Azure region (e.g., "eastus")
            vm_size: VM size (e.g., "Standard_B1s")
            image_publisher: Image publisher
            image_offer: Image offer
            image_sku: Image SKU
            image_version: Image version
            admin_username: Admin username
            admin_password: Admin password (for Windows)
            ssh_public_key: SSH public key (for Linux)
            subscription_id: Azure subscription ID
            client_id: Azure client ID
            client_secret: Azure client secret
            tenant_id: Azure tenant ID
            network_interface_id: Existing network interface ID (optional)
            os_disk_size_gb: OS disk size in GB
            
        Returns:
            Dict with VM creation results
        """
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
            
            # Build image reference
            image_reference = ImageReference(
                publisher=image_publisher,
                offer=image_offer,
                sku=image_sku,
                version=image_version
            )
            
            # Build OS profile
            os_profile = None
            if ssh_public_key:
                # Linux VM
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
                # Windows VM
                os_profile = OSProfile(
                    computer_name=vm_name,
                    admin_username=admin_username,
                    admin_password=admin_password,
                    windows_configuration=WindowsConfiguration(
                        enable_automatic_updates=True
                    )
                )
            else:
                return {
                    "success": False,
                    "error": "Either ssh_public_key (for Linux) or admin_password (for Windows) must be provided"
                }
            
            # Build storage profile
            storage_profile = StorageProfile(
                image_reference=image_reference,
                os_disk=OSDisk(
                    create_option=DiskCreateOptionTypes.from_image,
                    disk_size_gb=os_disk_size_gb,
                    name=f"{vm_name}-osdisk"
                )
            )
            
            # Build network profile
            network_profile = None
            if network_interface_id:
                network_profile = NetworkProfile(
                    network_interfaces=[
                        NetworkInterfaceReference(id=network_interface_id)
                    ]
                )
            
            # Create VM
            vm_parameters = VirtualMachine(
                location=location,
                hardware_profile={"vm_size": vm_size},
                storage_profile=storage_profile,
                os_profile=os_profile,
                network_profile=network_profile
            )
            
            # Begin async creation
            poller = compute_client.virtual_machines.begin_create_or_update(
                resource_group_name=resource_group,
                vm_name=vm_name,
                parameters=vm_parameters
            )
            
            # Wait for completion
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
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure VM: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_virtual_network(
        self,
        resource_group: str,
        vnet_name: str,
        location: str,
        address_prefix: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        subnets: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Create an Azure virtual network"""
        try:
            from azure.mgmt.network import NetworkManagementClient
            from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet
            from azure.core.exceptions import HttpResponseError
            
            credential = self._get_credential(tenant_id, client_id, client_secret)
            network_client = NetworkManagementClient(credential, subscription_id)
            
            # Build subnet list
            subnet_list = []
            if subnets:
                for subnet in subnets:
                    subnet_list.append(
                        Subnet(
                            name=subnet.get("name", "default"),
                            address_prefix=subnet.get("address_prefix", "10.0.1.0/24")
                        )
                    )
            else:
                # Default subnet
                subnet_list.append(
                    Subnet(
                        name="default",
                        address_prefix="10.0.1.0/24"
                    )
                )
            
            # Create virtual network
            vnet_parameters = VirtualNetwork(
                location=location,
                address_space=AddressSpace(address_prefixes=[address_prefix]),
                subnets=subnet_list
            )
            
            poller = network_client.virtual_networks.begin_create_or_update(
                resource_group_name=resource_group,
                virtual_network_name=vnet_name,
                parameters=vnet_parameters
            )
            
            vnet_result = poller.result()
            
            return {
                "success": True,
                "vnet_id": vnet_result.id,
                "vnet_name": vnet_result.name,
                "location": vnet_result.location,
                "address_space": [prefix for prefix in vnet_result.address_space.address_prefixes] if vnet_result.address_space else []
            }
            
        except HttpResponseError as e:
            logger.error(f"Error creating Azure VNet: {e}")
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure VNet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_subnet(
        self,
        resource_group: str,
        vnet_name: str,
        subnet_name: str,
        address_prefix: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a subnet in an existing virtual network"""
        try:
            from azure.mgmt.network import NetworkManagementClient
            from azure.mgmt.network.models import Subnet
            from azure.core.exceptions import HttpResponseError
            
            credential = self._get_credential(tenant_id, client_id, client_secret)
            network_client = NetworkManagementClient(credential, subscription_id)
            
            subnet_parameters = Subnet(address_prefix=address_prefix)
            
            poller = network_client.subnets.begin_create_or_update(
                resource_group_name=resource_group,
                virtual_network_name=vnet_name,
                subnet_name=subnet_name,
                subnet_parameters=subnet_parameters
            )
            
            subnet_result = poller.result()
            
            return {
                "success": True,
                "subnet_id": subnet_result.id,
                "subnet_name": subnet_result.name,
                "address_prefix": subnet_result.address_prefix
            }
            
        except HttpResponseError as e:
            logger.error(f"Error creating Azure subnet: {e}")
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure subnet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_network_interface(
        self,
        resource_group: str,
        nic_name: str,
        location: str,
        subnet_id: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        public_ip_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a network interface"""
        try:
            from azure.mgmt.network import NetworkManagementClient
            from azure.mgmt.network.models import NetworkInterface, NetworkInterfaceIPConfiguration, PublicIPAddress
            from azure.core.exceptions import HttpResponseError
            
            credential = self._get_credential(tenant_id, client_id, client_secret)
            network_client = NetworkManagementClient(credential, subscription_id)
            
            # Build IP configuration
            ip_config = NetworkInterfaceIPConfiguration(
                name="ipconfig1",
                subnet={"id": subnet_id}
            )
            
            if public_ip_id:
                ip_config.public_ip_address = {"id": public_ip_id}
            
            # Create network interface
            nic_parameters = NetworkInterface(
                location=location,
                ip_configurations=[ip_config]
            )
            
            poller = network_client.network_interfaces.begin_create_or_update(
                resource_group_name=resource_group,
                network_interface_name=nic_name,
                parameters=nic_parameters
            )
            
            nic_result = poller.result()
            
            return {
                "success": True,
                "nic_id": nic_result.id,
                "nic_name": nic_result.name,
                "location": nic_result.location
            }
            
        except HttpResponseError as e:
            logger.error(f"Error creating Azure NIC: {e}")
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure NIC: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_public_ip(
        self,
        resource_group: str,
        public_ip_name: str,
        location: str,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        allocation_method: str = "Static"
    ) -> Dict[str, Any]:
        """Create a public IP address"""
        try:
            from azure.mgmt.network import NetworkManagementClient
            from azure.mgmt.network.models import PublicIPAddress, IPAllocationMethod
            from azure.core.exceptions import HttpResponseError
            
            credential = self._get_credential(tenant_id, client_id, client_secret)
            network_client = NetworkManagementClient(credential, subscription_id)
            
            allocation = IPAllocationMethod.static if allocation_method.lower() == "static" else IPAllocationMethod.dynamic
            
            public_ip_parameters = PublicIPAddress(
                location=location,
                public_ip_allocation_method=allocation
            )
            
            poller = network_client.public_ip_addresses.begin_create_or_update(
                resource_group_name=resource_group,
                public_ip_address_name=public_ip_name,
                parameters=public_ip_parameters
            )
            
            public_ip_result = poller.result()
            
            return {
                "success": True,
                "public_ip_id": public_ip_result.id,
                "public_ip_name": public_ip_result.name,
                "ip_address": public_ip_result.ip_address,
                "location": public_ip_result.location
            }
            
        except HttpResponseError as e:
            logger.error(f"Error creating Azure public IP: {e}")
            return {
                "success": False,
                "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating Azure public IP: {e}")
            return {
                "success": False,
                "error": str(e)
            }

