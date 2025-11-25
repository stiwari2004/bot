"""
Execution tracking and orchestration API endpoints
"""
from typing import Any, Dict, List, Optional, Literal
import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.controllers.execution_controller import ExecutionController
from app.services.execution_orchestrator import execution_orchestrator
from app.services.queue_client import queue_client

router = APIRouter()
logger = get_logger(__name__)


# Request models
class ExecutionSessionCreate(BaseModel):
    runbook_id: int
    issue_description: Optional[str] = None
    tenant_id: Optional[int] = 1
    ticket_id: Optional[int] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Optional idempotency key to avoid duplicate session creation.",
    )


class ExecutionStepUpdate(BaseModel):
    step_number: int
    step_type: str
    completed: bool
    success: Optional[bool] = None
    output: Optional[str] = None
    notes: Optional[str] = None
    approved: Optional[bool] = None


class ExecutionFeedbackCreate(BaseModel):
    was_successful: bool
    issue_resolved: bool
    rating: int
    feedback_text: Optional[str] = None
    suggestions: Optional[str] = None


# Response models
class ExecutionSessionResponse(BaseModel):
    id: int
    tenant_id: int
    runbook_id: int
    runbook_title: Optional[str] = None
    ticket_id: Optional[int] = None
    issue_description: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_minutes: Optional[int] = None
    current_step: Optional[int] = None
    waiting_for_approval: Optional[bool] = None
    transport_channel: Optional[str] = None
    sandbox_profile: Optional[str] = None
    assignment_retry_count: Optional[int] = None
    last_event_seq: Optional[str] = None
    connection: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionEventResponse(BaseModel):
    id: int
    session_id: int
    event: str
    payload: Dict[str, Any]
    stream_id: Optional[str] = None
    created_at: str
    step_number: Optional[int] = None


class ExecutionHistoryResponse(BaseModel):
    sessions: List[Dict[str, Any]]


class ManualCommandRequest(BaseModel):
    command: str = Field(..., min_length=1)
    shell: Optional[str] = Field(default="bash")
    run_as: Optional[str] = None
    reason: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=600, ge=1)
    user_id: Optional[int] = None
    idempotency_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional idempotency key to avoid executing the same command twice.",
    )


class SessionControlRequest(BaseModel):
    action: Literal["pause", "resume", "rollback"]
    reason: Optional[str] = None
    user_id: Optional[int] = None


@router.post("/demo/sessions", response_model=ExecutionSessionResponse)
async def create_execution_session(data: ExecutionSessionCreate, db: Session = Depends(get_db)):
    """Create a new execution session for a runbook"""
    controller = ExecutionController(db, tenant_id=data.tenant_id or 1)
    return await controller.create_execution_session(
        runbook_id=data.runbook_id,
        issue_description=data.issue_description,
        ticket_id=data.ticket_id,
        user_id=data.user_id,
        metadata=data.metadata,
        idempotency_key=data.idempotency_key
    )


