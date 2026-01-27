"""
Decision-making API endpoints
Provides recommendations, pattern matching, and decision logic
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.services.auth import get_current_user
from app.core.rate_limiting import rate_limit
from app.services.decision import (
    RecommendationEngine,
    PatternMatchingService,
    ContextCorrelationService,
    PatternStorageService,
    ConditionalLogicService
)
from app.core.logging import get_logger
from app.controllers.pattern_feedback_controller import PatternFeedbackController
from app.controllers.pattern_quality_controller import PatternQualityController
from app.controllers.confidence_controller import ConfidenceController

router = APIRouter()
logger = get_logger(__name__)


class RecommendationResponse(BaseModel):
    """Recommendation response model"""
    runbook_id: Optional[int] = None
    runbook_title: Optional[str] = None
    confidence: float
    pattern_id: Optional[int] = None
    pattern_success_rate: Optional[float] = None
    reasoning: str
    should_auto_execute: bool
    should_escalate: bool
    context_signals: Dict[str, Any]


class PatternMatchResponse(BaseModel):
    """Pattern match response model"""
    pattern_id: int
    pattern_type: str
    runbook_id: Optional[int] = None
    issue_signature: Optional[str] = None
    match_score: float
    success_rate: Optional[float] = None
    usage_count: int


class ContextCorrelationResponse(BaseModel):
    """Context correlation response model"""
    ticket_id: int
    alert_count: int
    execution_count: int
    signals: Dict[str, Any]
    correlated_at: str


@router.get("/demo/tickets/{ticket_id}/recommendation", response_model=RecommendationResponse)
@rate_limit("60/minute")
async def get_recommendation(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get runbook recommendation for a ticket
    
    Returns recommendation with confidence score and suggested actions
    """
    try:
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == current_user.tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get recommendation
        recommendation_engine = RecommendationEngine()
        recommendation = recommendation_engine.recommend_runbook(ticket, db)
        
        return RecommendationResponse(**recommendation.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting recommendation for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/patterns", response_model=List[PatternMatchResponse])
@rate_limit("60/minute")
async def get_matching_patterns(
    ticket_id: int,
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get patterns matching a ticket
    
    Returns list of matching patterns with scores
    """
    try:
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == current_user.tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Build context
        context = {
            "tenant_id": ticket.tenant_id,
            "environment": ticket.environment,
            "service": ticket.service,
            "severity": ticket.severity,
        }
        
        # Find matching patterns
        pattern_matching_service = PatternMatchingService()
        issue_description = ticket.description or ticket.title
        matching_patterns = pattern_matching_service.find_matching_patterns(
            issue_description,
            context,
            db,
            pattern_type=pattern_type,
            limit=limit
        )
        
        # Convert to response
        results = []
        for pattern, score in matching_patterns:
            results.append(PatternMatchResponse(
                pattern_id=pattern.id,
                pattern_type=pattern.pattern_type,
                runbook_id=pattern.runbook_id,
                issue_signature=pattern.issue_signature,
                match_score=score,
                success_rate=pattern.success_rate,
                usage_count=pattern.usage_count
            ))
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting patterns for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/context", response_model=ContextCorrelationResponse)
@rate_limit("60/minute")
async def get_ticket_context(
    ticket_id: int,
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get correlated context for a ticket
    
    Returns correlated alerts, executions, and context signals
    """
    try:
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == current_user.tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Correlate context
        context_service = ContextCorrelationService()
        context_data = context_service.correlate_ticket_context(
            ticket_id, db, time_window_hours
        )
        
        return ContextCorrelationResponse(
            ticket_id=ticket_id,
            alert_count=len(context_data["alerts"]),
            execution_count=len(context_data["executions"]),
            signals=context_data["signals"],
            correlated_at=context_data["correlated_at"].isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error getting context for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/patterns", response_model=List[PatternMatchResponse])
@rate_limit("60/minute")
async def list_patterns(
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    runbook_id: Optional[int] = Query(None, description="Filter by runbook ID"),
    min_success_rate: Optional[float] = Query(None, ge=0, le=100, description="Minimum success rate"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List execution patterns
    
    Returns list of patterns with optional filters
    """
    try:
        from app.models.execution_pattern import ExecutionPattern
        from sqlalchemy import and_
        
        # Build query
        query = db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == current_user.tenant_id
        )
        
        if pattern_type:
            query = query.filter(ExecutionPattern.pattern_type == pattern_type)
        
        if runbook_id:
            query = query.filter(ExecutionPattern.runbook_id == runbook_id)
        
        if min_success_rate is not None:
            query = query.filter(ExecutionPattern.success_rate >= min_success_rate)
        
        # Order by success rate and usage count
        patterns = query.order_by(
            ExecutionPattern.success_rate.desc(),
            ExecutionPattern.usage_count.desc()
        ).limit(limit).all()
        
        # Convert to response
        results = []
        for pattern in patterns:
            results.append(PatternMatchResponse(
                pattern_id=pattern.id,
                pattern_type=pattern.pattern_type,
                runbook_id=pattern.runbook_id,
                issue_signature=pattern.issue_signature,
                match_score=0.0,  # Not calculated in list view
                success_rate=pattern.success_rate,
                usage_count=pattern.usage_count
            ))
        
        return results
    
    except Exception as e:
        logger.error(f"Error listing patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns")
@rate_limit("30/minute")
async def create_pattern(
    pattern_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new execution pattern
    
    Used internally by the system to store patterns after execution
    """
    try:
        pattern_storage_service = PatternStorageService()
        
        # Extract required fields
        pattern_type = pattern_data.get("pattern_type", "execution")
        runbook_id = pattern_data.get("runbook_id")
        ticket_id = pattern_data.get("ticket_id")
        session_id = pattern_data.get("session_id")
        issue_signature = pattern_data.get("issue_signature")
        context = pattern_data.get("context", {})
        pattern_data_json = pattern_data.get("pattern_data", {})
        
        # Store pattern
        pattern = await pattern_storage_service.store_pattern(
            tenant_id=current_user.tenant_id,
            pattern_type=pattern_type,
            runbook_id=runbook_id,
            ticket_id=ticket_id,
            session_id=session_id,
            issue_signature=issue_signature,
            context=context,
            pattern_data=pattern_data_json,
            db=db
        )
        
        return {
            "pattern_id": pattern.id,
            "message": "Pattern created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PatternFeedbackRequest(BaseModel):
    """Request model for pattern feedback"""
    pattern_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    ticket_id: Optional[int] = None
    feedback_type: str  # 'thumbs_up', 'thumbs_down', 'not_relevant', 'outdated', 'wrong_runbook'
    reason: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class PatternFeedbackResponse(BaseModel):
    """Response model for pattern feedback"""
    feedback_id: int
    message: str
    pattern_id: Optional[int] = None


@router.post("/demo/patterns/{pattern_id}/feedback", response_model=PatternFeedbackResponse)
@rate_limit("60/minute")
async def submit_pattern_feedback(
    pattern_id: int,
    feedback: PatternFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback on a pattern
    
    Allows users to provide thumbs up/down or other feedback on execution patterns
    """
    try:
        controller = PatternFeedbackController(db, current_user.tenant_id)
        result = await controller.submit_feedback(
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
        logger.error(f"Error submitting pattern feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/recommendations/feedback", response_model=PatternFeedbackResponse)
@rate_limit("60/minute")
async def submit_recommendation_feedback(
    feedback: PatternFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback on a recommendation (without pattern_id)
    
    Used when user provides feedback on a recommendation that may not have a pattern yet
    """
    try:
        controller = PatternFeedbackController(db, current_user.tenant_id)
        result = await controller.submit_feedback(
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
        logger.error(f"Error submitting recommendation feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/patterns/{pattern_id}/feedback/summary")
@rate_limit("60/minute")
async def get_pattern_feedback_summary(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get feedback summary for a pattern
    
    Returns counts and breakdown of feedback types
    """
    try:
        controller = PatternFeedbackController(db, current_user.tenant_id)
        summary = await controller.get_feedback_summary(pattern_id)
        return summary
    
    except Exception as e:
        logger.error(f"Error getting feedback summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/tickets/{ticket_id}/feedback")
@rate_limit("60/minute")
async def get_ticket_feedback(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all feedback for a ticket
    
    Returns list of feedback items associated with the ticket
    """
    try:
        controller = PatternFeedbackController(db, current_user.tenant_id)
        feedback_data = await controller.get_ticket_feedback(ticket_id)
        return feedback_data
    
    except Exception as e:
        logger.error(f"Error getting ticket feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/deprecate")
@rate_limit("30/minute")
async def deprecate_pattern(
    pattern_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deprecate a pattern
    
    Marks a pattern as deprecated, preventing it from being used in recommendations
    """
    try:
        controller = PatternQualityController(db, current_user.tenant_id)
        result = await controller.deprecate_pattern(pattern_id, reason)
        return result
    
    except Exception as e:
        logger.error(f"Error deprecating pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/restore")
@rate_limit("30/minute")
async def restore_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Restore a deprecated pattern
    
    Re-enables a deprecated pattern for use in recommendations
    """
    try:
        controller = PatternQualityController(db, current_user.tenant_id)
        result = await controller.restore_pattern(pattern_id)
        return result
    
    except Exception as e:
        logger.error(f"Error restoring pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/patterns/quality-report")
@rate_limit("60/minute")
async def get_pattern_quality_report(
    min_quality_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum quality score"),
    include_deprecated: bool = Query(False, description="Include deprecated patterns"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quality report for all patterns
    
    Returns breakdown of pattern quality, including high/low quality patterns
    and deprecated patterns
    """
    try:
        controller = PatternQualityController(db, current_user.tenant_id)
        report = await controller.get_quality_report(
            min_quality_score=min_quality_score,
            include_deprecated=include_deprecated
        )
        return report
    
    except Exception as e:
        logger.error(f"Error getting quality report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/{pattern_id}/update-quality-score")
@rate_limit("30/minute")
async def update_pattern_quality_score(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quality score for a pattern
    
    Recalculates and updates the quality score based on current metrics
    """
    try:
        controller = PatternQualityController(db, current_user.tenant_id)
        result = await controller.update_quality_score(pattern_id)
        return result
    
    except Exception as e:
        logger.error(f"Error updating quality score for pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/patterns/prune")
@rate_limit("10/hour")
async def prune_low_quality_patterns(
    max_quality_score: float = Query(20.0, ge=0, le=100, description="Maximum quality score to prune"),
    min_age_days: int = Query(90, ge=1, le=365, description="Minimum age in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatically deprecate old, low-quality patterns
    
    This endpoint prunes patterns that are old and have low quality scores
    """
    try:
        controller = PatternQualityController(db, current_user.tenant_id)
        result = await controller.prune_low_quality_patterns(
            max_quality_score=max_quality_score,
            min_age_days=min_age_days
        )
        return result
    
    except Exception as e:
        logger.error(f"Error pruning patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/runbooks/{runbook_id}/confidence")
@rate_limit("60/minute")
async def get_runbook_confidence(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get confidence breakdown for a runbook
    
    Returns detailed breakdown of confidence score components
    """
    try:
        controller = ConfidenceController(db, current_user.tenant_id)
        breakdown = await controller.get_confidence_breakdown(runbook_id=runbook_id)
        return breakdown
    
    except Exception as e:
        logger.error(f"Error getting runbook confidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/recommendations/{recommendation_id}/confidence")
@rate_limit("60/minute")
async def get_recommendation_confidence(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get confidence breakdown for a recommendation
    
    Returns detailed breakdown of confidence score components
    """
    try:
        controller = ConfidenceController(db, current_user.tenant_id)
        breakdown = await controller.get_confidence_breakdown(recommendation_id=recommendation_id)
        return breakdown
    
    except Exception as e:
        logger.error(f"Error getting recommendation confidence: {e}")
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
    current_user: User = Depends(get_current_user)
):
    """
    Calculate and store confidence breakdown for a runbook
    
    This endpoint calculates the multi-factor confidence score
    """
    try:
        controller = ConfidenceController(db, current_user.tenant_id)
        breakdown = await controller.calculate_confidence_breakdown(
            runbook_id=runbook_id,
            search_results=search_results,
            runbook_yaml=runbook_yaml,
            llm_output=llm_output,
            context_text=context_text,
        )
        return breakdown
    
    except Exception as e:
        logger.error(f"Error calculating runbook confidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExplanationRequest(BaseModel):
    """Request model for explanation generation"""
    recommendation_id: Optional[int] = None


class ExplanationResponse(BaseModel):
    """Response model for explanation"""
    ticket_id: int
    recommendation_id: Optional[int] = None
    has_breakdown: bool
    confidence_breakdown: Optional[Dict[str, Any]] = None
    detailed_explanation: Optional[Dict[str, Any]] = None


@router.get("/demo/tickets/{ticket_id}/explanation", response_model=ExplanationResponse)
@rate_limit("60/minute")
async def get_recommendation_explanation(
    ticket_id: int,
    recommendation_id: Optional[int] = Query(None, description="Optional recommendation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed explanation for a recommendation
    
    Returns comprehensive explanation including confidence breakdown,
    reasoning steps, citations, and pattern match details
    """
    try:
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == current_user.tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Generate explanation
        recommendation_engine = RecommendationEngine()
        explanation = await recommendation_engine.generate_explanation(
            ticket_id=ticket_id,
            recommendation_id=recommendation_id,
            db=db
        )
        
        return ExplanationResponse(**explanation)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting explanation for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/tickets/{ticket_id}/explain", response_model=ExplanationResponse)
@rate_limit("30/minute")
async def explain_recommendation(
    ticket_id: int,
    request: ExplanationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate explanation for a recommendation
    
    Creates a detailed explanation including confidence breakdown
    """
    try:
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == current_user.tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Generate explanation
        recommendation_engine = RecommendationEngine()
        explanation = await recommendation_engine.generate_explanation(
            ticket_id=ticket_id,
            recommendation_id=request.recommendation_id,
            db=db
        )
        
        return ExplanationResponse(**explanation)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining recommendation for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
