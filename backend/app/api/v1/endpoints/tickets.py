"""
Ticket analysis endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.schemas.ticket import (
    TicketAnalysisRequest, 
    TicketAnalysisResponse, 
    RunbookMatch,
    RunbookUsageRequest,
    RunbookFeedbackRequest
)
from app.services.runbook_search import RunbookSearchService
from app.services.config_service import ConfigService
from app.models.runbook_usage import RunbookUsage
from app.models.runbook import Runbook
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/analyze", response_model=TicketAnalysisResponse)
async def analyze_ticket(
    request: TicketAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze a ticket/issue and recommend action.
    
    Returns:
    - existing_runbook: If high-confidence match found
    - generate_new: If no good match exists
    - escalate: If issue is too complex/risky
    """
    try:
        # Get confidence threshold from config
        threshold = ConfigService.get_confidence_threshold(db, current_user.tenant_id)
        
        # Search for similar runbooks
        search_service = RunbookSearchService()
        matched_runbooks = await search_service.search_similar_runbooks(
            issue_description=request.issue_description,
            tenant_id=current_user.tenant_id,
            db=db,
            top_k=5,
            min_confidence=0.5  # Lower threshold for showing all candidates
        )
        
        # Apply decision logic
        if not matched_runbooks:
            # No runbooks found
            recommendation = "generate_new"
            confidence = 0.9
            reasoning = "No similar runbooks found in knowledge base. Suggest generating new runbook."
            suggested_actions = [
                "Generate new runbook for this issue",
                "Review existing knowledge base for partial solutions",
                "Consider escalating if issue is critical"
            ]
        else:
            # Check if top match exceeds threshold
            top_match = matched_runbooks[0]
            
            if top_match['confidence_score'] >= threshold:
                # High confidence match
                recommendation = "existing_runbook"
                confidence = top_match['confidence_score']
                reasoning = f"Found {len(matched_runbooks)} similar runbook(s). Top match: {top_match['reasoning']}"
                suggested_actions = [
                    f"Use runbook: {top_match['title']}",
                    f"Confidence: {confidence:.1%}",
                    "Review steps and execute"
                ]
                
                if len(matched_runbooks) > 1:
                    suggested_actions.append(f"Also consider {len(matched_runbooks) - 1} alternative runbook(s)")
            else:
                # Low confidence - suggest generating new
                recommendation = "generate_new"
                confidence = 0.7
                reasoning = f"Found {len(matched_runbooks)} partially similar runbook(s) but confidence ({top_match['confidence_score']:.1%}) below threshold ({threshold:.1%})"
                suggested_actions = [
                    f"Top match only {top_match['confidence_score']:.1%} similar: {top_match['title']}",
                    "Consider generating a more specific runbook",
                    "Review suggested runbooks for ideas"
                ]
        
        return TicketAnalysisResponse(
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            matched_runbooks=[RunbookMatch(**rb) for rb in matched_runbooks],
            suggested_actions=suggested_actions,
            threshold_used=threshold
        )
        
    except Exception as e:
        logger.error(f"Error analyzing ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze ticket: {str(e)}")


@router.post("/demo/analyze", response_model=TicketAnalysisResponse)
async def analyze_ticket_demo(
    request: TicketAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Demo version without authentication"""
    try:
        # Use demo tenant (tenant_id = 1)
        demo_tenant_id = 1
        
        # Get confidence threshold from config
        threshold = ConfigService.get_confidence_threshold(db, demo_tenant_id)
        
        # Search for similar runbooks
        search_service = RunbookSearchService()
        matched_runbooks = await search_service.search_similar_runbooks(
            issue_description=request.issue_description,
            tenant_id=demo_tenant_id,
            db=db,
            top_k=5,
            min_confidence=0.5
        )
        
        # Apply decision logic (same as authenticated version)
        if not matched_runbooks:
            recommendation = "generate_new"
            confidence = 0.9
            reasoning = "No similar runbooks found in knowledge base. Suggest generating new runbook."
            suggested_actions = [
                "Generate new runbook for this issue",
                "Review existing knowledge base for partial solutions",
                "Consider escalating if issue is critical"
            ]
        else:
            top_match = matched_runbooks[0]
            
            if top_match['confidence_score'] >= threshold:
                recommendation = "existing_runbook"
                confidence = top_match['confidence_score']
                reasoning = f"Found {len(matched_runbooks)} similar runbook(s). Top match: {top_match['reasoning']}"
                suggested_actions = [
                    f"Use runbook: {top_match['title']}",
                    f"Confidence: {confidence:.1%}",
                    "Review steps and execute"
                ]
                
                if len(matched_runbooks) > 1:
                    suggested_actions.append(f"Also consider {len(matched_runbooks) - 1} alternative runbook(s)")
            else:
                recommendation = "generate_new"
                confidence = 0.7
                reasoning = f"Found {len(matched_runbooks)} partially similar runbook(s) but confidence ({top_match['confidence_score']:.1%}) below threshold ({threshold:.1%})"
                suggested_actions = [
                    f"Top match only {top_match['confidence_score']:.1%} similar: {top_match['title']}",
                    "Consider generating a more specific runbook",
                    "Review suggested runbooks for ideas"
                ]
        
        return TicketAnalysisResponse(
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            matched_runbooks=[RunbookMatch(**rb) for rb in matched_runbooks],
            suggested_actions=suggested_actions,
            threshold_used=threshold
        )
        
    except Exception as e:
        logger.error(f"Error analyzing ticket (demo): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze ticket: {str(e)}")


@router.post("/{runbook_id}/usage")
async def record_runbook_usage(
    runbook_id: int,
    usage: RunbookUsageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record that a runbook was used"""
    try:
        # Verify runbook exists and belongs to tenant
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        # Create usage record
        usage_record = RunbookUsage(
            runbook_id=runbook_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            issue_description=usage.issue_description,
            confidence_score=usage.confidence_score
        )
        
        db.add(usage_record)
        db.commit()
        
        return {"message": "Usage recorded successfully", "usage_id": usage_record.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording runbook usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record usage: {str(e)}")


@router.post("/{runbook_id}/feedback")
async def submit_runbook_feedback(
    runbook_id: int,
    feedback: RunbookFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on runbook effectiveness"""
    try:
        # Verify runbook exists
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        # Find most recent usage by this user for this runbook
        usage_record = db.query(RunbookUsage).filter(
            RunbookUsage.runbook_id == runbook_id,
            RunbookUsage.user_id == current_user.id,
            RunbookUsage.was_helpful.is_(None)  # Only update records without feedback yet
        ).order_by(RunbookUsage.created_at.desc()).first()
        
        if not usage_record:
            # Create new usage record with feedback
            usage_record = RunbookUsage(
                runbook_id=runbook_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                was_helpful=feedback.was_helpful,
                feedback_text=feedback.feedback_text,
                execution_time_minutes=feedback.execution_time_minutes
            )
            db.add(usage_record)
        else:
            # Update existing usage record
            usage_record.was_helpful = feedback.was_helpful
            usage_record.feedback_text = feedback.feedback_text
            usage_record.execution_time_minutes = feedback.execution_time_minutes
        
        db.commit()
        
        return {"message": "Feedback submitted successfully", "usage_id": usage_record.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

