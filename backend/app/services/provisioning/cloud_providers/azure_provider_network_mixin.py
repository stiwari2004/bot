"""
Mixin: network resource creation for AzureProvider
"""
from typing import Dict, Any, Optional, List
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureProviderNetworkMixin:
    """Network resource creation helpers for AzureProvider."""

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
                subnet_list.append(Subnet(name="default", address_prefix="10.0.1.0/24"))

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
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure VNet: {e}")
            return {"success": False, "error": str(e)}

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

            poller = network_client.subnets.begin_create_or_update(
                resource_group_name=resource_group,
                virtual_network_name=vnet_name,
                subnet_name=subnet_name,
                subnet_parameters=Subnet(address_prefix=address_prefix)
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
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure subnet: {e}")
            return {"success": False, "error": str(e)}

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
            from azure.mgmt.network.models import NetworkInterface, NetworkInterfaceIPConfiguration
            from azure.core.exceptions import HttpResponseError

            credential = self._get_credential(tenant_id, client_id, client_secret)
            network_client = NetworkManagementClient(credential, subscription_id)

            ip_config = NetworkInterfaceIPConfiguration(
                name="ipconfig1",
                subnet={"id": subnet_id}
            )
            if public_ip_id:
                ip_config.public_ip_address = {"id": public_ip_id}

            poller = network_client.network_interfaces.begin_create_or_update(
                resource_group_name=resource_group,
                network_interface_name=nic_name,
                parameters=NetworkInterface(location=location, ip_configurations=[ip_config])
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
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure NIC: {e}")
            return {"success": False, "error": str(e)}

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

            poller = network_client.public_ip_addresses.begin_create_or_update(
                resource_group_name=resource_group,
                public_ip_address_name=public_ip_name,
                parameters=PublicIPAddress(location=location, public_ip_allocation_method=allocation)
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
            return {"success": False, "error": f"Azure API error: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Azure public IP: {e}")
            return {"success": False, "error": str(e)}
