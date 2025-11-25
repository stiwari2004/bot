"""
Azure connector for executing commands via Azure Run Command API

CLEAN REWRITE - Simple, minimal implementation
No retries, no workarounds, no complex logic
Just execute command and return result
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class AzureBastionConnector(InfrastructureConnector):
    """Connector that executes commands through Azure Run Command API."""
    
    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        Execute command on Azure VM using Azure Run Command API.
        
        Returns:
        {
            "success": bool,
            "output": str,
            "error": str,
            "exit_code": int,
            "connection_error": bool
        }
        """
        # Get resource ID
        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        if not resource_id:
            return {
                "success": False,
                "output": "",
                "error": "Azure connector requires resource_id (VM resource ID).",
                "exit_code": -1,
                "connection_error": True,
            }
        
        # Parse resource ID: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
        parts = resource_id.split("/")
        if len(parts) < 9 or "subscriptions" not in parts or "resourceGroups" not in parts or "virtualMachines" not in parts:
            return {
                "success": False,
                "output": "",
                "error": f"Invalid Azure resource ID format: {resource_id}",
                "exit_code": -1,
                "connection_error": True,
            }
        
        subscription_id = parts[parts.index("subscriptions") + 1]
        resource_group = parts[parts.index("resourceGroups") + 1]
        vm_name = parts[parts.index("virtualMachines") + 1]
        
        # Get credentials
        azure_creds = connection_config.get("azure_credentials") or {}
        tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
        client_id = azure_creds.get("client_id") or connection_config.get("client_id")
        client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
        
        # Authenticate
        try:
            from azure.identity import ClientSecretCredential, DefaultAzureCredential
            from azure.mgmt.compute import ComputeManagementClient
        except ImportError:
            return {
                "success": False,
                "output": "",
                "error": "Azure SDK not installed. Install: pip install azure-identity azure-mgmt-compute",
                "exit_code": -1,
                "connection_error": True,
            }
        
        if tenant_id and client_id and client_secret:
            credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        else:
            try:
                credential = DefaultAzureCredential()
            except Exception as e:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Azure credentials required. Error: {e}",
                    "exit_code": -1,
                    "connection_error": True,
                }
        
        compute_client = ComputeManagementClient(credential, subscription_id)
        
        # Determine shell (Windows = PowerShell, Linux = bash)
        os_type = connection_config.get("os_type", "")
        shell = connection_config.get("shell")
        if not shell:
            shell = "powershell" if (os_type and "windows" in os_type.lower()) else "bash"
        
        command_id = "RunPowerShellScript" if shell.lower() in ("powershell", "pwsh", "ps1") else "RunShellScript"
        
        logger.info(f"Azure Run Command: VM={vm_name}, Command={command[:80]}..., Shell={shell}")
        
        # Check VM state before attempting command (optional pre-check)
        # Note: This doesn't prevent conflicts, but helps with diagnostics
        try:
            def check_vm_state_sync():
                instance_view = compute_client.virtual_machines.instance_view(
                    resource_group_name=resource_group,
                    vm_name=vm_name
                )
                return instance_view
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                instance_view = await asyncio.wait_for(
                    loop.run_in_executor(executor, check_vm_state_sync),
                    timeout=10  # Quick check, 10s timeout
                )
            # Check power state
            power_state = None
            for status in instance_view.statuses or []:
                if status.code and status.code.startswith("PowerState/"):
                    power_state = status.code.replace("PowerState/", "")
                    break
            if power_state and power_state != "running":
                logger.warning(f"VM {vm_name} is not running (state: {power_state})")
        except Exception as check_error:
            # Don't fail on pre-check errors, just log
            logger.debug(f"Could not check VM state (non-fatal): {check_error}")
        
        # Execute command
        def run_command_sync():
            # begin_run_command initiates the command - conflict happens here if VM is busy
            poller = compute_client.virtual_machines.begin_run_command(
                resource_group_name=resource_group,
                vm_name=vm_name,
                parameters={"commandId": command_id, "script": [command]},
            )
            # poller.result() waits for completion by polling Azure status
            # This does NOT send new commands, just checks status of the command started above
            return poller.result(timeout=timeout)
        
        result = None
        retry_succeeded = False
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
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
            error_str = str(e)
            is_conflict = (
                "Conflict" in error_str or 
                "execution is in progress" in error_str.lower() or
                (hasattr(e, 'status_code') and getattr(e, 'status_code', None) == 409) or
                (hasattr(e, 'status') and getattr(e, 'status', None) == 409)
            )
            
            if is_conflict:
                logger.warning(f"Azure Run Command conflict detected for VM {vm_name}, attempting self-healing cleanup...")
                
                # Attempt self-healing cleanup with retries
                cleanup_result = None
                max_cleanup_retries = 3
                cleanup_retry_delays = [5, 15, 30]  # Increasing delays: 5s, 15s, 30s
                
                for retry_attempt in range(max_cleanup_retries):
                    if retry_attempt > 0:
                        wait_time = cleanup_retry_delays[retry_attempt - 1]
                        logger.info(f"Waiting {wait_time}s before cleanup retry {retry_attempt + 1}/{max_cleanup_retries}...")
                        await asyncio.sleep(wait_time)
                    
                    cleanup_result = await self._attempt_azure_cleanup(
                        vm_name=vm_name,
                        resource_group=resource_group,
                        compute_client=compute_client,
                        credential=credential,
                        subscription_id=subscription_id,
                        shell=shell,
                    )
                    
                    if cleanup_result.get("cleanup_success"):
                        logger.info(f"Self-healing cleanup successful for VM {vm_name} on attempt {retry_attempt + 1}")
                        break
                    else:
                        cleanup_error = cleanup_result.get("error", "Unknown")
                        is_cleanup_conflict = "conflict" in cleanup_error.lower() or "execution is in progress" in cleanup_error.lower()
                        if is_cleanup_conflict and retry_attempt < max_cleanup_retries - 1:
                            logger.warning(f"Cleanup attempt {retry_attempt + 1} conflicted, will retry...")
                            continue
                        else:
                            logger.warning(f"Cleanup attempt {retry_attempt + 1} failed: {cleanup_error}")
                
                if cleanup_result and cleanup_result.get("cleanup_success"):
                    logger.info(f"Self-healing cleanup successful for VM {vm_name}, retrying original command...")
                    # Wait a moment for cleanup to settle
                    await asyncio.sleep(2)
                    
                    # Retry original command once after cleanup
                    # Reuse the same executor from outer try block
                    try:
                        retry_result = await asyncio.wait_for(
                            loop.run_in_executor(executor, run_command_sync),
                            timeout=timeout
                        )
                        # If retry succeeds, use the retry result (will be parsed below)
                        result = retry_result
                        retry_succeeded = True
                        logger.info(f"Retry after cleanup succeeded for VM {vm_name}")
                    except asyncio.TimeoutError:
                        return {
                            "success": False,
                            "output": "",
                            "error": f"Azure Run Command timed out after {timeout} seconds (after cleanup)",
                            "exit_code": -1,
                            "connection_error": False,
                        }
                    except Exception as retry_error:
                        retry_error_str = str(retry_error)
                        is_retry_conflict = (
                            "Conflict" in retry_error_str or
                            "execution is in progress" in retry_error_str.lower() or
                            (hasattr(retry_error, 'status_code') and getattr(retry_error, 'status_code', None) == 409) or
                            (hasattr(retry_error, 'status') and getattr(retry_error, 'status', None) == 409)
                        )
                        
                        if is_retry_conflict:
                            # Retry also conflicted - VM is truly stuck
                            logger.error(f"Retry after cleanup also conflicted for VM {vm_name} - VM is truly stuck")
                            return {
                                "success": False,
                                "output": "",
                                "error": (
                                    f"Azure Run Command failed after self-healing attempt.\n\n"
                                    f"VM: {vm_name} (Resource Group: {resource_group})\n"
                                    f"Self-healing cleanup succeeded but command still conflicts.\n"
                                    f"This indicates a persistent stuck state that requires manual intervention.\n\n"
                                    f"Manual intervention required:\n"
                                    f"1. Restart the VM via Azure Portal (recommended)\n"
                                    f"2. Manually kill RunCommandExtension processes on the VM\n"
                                    f"3. Wait 5-10 minutes for Azure to timeout\n\n"
                                    f"Original error: {error_str[:300]}"
                                ),
                                "exit_code": -1,
                                "connection_error": True,
                            }
                        else:
                            # Retry failed for different reason
                            logger.error(f"Retry after cleanup failed for VM {vm_name}: {retry_error_str[:200]}")
                            return {
                                "success": False,
                                "output": "",
                                "error": f"Azure Run Command failed after cleanup: {retry_error_str[:500]}",
                                "exit_code": -1,
                                "connection_error": True,
                            }
                else:
                    # Cleanup failed after all retries - VM is truly stuck
                    cleanup_error = cleanup_result.get("error", "Unknown") if cleanup_result else "Cleanup not attempted"
                    logger.error(
                        f"Self-healing cleanup failed after {max_cleanup_retries} attempts for VM {vm_name}. "
                        f"Final cleanup error: {cleanup_error}"
                    )
                    return {
                        "success": False,
                        "output": "",
                        "error": (
                            f"Azure Run Command failed: (Conflict) Run command extension execution is in progress.\n\n"
                            f"VM: {vm_name} (Resource Group: {resource_group})\n"
                            f"Self-healing cleanup failed after {max_cleanup_retries} attempts - VM has persistent stuck command state.\n\n"
                            f"Attempted cleanup commands:\n"
                            f"1. Get-Process cmd | Where-Object {{ $_.SI -eq 0 }} | Stop-Process -Force\n"
                            f"2. Get-Process powershell | Where-Object {{ $_.SI -eq 0 }} | Stop-Process -Force\n"
                            f"3. Get-Process RunCommandExtension -ErrorAction SilentlyContinue | Stop-Process -Force\n\n"
                            f"Manual intervention required:\n"
                            f"1. Restart the VM via Azure Portal (recommended)\n"
                            f"2. Manually kill RunCommandExtension processes on the VM:\n"
                            f"   - Get-Process | Where-Object {{$_.ProcessName -like '*RunCommand*'}} | Stop-Process -Force\n"
                            f"   - Restart-Service RdAgent\n"
                            f"   - Restart-Service WindowsAzureGuestAgent\n"
                            f"3. Wait 5-10 minutes for Azure to timeout\n\n"
                            f"Check Azure Portal > VM '{vm_name}' > Activity Logs for stuck operations."
                        ),
                        "exit_code": -1,
                        "connection_error": True,
                    }
            else:
                # Non-conflict error
                logger.error(f"Azure Run Command failed: {error_str[:500]}")
                return {
                    "success": False,
                    "output": "",
                    "error": f"Azure Run Command failed: {error_str[:500]}",
                    "exit_code": -1,
                    "connection_error": True,
                }
        
        # If retry succeeded, we have result to parse; otherwise result should already be set from initial try
        if retry_succeeded and result:
            # Result is already set from retry, continue to parsing
            pass
        elif not result:
            # This shouldn't happen, but handle gracefully
            return {
                "success": False,
                "output": "",
                "error": "Azure Run Command completed but returned no result",
                "exit_code": -1,
                "connection_error": False,
            }
        
        # Parse result
        if not result:
            logger.error(f"Azure Run Command returned None result for VM {vm_name}")
            return {
                "success": False,
                "output": "",
                "error": "Azure Run Command returned no result",
                "exit_code": -1,
                "connection_error": False,
            }
        
        if not hasattr(result, 'value'):
            logger.error(f"Azure Run Command result for VM {vm_name} has no 'value' attribute. Result type: {type(result)}, Result: {result}")
            return {
                "success": False,
                "output": "",
                "error": "Azure Run Command returned invalid result structure",
                "exit_code": -1,
                "connection_error": False,
            }
        
        if not result.value:
            logger.warning(f"Azure Run Command result for VM {vm_name} has empty value list")
            return {
                "success": False,
                "output": "",
                "error": "Azure Run Command returned no output",
                "exit_code": -1,
                "connection_error": False,
            }
        
        stdout = ""
        stderr = ""
        exit_code = 0
        
        logger.info(f"Parsing Azure Run Command result for VM {vm_name}: {len(result.value)} output items")
        
        # Log the full result structure for debugging
        logger.debug(f"Azure result structure: type={type(result)}, value type={type(result.value)}, value length={len(result.value)}")
        for idx, output in enumerate(result.value):
            logger.debug(f"  Item {idx}: type={type(output)}, has code={hasattr(output, 'code')}, has message={hasattr(output, 'message')}")
        
        # Log all output codes to debug parsing issues
        all_codes = []
        for output in result.value:
            code = output.code
            message = output.message or ""
            all_codes.append(f"{code}(len={len(message)})")
            logger.debug(f"Azure output item: code={code}, message_length={len(message)}, message_preview={message[:100] if message else 'EMPTY'}")
        
        logger.info(f"Azure output codes found: {', '.join(all_codes)}")
        
        for output in result.value:
            code = output.code
            message = output.message or ""
            
            # Handle various Azure output code formats
            code_lower = str(code).lower() if code else ""
            
            if code_lower in ("stdout", "standardoutput", "output"):
                stdout += message
                if message:
                    logger.debug(f"Added to stdout: {len(message)} chars, preview: {message[:100]}")
            elif code_lower in ("stderr", "standarderror", "error"):
                stderr += message
                if message:
                    logger.debug(f"Added to stderr: {len(message)} chars, preview: {message[:100]}")
            elif code_lower in ("exitcode", "exit_code", "exit"):
                try:
                    exit_code = int(message or "0")
                    logger.debug(f"Exit code: {exit_code}")
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse exit code from message: {message}")
                    pass
            else:
                # Unknown code - log it and add to stdout as fallback (might be output in different format)
                logger.warning(f"Unknown Azure output code: {code}, adding to stdout. Message preview: {message[:100] if message else 'EMPTY'}")
                if message:
                    stdout += message
        
        # If stdout is empty but stderr has content and exit_code is 0, treat stderr as output
        # (Some commands like ping output to stderr even on success)
        if not stdout and stderr and exit_code == 0:
            logger.info(f"VM {vm_name}: stdout empty but stderr has content with exit_code=0, treating stderr as output")
            stdout = stderr
            stderr = ""
        
        logger.info(
            f"Azure Run Command result for VM {vm_name}: "
            f"exit_code={exit_code}, stdout_length={len(stdout)}, stderr_length={len(stderr)}, "
            f"stdout_preview={stdout[:300] if stdout else 'EMPTY'}..."
        )
        
        return {
            "success": exit_code == 0,
            "output": stdout,
            "error": stderr,
            "exit_code": exit_code,
            "connection_error": False,
        }
    
    async def _attempt_azure_cleanup(
        self,
        vm_name: str,
        resource_group: str,
        compute_client,
        credential,
        subscription_id: str,
        shell: str,
    ) -> Dict[str, Any]:
        """
        Attempt to clean up stuck RunCommandExtension processes on Azure VM.
        
        Returns:
        {
            "cleanup_success": bool,
            "error": str (if failed),
            "output": str (if succeeded)
        }
        """
        logger.info(f"Attempting self-healing cleanup for VM {vm_name}...")
        logger.info(f"Executing cleanup commands: Get-Process cmd/powershell/RunCommandExtension | Stop-Process -Force")
        
        # Direct cleanup commands - kill stuck processes in session 0
        # These are the exact commands the user specified
        cleanup_command = """
        # Kill stuck cmd processes in session 0
        Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.SI -eq 0 } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Kill stuck powershell processes in session 0
        Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.SI -eq 0 } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Kill RunCommandExtension process
        Get-Process RunCommandExtension -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Start-Sleep -Seconds 2
        Write-Output "Cleanup commands executed successfully"
        """
        
        command_id = "RunPowerShellScript" if shell.lower() in ("powershell", "pwsh", "ps1") else "RunShellScript"
        
        def run_cleanup_sync():
            try:
                poller = compute_client.virtual_machines.begin_run_command(
                    resource_group_name=resource_group,
                    vm_name=vm_name,
                    parameters={"commandId": command_id, "script": [cleanup_command]},
                )
                # Use shorter timeout for cleanup (30 seconds)
                return poller.result(timeout=30)
            except Exception as e:
                # If cleanup also conflicts, that's the result we need to return
                raise
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                cleanup_result = await asyncio.wait_for(
                    loop.run_in_executor(executor, run_cleanup_sync),
                    timeout=30
                )
            
            # Parse cleanup result
            if cleanup_result and hasattr(cleanup_result, 'value') and cleanup_result.value:
                stdout = ""
                for output in cleanup_result.value:
                    if output.code in ("StdOut", "stdout") and output.message:
                        stdout += output.message
                
                logger.info(f"Self-healing cleanup completed for VM {vm_name}: {stdout[:200]}")
                return {
                    "cleanup_success": True,
                    "output": stdout,
                }
            else:
                logger.warning(f"Self-healing cleanup returned no output for VM {vm_name}")
                return {
                    "cleanup_success": False,
                    "error": "Cleanup command returned no output",
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Self-healing cleanup timed out for VM {vm_name}")
            return {
                "cleanup_success": False,
                "error": "Cleanup command timed out after 30 seconds",
            }
        except Exception as cleanup_error:
            error_str = str(cleanup_error)
            is_cleanup_conflict = (
                "Conflict" in error_str or
                "execution is in progress" in error_str.lower() or
                (hasattr(cleanup_error, 'status_code') and getattr(cleanup_error, 'status_code', None) == 409) or
                (hasattr(cleanup_error, 'status') and getattr(cleanup_error, 'status', None) == 409)
            )
            
            if is_cleanup_conflict:
                logger.error(f"Self-healing cleanup also conflicted for VM {vm_name} - VM is truly stuck")
                return {
                    "cleanup_success": False,
                    "error": "Cleanup command also conflicted - VM has persistent stuck state",
                }
            else:
                logger.error(f"Self-healing cleanup failed for VM {vm_name}: {error_str[:200]}")
                return {
                    "cleanup_success": False,
                    "error": f"Cleanup command failed: {error_str[:200]}",
                }
