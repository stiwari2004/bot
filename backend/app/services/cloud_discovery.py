"""
Cloud resource discovery service
Discovers VMs/servers from cloud accounts (Azure, GCP, AWS) on-the-fly
"""
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CloudDiscoveryService:
    """Service to discover cloud resources (VMs, instances) from cloud accounts"""
    
    @staticmethod
    async def discover_azure_vm(
        db: Session,
        vm_name: str,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        tenant_id: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Discover an Azure VM by name from cloud account connections.
        
        Args:
            db: Database session
            vm_name: Name of the VM to find
            subscription_id: Optional subscription ID to search in
            resource_group: Optional resource group to search in
            tenant_id: Tenant ID
            
        Returns:
            Dict with resource_id, subscription_id, resource_group, vm_name, and credentials
            or None if not found
        """
        try:
            from app.models.credential import InfrastructureConnection, Credential
            from app.services.credential_service import CredentialService
            
            # Find cloud account connections (connection_type = 'cloud_account' or 'azure_subscription')
            query = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.tenant_id == tenant_id,
                InfrastructureConnection.is_active == True,
                InfrastructureConnection.connection_type.in_(['cloud_account', 'azure_subscription', 'azure_bastion'])
            )
            
            if subscription_id:
                # Filter by subscription_id in meta_data
                connections = query.all()
                connections = [
                    c for c in connections
                    if json.loads(c.meta_data or '{}').get('subscription_id') == subscription_id
                ]
            else:
                connections = query.all()
            
            if not connections:
                logger.warning(f"No Azure cloud account connections found for tenant {tenant_id}")
                return None
            
            # Try each cloud account connection
            for connection in connections:
                try:
                    # Get credentials
                    credential = db.query(Credential).filter(
                        Credential.id == connection.credential_id,
                        Credential.credential_type == 'azure'
                    ).first()
                    
                    if not credential:
                        continue
                    
                    # Decrypt credentials
                    cred_service = CredentialService()
                    cred_data = cred_service.get_credential(db, credential.id, tenant_id)
                    
                    tenant_id_cred = cred_data.get('tenant_id')
                    client_id = cred_data.get('client_id')
                    client_secret = cred_data.get('client_secret')
                    sub_id = cred_data.get('subscription_id') or json.loads(connection.meta_data or '{}').get('subscription_id')
                    
                    if not (tenant_id_cred and client_id and client_secret and sub_id):
                        continue
                    
                    # Query Azure API to find VM
                    vm_info = await CloudDiscoveryService._query_azure_vm(
                        tenant_id=tenant_id_cred,
                        client_id=client_id,
                        client_secret=client_secret,
                        subscription_id=sub_id,
                        vm_name=vm_name,
                        resource_group=resource_group
                    )
                    
                    if vm_info:
                        return {
                            'resource_id': vm_info['resource_id'],
                            'subscription_id': sub_id,
                            'resource_group': vm_info['resource_group'],
                            'vm_name': vm_info['vm_name'],
                            'os_type': vm_info.get('os_type'),  # Include OS type for shell detection
                            'azure_credentials': {
                                'tenant_id': tenant_id_cred,
                                'client_id': client_id,
                                'client_secret': client_secret
                            },
                            'connection_id': connection.id,
                            'credential_id': credential.id
                        }
                        
                except Exception as e:
                    logger.error(f"Error discovering VM from connection {connection.id}: {e}")
                    continue
            
            logger.warning(f"VM '{vm_name}' not found in any Azure cloud account")
            return None
            
        except Exception as e:
            logger.error(f"Error in discover_azure_vm: {e}")
            return None
    
    @staticmethod
    async def _query_azure_vm(
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
        vm_name: str,
        resource_group: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query Azure API to find a VM by name.
        
        Returns:
            Dict with resource_id, resource_group, vm_name or None
        """
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.compute import ComputeManagementClient
            from azure.core.exceptions import AzureError
            
            # Authenticate
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            # Create compute client
            compute_client = ComputeManagementClient(credential, subscription_id)
            
            # If resource group is specified, search in that RG
            if resource_group:
                try:
                    vm = compute_client.virtual_machines.get(
                        resource_group_name=resource_group,
                        vm_name=vm_name
                    )
                    # Get OS type
                    os_type = None
                    if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                        os_type_val = vm.storage_profile.os_disk.os_type
                        if hasattr(os_type_val, 'value'):
                            os_type = os_type_val.value
                        else:
                            os_type = str(os_type_val)
                    return {
                        'resource_id': vm.id,
                        'resource_group': resource_group,
                        'vm_name': vm.name,
                        'os_type': os_type
                    }
                except AzureError:
                    return None
            
            # Otherwise, search all resource groups
            from azure.mgmt.resource import ResourceManagementClient
            resource_client = ResourceManagementClient(credential, subscription_id)
            resource_groups = resource_client.resource_groups.list()
            
            for rg in resource_groups:
                try:
                    vm = compute_client.virtual_machines.get(
                        resource_group_name=rg.name,
                        vm_name=vm_name
                    )
                    # Get OS type
                    os_type = None
                    if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                        os_type_val = vm.storage_profile.os_disk.os_type
                        if hasattr(os_type_val, 'value'):
                            os_type = os_type_val.value
                        else:
                            os_type = str(os_type_val)
                    return {
                        'resource_id': vm.id,
                        'resource_group': rg.name,
                        'vm_name': vm.name,
                        'os_type': os_type
                    }
                except AzureError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying Azure API for VM '{vm_name}': {e}")
            return None
    
    @staticmethod
    async def list_azure_vms(
        db: Session,
        subscription_id: Optional[str] = None,
        tenant_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        List all VMs from Azure cloud account connections.
        
        Returns:
            List of VM info dicts with resource_id, name, resource_group, subscription_id
        """
        try:
            from app.models.credential import InfrastructureConnection, Credential
            from app.services.credential_service import CredentialService
            
            # Find cloud account connections
            query = db.query(InfrastructureConnection).filter(
                InfrastructureConnection.tenant_id == tenant_id,
                InfrastructureConnection.is_active == True,
                InfrastructureConnection.connection_type.in_(['cloud_account', 'azure_subscription', 'azure_bastion'])
            )
            
            if subscription_id:
                connections = query.all()
                connections = [
                    c for c in connections
                    if json.loads(c.meta_data or '{}').get('subscription_id') == subscription_id
                ]
                logger.info(f"Filtered to {len(connections)} connections matching subscription_id: {subscription_id}")
            else:
                connections = query.all()
                logger.info(f"Found {len(connections)} cloud account connections (no subscription filter)")
            
            if not connections:
                logger.warning(f"No cloud account connections found for tenant {tenant_id}")
                return []
            
            all_vms = []
            
            for connection in connections:
                try:
                    # Get credentials
                    credential = db.query(Credential).filter(
                        Credential.id == connection.credential_id,
                        Credential.credential_type == 'azure'
                    ).first()
                    
                    if not credential:
                        continue
                    
                    # Decrypt credentials
                    cred_service = CredentialService()
                    cred_data = cred_service.get_credential(db, credential.id, tenant_id)
                    
                    tenant_id_cred = cred_data.get('tenant_id')
                    client_id = cred_data.get('client_id')
                    client_secret = cred_data.get('client_secret')
                    sub_id = cred_data.get('subscription_id') or json.loads(connection.meta_data or '{}').get('subscription_id')
                    
                    logger.info(f"Processing connection {connection.id}: subscription_id={sub_id}, has_tenant={bool(tenant_id_cred)}, has_client_id={bool(client_id)}, has_secret={bool(client_secret)}")
                    
                    if not (tenant_id_cred and client_id and client_secret and sub_id):
                        logger.warning(f"Skipping connection {connection.id}: Missing required credentials (tenant_id={bool(tenant_id_cred)}, client_id={bool(client_id)}, secret={bool(client_secret)}, sub_id={bool(sub_id)})")
                        continue
                    
                    # Query Azure API to list all VMs
                    try:
                        vms = await CloudDiscoveryService._list_azure_vms_api(
                            tenant_id=tenant_id_cred,
                            client_id=client_id,
                            client_secret=client_secret,
                            subscription_id=sub_id
                        )
                        
                        for vm in vms:
                            vm['connection_id'] = connection.id
                            vm['subscription_id'] = sub_id
                        
                        all_vms.extend(vms)
                    except ValueError as e:
                        # Permission or other clear errors - log and continue
                        logger.warning(f"Could not list VMs from connection {connection.id}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error listing VMs from connection {connection.id}: {e}", exc_info=True)
                        continue
                except Exception as e:
                    logger.error(f"Error processing connection {connection.id}: {e}", exc_info=True)
                    continue
            
            return all_vms
            
        except Exception as e:
            logger.error(f"Error in list_azure_vms: {e}")
            return []
    
    @staticmethod
    async def _list_azure_vms_api(
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str
    ) -> List[Dict[str, Any]]:
        """Query Azure API to list all VMs in a subscription"""
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.compute import ComputeManagementClient
            from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
            
            # Authenticate
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            # Create compute client
            compute_client = ComputeManagementClient(credential, subscription_id)
            
            vms = []
            try:
                # List all VMs (including stopped/deallocated ones)
                logger.info(f"Calling Azure API to list VMs for subscription {subscription_id}")
                vm_list = list(compute_client.virtual_machines.list_all())
                logger.info(f"Azure API returned {len(vm_list)} VMs from subscription {subscription_id}")
                
                if len(vm_list) == 0:
                    logger.warning(f"No VMs found in subscription {subscription_id}. This could mean: 1) No VMs exist, 2) Service principal lacks permissions, or 3) VMs are in a different subscription.")
                
                for vm in vm_list:
                    try:
                        # Parse resource ID to get resource group
                        parts = vm.id.strip("/").split("/")
                        if "resourceGroups" in parts:
                            rg_idx = parts.index("resourceGroups")
                            resource_group = parts[rg_idx + 1]
                        else:
                            resource_group = "unknown"
                        
                        # Get VM power state - try to get instance view, but don't fail if it's not available
                        power_state = "unknown"
                        provisioning_state = vm.provisioning_state or "unknown"
                        
                        # Try to get instance view for power state (requires additional API call)
                        # This might fail for stopped/deallocated VMs or due to permissions
                        try:
                            # Get instance view separately - this requires additional permissions
                            from azure.mgmt.compute.models import InstanceViewTypes
                            instance_view = compute_client.virtual_machines.instance_view(
                                resource_group_name=resource_group,
                                vm_name=vm.name
                            )
                            if instance_view and instance_view.statuses:
                                for status in instance_view.statuses:
                                    if status.code and status.code.startswith("PowerState/"):
                                        power_state = status.code.replace("PowerState/", "")
                                        break
                        except Exception as e:
                            # If we can't get instance view, that's okay - we'll use "unknown"
                            logger.debug(f"Could not get instance view for VM {vm.name}: {e}")
                            # For stopped/deallocated VMs, we can infer from provisioning state
                            if provisioning_state and "deallocated" in provisioning_state.lower():
                                power_state = "deallocated"
                        
                        # Get OS type - handle both enum and string types
                        os_type = None
                        if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                            os_type_val = vm.storage_profile.os_disk.os_type
                            # Check if it's an enum with .value attribute, or already a string
                            if hasattr(os_type_val, 'value'):
                                os_type = os_type_val.value
                            else:
                                os_type = str(os_type_val)
                        
                        vms.append({
                            'resource_id': vm.id,
                            'name': vm.name,
                            'resource_group': resource_group,
                            'location': vm.location,
                            'vm_size': vm.hardware_profile.vm_size if vm.hardware_profile else None,
                            'os_type': os_type,
                            'power_state': power_state,
                            'provisioning_state': provisioning_state
                        })
                    except Exception as e:
                        logger.warning(f"Error processing VM {vm.name if hasattr(vm, 'name') else 'unknown'}: {e}")
                        continue
                
                logger.info(f"Successfully processed {len(vms)} VMs from subscription {subscription_id}")
                return vms
                
            except ClientAuthenticationError as e:
                logger.error(f"Authentication error listing VMs: {e}")
                raise
            except HttpResponseError as e:
                if e.status_code == 403:
                    logger.error(f"Permission denied (403) listing VMs. Service principal needs 'Reader' role on subscription {subscription_id}")
                    raise ValueError(f"Permission denied: Service principal needs 'Reader' role on subscription {subscription_id}")
                else:
                    logger.error(f"HTTP error listing VMs: {e.status_code} - {e}")
                    raise
                    
        except ValueError:
            # Re-raise permission errors
            raise
        except Exception as e:
            logger.error(f"Error listing VMs from Azure API: {e}", exc_info=True)
            raise ValueError(f"Failed to list VMs: {str(e)}")

