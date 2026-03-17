"""
Mixin: Azure VM cleanup for AzureBastionConnector
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureConnectorCleanupMixin:
    """Azure VM self-healing cleanup for AzureBastionConnector."""

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

        # No sleep needed - processes are killed immediately
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
