"""
Connector service for business logic: testing, discovery, command execution
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.credential import Credential, InfrastructureConnection
from app.services.credential_service import get_credential_service
from app.services.cloud_discovery import CloudDiscoveryService
from app.services.infrastructure import get_connector
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class ConnectorService:
    """Business logic for connector operations"""
    
    def test_connection(self, db: Session, connection_id: int, tenant_id: int) -> Dict[str, Any]:
        """Test infrastructure connection by validating credentials and connectivity"""
        logger.info(f"Testing infrastructure connection {connection_id}")
        
        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        ).first()
        
        if not infra_conn:
            logger.warning(f"Infrastructure connection {connection_id} not found")
            raise ValueError("Infrastructure connection not found")
        
        logger.info(f"Found connection: {infra_conn.name}, type: {infra_conn.connection_type}")
        
        # Get credential
        if not infra_conn.credential_id:
            logger.warning(f"Connection {connection_id} has no credential assigned")
            raise ValueError("Connection has no credential assigned")
        
        credential = db.query(Credential).filter(
            Credential.id == infra_conn.credential_id,
            Credential.tenant_id == tenant_id
        ).first()
        
        if not credential:
            logger.warning(f"Credential {infra_conn.credential_id} not found")
            raise ValueError("Credential not found")
        
        logger.info(f"Found credential: {credential.name}, type: {credential.credential_type}")
        
        # Test based on connection type
        if infra_conn.connection_type in ['cloud_account', 'azure_subscription', 'azure_bastion']:
            return self._test_azure_connection(db, infra_conn, credential, tenant_id)
        
        # For other connection types, return basic success
        return {
            "success": True,
            "message": f"Connection '{infra_conn.name}' is configured.",
            "details": {
                "connection_type": infra_conn.connection_type,
                "note": "Full testing not implemented for this connection type yet."
            }
        }
    
    def _test_azure_connection(
        self,
        db: Session,
        infra_conn: InfrastructureConnection,
        credential: Credential,
        tenant_id: int
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
            error_msg = str(e) if str(e) else type(e).__name__
            raise ValueError(f"Failed to retrieve credential: {error_msg}")
        
        if not cred_data:
            logger.error(f"Credential data is None for credential {credential.id}")
            raise ValueError("Failed to retrieve credential data. Credential may be corrupted or missing.")
        
        logger.info(f"Retrieved credential data. Keys: {list(cred_data.keys())}")
        logger.info(f"Credential type: {credential.credential_type}")
        
        if credential.credential_type != "azure":
            logger.error(f"Credential type mismatch. Expected 'azure', got '{credential.credential_type}'")
            raise ValueError(f"Credential type is '{credential.credential_type}', but 'azure' is required for Azure connections. Please select an Azure credential.")
        
        tenant_id_cred = cred_data.get('tenant_id')
        client_id = cred_data.get('client_id')
        client_secret = cred_data.get('client_secret')
        
        # Try to get subscription_id from credential metadata or connection metadata
        sub_id = cred_data.get('subscription_id')
        if not sub_id and infra_conn.meta_data:
            try:
                conn_meta = json.loads(infra_conn.meta_data)
                sub_id = conn_meta.get('subscription_id')
            except:
                pass
        
        logger.info(f"Azure credentials check - tenant_id: {bool(tenant_id_cred)}, client_id: {bool(client_id)}, client_secret: {bool(client_secret)}, subscription_id: {bool(sub_id)}")
        
        if not (tenant_id_cred and client_id and client_secret):
            missing = []
            if not tenant_id_cred:
                missing.append("tenant_id")
            if not client_id:
                missing.append("client_id")
            if not client_secret:
                missing.append("client_secret")
            logger.warning(f"Azure credentials incomplete. Missing: {missing}")
            raise ValueError(f"Azure credentials incomplete. Missing: {', '.join(missing)}. Required: tenant_id, client_id, client_secret")
        
        # Test Azure authentication
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.compute import ComputeManagementClient
            
            azure_credential = ClientSecretCredential(
                tenant_id=tenant_id_cred,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            # Try to create a compute client (this validates credentials)
            if sub_id:
                compute_client = ComputeManagementClient(azure_credential, sub_id)
                # Try to list VMs to verify access
                try:
                    vms = list(compute_client.virtual_machines.list_all())
                    logger.info(f"Test: Found {len(vms)} VMs in subscription {sub_id}")
                    
                    from azure.mgmt.resource import ResourceManagementClient
                    resource_client = ResourceManagementClient(azure_credential, sub_id)
                    rgs = list(resource_client.resource_groups.list())
                    logger.info(f"Test: Found {len(rgs)} resource groups in subscription {sub_id}")
                    
                    vm_names = [vm.name for vm in vms[:10]]
                    return {
                        "success": True,
                        "message": f"Azure connection successful! Found {len(rgs)} resource groups and {len(vms)} VMs.",
                        "details": {
                            "subscription_id": sub_id,
                            "resource_groups": len(rgs),
                            "virtual_machines": len(vms),
                            "sample_vms": vm_names,
                            "note": "VMs include stopped/deallocated ones"
                        }
                    }
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Azure test error: {error_msg}", exc_info=True)
                    return {
                        "success": True,
                        "message": "Azure authentication successful, but limited access to resources.",
                        "details": {
                            "subscription_id": sub_id,
                            "warning": error_msg,
                            "hint": "Check if service principal has 'Reader' role on subscription or resource groups"
                        }
                    }
            else:
                return {
                    "success": True,
                    "message": "Azure credentials are valid (authentication successful).",
                    "details": {
                        "note": "Subscription ID not provided. Add subscription_id to discover VMs."
                    }
                }
                
        except Exception as e:
            logger.error(f"Azure connection test failed: {e}", exc_info=True)
            error_msg = str(e)
            if "AADSTS" in error_msg or "authentication" in error_msg.lower():
                hint = "Authentication failed. Check tenant_id, client_id, and client_secret are correct."
            elif "subscription" in error_msg.lower():
                hint = "Subscription access denied. Ensure the service principal has 'Reader' role on the subscription."
            else:
                hint = "Check tenant_id, client_id, and client_secret are correct"
            
            return {
                "success": False,
                "message": f"Azure connection test failed: {error_msg}",
                "details": {
                    "error": error_msg,
                    "hint": hint
                }
            }
    
    async def discover_cloud_resources(
        self,
        db: Session,
        connection_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """Discover resources (VMs, instances) from a cloud account connection"""
        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        ).first()
        
        if not infra_conn:
            raise ValueError("Infrastructure connection not found")
        
        # Check if it's a cloud account connection
        if infra_conn.connection_type not in ['cloud_account', 'azure_subscription', 'azure_bastion']:
            raise ValueError(f"Connection type '{infra_conn.connection_type}' does not support resource discovery. Use 'cloud_account' or 'azure_subscription'.")
        
        # Get subscription_id from connection metadata
        subscription_id = None
        if infra_conn.meta_data:
            try:
                conn_meta = json.loads(infra_conn.meta_data)
                subscription_id = conn_meta.get('subscription_id')
            except:
                pass
        
        # Also try to get from credential
        if not subscription_id and infra_conn.credential_id:
            try:
                cred_service = get_credential_service()
                cred_data = cred_service.get_credential(db, infra_conn.credential_id, tenant_id)
                if cred_data:
                    subscription_id = cred_data.get('subscription_id')
            except Exception as e:
                logger.warning(f"Could not get subscription_id from credential: {e}")
        
        logger.info(f"Discovering VMs for connection {connection_id} (name: {infra_conn.name}), subscription_id: {subscription_id}")
        
        vms = await CloudDiscoveryService.list_azure_vms(
            db=db,
            subscription_id=subscription_id,
            tenant_id=tenant_id
        )
        
        logger.info(f"list_azure_vms returned {len(vms)} total VMs")
        
        # Filter to only VMs from this connection
        connection_vms = [
            vm for vm in vms
            if vm.get('connection_id') == connection_id
        ]
        
        logger.info(f"Filtered to {len(connection_vms)} VMs for connection {connection_id}")
        
        # If no VMs found, check if it's a permissions issue
        if len(connection_vms) == 0:
            if not subscription_id:
                return {
                    "connection_id": connection_id,
                    "connection_name": infra_conn.name,
                    "resources": [],
                    "total": 0,
                    "warning": "Subscription ID not set in connection metadata. Please add subscription_id to the connection."
                }
            else:
                return {
                    "connection_id": connection_id,
                    "connection_name": infra_conn.name,
                    "resources": [],
                    "total": 0,
                    "warning": f"No VMs found in subscription {subscription_id}. This could mean: 1) No VMs exist, 2) Service principal lacks 'Reader' role, or 3) VMs are in a different subscription."
                }
        
        return {
            "connection_id": connection_id,
            "connection_name": infra_conn.name,
            "resources": connection_vms,
            "total": len(connection_vms)
        }
    
    async def test_command_on_vm(
        self,
        db: Session,
        connection_id: int,
        vm_resource_id: str,
        command: str,
        shell: Optional[str],
        tenant_id: int
    ) -> Dict[str, Any]:
        """Execute a test command on an Azure VM via Run Command API"""
        # Get infrastructure connection
        infra_conn = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.id == connection_id,
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        ).first()
        
        if not infra_conn:
            raise ValueError("Infrastructure connection not found")
        
        # Check if it's an Azure connection
        if infra_conn.connection_type not in ['cloud_account', 'azure_subscription', 'azure_bastion']:
            raise ValueError(f"Test command is only supported for Azure connections. Connection type: {infra_conn.connection_type}")
        
        # Get credentials
        if not infra_conn.credential_id:
            raise ValueError("Connection has no associated credential")
        
        cred_service = get_credential_service()
        cred_data = cred_service.get_credential(db, infra_conn.credential_id, tenant_id)
        
        if not cred_data:
            raise ValueError("Credential not found")
        
        # Get subscription_id
        subscription_id = cred_data.get('subscription_id')
        if not subscription_id:
            if infra_conn.meta_data:
                try:
                    conn_meta = json.loads(infra_conn.meta_data)
                    subscription_id = conn_meta.get('subscription_id')
                except:
                    pass
        
        if not subscription_id:
            raise ValueError("Subscription ID not found in credential or connection metadata")
        
        # Get Azure credentials
        tenant_id_cred = cred_data.get('tenant_id')
        client_id = cred_data.get('client_id')
        client_secret = cred_data.get('client_secret')
        
        if not (tenant_id_cred and client_id and client_secret):
            raise ValueError("Azure credentials (tenant_id, client_id, client_secret) are required")
        
        # Parse resource_id to get VM info and determine OS type if shell not provided
        parts = vm_resource_id.strip("/").split("/")
        if len(parts) < 9 or "subscriptions" not in parts or "virtualMachines" not in parts:
            raise ValueError(f"Invalid VM resource ID format: {vm_resource_id}")
        
        vm_idx = parts.index("virtualMachines")
        vm_name = parts[vm_idx + 1]
        rg_idx = parts.index("resourceGroups")
        resource_group = parts[rg_idx + 1]
        
        # If shell not provided, try to detect from VM
        if not shell:
            try:
                from azure.identity import ClientSecretCredential
                from azure.mgmt.compute import ComputeManagementClient
                
                credential = ClientSecretCredential(
                    tenant_id=tenant_id_cred,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                compute_client = ComputeManagementClient(credential, subscription_id)
                
                # Get VM to detect OS type
                vm = compute_client.virtual_machines.get(
                    resource_group_name=resource_group,
                    vm_name=vm_name
                )
                
                if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                    os_type_val = vm.storage_profile.os_disk.os_type
                    if hasattr(os_type_val, 'value'):
                        os_type = os_type_val.value
                    else:
                        os_type = str(os_type_val)
                    
                    if os_type and "windows" in os_type.lower():
                        shell = "powershell"
                    else:
                        shell = "bash"
                else:
                    shell = "powershell"
            except Exception as e:
                logger.warning(f"Could not detect OS type for VM {vm_name}, defaulting to PowerShell: {e}")
                shell = "powershell"
        
        # Build connection config for connector
        connection_config = {
            "resource_id": vm_resource_id,
            "subscription_id": subscription_id,
            "shell": shell,
            "azure_credentials": {
                "tenant_id": tenant_id_cred,
                "client_id": client_id,
                "client_secret": client_secret
            },
            "tenant_id": tenant_id_cred,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        # Execute command using AzureBastionConnector
        connector = get_connector("azure_bastion")
        
        logger.info(f"Executing test command on VM {vm_name} (RG: {resource_group}): {command[:50]}")
        result = await connector.execute_command(
            command=command,
            connection_config=connection_config,
            timeout=60
        )
        
        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error", ""),
            "exit_code": result.get("exit_code", -1),
            "vm_name": vm_name,
            "resource_group": resource_group,
            "shell": shell,
            "command": command
        }


