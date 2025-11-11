"""
Agent worker management endpoints (registration, heartbeat, assignment acknowledgements).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.execution_session import AgentWorkerAssignment, ExecutionSession
from app.services.agent_worker_manager import agent_worker_manager
from app.services.execution_orchestrator import execution_orchestrator
from app.core import metrics

router = APIRouter()
logger = get_logger(__name__)


class WorkerRegistrationRequest(BaseModel):
    worker_id: str
    capabilities: List[str] = Field(default_factory=list)
    network_segment: Optional[str] = None
    environment: Optional[str] = None
    max_concurrency: int = Field(default=1, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class WorkerStateResponse(BaseModel):
    worker_id: str
    capabilities: List[str]
    network_segment: Optional[str]
    environment: Optional[str]
    max_concurrency: int
    current_load: int
    last_heartbeat: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    current_load: Optional[int] = Field(default=None, ge=0)


class AssignmentAckRequest(BaseModel):
    session_id: int
    worker_id: str
    assignment_id: Optional[int] = None


class AssignmentAckResponse(BaseModel):
    assignment_id: int
    status: str
    acknowledged_at: str


class WorkerEventRequest(BaseModel):
    session_id: int
    event: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    step_number: Optional[int] = None


class WorkerEventResponse(BaseModel):
    stream_id: str
    event: str
    created_at: str


@router.post("/register", response_model=WorkerStateResponse)
async def register_worker(payload: WorkerRegistrationRequest) -> WorkerStateResponse:
    """Register a worker and record initial heartbeat."""
    state = agent_worker_manager.register_worker(
        worker_id=payload.worker_id,
        capabilities=payload.capabilities,
        network_segment=payload.network_segment,
        environment=payload.environment,
        max_concurrency=payload.max_concurrency,
        metadata=payload.metadata,
    )
    logger.info("Worker registered worker_id=%s environment=%s", state.worker_id, state.environment)
    return WorkerStateResponse(**state.to_dict())


@router.post("/heartbeat", response_model=WorkerStateResponse)
async def heartbeat_worker(payload: WorkerHeartbeatRequest) -> WorkerStateResponse:
    """Update worker heartbeat and current load."""
    state = agent_worker_manager.heartbeat(payload.worker_id, payload.current_load)
    if not state:
        raise HTTPException(status_code=404, detail="Worker not registered")
    return WorkerStateResponse(**state.to_dict())


@router.get("", response_model=List[WorkerStateResponse])
async def list_workers(
    capabilities: Optional[List[str]] = None,
    environment: Optional[str] = None,
    network_segment: Optional[str] = None,
) -> List[WorkerStateResponse]:
    """Return active workers filtered by optional criteria."""
    workers = agent_worker_manager.list_active_workers(
        capabilities=capabilities,
        environment=environment,
        network_segment=network_segment,
    )
    return [WorkerStateResponse(**worker.to_dict()) for worker in workers]


@router.post("/assignments/ack", response_model=AssignmentAckResponse)
async def acknowledge_assignment(
    payload: AssignmentAckRequest,
    db: Session = Depends(get_db),
) -> AssignmentAckResponse:
    """Mark the latest pending assignment for a session as acknowledged by worker."""
    query = db.query(AgentWorkerAssignment).filter(
        AgentWorkerAssignment.session_id == payload.session_id
    )
    if payload.assignment_id:
        query = query.filter(AgentWorkerAssignment.id == payload.assignment_id)
    else:
        query = query.filter(AgentWorkerAssignment.status == "pending")

    assignment = query.order_by(AgentWorkerAssignment.id.desc()).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Validate session exists
    session_exists = (
        db.query(ExecutionSession.id)
        .filter(ExecutionSession.id == payload.session_id)
        .first()
    )
    if not session_exists:
        raise HTTPException(status_code=404, detail="Execution session not found")

    assignment.worker_id = payload.worker_id
    assignment.status = "acknowledged"
    assignment.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)

    agent_worker_manager.heartbeat(payload.worker_id)
    metrics.record_assignment(assignment.status)

    return AssignmentAckResponse(
        assignment_id=assignment.id,
        status=assignment.status,
        acknowledged_at=assignment.acknowledged_at.isoformat(),
    )


@router.post("/events", response_model=WorkerEventResponse)
async def record_worker_event(
    payload: WorkerEventRequest,
    db: Session = Depends(get_db),
) -> WorkerEventResponse:
    """Allow workers to publish execution events back to orchestrator."""
    session = (
        db.query(ExecutionSession)
        .filter(ExecutionSession.id == payload.session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Execution session not found")

    stream_id = await execution_orchestrator.record_event(
        db,
        session_id=payload.session_id,
        event_type=payload.event,
        payload=payload.payload,
        step_number=payload.step_number,
    )
    db.commit()

    created_at = datetime.now(timezone.utc).isoformat()
    return WorkerEventResponse(stream_id=stream_id, event=payload.event, created_at=created_at)


