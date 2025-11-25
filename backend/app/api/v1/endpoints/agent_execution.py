"""
Agent execution endpoints with human validation
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional, List
from app.core.database import get_db
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.models.user import User
from app.services.auth import get_current_user
from app.services.execution import ExecutionEngine
from app.services.runbook_search import RunbookSearchService
from app.services.ticket_status_service import get_ticket_status_service
from app.core.logging import get_logger
from pydantic import BaseModel
from datetime import datetime, timezone
import json

router = APIRouter()
logger = get_logger(__name__)

# Store active WebSocket connections
active_connections: dict = {}


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
    db: Session = Depends(get_db)
):
    """Get all sessions waiting for approval"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
        sessions = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.waiting_for_approval == True,
            ExecutionSession.status == "waiting_approval"
        ).all()
        
        result = []
        for session in sessions:
            step = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.step_number == session.approval_step_number
            ).first()
            
            runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
            
            result.append({
                "session_id": session.id,
                "runbook_id": session.runbook_id,
                "runbook_title": runbook.title if runbook else "Unknown",
                "step_number": session.approval_step_number,
                "step_type": step.step_type if step else None,
                "command": step.command if step else None,
                "issue_description": session.issue_description,
                "created_at": session.created_at.isoformat() if session.created_at else None
            })
        
        return {"pending_approvals": result}
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")


