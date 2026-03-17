"""
Agent session endpoints for execution API
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from app.controllers.execution_controller import ExecutionController

router = APIRouter()
logger = get_logger(__name__)


class AgentSessionCreate(BaseModel):
    """Start an agentic execution session for an issue with no matching runbook."""
    issue_description: str = Field(..., min_length=5)
    ticket_id: Optional[int] = None
    tenant_id: Optional[int] = 1
    user_id: Optional[int] = None
    connection_id: Optional[int] = None


class PlanRejectRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="Why the plan is wrong and what to do instead.")


class AgentSessionReview(BaseModel):
    """Human review after an agent session — mark weeds + optionally crystallise."""
    weed_step_numbers: List[int] = Field(
        default_factory=list,
        description="Step numbers the human considers unnecessary (excluded from runbook)",
    )
    save_as_runbook: bool = Field(default=True, description="Crystallise kept steps into a new runbook")
    runbook_title: Optional[str] = Field(default=None, description="Title for new runbook (auto-generated if omitted)")


@router.post("/demo/agent-sessions")
@rate_limit("20/minute")
async def create_agent_session(data: AgentSessionCreate, db: Session = Depends(get_db)):
    """Start an agentic execution session for an issue where no matching runbook exists."""
    controller = ExecutionController(db, tenant_id=data.tenant_id or 1)
    return await controller.create_agent_session(
        issue_description=data.issue_description,
        ticket_id=data.ticket_id,
        user_id=data.user_id,
        connection_id=data.connection_id,
    )


@router.get("/demo/agent-sessions/{session_id}/plan")
async def get_agent_session_plan(session_id: int, db: Session = Depends(get_db)):
    """Return the current diagnosis findings and proposed plan."""
    return ExecutionController(db, tenant_id=1).get_agent_session_plan(session_id)


@router.post("/demo/agent-sessions/{session_id}/plan/approve")
async def approve_agent_plan(session_id: int, db: Session = Depends(get_db)):
    """Approve the proposed plan — agent transitions into the execute phase."""
    return ExecutionController(db, tenant_id=1).approve_agent_plan(session_id)


@router.post("/demo/agent-sessions/{session_id}/plan/reject")
async def reject_agent_plan(session_id: int, data: PlanRejectRequest, db: Session = Depends(get_db)):
    """Reject the proposed plan with corrective feedback."""
    return ExecutionController(db, tenant_id=1).reject_agent_plan(session_id, data.feedback)


@router.post("/demo/agent-sessions/{session_id}/review")
async def review_agent_session(session_id: int, data: AgentSessionReview, db: Session = Depends(get_db)):
    """Human review: mark weeds and optionally crystallise into a runbook."""
    return await ExecutionController(db, tenant_id=1).review_agent_session(
        session_id=session_id,
        weed_step_numbers=data.weed_step_numbers,
        save_as_runbook=data.save_as_runbook,
        runbook_title=data.runbook_title,
    )


@router.get("/demo/agent-sessions/{session_id}/step-review")
async def get_agent_session_steps_for_review(session_id: int, db: Session = Depends(get_db)):
    """Return all steps formatted for the human review UI."""
    return ExecutionController(db, tenant_id=1).get_agent_session_steps_for_review(session_id)
