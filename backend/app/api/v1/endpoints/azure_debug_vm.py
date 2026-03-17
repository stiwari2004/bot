"""
Azure VM status and restart debug endpoints
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.connection_service import ConnectionService

router = APIRouter()
logger = get_logger(__name__)


def _parse_azure_resource_id(resource_id: str) -> dict:
    """Parse Azure resource ID into components"""
    parts = resource_id.split("/")
    if len(parts) < 9:
        raise ValueError(f"Invalid resource ID format: {resource_id}")
    sub_idx = parts.index("subscriptions")
    rg_idx = parts.index("resourceGroups")
    vm_idx = parts.index("virtualMachines")
    return {
        "subscription_id": parts[sub_idx + 1],
        "resource_group": parts[rg_idx + 1],
        "vm_name": parts[vm_idx + 1],
    }


def _get_azure_credentials(connection_config: dict):
    """Get Azure credentials from connection config"""
    azure_creds = connection_config.get("azure_credentials") or {}
    tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
    client_id = azure_creds.get("client_id") or connection_config.get("client_id")
    client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
    if tenant_id and client_id and client_secret:
        return ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
    return DefaultAzureCredential()


@router.get("/debug/check-azure-vm-status")
async def check_azure_vm_status(session_id: int, db: Session = Depends(get_db)):
    """Check Azure VM status and see if there's actually a command running"""
    try:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id, ExecutionStep.step_number == 1
        ).first()
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")

        connection_service = ConnectionService()
        connection_config = await connection_service.get_connection_config(db, session, first_step)
        connector_type = connection_config.get("connector_type", "local")

        if connector_type != "azure_bastion":
            return {"error": f"Connector type is {connector_type}, not azure_bastion. This endpoint only works for Azure VMs."}

        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        if not resource_id:
            return {"error": "No resource_id found in connection config"}

        try:
            resource_info = _parse_azure_resource_id(resource_id)
        except ValueError as e:
            return {"error": str(e)}

        try:
            credential = _get_azure_credentials(connection_config)
        except Exception as e:
            return {"error": f"Failed to get Azure credentials: {e}"}

        compute_client = ComputeManagementClient(credential, resource_info["subscription_id"])

        status_info = {
            "vm_name": resource_info["vm_name"],
            "resource_group": resource_info["resource_group"],
            "subscription_id": resource_info["subscription_id"],
            "vm_instance_view": None,
            "vm_power_state": None,
            "vm_provisioning_state": None,
            "extensions": [],
            "running_command_detected": False,
            "stuck_command_message": None,
            "error": None,
            "note": "If this endpoint hangs, Azure API is slow. Check backend logs for details.",
        }

        try:
            logger.info(f"[CHECK_VM_STATUS] Getting instance view for VM {resource_info['vm_name']}...")

            def get_instance_view_sync():
                return compute_client.virtual_machines.instance_view(
                    resource_group_name=resource_info["resource_group"],
                    vm_name=resource_info["vm_name"],
                )

            loop = asyncio.get_event_loop()
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    vm_instance_view = await asyncio.wait_for(
                        loop.run_in_executor(executor, get_instance_view_sync), timeout=30
                    )
            except asyncio.TimeoutError:
                status_info["error"] = "Timeout: Azure API call took longer than 30 seconds"
                return status_info
            except Exception as e:
                status_info["error"] = f"Error getting instance view: {str(e)}"
                logger.error(f"Error getting VM instance view: {e}", exc_info=True)
                return status_info

            status_info["vm_instance_view"] = {
                "statuses": [
                    {
                        "code": s.code,
                        "display_status": s.display_status,
                        "level": s.level.value if hasattr(s.level, "value") else str(s.level),
                        "time": s.time.isoformat() if hasattr(s.time, "isoformat") else str(s.time),
                    }
                    for s in (vm_instance_view.statuses or [])
                ]
            }

            for s in vm_instance_view.statuses or []:
                if s.code and "PowerState" in s.code:
                    status_info["vm_power_state"] = s.display_status
                elif s.code and "ProvisioningState" in s.code:
                    status_info["vm_provisioning_state"] = s.display_status

            if vm_instance_view.extensions:
                for ext in vm_instance_view.extensions:
                    ext_info = {
                        "name": ext.name, "type": ext.type,
                        "type_handler_version": ext.type_handler_version,
                        "provisioning_state": ext.provisioning_state,
                        "statuses": [],
                    }
                    if ext.statuses:
                        for ext_status in ext.statuses:
                            ext_info["statuses"].append({
                                "code": ext_status.code,
                                "display_status": ext_status.display_status,
                                "level": ext_status.level.value if hasattr(ext_status.level, "value") else str(ext_status.level),
                                "message": ext_status.message,
                                "time": ext_status.time.isoformat() if hasattr(ext_status.time, "isoformat") else str(ext_status.time),
                            })
                            if "RunCommand" in ext.name or "runcommand" in ext.name.lower():
                                msg = ext_status.message or ""
                                if (
                                    "running" in ext_status.display_status.lower()
                                    or "executing" in ext_status.display_status.lower()
                                    or "execution is in progress" in msg.lower()
                                ):
                                    status_info["running_command_detected"] = True
                                    status_info["stuck_command_message"] = msg or ext_status.display_status
                                    logger.warning(f"[CHECK_VM_STATUS] Found stuck command: {msg or ext_status.display_status}")
                    status_info["extensions"].append(ext_info)

            try:
                def get_vm_sync():
                    return compute_client.virtual_machines.get(
                        resource_group_name=resource_info["resource_group"],
                        vm_name=resource_info["vm_name"],
                    )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    vm = await asyncio.wait_for(
                        loop.run_in_executor(executor, get_vm_sync), timeout=10
                    )
                if vm.provisioning_state:
                    status_info["vm_provisioning_state"] = vm.provisioning_state
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting VM details for {resource_info['vm_name']}")
            except Exception as e:
                logger.warning(f"Could not get VM details: {e}")

        except Exception as e:
            import traceback
            status_info["error"] = str(e)
            status_info["traceback"] = traceback.format_exc()
            logger.error(f"Error checking VM status: {e}", exc_info=True)

        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_azure_vm_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/debug/restart-azure-vm")