@router.get("/demo/sessions/{session_id}", response_model=ExecutionSessionResponse)
async def get_execution_session(session_id: int, db: Session = Depends(get_db)):
    """Get execution session details with all steps"""
    try:
        controller = ExecutionController(db, tenant_id=1)  # Demo tenant
        result = controller.get_execution_session(session_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Execution session {session_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution session: {str(e)}"
        )


@router.get("/demo/sessions/{session_id}/events", response_model=List[ExecutionEventResponse])
async def list_session_events(
    session_id: int,
    since_id: Optional[int] = None,
    limit: int = 200,  # Increased default limit
    db: Session = Depends(get_db),
):
    """Return recorded execution events for a session."""
    try:
        controller = ExecutionController(db, tenant_id=1)  # Demo tenant
        events = controller.list_session_events(session_id, since_id, limit)
        if events is None:
            return []
        return [ExecutionEventResponse(**event) for event in events]
    except Exception as e:
        logger.error(f"Error listing events for session {session_id}: {e}", exc_info=True)
        # Return empty list instead of crashing
        return []


@router.patch("/demo/sessions/{session_id}/steps")
async def update_execution_step(
    session_id: int, 
    step_data: ExecutionStepUpdate,
    db: Session = Depends(get_db)
):
    """Update a specific step's completion status"""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    return await controller.update_execution_step(
        session_id=session_id,
        step_number=step_data.step_number,
        step_type=step_data.step_type,
        completed=step_data.completed,
        success=step_data.success,
        output=step_data.output,
        notes=step_data.notes,
        approved=step_data.approved
    )


@router.post("/demo/sessions/{session_id}/commands", response_model=ExecutionEventResponse)
async def submit_manual_command(
    session_id: int,
    payload: ManualCommandRequest,
    db: Session = Depends(get_db),
):
    """Submit a manual command to run within the execution session."""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    event_record = await controller.submit_manual_command(
        session_id=session_id,
        command=payload.command,
        shell=payload.shell,
        run_as=payload.run_as,
        reason=payload.reason,
        timeout_seconds=payload.timeout_seconds,
        user_id=payload.user_id,
        idempotency_key=payload.idempotency_key
    )
    return ExecutionEventResponse(**event_record)


@router.post("/demo/sessions/{session_id}/control", response_model=ExecutionSessionResponse)
async def control_execution_session(
    session_id: int,
    payload: SessionControlRequest,
    db: Session = Depends(get_db),
):
    """Pause, resume, or request rollback for a session."""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    serialized = await controller.control_execution_session(
        session_id=session_id,
        action=payload.action,
        reason=payload.reason,
        user_id=payload.user_id
    )
    return ExecutionSessionResponse(**serialized)


@router.post("/demo/sessions/{session_id}/complete")
async def complete_execution_session(
    session_id: int,
    feedback: ExecutionFeedbackCreate,
    db: Session = Depends(get_db)
):
    """Complete an execution session and record feedback"""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    return controller.complete_execution_session(
        session_id=session_id,
        was_successful=feedback.was_successful,
        issue_resolved=feedback.issue_resolved,
        rating=feedback.rating,
        feedback_text=feedback.feedback_text,
        suggestions=feedback.suggestions
    )


@router.post("/demo/sessions/{session_id}/abandon")
async def abandon_execution_session(
    session_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Abandon a stuck execution session"""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    return controller.abandon_execution_session(session_id, reason)


@router.get("/demo/runbooks/{runbook_id}/executions", response_model=ExecutionHistoryResponse)
async def get_runbook_execution_history(runbook_id: int, db: Session = Depends(get_db)):
    """Get all execution sessions for a specific runbook"""
    controller = ExecutionController(db, tenant_id=1)  # Demo tenant
    return ExecutionHistoryResponse(**controller.get_runbook_execution_history(runbook_id))


@router.get("/demo/executions", response_model=ExecutionHistoryResponse)
async def list_all_executions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all execution sessions (paginated)"""
    try:
        controller = ExecutionController(db, tenant_id=1)  # Demo tenant
        result = controller.list_all_executions(limit, offset)
        # Ensure result is a dict with 'sessions' key
        if not isinstance(result, dict):
            result = {"sessions": []}
        if "sessions" not in result:
            result = {"sessions": result if isinstance(result, list) else []}
        return ExecutionHistoryResponse(**result)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error in list_all_executions: {e}", exc_info=True)
        # Return empty result instead of crashing
        return ExecutionHistoryResponse(sessions=[])


@router.websocket("/ws/sessions/{session_id}")
async def stream_execution_events(websocket: WebSocket, session_id: int):
    """WebSocket stream for execution events."""
    await websocket.accept()

    session = None
    db = SessionLocal()
    try:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if session:
            initial_events = execution_orchestrator.list_events(db, session_id, limit=50)
        else:
            initial_events = []
    finally:
        db.close()

    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    last_id = "0-0"
    if initial_events:
        last_id = initial_events[-1].get("stream_id") or "0-0"
        await websocket.send_json({"events": initial_events})

    try:
        while True:
            messages = await queue_client.read_stream(
                settings.REDIS_STREAM_EVENTS,
                last_id=last_id,
                count=25,
                block=5_000,
            )

            batch: List[Dict[str, Any]] = []
            for message_id, payload in messages:
                last_id = message_id
                if payload.get("session_id") == session_id:
                    payload["stream_id"] = message_id
                    batch.append(payload)

            if batch:
                await websocket.send_json({"events": batch})
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("Execution event stream disconnected session=%s", session_id)
    except Exception as exc:
        logger.exception("WebSocket error session=%s: %s", session_id, exc)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


