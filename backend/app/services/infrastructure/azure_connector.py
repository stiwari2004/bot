"""
Azure connector for executing commands via Azure Run Command API or Bastion
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class AzureBastionConnector(InfrastructureConnector):
    """Connector that executes commands through Azure Bastion or Azure Run Command API."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute command on Azure VM using Azure Run Command API or SSH through Bastion.
        
        For Azure Run Command (recommended):
        - connection_config needs: resource_id (VM resource ID), subscription_id
        - Optional: use_ssh (if True, use SSH through Bastion instead)
        
        For SSH through Bastion:
        - connection_config needs: resource_id, bastion_host, target_host, username, password/private_key
        """
        resource_id = (
            connection_config.get("resource_id")
            or connection_config.get("target_resource_id")
        )
        
        if not resource_id:
            return {
                "success": False,
                "output": "",
                "error": "Azure connector requires resource_id (VM resource ID).",
                "exit_code": -1,
                "connection_error": True,
            }
        
        # Check if we should use SSH through Bastion or Run Command API
        use_ssh = connection_config.get("use_ssh", False)
        bastion_host = connection_config.get("bastion_host")
        target_host = connection_config.get("host") or connection_config.get("target_host")
        
        # If use_ssh is True and bastion details are provided, use SSH through Bastion
        if use_ssh and bastion_host and target_host:
            return await self._execute_via_bastion_ssh(
                command, connection_config, timeout
            )
        
        # Otherwise, use Azure Run Command API (simpler, no public IP needed)
        return await self._execute_via_run_command(
            command, connection_config, timeout, resource_id
        )
    
    async def _execute_via_run_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int,
        resource_id: str,
    ) -> Dict[str, Any]:
        """Execute command using Azure Run Command API"""
        try:
            from azure.identity import ClientSecretCredential, DefaultAzureCredential
            from azure.mgmt.compute import ComputeManagementClient
            
            # Parse resource ID to get subscription, resource group, VM name
            # Format: /subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
            parts = resource_id.strip("/").split("/")
            if len(parts) < 9 or "subscriptions" not in parts:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Invalid Azure resource ID format: {resource_id}. Expected: /subscriptions/.../virtualMachines/...",
                    "exit_code": -1,
                    "connection_error": True,
                }
            
            sub_idx = parts.index("subscriptions")
            rg_idx = parts.index("resourceGroups")
            vm_idx = parts.index("virtualMachines")
            
            subscription_id = parts[sub_idx + 1]
            resource_group = parts[rg_idx + 1]
            vm_name = parts[vm_idx + 1]
            
            # Get Azure credentials - check both azure_credentials dict and direct fields
            azure_creds = connection_config.get("azure_credentials") or {}
            tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
            client_id = azure_creds.get("client_id") or connection_config.get("client_id")
            client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
            
            logger.info(f"Azure Run Command credential check: has_tenant_id={bool(tenant_id)}, has_client_id={bool(client_id)}, has_client_secret={bool(client_secret)}")
            
            if tenant_id and client_id and client_secret:
                # Use Service Principal
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            else:
                # Try DefaultAzureCredential (Managed Identity, Azure CLI, etc.)
                try:
                    credential = DefaultAzureCredential()
                except Exception as e:
                    logger.warning(f"Failed to use DefaultAzureCredential: {e}")
                    return {
                        "success": False,
                        "output": "",
                        "error": "Azure credentials required (tenant_id, client_id, client_secret) or DefaultAzureCredential must be configured.",
                        "exit_code": -1,
                        "connection_error": True,
                    }
            
            # Create Compute Management Client
            compute_client = ComputeManagementClient(credential, subscription_id)
            
            # Prepare command
            exec_command = (command or "").strip() or "echo 'Azure Run Command test'"
            
            # Determine shell based on VM OS
            # Priority: 1) connection_config["shell"], 2) os_type from discovery, 3) default to PowerShell for Windows
            shell = connection_config.get("shell")
            os_type = connection_config.get("os_type")
            
            # If shell not explicitly set, detect from OS type
            if not shell:
                if os_type and isinstance(os_type, str):
                    if "windows" in os_type.lower():
                        shell = "powershell"
                    else:
                        shell = "bash"
                else:
                    # Default to PowerShell for Windows VMs (most common case)
                    # If OS type unknown, default to bash (can be overridden)
                    shell = "bash"
            
            if shell.lower() in ("powershell", "pwsh", "ps1"):
                script = exec_command
                script_type = "PowerShell"
            else:
                script = exec_command
                script_type = "LinuxShell"
            
            logger.info(f"Azure Run Command: shell={shell}, script_type={script_type}, os_type={os_type}")
            
            logger.info(f"Executing Azure Run Command on VM {vm_name} (RG: {resource_group}): {exec_command[:50]}")
            
            # Execute Run Command
            # Note: Azure SDK operations are synchronous, so we run them in a thread pool
            def run_command_sync():
                poller = compute_client.virtual_machines.begin_run_command(
                    resource_group_name=resource_group,
                    vm_name=vm_name,
                    parameters={
                        "commandId": "RunShellScript" if script_type == "LinuxShell" else "RunPowerShellScript",
                        "script": [script] if isinstance(script, str) else script,
                    },
                )
                # Wait for completion (poller.result() blocks until done)
                return poller.result(timeout=timeout)
            
            # Run in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(executor, run_command_sync),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Azure Run Command timed out after {timeout} seconds",
                        "exit_code": -1,
                        "connection_error": False,
                    }
                except Exception as e:
                    logger.error(f"Azure Run Command execution error: {e}", exc_info=True)
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Azure Run Command failed: {str(e)}",
                        "exit_code": -1,
                        "connection_error": True,
                    }
            
            # Parse result
            if result.value and len(result.value) > 0:
                # Get stdout and stderr
                stdout = ""
                stderr = ""
                exit_code = 0
                
                for output in result.value:
                    code = output.code
                    if code == "StdOut":
                        stdout += output.message or ""
                    elif code == "StdErr":
                        stderr += output.message or ""
                    elif code == "ExitCode":
                        try:
                            exit_code = int(output.message or "0")
                        except:
                            pass
                
                return {
                    "success": exit_code == 0,
                    "output": stdout,
                    "error": stderr,
                    "exit_code": exit_code,
                    "connection_error": False,
                }
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": "Azure Run Command returned no output",
                    "exit_code": -1,
                    "connection_error": False,
                }
                
        except ImportError:
            logger.error("Azure SDK not installed. Install: pip install azure-identity azure-mgmt-compute")
            return {
                "success": False,
                "output": "",
                "error": "Azure SDK not installed. Please install: pip install azure-identity azure-mgmt-compute azure-mgmt-network",
                "exit_code": -1,
                "connection_error": True,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Azure Run Command error: {e}", exc_info=True)
            
            # Provide user-friendly error messages for common scenarios
            if "deallocated" in error_msg.lower() or "stopped" in error_msg.lower() or "powerstate" in error_msg.lower():
                return {
                    "success": False,
                    "output": "",
                    "error": f"VM is stopped or deallocated. Azure Run Command requires the VM to be running. Please start the VM first.",
                    "exit_code": -1,
                    "connection_error": True,
                }
            elif "403" in error_msg or "forbidden" in error_msg.lower() or "permission" in error_msg.lower():
                return {
                    "success": False,
                    "output": "",
                    "error": f"Permission denied. Service principal needs 'Virtual Machine Contributor' role on the VM resource group or subscription.",
                    "exit_code": -1,
                    "connection_error": True,
                }
            elif "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command execution timed out after {timeout} seconds. The command may still be running on the VM.",
                    "exit_code": -1,
                    "connection_error": False,
                }
            elif "invalid" in error_msg.lower() and "resource" in error_msg.lower():
                return {
                    "success": False,
                    "output": "",
                    "error": f"Invalid VM resource ID format. Expected: /subscriptions/.../virtualMachines/...",
                    "exit_code": -1,
                    "connection_error": True,
                }
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Azure Run Command failed: {error_msg}",
                    "exit_code": -1,
                    "connection_error": True,
                }
    
    async def _execute_via_bastion_ssh(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Execute command via SSH through Azure Bastion tunnel.
        This is more complex - for now, we'll use a simplified approach.
        """
        # For now, if SSH is requested but we don't have full Bastion implementation,
        # fall back to suggesting Run Command
        logger.warning("SSH through Azure Bastion not yet fully implemented. Using Run Command API instead.")
        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        return await self._execute_via_run_command(command, connection_config, timeout, resource_id)


