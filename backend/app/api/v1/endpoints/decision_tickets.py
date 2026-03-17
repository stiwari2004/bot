"""
Decision — ticket-scoped recommendation and feedback endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from app.controllers.decision_controller import get_decision_controller
from app.controllers.pattern_feedback_controller import PatternFeedbackController
from app.models.user import User
from app.services.auth import get_current_user
from app.api.v1.endpoints.decision_schemas import (
    RecommendationResponse, PatternMatchResponse, ContextCorrelationResponse,
    MarkProblemCandidateRequest, MarkProblemCandidateResponse,
    RunbookFeedbackRequest, RunbookFeedbackResponse,
    PatternFeedbackRequest, PatternFeedbackResponse,
    ExplanationRequest, ExplanationResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/demo/tickets/{ticket_id}/runbook-feedback",
    response_model=RunbookFeedbackResponse,
)
@rate_limit("60/minute")
async def submit_runbook_feedback(
    ticket_id: int,
    request: RunbookFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback that a runbook does or does not match the ticket."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.submit_runbook_feedback(
            ticket_id=ticket_id,
            runbook_id=request.runbook_id,
            matches=request.matches,
            user_email=current_user.email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error submitting runbook feedback for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Failed to submit runbook feedback")


@router.get("/demo/tickets/{ticket_id}/recommendation", response_model=RecommendationResponse)
@rate_limit("60/minute")
async def get_recommendation(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get runbook recommendation for a ticket."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.get_recommendation(ticket_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting recommendation for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/demo/tickets/{ticket_id}/mark-problem-candidate",
    response_model=MarkProblemCandidateResponse,
)
@rate_limit("60/minute")
async def mark_problem_candidate(
    ticket_id: int,
    request: MarkProblemCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a ticket as a problem candidate."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.mark_problem_candidate(
            ticket_id=ticket_id,
            note=request.note,
            user_email=current_user.email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error marking ticket %d as problem candidate: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Failed to mark ticket as problem candidate")


@router.get("/demo/tickets/{ticket_id}/patterns", response_model=List[PatternMatchResponse])
@rate_limit("60/minute")
async def get_matching_patterns(
    ticket_id: int,
    pattern_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get patterns matching a ticket."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.get_matching_patterns(ticket_id, pattern_type, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting patterns for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/context", response_model=ContextCorrelationResponse)
@rate_limit("60/minute")
async def get_ticket_context(
    ticket_id: int,
    time_window_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get correlated context for a ticket."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.get_ticket_context(ticket_id, time_window_hours)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting context for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/feedback")
@rate_limit("60/minute")
async def get_ticket_feedback(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all feedback for a ticket."""
    try:
        ctrl = PatternFeedbackController(db, current_user.tenant_id)
        return await ctrl.get_ticket_feedback(ticket_id)
    except Exception as e:
        logger.error("Error getting ticket feedback: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/explanation", response_model=ExplanationResponse)
@rate_limit("60/minute")
async def get_recommendation_explanation(
    ticket_id: int,
    recommendation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed explanation for a recommendation."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return await ctrl.get_explanation(ticket_id, recommendation_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting explanation for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/tickets/{ticket_id}/explain", response_model=ExplanationResponse)
@rate_limit("30/minute")
async def explain_recommendation(
    ticket_id: int,
    request: ExplanationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate explanation for a recommendation."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return await ctrl.get_explanation(ticket_id, request.recommendation_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error explaining recommendation for ticket %d: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))
