"""
GCP provider for infrastructure provisioning
"""
import json
from typing import Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class GCPProvider:
    """GCP cloud provider integration for provisioning resources"""
    
    def __init__(self):
        pass
    
    def _get_credentials(self, service_account_key: Optional[str] = None, credentials_path: Optional[str] = None):
        """Get GCP credentials"""
        try:
            from google.oauth2 import service_account
            from google.auth import default
            
            if service_account_key:
                # Parse service account key JSON
                if isinstance(service_account_key, str):
                    key_data = json.loads(service_account_key)
                else:
                    key_data = service_account_key
                
                return service_account.Credentials.from_service_account_info(key_data)
            elif credentials_path:
                return service_account.Credentials.from_service_account_file(credentials_path)
            else:
                # Try default credentials
                credentials, project = default()
                return credentials
        except ImportError:
            raise ImportError("GCP SDK not installed. Install: pip install google-cloud-compute google-auth")
    
    async def create_vm(
        self,
        project_id: str,
        zone: str,
        instance_name: str,
        machine_type: str,
        image_family: str = "ubuntu-2204-jammy-v20240111",
        image_project: str = "ubuntu-os-cloud",
        service_account_email: Optional[str] = None,
        service_account_key: Optional[str] = None,
        credentials_path: Optional[str] = None,
        network: Optional[str] = None,
        subnetwork: Optional[str] = None,
        disk_size_gb: int = 20,
        ssh_public_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a GCP VM instance
        
        Args:
            project_id: GCP project ID
            zone: GCP zone (e.g., "us-central1-a")
            instance_name: Instance name
            machine_type: Machine type (e.g., "e2-micro")
            image_family: Image family
            image_project: Image project
            service_account_email: Service account email
            service_account_key: Service account key JSON (string or dict)
            credentials_path: Path to service account key file
            network: Network name (default: "default")
            subnetwork: Subnetwork name
            disk_size_gb: Boot disk size in GB
            ssh_public_key: SSH public key for access
            
        Returns:
            Dict with VM creation results
        """
        try:
            from google.cloud import compute_v1
            from google.api_core import exceptions
            
            credentials = self._get_credentials(service_account_key, credentials_path)
            instance_client = compute_v1.InstancesClient(credentials=credentials)
            image_client = compute_v1.ImagesClient(credentials=credentials)
            
            # Get image
            image_response = image_client.get(
                project=image_project,
                image=image_family
            )
            
            # Build instance
            instance = compute_v1.Instance()
            instance.name = instance_name
            instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"
            
            # Configure disk
            disk = compute_v1.AttachedDisk()
            disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
            disk.initialize_params.source_image = image_response.self_link
            disk.initialize_params.disk_size_gb = disk_size_gb
            disk.auto_delete = True
            disk.boot = True
            instance.disks = [disk]
            
            # Configure network
            network_interface = compute_v1.NetworkInterface()
            if network:
                network_interface.network = f"projects/{project_id}/global/networks/{network}"
            else:
                network_interface.network = f"projects/{project_id}/global/networks/default"
            
            if subnetwork:
                network_interface.subnetwork = f"projects/{project_id}/regions/{zone.rsplit('-', 1)[0]}/subnetworks/{subnetwork}"
            
            # Add external IP
            access_config = compute_v1.AccessConfig()
            access_config.name = "External NAT"
            access_config.type_ = "ONE_TO_ONE_NAT"
            network_interface.access_configs = [access_config]
            
            instance.network_interfaces = [network_interface]
            
            # Configure SSH key if provided
            if ssh_public_key:
                metadata = compute_v1.Metadata()
                metadata_item = compute_v1.Items()
                metadata_item.key = "ssh-keys"
                metadata_item.value = f"resolvify:{ssh_public_key}"
                metadata.items = [metadata_item]
                instance.metadata = metadata
            
            # Configure service account if provided
            if service_account_email:
                service_account_config = compute_v1.ServiceAccount()
                service_account_config.email = service_account_email
                service_account_config.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
                instance.service_accounts = [service_account_config]
            
            # Create instance
            operation = instance_client.insert(
                project=project_id,
                zone=zone,
                instance_resource=instance
            )
            
            # Wait for operation to complete
            operation_client = compute_v1.ZoneOperationsClient(credentials=credentials)
            while operation.status != "DONE":
                operation = operation_client.get(
                    project=project_id,
                    zone=zone,
                    operation=operation.name
                )
            
            if operation.error:
                return {
                    "success": False,
                    "error": f"GCP operation failed: {operation.error}"
                }
            
            # Get created instance
            created_instance = instance_client.get(
                project=project_id,
                zone=zone,
                instance=instance_name
            )
            
            return {
                "success": True,
                "instance_id": created_instance.id,
                "instance_name": created_instance.name,
                "zone": zone,
                "status": created_instance.status,
                "machine_type": created_instance.machine_type.split("/")[-1],
                "network_interfaces": [
                    {
                        "network": ni.network.split("/")[-1],
                        "ip_address": ni.network_i_p if hasattr(ni, 'network_i_p') else None
                    }
                    for ni in created_instance.network_interfaces
                ]
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error creating GCP VM: {e}")
            return {
                "success": False,
                "error": f"GCP API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating GCP VM: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_network(
        self,
        project_id: str,
        network_name: str,
        service_account_key: Optional[str] = None,
        credentials_path: Optional[str] = None,
        auto_create_subnetworks: bool = True,
        routing_mode: str = "REGIONAL"
    ) -> Dict[str, Any]:
        """Create a GCP VPC network"""
        try:
            from google.cloud import compute_v1
            from google.api_core import exceptions
            
            credentials = self._get_credentials(service_account_key, credentials_path)
            network_client = compute_v1.NetworksClient(credentials=credentials)
            
            network = compute_v1.Network()
            network.name = network_name
            network.auto_create_subnetworks = auto_create_subnetworks
            network.routing_config = compute_v1.NetworkRoutingConfig()
            network.routing_config.routing_mode = routing_mode
            
            operation = network_client.insert(
                project=project_id,
                network_resource=network
            )
            
            # Wait for completion
            operation_client = compute_v1.GlobalOperationsClient(credentials=credentials)
            while operation.status != "DONE":
                operation = operation_client.get(
                    project=project_id,
                    operation=operation.name
                )
            
            if operation.error:
                return {
                    "success": False,
                    "error": f"GCP operation failed: {operation.error}"
                }
            
            # Get created network
            created_network = network_client.get(
                project=project_id,
                network=network_name
            )
            
            return {
                "success": True,
                "network_id": created_network.id,
                "network_name": created_network.name,
                "self_link": created_network.self_link
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error creating GCP network: {e}")
            return {
                "success": False,
                "error": f"GCP API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating GCP network: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_subnetwork(
        self,
        project_id: str,
        region: str,
        subnetwork_name: str,
        network: str,
        ip_cidr_range: str,
        service_account_key: Optional[str] = None,
        credentials_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a GCP subnetwork"""
        try:
            from google.cloud import compute_v1
            from google.api_core import exceptions
            
            credentials = self._get_credentials(service_account_key, credentials_path)
            subnet_client = compute_v1.SubnetworksClient(credentials=credentials)
            
            subnetwork = compute_v1.Subnetwork()
            subnetwork.name = subnetwork_name
            subnetwork.network = f"projects/{project_id}/global/networks/{network}"
            subnetwork.ip_cidr_range = ip_cidr_range
            
            operation = subnet_client.insert(
                project=project_id,
                region=region,
                subnetwork_resource=subnetwork
            )
            
            # Wait for completion
            operation_client = compute_v1.RegionOperationsClient(credentials=credentials)
            while operation.status != "DONE":
                operation = operation_client.get(
                    project=project_id,
                    region=region,
                    operation=operation.name
                )
            
            if operation.error:
                return {
                    "success": False,
                    "error": f"GCP operation failed: {operation.error}"
                }
            
            # Get created subnetwork
            created_subnet = subnet_client.get(
                project=project_id,
                region=region,
                subnetwork=subnetwork_name
            )
            
            return {
                "success": True,
                "subnetwork_id": created_subnet.id,
                "subnetwork_name": created_subnet.name,
                "ip_cidr_range": created_subnet.ip_cidr_range,
                "self_link": created_subnet.self_link
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error creating GCP subnetwork: {e}")
            return {
                "success": False,
                "error": f"GCP API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating GCP subnetwork: {e}")
            return {
                "success": False,
                "error": str(e)
            }

