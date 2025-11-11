"""
Execution tracking and orchestration API endpoints
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal
import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep, ExecutionFeedback
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
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


class SessionControlRequest(BaseModel):
    action: Literal["pause", "resume", "rollback"]
    reason: Optional[str] = None
    user_id: Optional[int] = None


@router.post("/demo/sessions", response_model=ExecutionSessionResponse)
async def create_execution_session(data: ExecutionSessionCreate, db: Session = Depends(get_db)):
    """Create a new execution session for a runbook"""
    try:
        runbook = db.query(Runbook).filter(Runbook.id == data.runbook_id).first()
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        tenant_id = data.tenant_id or 1

        session = await execution_orchestrator.enqueue_session(
            db,
            runbook_id=data.runbook_id,
            tenant_id=tenant_id,
            ticket_id=data.ticket_id,
            issue_description=data.issue_description,
            user_id=data.user_id,
            metadata=data.metadata,
        )

        payload = execution_orchestrator.serialize_session(session)
        payload["runbook_title"] = runbook.title

        return ExecutionSessionResponse(**payload)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to enqueue execution session: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create execution session")


@router.get("/demo/sessions/{session_id}", response_model=ExecutionSessionResponse)
async def get_execution_session(session_id: int, db: Session = Depends(get_db)):
    """Get execution session details with all steps"""
    session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Execution session not found")

    runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()

    payload = execution_orchestrator.serialize_session(session)
    payload["runbook_title"] = runbook.title if runbook else "Unknown"

    return ExecutionSessionResponse(**payload)


@router.get("/demo/sessions/{session_id}/events", response_model=List[ExecutionEventResponse])
async def list_session_events(
    session_id: int,
    since_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Return recorded execution events for a session."""
    session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Execution session not found")

    events = execution_orchestrator.list_events(
        db,
        session_id=session_id,
        since_id=since_id,
        limit=limit,
    )
    return [ExecutionEventResponse(**event) for event in events]


@router.patch("/demo/sessions/{session_id}/steps")
async def update_execution_step(
    session_id: int, 
    step_data: ExecutionStepUpdate,
    db: Session = Depends(get_db)
):
    """Update a specific step's completion status"""
    try:
        # Verify session exists
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Find the step
        step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_data.step_number,
            ExecutionStep.step_type == step_data.step_type
        ).first()
        
        if not step:
            raise HTTPException(status_code=404, detail="Execution step not found")
        
        # Update step
        step.completed = step_data.completed
        if step_data.success is not None:
            step.success = step_data.success
        elif not step_data.completed:
            # Reset success if step reopened
            step.success = None

        if step_data.output is not None:
            step.output = step_data.output
        if step_data.notes is not None:
            step.notes = step_data.notes

        if step_data.completed:
            step.completed_at = datetime.now(timezone.utc)
        else:
            step.completed_at = None

        if step_data.approved is not None:
            step.approved = step_data.approved
            step.approved_at = datetime.now(timezone.utc)
        elif step.requires_approval and step.approved is None:
            # If approval not provided, ensure waiting_for_approval stays true
            session.waiting_for_approval = True

        # Update session progress indicators
        remaining_steps = [s for s in session.steps if not s.completed]
        if remaining_steps:
            session.current_step = remaining_steps[0].step_number
        else:
            session.current_step = session.steps[-1].step_number if session.steps else None
        session.waiting_for_approval = any(s.requires_approval and s.approved is None for s in session.steps)
        if session.waiting_for_approval:
            session.status = "waiting_approval"
        else:
            session.status = "in_progress"
        
        db.commit()
        
        return {"message": "Step updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/sessions/{session_id}/commands", response_model=ExecutionEventResponse)