async def restart_azure_vm(session_id: int, db: Session = Depends(get_db)):
    """
    Restart Azure VM to clear stuck Run Command states.

    WARNING: This will restart the VM, which may interrupt any running processes.
    Use this only when Azure has a stuck Run Command state that prevents new commands.
    """
    try:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id, ExecutionStep.step_number == 1
        ).first()
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")

        connection_service = ConnectionService()
        connection_config = await connection_service.get_connection_config(db, session, first_step)
        connector_type = connection_config.get("connector_type", "local")

        if connector_type != "azure_bastion":
            raise HTTPException(
                status_code=400,
                detail=f"Connector type is {connector_type}, not azure_bastion. This endpoint only works for Azure VMs.",
            )

        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        if not resource_id:
            raise HTTPException(status_code=400, detail="No resource_id found in connection config")

        try:
            resource_info = _parse_azure_resource_id(resource_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            credential = _get_azure_credentials(connection_config)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get Azure credentials: {e}")

        compute_client = ComputeManagementClient(credential, resource_info["subscription_id"])

        logger.info(
            f"[RESTART_VM] Restarting VM {resource_info['vm_name']} in "
            f"resource group {resource_info['resource_group']} to clear stuck Run Command state..."
        )

        def restart_vm_sync():
            poller = compute_client.virtual_machines.begin_restart(
                resource_group_name=resource_info["resource_group"],
                vm_name=resource_info["vm_name"],
            )
            return poller.result(timeout=300)

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await asyncio.wait_for(loop.run_in_executor(executor, restart_vm_sync), timeout=300)
            logger.info(f"[RESTART_VM] VM {resource_info['vm_name']} restarted successfully")
            return {
                "success": True,
                "message": f"VM {resource_info['vm_name']} restarted successfully. Wait 1-2 minutes before executing commands.",
                "vm_name": resource_info["vm_name"],
                "resource_group": resource_info["resource_group"],
                "note": "The VM restart will clear any stuck Run Command states. You can now retry your execution.",
            }
        except asyncio.TimeoutError:
            logger.warning(f"[RESTART_VM] VM restart timed out after 5 minutes, but it may still be restarting")
            return {
                "success": False,
                "message": "VM restart operation timed out. The VM may still be restarting. Check Azure Portal for status.",
                "vm_name": resource_info["vm_name"],
                "resource_group": resource_info["resource_group"],
            }
        except Exception as e:
            logger.error(f"[RESTART_VM] Failed to restart VM: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to restart VM: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in restart_azure_vm: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error restarting VM: {str(e)}")