@router.post("/execute")
async def start_execution(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start execution of a runbook"""
    import time
    start_time = time.time()
    logger.info(f"[START_EXECUTION] Received execution request: runbook_id={request.runbook_id}, ticket_id={request.ticket_id}, issue_description={request.issue_description[:50] if request.issue_description else None}")
    try:
        # Use demo tenant for POC
        tenant_id = 1
        user_id = None
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
            user_id = current_user.id
        except:
            pass  # Use defaults for demo
        
        # Verify runbook exists
        runbook = db.query(Runbook).filter(
            Runbook.id == request.runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        if runbook.status != "approved":
            raise HTTPException(status_code=400, detail="Runbook must be approved before execution")
        
        # Create execution session
        engine = ExecutionEngine()
        session = await engine.create_execution_session(
            db=db,
            runbook_id=request.runbook_id,
            tenant_id=tenant_id,
            ticket_id=request.ticket_id,
            issue_description=request.issue_description,
            user_id=user_id
            # Note: metadata is not used in execution engine, but can be stored in session if needed
        )
        
        # Update ticket status when execution starts (if ticket_id provided)
        if request.ticket_id:
            ticket_status_service = get_ticket_status_service()
            ticket_status_service.update_ticket_on_execution_start(db, request.ticket_id)
        
        # Return session immediately, then start execution asynchronously
        db.refresh(session)
        
        # Return full session data including steps
        from app.services.execution_orchestrator import execution_orchestrator
        payload = execution_orchestrator.serialize_session(session)
        payload["runbook_title"] = runbook.title
        
        elapsed = time.time() - start_time
        logger.info(f"[START_EXECUTION] Session created in {elapsed:.2f}s, returning session {session.id}")
        
        # Start execution in background - use asyncio.create_task for async functions
        async def start_execution_async(session_id: int):
            try:
                logger.info(f"[START_EXECUTION] ===== ASYNC TASK STARTED =====")
                logger.info(f"[START_EXECUTION] Session ID: {session_id}")
                logger.info(f"[START_EXECUTION] About to create new DB session...")
                
                # Need a new DB session for async execution
                from app.core.database import SessionLocal
                async_db = SessionLocal()
                try:
                    logger.info(f"[START_EXECUTION] DB session created, querying session {session_id}...")
                    execution_engine = ExecutionEngine()
                    session_refreshed = async_db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
                    
                    if not session_refreshed:
                        logger.error(f"[START_EXECUTION] ❌ Session {session_id} not found in database!")
                        return
                    
                    logger.info(f"[START_EXECUTION] Session found: id={session_refreshed.id}, status={session_refreshed.status}, current_step={session_refreshed.current_step}")
                    
                    if session_refreshed.status == "pending":
                        logger.info(f"[START_EXECUTION] ✅ Session {session_id} is pending, calling execution_engine.start_execution()...")
                        session_refreshed = await execution_engine.start_execution(async_db, session_refreshed.id)
                        async_db.refresh(session_refreshed)
                        logger.info(f"[START_EXECUTION] ✅ Execution engine returned. Session status: {session_refreshed.status}, current_step: {session_refreshed.current_step}")
                    else:
                        logger.warning(
                            f"[START_EXECUTION] ⚠️ Session {session_id} is not pending "
                            f"(status: {session_refreshed.status}), skipping execution start"
                        )
                except Exception as db_error:
                    logger.error(f"[START_EXECUTION] ❌ Database error for session {session_id}: {db_error}", exc_info=True)
                    import traceback
                    logger.error(f"[START_EXECUTION] Traceback: {traceback.format_exc()}")
                    raise
                finally:
                    async_db.close()
                    logger.info(f"[START_EXECUTION] DB session closed")
            except Exception as e:
                logger.error(f"[START_EXECUTION] ❌ CRITICAL ERROR in async execution for session {session_id}: {e}", exc_info=True)
                import traceback
                logger.error(f"[START_EXECUTION] Full traceback: {traceback.format_exc()}")
                # Re-raise to ensure the error is logged
                raise
        
        # Use asyncio.create_task to run the async function in the background
        # This ensures it runs even if the response is sent
        import asyncio
        try:
            logger.info(f"[START_EXECUTION] Creating asyncio task for session {session.id}...")
            task = asyncio.create_task(start_execution_async(session.id))
            logger.info(f"[START_EXECUTION] ✅ Task created: {task}")
            
            # Add done callback to log completion/errors
            def task_done_callback(future_task):
                try:
                    # Get the result (this will raise if there was an exception)
                    result = future_task.result()
                    logger.info(f"[START_EXECUTION] ✅ Background task completed for session {session.id}, result: {result}")
                except Exception as e:
                    logger.error(f"[START_EXECUTION] ❌ Background task failed for session {session.id}: {e}", exc_info=True)
                    import traceback
                    logger.error(f"[START_EXECUTION] Task failure traceback: {traceback.format_exc()}")
            task.add_done_callback(task_done_callback)
            logger.info(f"[START_EXECUTION] Done callback added to task")
        except Exception as e:
            logger.error(f"[START_EXECUTION] Failed to create background task for session {session.id}: {e}", exc_info=True)
            # Fallback: try to start execution synchronously (but this will block)
            # This should rarely happen, but it's a safety net
            logger.warning(f"[START_EXECUTION] Falling back to synchronous execution (this may block)")
            try:
                session = await engine.start_execution(db, session.id)
                db.refresh(session)
                logger.info(f"[START_EXECUTION] Fallback synchronous execution completed for session {session.id}")
            except Exception as sync_error:
                logger.error(f"[START_EXECUTION] Fallback execution also failed: {sync_error}", exc_info=True)
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/{session_id}/approve-step")
async def approve_step(
    session_id: int,
    request: StepApprovalRequest,
    db: Session = Depends(get_db)
):
    """Approve or reject a step"""
    try:
        # Get the session to determine which step needs approval
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Determine step_number: use from request, or from session's approval_step_number, or current_step
        step_number = request.step_number
        if step_number is None:
            # Use is not None checks to handle step 0 correctly (0 is falsy but valid)
            if session.approval_step_number is not None:
                step_number = session.approval_step_number
            elif session.current_step is not None:
                step_number = session.current_step
            else:
                raise HTTPException(status_code=400, detail="step_number is required. Either provide it in the request body or ensure the session has an approval_step_number or current_step.")
        
        # Use demo user for POC
        user_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            user_id = current_user.id
        except:
            pass  # Use default for demo
        
        if user_id is not None:
            user_exists = db.query(User).filter(User.id == user_id).first()
            if not user_exists:
                logger.warning(
                    "Fallback approver user_id=%s not found; proceeding without user reference.",
                    user_id,
                )
                user_id = None

        engine = ExecutionEngine()
        session = await engine.approve_step(
            db=db,
            session_id=session_id,
            step_number=step_number,
            user_id=user_id,
            approve=request.approve
        )
        
        db.refresh(session)
        
        # Get current step details
        current_step = None
        if session.current_step:
            current_step = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id,
                ExecutionStep.step_number == session.current_step
            ).first()
        
        return {
            "session_id": session.id,
            "status": session.status,
            "waiting_for_approval": session.waiting_for_approval,
            "approval_step_number": session.approval_step_number,
            "current_step": session.current_step,
            "step_details": {
                "step_number": current_step.step_number if current_step else None,
                "command": current_step.command if current_step else None,
                "output": current_step.output if current_step else None,
                "success": current_step.success if current_step else None
            } if current_step else None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving step: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve step: {str(e)}")


@router.get("/sessions")
async def list_execution_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    db: Session = Depends(get_db)
):
    """List all execution sessions with optional status filter"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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
    db: Session = Depends(get_db)
):
    """Get execution session status"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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
    db: Session = Depends(get_db)
):
    """Cancel a running execution session"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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
    db: Session = Depends(get_db)
):
    """Delete an execution session"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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
    db: Session = Depends(get_db)
):
    """Get all steps for a session with their execution status"""
    try:
        # Use demo tenant for POC
        tenant_id = 1
        
        # Try to get current user if available
        try:
            from app.services.auth import get_current_user
            current_user = await get_current_user()
            tenant_id = current_user.tenant_id
        except:
            pass  # Use default for demo
        
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


@router.websocket("/ws/approvals/{session_id}")
async def websocket_approvals(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time approval updates"""
    await websocket.accept()
    
    try:
        # Store connection
        if session_id not in active_connections:
            active_connections[session_id] = []
        active_connections[session_id].append(websocket)
        
        # Send initial status
        from app.core.database import SessionLocal
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
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
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
            
    except WebSocketDisconnect:
        # Remove connection
        if session_id in active_connections:
            active_connections[session_id].remove(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


async def notify_approval_needed(session_id: int, step_number: int):
    """Notify WebSocket clients that approval is needed"""
    if session_id in active_connections:
        message = {
            "type": "approval_needed",
            "session_id": session_id,
            "step_number": step_number
        }
        # Send to all connected clients
        for ws in active_connections[session_id]:
            try:
                await ws.send_json(message)
            except:
                pass