async def submit_manual_command(
    session_id: int,
    payload: ManualCommandRequest,
    db: Session = Depends(get_db),
):
    """Submit a manual command to run within the execution session."""
    try:
        event_record = await execution_orchestrator.submit_manual_command(
            db,
            session_id=session_id,
            command=payload.command,
            shell=payload.shell,
            run_as=payload.run_as,
            reason=payload.reason,
            timeout_seconds=payload.timeout_seconds,
            user_id=payload.user_id,
        )
        return ExecutionEventResponse(**event_record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to submit manual command: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to submit manual command")


@router.post("/demo/sessions/{session_id}/control", response_model=ExecutionSessionResponse)
async def control_execution_session(
    session_id: int,
    payload: SessionControlRequest,
    db: Session = Depends(get_db),
):
    """Pause, resume, or request rollback for a session."""
    try:
        session = await execution_orchestrator.control_session(
            db,
            session_id=session_id,
            action=payload.action,
            reason=payload.reason,
            user_id=payload.user_id,
        )
        serialized = execution_orchestrator.serialize_session(session)
        return ExecutionSessionResponse(**serialized)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to perform session control action: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to control session")


@router.post("/demo/sessions/{session_id}/complete")
async def complete_execution_session(
    session_id: int,
    feedback: ExecutionFeedbackCreate,
    db: Session = Depends(get_db)
):
    """Complete an execution session and record feedback"""
    try:
        # Get session
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Execution session not found")
        
        # Calculate duration
        completed_at = datetime.now()
        duration_minutes = int((completed_at - session.started_at).total_seconds() / 60)
        
        # Update session
        session.status = "completed" if feedback.was_successful else "failed"
        session.completed_at = completed_at
        session.total_duration_minutes = duration_minutes
        
        # Create feedback
        feedback_record = ExecutionFeedback(
            session_id=session_id,
            was_successful=feedback.was_successful,
            issue_resolved=feedback.issue_resolved,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            suggestions=feedback.suggestions
        )
        db.add(feedback_record)
        
        # Create or update runbook usage tracking
        runbook_usage = RunbookUsage(
            runbook_id=session.runbook_id,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            issue_description=session.issue_description,
            confidence_score=0.0,  # Will be set by search/analysis
            was_helpful=feedback.was_successful,
            feedback_text=feedback.feedback_text,
            execution_time_minutes=duration_minutes
        )
        db.add(runbook_usage)
        
        db.commit()
        
        return {"message": "Execution session completed", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/runbooks/{runbook_id}/executions", response_model=ExecutionHistoryResponse)
async def get_runbook_execution_history(runbook_id: int, db: Session = Depends(get_db)):
    """Get all execution sessions for a specific runbook"""
    sessions = db.query(ExecutionSession).filter(
        ExecutionSession.runbook_id == runbook_id
    ).order_by(ExecutionSession.started_at.desc()).all()
    
    result: List[Dict[str, Any]] = []
    for session in sessions:
        payload = execution_orchestrator.serialize_session(session)
        payload["steps_count"] = len(session.steps)
        if session.feedback:
            payload["feedback"] = {
                "was_successful": session.feedback.was_successful,
                "issue_resolved": session.feedback.issue_resolved,
                "rating": session.feedback.rating,
                "feedback_text": session.feedback.feedback_text,
            }
        result.append(payload)

    return ExecutionHistoryResponse(sessions=result)


@router.get("/demo/executions", response_model=ExecutionHistoryResponse)
async def list_all_executions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all execution sessions (paginated)"""
    sessions = db.query(ExecutionSession).filter(
        ExecutionSession.tenant_id == 1  # Demo tenant
    ).order_by(ExecutionSession.started_at.desc()).limit(limit).offset(offset).all()
    
    result: List[Dict[str, Any]] = []
    for session in sessions:
        runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        payload = execution_orchestrator.serialize_session(session)
        payload["runbook_title"] = runbook.title if runbook else "Unknown"
        if session.feedback:
            payload["feedback"] = {
                "was_successful": session.feedback.was_successful,
                "issue_resolved": session.feedback.issue_resolved,
                "rating": session.feedback.rating,
            }
        result.append(payload)
    
    return ExecutionHistoryResponse(sessions=result)


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


