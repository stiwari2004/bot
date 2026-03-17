"""
Decision — pattern management, quality, and confidence endpoints
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from app.controllers.decision_controller import get_decision_controller
from app.controllers.pattern_feedback_controller import PatternFeedbackController
from app.controllers.pattern_quality_controller import PatternQualityController
from app.controllers.confidence_controller import ConfidenceController
from app.models.user import User
from app.services.auth import get_current_user
from app.api.v1.endpoints.decision_schemas import (
    PatternMatchResponse, PatternFeedbackRequest, PatternFeedbackResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/demo/patterns", response_model=List[PatternMatchResponse])
@rate_limit("60/minute")
async def list_patterns(
    pattern_type: Optional[str] = Query(None),
    runbook_id: Optional[int] = Query(None),
    min_success_rate: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List execution patterns."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return ctrl.list_patterns(pattern_type, runbook_id, min_success_rate, limit)
    except Exception as e:
        logger.error("Error listing patterns: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns")
@rate_limit("30/minute")
async def create_pattern(
    pattern_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new execution pattern."""
    try:
        ctrl = get_decision_controller(db, current_user.tenant_id)
        return await ctrl.create_pattern(pattern_data)
    except Exception as e:
        logger.error("Error creating pattern: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/feedback", response_model=PatternFeedbackResponse)
@rate_limit("60/minute")
async def submit_pattern_feedback(
    pattern_id: int,
    feedback: PatternFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback on a pattern."""
    try:
        ctrl = PatternFeedbackController(db, current_user.tenant_id)
        result = await ctrl.submit_feedback(
            pattern_id=pattern_id,
            recommendation_id=feedback.recommendation_id,
            ticket_id=feedback.ticket_id,
            user_id=current_user.id,
            feedback_type=feedback.feedback_type,
            reason=feedback.reason,
            meta_data=feedback.meta_data,
        )
        return PatternFeedbackResponse(**result)
    except Exception as e:
        logger.error("Error submitting pattern feedback: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/recommendations/feedback", response_model=PatternFeedbackResponse)
@rate_limit("60/minute")
async def submit_recommendation_feedback(
    feedback: PatternFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback on a recommendation."""
    try:
        ctrl = PatternFeedbackController(db, current_user.tenant_id)
        result = await ctrl.submit_feedback(
            pattern_id=feedback.pattern_id,
            recommendation_id=feedback.recommendation_id,
            ticket_id=feedback.ticket_id,
            user_id=current_user.id,
            feedback_type=feedback.feedback_type,
            reason=feedback.reason,
            meta_data=feedback.meta_data,
        )
        return PatternFeedbackResponse(**result)
    except Exception as e:
        logger.error("Error submitting recommendation feedback: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/patterns/{pattern_id}/feedback/summary")
@rate_limit("60/minute")
async def get_pattern_feedback_summary(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback summary for a pattern."""
    try:
        ctrl = PatternFeedbackController(db, current_user.tenant_id)
        return await ctrl.get_feedback_summary(pattern_id)
    except Exception as e:
        logger.error("Error getting feedback summary: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/deprecate")
@rate_limit("30/minute")
async def deprecate_pattern(
    pattern_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deprecate a pattern."""
    try:
        ctrl = PatternQualityController(db, current_user.tenant_id)
        return await ctrl.deprecate_pattern(pattern_id, reason)
    except Exception as e:
        logger.error("Error deprecating pattern %d: %s", pattern_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/restore")
@rate_limit("30/minute")
async def restore_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a deprecated pattern."""
    try:
        ctrl = PatternQualityController(db, current_user.tenant_id)
        return await ctrl.restore_pattern(pattern_id)
    except Exception as e:
        logger.error("Error restoring pattern %d: %s", pattern_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/patterns/quality-report")
@rate_limit("60/minute")
async def get_pattern_quality_report(
    min_quality_score: Optional[float] = Query(None, ge=0, le=100),
    include_deprecated: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quality report for all patterns."""
    try:
        ctrl = PatternQualityController(db, current_user.tenant_id)
        return await ctrl.get_quality_report(
            min_quality_score=min_quality_score,
            include_deprecated=include_deprecated,
        )
    except Exception as e:
        logger.error("Error getting quality report: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/update-quality-score")
@rate_limit("30/minute")
async def update_pattern_quality_score(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update quality score for a pattern."""
    try:
        ctrl = PatternQualityController(db, current_user.tenant_id)
        return await ctrl.update_quality_score(pattern_id)
    except Exception as e:
        logger.error("Error updating quality score for pattern %d: %s", pattern_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/prune")
@rate_limit("10/hour")
async def prune_low_quality_patterns(
    max_quality_score: float = Query(20.0, ge=0, le=100),
    min_age_days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Automatically deprecate old, low-quality patterns."""
    try:
        ctrl = PatternQualityController(db, current_user.tenant_id)
        return await ctrl.prune_low_quality_patterns(
            max_quality_score=max_quality_score,
            min_age_days=min_age_days,
        )
    except Exception as e:
        logger.error("Error pruning patterns: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Confidence routes ─────────────────────────────────────────────────────────

@router.get("/demo/runbooks/{runbook_id}/confidence")
@rate_limit("60/minute")
async def get_runbook_confidence(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get confidence breakdown for a runbook."""
    try:
        ctrl = ConfidenceController(db, current_user.tenant_id)
        return await ctrl.get_confidence_breakdown(runbook_id=runbook_id)
    except Exception as e:
        logger.error("Error getting runbook confidence: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/recommendations/{recommendation_id}/confidence")
@rate_limit("60/minute")
async def get_recommendation_confidence(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get confidence breakdown for a recommendation."""
    try:
        ctrl = ConfidenceController(db, current_user.tenant_id)
        return await ctrl.get_confidence_breakdown(recommendation_id=recommendation_id)
    except Exception as e:
        logger.error("Error getting recommendation confidence: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/runbooks/{runbook_id}/calculate-confidence")
@rate_limit("30/minute")
async def calculate_runbook_confidence(
    runbook_id: int,
    search_results: Optional[List[Dict[str, Any]]] = None,
    runbook_yaml: Optional[str] = None,
    llm_output: Optional[str] = None,
    context_text: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate and store confidence breakdown for a runbook."""
    try:
        ctrl = ConfidenceController(db, current_user.tenant_id)
        return await ctrl.calculate_confidence_breakdown(
            runbook_id=runbook_id,
            search_results=search_results,
            runbook_yaml=runbook_yaml,
            llm_output=llm_output,
            context_text=context_text,
        )
    except Exception as e:
        logger.error("Error calculating runbook confidence: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
