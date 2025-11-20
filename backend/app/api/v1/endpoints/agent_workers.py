"""
Agent worker management endpoints (registration, heartbeat, assignment acknowledgements).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.controllers.agent_worker_controller import AgentWorkerController

router = APIRouter()
controller = AgentWorkerController()


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
    result = controller.register_worker(
        worker_id=payload.worker_id,
        capabilities=payload.capabilities,
        network_segment=payload.network_segment,
        environment=payload.environment,
        max_concurrency=payload.max_concurrency,
        metadata=payload.metadata,
    )
    return WorkerStateResponse(**result)


@router.post("/heartbeat", response_model=WorkerStateResponse)
async def heartbeat_worker(payload: WorkerHeartbeatRequest) -> WorkerStateResponse:
    """Update worker heartbeat and current load."""
    result = controller.heartbeat_worker(
        worker_id=payload.worker_id,
        current_load=payload.current_load
    )
    return WorkerStateResponse(**result)


@router.get("", response_model=List[WorkerStateResponse])
async def list_workers(
    capabilities: Optional[List[str]] = None,
    environment: Optional[str] = None,
    network_segment: Optional[str] = None,
) -> List[WorkerStateResponse]:
    """Return active workers filtered by optional criteria."""
    workers = controller.list_workers(
        capabilities=capabilities,
        environment=environment,
        network_segment=network_segment,
    )
    return [WorkerStateResponse(**worker) for worker in workers]


@router.post("/assignments/ack", response_model=AssignmentAckResponse)
async def acknowledge_assignment(
    payload: AssignmentAckRequest,
    db: Session = Depends(get_db),
) -> AssignmentAckResponse:
    """Mark the latest pending assignment for a session as acknowledged by worker."""
    result = controller.acknowledge_assignment(
        session_id=payload.session_id,
        worker_id=payload.worker_id,
        assignment_id=payload.assignment_id,
        db=db
    )
    return AssignmentAckResponse(**result)


@router.post("/events", response_model=WorkerEventResponse)
async def record_worker_event(
    payload: WorkerEventRequest,
    db: Session = Depends(get_db),
) -> WorkerEventResponse:
    """Allow workers to publish execution events back to orchestrator."""
    result = await controller.record_worker_event(
        session_id=payload.session_id,
        event=payload.event,
        payload=payload.payload,
        step_number=payload.step_number,
        db=db
    )
    return WorkerEventResponse(**result)


