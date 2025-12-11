"""
Agent execution endpoints with human validation
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query, status
from fastapi.exceptions import WebSocketException
try:
    from websockets.exceptions import ConnectionClosed
except ImportError:
    ConnectionClosed = Exception  # Fallback if websockets not installed
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional, List
from fastapi import Depends
from app.core.database import get_db
from app.core.tenant_utils import get_tenant_id
from app.core.config import settings
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_optional
from app.services.execution import ExecutionEngine
from app.services.runbook_search import RunbookSearchService
from app.services.ticket_status_service import get_ticket_status_service
from app.controllers.execution_controller import ExecutionController
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from app.core.errors import handle_exception
from app.core.input_sanitizer import sanitize_for_logging
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import asyncio
from typing import Dict, List, Tuple

router = APIRouter()
logger = get_logger(__name__)

# Store active WebSocket connections with metadata
# Format: {session_id: [(websocket, last_activity_time, user_id), ...]}
active_connections: Dict[int, List[Tuple[WebSocket, datetime, int]]] = {}

# WebSocket configuration
WEBSOCKET_IDLE_TIMEOUT = 30 * 60  # 30 minutes in seconds
WEBSOCKET_MAX_CONNECTIONS_PER_SESSION = 10
WEBSOCKET_HEARTBEAT_INTERVAL = 60  # 1 minute


class ExecutionRequest(BaseModel):
    runbook_id: int
    ticket_id: Optional[int] = None
    issue_description: Optional[str] = None
    metadata: Optional[dict] = None  # Accept metadata from frontend


class StepApprovalRequest(BaseModel):
    approve: bool
    step_number: Optional[int] = None  # Optional - will use session's approval_step_number if not provided
    notes: Optional[str] = None


@router.get("/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sessions waiting for approval"""
    try:
        tenant_id = get_tenant_id(current_user)
        controller = ExecutionController(db, tenant_id)
        return controller.get_pending_approvals()
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")


