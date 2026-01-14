"""
Debug endpoints for execution sessions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.services.execution.connection_service import ConnectionService
from app.services.infrastructure import get_connector

router = APIRouter()
logger = get_logger(__name__)


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