@router.post("/execute")
@rate_limit("100/minute")  # High limit for dev/test
async def start_execution(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Start execution of a runbook"""
    import time
    start_time = time.time()
    logger.info(f"[START_EXECUTION] Received execution request: runbook_id={request.runbook_id}, ticket_id={request.ticket_id}, issue_description={request.issue_description[:50] if request.issue_description else None}")
    try:
        # Get tenant_id and user_id from current user or defaults
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None
        
        # Delegate to controller - all business logic is now in ExecutionController
        controller = ExecutionController(db, tenant_id)
        payload = await controller.create_execution_session(
            runbook_id=request.runbook_id,
            issue_description=request.issue_description,
            ticket_id=request.ticket_id,
            user_id=user_id,
            metadata=request.metadata,
            auto_start=False  # Don't auto-start here - we'll do it in background
        )
        
        elapsed = time.time() - start_time
        logger.info(f"[START_EXECUTION] Session created in {elapsed:.2f}s, returning session {payload.get('id')}")
        
        # Start execution in background (non-blocking)
        session_id = payload.get('id')
        if session_id:
            async def start_execution_background():
                """Background task to start execution"""
                from app.core.database import SessionLocal
                from app.services.execution import ExecutionEngine
                from app.models.execution_session import ExecutionSession
                import asyncio
                
                # Small delay to ensure response is sent first
                await asyncio.sleep(0.1)
                
                background_db = SessionLocal()
                try:
                    logger.info(f"[BACKGROUND] Starting execution for session {session_id}")
                    
                    # Check session status and update if needed
                    session = background_db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
                    if not session:
                        logger.error(f"[BACKGROUND] Session {session_id} not found")
                        return
                    
                    # If session is queued, change it to pending to allow execution
                    if session.status == "queued":
                        logger.info(f"[BACKGROUND] Session {session_id} is queued, changing to pending")
                        session.status = "pending"
                        background_db.commit()
                        background_db.refresh(session)
                    
                    engine = ExecutionEngine()
                    session = await engine.start_execution(background_db, session_id)
                    logger.info(f"[BACKGROUND] Execution started for session {session_id}, status: {session.status}")
                    
                    # Ensure events are published by committing
                    background_db.commit()
                except Exception as e:
                    logger.error(f"[BACKGROUND] Failed to start execution for session {session_id}: {e}", exc_info=True)
                    import traceback
                    logger.error(f"[BACKGROUND] Traceback: {traceback.format_exc()}")
                    background_db.rollback()
                finally:
                    background_db.close()
            
            # FastAPI BackgroundTasks supports async functions
            background_tasks.add_task(start_execution_background)
            logger.info(f"[START_EXECUTION] Queued background execution for session {session_id}")
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/{session_id}/approve-step")
@rate_limit("200/minute")  # High limit for dev/test
async def approve_step(
    session_id: int,
    request: StepApprovalRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Approve or reject a step"""
    try:
        # Get tenant_id and user_id from current user or defaults
        tenant_id = get_tenant_id(current_user)
        user_id = current_user.id if current_user else None
        
        # Delegate to controller
        from app.controllers.execution_controller import ExecutionController
        controller = ExecutionController(db, tenant_id=tenant_id)
        result = await controller.approve_step(
            session_id=session_id,
            step_number=request.step_number,
            user_id=user_id,
            approve=request.approve,
            notes=request.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving step: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve step: {str(e)}")


@router.get("/sessions")
async def list_execution_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all execution sessions for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        
        query = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(ExecutionSession.status == status)
        
        sessions = query.order_by(ExecutionSession.created_at.desc()).limit(limit).all()
        
        # Get runbook titles
        from app.models.runbook import Runbook
        runbook_ids = [s.runbook_id for s in sessions]
        runbooks = {r.id: r.title for r in db.query(Runbook).filter(Runbook.id.in_(runbook_ids)).all()}
        
        return {
            "sessions": [
                {
                    "id": s.id,
                    "runbook_id": s.runbook_id,
                    "runbook_title": runbooks.get(s.runbook_id, "Unknown"),
                    "ticket_id": s.ticket_id,
                    "status": s.status,
                    "current_step": s.current_step,
                    "waiting_for_approval": s.waiting_for_approval,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "total_duration_minutes": s.total_duration_minutes,
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error(f"Error listing execution sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}")
async def get_execution_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution session status for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Get all steps
        steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id
        ).order_by(ExecutionStep.step_number).all()
        
        return {
            "session_id": session.id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "command": s.command,
                    "requires_approval": s.requires_approval,
                    "approved": s.approved,
                    "completed": s.completed,
                    "success": s.success,
                    "output": s.output,
                    "error": s.error
                }
                for s in steps
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.post("/{session_id}/cancel")
async def cancel_execution(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Cancel a running execution session"""
    try:
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
        tenant_id = current_user.tenant_id if current_user else 1
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Only allow canceling if session is in a cancellable state
        if session.status in ["completed", "failed", "abandoned"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel session with status '{session.status}'"
            )
        
        # Update session status to abandoned
        session.status = "abandoned"
        session.completed_at = func.now()
        db.commit()
        db.refresh(session)
        
        logger.info(f"Session {session_id} cancelled by user")
        
        return {
            "session_id": session.id,
            "status": session.status,
            "message": "Session cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel session: {str(e)}")
@router.delete("/{session_id}")
async def delete_execution_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete an execution session"""
    try:
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
        tenant_id = current_user.tenant_id if current_user else 1
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Don't allow deleting running sessions - cancel them first
        if session.status in ["pending", "waiting_approval", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete session with status '{session.status}'. Cancel it first."
            )
        
        db.delete(session)
        db.commit()
        
        logger.info(f"Session {session_id} deleted by user")
        
        return {
            "session_id": session_id,
            "message": "Session deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting execution session: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/debug/check-azure-vm-status")
async def check_azure_vm_status(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Check Azure VM status and see if there's actually a command running"""
    try:
        from app.services.execution.connection_service import ConnectionService
        from app.services.infrastructure import get_connector
        from azure.identity import ClientSecretCredential, DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")
        
        connection_service = ConnectionService()
        connection_config = await connection_service.get_connection_config(db, session, first_step)
        connector_type = connection_config.get("connector_type", "local")
        
        if connector_type != "azure_bastion":
            return {
                "error": f"Connector type is {connector_type}, not azure_bastion. This endpoint only works for Azure VMs."
            }
        
        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        if not resource_id:
            return {
                "error": "No resource_id found in connection config"
            }
        
        # Parse resource ID
        parts = resource_id.split("/")
        if len(parts) < 9:
            return {
                "error": f"Invalid resource ID format: {resource_id}"
            }
        
        sub_idx = parts.index("subscriptions")
        rg_idx = parts.index("resourceGroups")
        vm_idx = parts.index("virtualMachines")
        
        subscription_id = parts[sub_idx + 1]
        resource_group = parts[rg_idx + 1]
        vm_name = parts[vm_idx + 1]
        
        # Get Azure credentials
        azure_creds = connection_config.get("azure_credentials") or {}
        tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
        client_id = azure_creds.get("client_id") or connection_config.get("client_id")
        client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
        
        if tenant_id and client_id and client_secret:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            try:
                credential = DefaultAzureCredential()
            except Exception as e:
                return {
                    "error": f"Failed to get Azure credentials: {e}"
                }
        
        compute_client = ComputeManagementClient(credential, subscription_id)
        
        status_info = {
            "vm_name": vm_name,
            "resource_group": resource_group,
            "subscription_id": subscription_id,
            "vm_instance_view": None,
            "vm_power_state": None,
            "vm_provisioning_state": None,
            "extensions": [],
            "running_command_detected": False,
            "stuck_command_message": None,
            "error": None,
            "note": "If this endpoint hangs, Azure API is slow. Check backend logs for details."
        }
        
        # Import asyncio and ThreadPoolExecutor at function level
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            # Get VM instance view - this shows current state including running extensions
            # Use async with timeout to prevent hanging
            logger.info(f"[CHECK_VM_STATUS] Getting instance view for VM {vm_name}...")
            
            def get_instance_view_sync():
                try:
                    return compute_client.virtual_machines.instance_view(
                        resource_group_name=resource_group,
                        vm_name=vm_name
                    )
                except Exception as e:
                    raise e
            
            # Run in thread pool with timeout
            loop = asyncio.get_event_loop()
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    vm_instance_view = await asyncio.wait_for(
                        loop.run_in_executor(executor, get_instance_view_sync),
                        timeout=30  # 30 second timeout
                    )
            except asyncio.TimeoutError:
                status_info["error"] = "Timeout: Azure API call took longer than 30 seconds"
                status_info["vm_instance_view"] = None
                return status_info
            except Exception as e:
                status_info["error"] = f"Error getting instance view: {str(e)}"
                logger.error(f"Error getting VM instance view: {e}", exc_info=True)
                return status_info
            
            status_info["vm_instance_view"] = {
                "statuses": [
                    {
                        "code": status.code,
                        "display_status": status.display_status,
                        "level": status.level.value if hasattr(status.level, 'value') else str(status.level),
                        "time": status.time.isoformat() if hasattr(status.time, 'isoformat') else str(status.time)
                    }
                    for status in (vm_instance_view.statuses or [])
                ]
            }
            
            # Extract power state
            for status in vm_instance_view.statuses or []:
                if status.code and "PowerState" in status.code:
                    status_info["vm_power_state"] = status.display_status
                elif status.code and "ProvisioningState" in status.code:
                    status_info["vm_provisioning_state"] = status.display_status
            
            # Check extensions - Run Command uses an extension
            if vm_instance_view.extensions:
                for ext in vm_instance_view.extensions:
                    ext_info = {
                        "name": ext.name,
                        "type": ext.type,
                        "type_handler_version": ext.type_handler_version,
                        "provisioning_state": ext.provisioning_state,
                        "statuses": []
                    }
                    
                    if ext.statuses:
                        for ext_status in ext.statuses:
                            ext_info["statuses"].append({
                                "code": ext_status.code,
                                "display_status": ext_status.display_status,
                                "level": ext_status.level.value if hasattr(ext_status.level, 'value') else str(ext_status.level),
                                "message": ext_status.message,
                                "time": ext_status.time.isoformat() if hasattr(ext_status.time, 'isoformat') else str(ext_status.time)
                            })
                            
                            # Check if Run Command extension is in "running" state
                            if "RunCommand" in ext.name or "runcommand" in ext.name.lower():
                                if "running" in ext_status.display_status.lower() or "executing" in ext_status.display_status.lower() or "execution is in progress" in (ext_status.message or "").lower():
                                    status_info["running_command_detected"] = True
                                    status_info["stuck_command_message"] = ext_status.message or ext_status.display_status
                                    logger.warning(f"[CHECK_VM_STATUS] Found stuck command in RunCommand extension: {ext_status.message or ext_status.display_status}")
                    
                    status_info["extensions"].append(ext_info)
            
            # Also try to get VM details to check provisioning state (with timeout)
            try:
                def get_vm_sync():
                    return compute_client.virtual_machines.get(
                        resource_group_name=resource_group,
                        vm_name=vm_name
                    )
                
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    vm = await asyncio.wait_for(
                        loop.run_in_executor(executor, get_vm_sync),
                        timeout=10  # 10 second timeout for this call
                    )
                if vm.provisioning_state:
                    status_info["vm_provisioning_state"] = vm.provisioning_state
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting VM details for {vm_name}")
            except Exception as e:
                logger.warning(f"Could not get VM details: {e}")
            
        except Exception as e:
            status_info["error"] = str(e)
            import traceback
            status_info["traceback"] = traceback.format_exc()
            logger.error(f"Error checking VM status: {e}", exc_info=True)
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_azure_vm_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/debug/restart-azure-vm")
async def restart_azure_vm(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Restart Azure VM to clear stuck Run Command states.
    
    ⚠️ WARNING: This will restart the VM, which may interrupt any running processes.
    Use this only when Azure has a stuck Run Command state that prevents new commands.
    """
    try:
        from app.services.execution.connection_service import ConnectionService
        from azure.identity import ClientSecretCredential, DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")
        
        connection_service = ConnectionService()
        connection_config = await connection_service.get_connection_config(db, session, first_step)
        connector_type = connection_config.get("connector_type", "local")
        
        if connector_type != "azure_bastion":
            raise HTTPException(
                status_code=400,
                detail=f"Connector type is {connector_type}, not azure_bastion. This endpoint only works for Azure VMs."
            )
        
        resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
        if not resource_id:
            raise HTTPException(status_code=400, detail="No resource_id found in connection config")
        
        # Parse resource ID
        parts = resource_id.split("/")
        if len(parts) < 9:
            raise HTTPException(status_code=400, detail=f"Invalid resource ID format: {resource_id}")
        
        sub_idx = parts.index("subscriptions")
        rg_idx = parts.index("resourceGroups")
        vm_idx = parts.index("virtualMachines")
        
        subscription_id = parts[sub_idx + 1]
        resource_group = parts[rg_idx + 1]
        vm_name = parts[vm_idx + 1]
        
        # Get Azure credentials
        azure_creds = connection_config.get("azure_credentials") or {}
        tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
        client_id = azure_creds.get("client_id") or connection_config.get("client_id")
        client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
        
        if tenant_id and client_id and client_secret:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            try:
                credential = DefaultAzureCredential()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get Azure credentials: {e}")
        
        compute_client = ComputeManagementClient(credential, subscription_id)
        
        # Restart VM
        logger.info(f"[RESTART_VM] Restarting VM {vm_name} in resource group {resource_group} to clear stuck Run Command state...")
        
        def restart_vm_sync():
            poller = compute_client.virtual_machines.begin_restart(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            return poller.result(timeout=300)  # 5 minute timeout for restart
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, restart_vm_sync),
                    timeout=300
                )
            
            logger.info(f"[RESTART_VM] ✅ VM {vm_name} restarted successfully")
            return {
                "success": True,
                "message": f"VM {vm_name} restarted successfully. Wait 1-2 minutes for the VM to fully start before executing commands.",
                "vm_name": vm_name,
                "resource_group": resource_group,
                "note": "The VM restart will clear any stuck Run Command states. You can now retry your execution."
            }
        except asyncio.TimeoutError:
            logger.warning(f"[RESTART_VM] VM restart timed out after 5 minutes, but it may still be restarting")
            return {
                "success": False,
                "message": f"VM restart operation timed out. The VM may still be restarting. Check Azure Portal for status.",
                "vm_name": vm_name,
                "resource_group": resource_group
            }
        except Exception as e:
            error_str = str(e)
            logger.error(f"[RESTART_VM] Failed to restart VM: {error_str}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restart VM: {error_str}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in restart_azure_vm: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error restarting VM: {str(e)}")


@router.post("/debug/test-azure-connection")
async def test_azure_connection(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Diagnostic endpoint to test Azure connectivity step by step"""
    try:
        from app.services.execution.connection_service import ConnectionService
        from app.services.infrastructure import get_connector
        
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")
        
        diagnostic = {
            "session_id": session_id,
            "step_1": {
                "found": True,
                "command": first_step.command,
            },
            "step_2": {
                "connection_config": None,
                "connector_type": None,
                "has_resource_id": False,
                "has_azure_credentials": False,
                "error": None
            },
            "step_3": {
                "connector_found": False,
                "connector_class": None,
                "error": None
            },
            "step_4": {
                "test_command_result": None,
                "error": None
            }
        }
        
        # Step 2: Get connection config
        try:
            connection_service = ConnectionService()
            connection_config = await connection_service.get_connection_config(db, session, first_step)
            diagnostic["step_2"]["connection_config"] = {
                "keys": list(connection_config.keys()),
                "connector_type": connection_config.get("connector_type"),
            }
            diagnostic["step_2"]["connector_type"] = connection_config.get("connector_type")
            diagnostic["step_2"]["has_resource_id"] = bool(connection_config.get("resource_id"))
            diagnostic["step_2"]["has_azure_credentials"] = bool(connection_config.get("azure_credentials"))
        except Exception as e:
            diagnostic["step_2"]["error"] = str(e)
            return diagnostic
        
        # Step 3: Get connector
        try:
            connector_type = connection_config.get("connector_type", "local")
            connector = get_connector(connector_type)
            diagnostic["step_3"]["connector_found"] = True
            diagnostic["step_3"]["connector_class"] = type(connector).__name__
        except Exception as e:
            diagnostic["step_3"]["error"] = str(e)
            return diagnostic
        
        # Step 4: Test with a simple command (only for Azure)
        # ⚠️ DISABLED: Executing test commands causes Azure Run Command conflicts
        # Azure only allows one command at a time per VM. If we execute a test command here,
        # it will conflict with the actual step execution.
        # Instead, we just verify the connector can be instantiated.
        if connector_type == "azure_bastion":
            diagnostic["step_4"]["test_command_result"] = {
                "skipped": True,
                "reason": "Test command execution disabled to prevent Azure Run Command conflicts. Azure only allows one command at a time per VM. Use the actual step execution to test connectivity.",
                "note": "If you need to test connectivity, execute a real step instead of using this diagnostic endpoint."
            }
        
        return diagnostic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test_azure_connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostic error: {str(e)}")


@router.get("/debug/execution-state")
async def debug_execution_state(
    session_id: Optional[int] = Query(None, description="Session ID to debug"),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check execution state and identify issues"""
    try:
        debug_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "session_found": False,
            "session_status": None,
            "session_details": None,
            "steps": [],
            "first_step": None,
            "connection_config": None,
            "connector_type": None,
            "runbook_info": None,
            "parsing_info": None,
            "issues": []
        }
        
        if session_id:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if session:
                debug_info["session_found"] = True
                debug_info["session_status"] = session.status
                debug_info["session_details"] = {
                    "id": session.id,
                    "runbook_id": session.runbook_id,
                    "ticket_id": session.ticket_id,
                    "status": session.status,
                    "current_step": session.current_step,
                    "waiting_for_approval": session.waiting_for_approval,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                }
                
                # Get steps
                steps = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session_id
                ).order_by(ExecutionStep.step_number).all()
                
                debug_info["steps"] = [
                    {
                        "step_number": s.step_number,
                        "step_type": s.step_type,
                        "command": s.command,
                        "requires_approval": s.requires_approval,
                        "approved": s.approved,
                        "completed": s.completed,
                        "success": s.success,
                        "has_output": bool(s.output),
                        "has_error": bool(s.error),
                    }
                    for s in steps
                ]
                
                # Get first step
                first_step = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session_id,
                    ExecutionStep.step_number == 1
                ).first()
                
                if first_step:
                    debug_info["first_step"] = {
                        "step_number": first_step.step_number,
                        "command": first_step.command,
                        "requires_approval": first_step.requires_approval,
                        "completed": first_step.completed,
                    }
                    
                    # Try to get connection config
                    try:
                        from app.services.execution.connection_service import ConnectionService
                        connection_service = ConnectionService()
                        connection_config = await connection_service.get_connection_config(db, session, first_step)
                        debug_info["connection_config"] = {
                            "connector_type": connection_config.get("connector_type"),
                            "has_host": "host" in connection_config,
                            "has_resource_id": "resource_id" in connection_config,
                            "has_azure_credentials": "azure_credentials" in connection_config,
                            "keys": list(connection_config.keys()),
                        }
                        debug_info["connector_type"] = connection_config.get("connector_type")
                        
                        # Try to get connector
                        try:
                            from app.services.infrastructure import get_connector
                            connector = get_connector(connection_config.get("connector_type", "local"))
                            debug_info["connector_found"] = True
                            debug_info["connector_class"] = type(connector).__name__
                        except Exception as conn_error:
                            debug_info["connector_found"] = False
                            debug_info["connector_error"] = str(conn_error)
                            debug_info["issues"].append(f"Connector error: {conn_error}")
                    except Exception as config_error:
                        debug_info["connection_config_error"] = str(config_error)
                        debug_info["issues"].append(f"Connection config error: {config_error}")
                
                # Get runbook info
                runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
                if runbook:
                    debug_info["runbook_info"] = {
                        "id": runbook.id,
                        "title": runbook.title,
                        "status": runbook.status,
                        "body_length": len(runbook.body_md) if runbook.body_md else 0,
                        "body_preview": (runbook.body_md[:500] if runbook.body_md else "No body")[:500],
                    }
                    
                    # Try to parse the runbook to see what went wrong
                    try:
                        from app.services.runbook_parser import RunbookParser
                        parser = RunbookParser()
                        parsed = parser.parse_runbook(runbook.body_md or "")
                        if parsed:
                            debug_info["parsing_info"] = {
                                "has_prechecks": len(parsed.get("prechecks", [])) > 0,
                                "prechecks_count": len(parsed.get("prechecks", [])),
                                "has_main_steps": len(parsed.get("main_steps", [])) > 0,
                                "main_steps_count": len(parsed.get("main_steps", [])),
                                "has_postchecks": len(parsed.get("postchecks", [])) > 0,
                                "postchecks_count": len(parsed.get("postchecks", [])),
                                "total_steps": len(parsed.get("prechecks", [])) + len(parsed.get("main_steps", [])) + len(parsed.get("postchecks", [])),
                            }
                            if debug_info["parsing_info"]["total_steps"] == 0:
                                debug_info["issues"].append("Runbook parsing returned 0 steps - check runbook format")
                        else:
                            debug_info["parsing_info"] = {"error": "Parser returned None"}
                            debug_info["issues"].append("Runbook parser returned None - parsing failed")
                    except Exception as parse_error:
                        debug_info["parsing_info"] = {"error": str(parse_error)}
                        debug_info["issues"].append(f"Error parsing runbook: {parse_error}")
                
                # Check for issues
                if session.status == "pending":
                    debug_info["issues"].append("Session is still pending - execution may not have started")
                if not first_step:
                    debug_info["issues"].append("No first step found - cannot execute")
                if first_step and first_step.requires_approval and not first_step.approved:
                    debug_info["issues"].append("First step requires approval but not approved")
            else:
                debug_info["issues"].append(f"Session {session_id} not found")
        else:
            # Get all pending/in_progress sessions
            active_sessions = db.query(ExecutionSession).filter(
                ExecutionSession.status.in_(["pending", "in_progress", "waiting_approval"])
            ).all()
            debug_info["active_sessions"] = [
                {
                    "id": s.id,
                    "status": s.status,
                    "current_step": s.current_step,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in active_sessions
            ]
        
        return debug_info
    except Exception as e:
        logger.error(f"Error in debug_execution_state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/{session_id}/steps")
async def get_session_steps(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get all steps for a session with their execution status"""
    try:
        # Use authenticated user's tenant_id if available, otherwise fallback to demo tenant
        tenant_id = current_user.tenant_id if current_user else 1
        
        session = db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id,
            ExecutionSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id
        ).order_by(ExecutionStep.step_number).all()
        
        return {
            "session_id": session_id,
            "status": session.status,
            "current_step": session.current_step,
            "steps": [
                {
                    "id": s.id,
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "command": s.command,
                    "notes": s.notes,
                    "requires_approval": s.requires_approval,
                    "approved": s.approved,
                    "completed": s.completed,
                    "success": s.success,
                    "output": s.output,
                    "error": s.error,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session steps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session steps: {str(e)}")


def cleanup_connection(session_id: int, websocket: WebSocket):
    """Helper function to clean up a WebSocket connection"""
    if session_id in active_connections:
        # Remove this specific websocket from the list
        active_connections[session_id] = [
            (ws, last_activity, user_id) 
            for ws, last_activity, user_id in active_connections[session_id]
            if ws != websocket
        ]
        # Remove empty session entries
        if not active_connections[session_id]:
            del active_connections[session_id]
            logger.debug(f"Removed empty connection list for session {session_id}")


async def cleanup_idle_connections():
    """Background task to clean up idle WebSocket connections"""
    while True:
        try:
            await asyncio.sleep(WEBSOCKET_HEARTBEAT_INTERVAL)
            current_time = datetime.now(timezone.utc)
            sessions_to_remove = []
            
            for session_id, connections in list(active_connections.items()):
                active_conns = []
                for ws, last_activity, user_id in connections:
                    # Check if connection is idle
                    idle_time = (current_time - last_activity).total_seconds()
                    if idle_time > WEBSOCKET_IDLE_TIMEOUT:
                        logger.info(f"Closing idle WebSocket connection for session {session_id} (idle for {idle_time:.0f}s)")
                        try:
                            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Connection timeout")
                        except Exception:
                            pass  # Connection may already be closed
                    else:
                        # Check if connection is still alive
                        try:
                            # Try to ping the connection
                            await ws.send_json({"type": "ping"})
                            active_conns.append((ws, last_activity, user_id))
                        except Exception:
                            logger.debug(f"Removing dead connection for session {session_id}")
                            # Connection is dead, don't add it back
                
                if active_conns:
                    active_connections[session_id] = active_conns
                else:
                    sessions_to_remove.append(session_id)
            
            # Remove empty sessions
            for session_id in sessions_to_remove:
                del active_connections[session_id]
                logger.debug(f"Removed empty connection list for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error in cleanup_idle_connections: {e}", exc_info=True)


@router.websocket("/ws/approvals/{session_id}")
async def websocket_approvals(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time approval updates (MF-9: Requires authentication)"""
    # Security: Authenticate WebSocket connection
    token = websocket.query_params.get("token") or websocket.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    # Use context manager for database session
    from app.core.database import SessionLocal
    from jose import JWTError, jwt
    from app.core.config import settings
    
    db = None
    user_id = None
    try:
        # Authenticate user
        db = SessionLocal()
        try:
            # Validate token and get user
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                email: str = payload.get("sub")
                if not email:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                    return
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                    return
                user_id = user.id
            except (JWTError, Exception) as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        finally:
            db.close()
            db = None
        
        # Check connection limit
        if session_id in active_connections:
            current_connections = len(active_connections[session_id])
            if current_connections >= WEBSOCKET_MAX_CONNECTIONS_PER_SESSION:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Maximum connections ({WEBSOCKET_MAX_CONNECTIONS_PER_SESSION}) reached for this session"
                )
                return
        
        await websocket.accept()
        
        # Store connection with metadata
        current_time = datetime.now(timezone.utc)
        if session_id not in active_connections:
            active_connections[session_id] = []
        active_connections[session_id].append((websocket, current_time, user_id))
        logger.info(f"WebSocket connection established for session {session_id} (user {user_id}, total connections: {len(active_connections[session_id])})")
        
        # Send initial status
        db = SessionLocal()
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if session:
                await websocket.send_json({
                    "type": "status",
                    "session_id": session_id,
                    "status": session.status,
                    "waiting_for_approval": session.waiting_for_approval
                })
        finally:
            db.close()
            db = None
        
        # Listen for messages with timeout
        while True:
            try:
                # Wait for message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=WEBSOCKET_HEARTBEAT_INTERVAL
                )
                
                # Update last activity time
                current_time = datetime.now(timezone.utc)
                if session_id in active_connections:
                    for i, (ws, last_activity, uid) in enumerate(active_connections[session_id]):
                        if ws == websocket:
                            active_connections[session_id][i] = (ws, current_time, uid)
                            break
                
                if data.get("type") == "approval":
                    # Handle approval
                    approve = data.get("approve", False)
                    step_number = data.get("step_number")
                    
                    # Process approval (this would call the approval endpoint logic)
                    await websocket.send_json({
                        "type": "approval_received",
                        "approved": approve,
                        "step_number": step_number
                    })
                elif data.get("type") == "pong":
                    # Heartbeat response
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                try:
                    await websocket.send_json({"type": "ping"})
                    # Update last activity
                    current_time = datetime.now(timezone.utc)
                    if session_id in active_connections:
                        for i, (ws, last_activity, uid) in enumerate(active_connections[session_id]):
                            if ws == websocket:
                                active_connections[session_id][i] = (ws, current_time, uid)
                                break
                except Exception:
                    # Connection is dead, break the loop
                    break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        cleanup_connection(session_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        cleanup_connection(session_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass  # Connection may already be closed
    finally:
        # Ensure database session is closed
        if db is not None:
            try:
                db.close()
            except Exception as e:
                logger.debug(f"Error closing database session: {e}")
        # Final cleanup
        cleanup_connection(session_id, websocket)


async def notify_approval_needed(session_id: int, step_number: int):
    """Notify WebSocket clients that approval is needed"""
    if session_id in active_connections:
        message = {
            "type": "approval_needed",
            "session_id": session_id,
            "step_number": step_number
        }
        # Send to all connected clients and clean up dead connections
        current_time = datetime.now(timezone.utc)
        active_conns = []
        for ws, last_activity, user_id in active_connections[session_id]:
            try:
                await ws.send_json(message)
                # Update last activity
                active_conns.append((ws, current_time, user_id))
            except (WebSocketDisconnect, ConnectionClosed, WebSocketException, Exception) as e:
                logger.debug(f"Failed to send message to WebSocket client: {e}")
                # Don't add dead connection back
        # Update active connections
        if active_conns:
            active_connections[session_id] = active_conns
        else:
            # No active connections, remove the session
            del active_connections[session_id]

