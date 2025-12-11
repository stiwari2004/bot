"""
DecisionAnalyticsService
Calculates and tracks decision engine performance and accuracy
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.models.decision_analytics import DecisionAnalytics
from app.models.pattern_feedback import PatternFeedback
from app.models.execution_pattern import ExecutionPattern
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession
from app.repositories.decision_analytics_repository import DecisionAnalyticsRepository

logger = get_logger(__name__)


class DecisionAnalyticsService:
    """Service for calculating decision engine analytics"""
    
    def __init__(self):
        pass
    
    async def calculate_analytics(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime,
        period_type: str = 'daily'
    ) -> DecisionAnalytics:
        """
        Calculate analytics for a time period
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            period_type: 'daily', 'weekly', 'monthly'
            
        Returns:
            DecisionAnalytics object
        """
        # Get or create analytics record
        repo = DecisionAnalyticsRepository(db)
        analytics = repo.get_by_period(tenant_id, period_type, period_start, period_end)
        
        # Calculate recommendation metrics
        # (This is simplified - in production would track actual recommendation acceptance)
        tickets_with_recommendations = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.created_at >= period_start,
            Ticket.created_at < period_end,
            Ticket.meta_data.isnot(None)
        ).all()
        
        total_recommendations = len(tickets_with_recommendations)
        accepted_recommendations = sum(
            1 for t in tickets_with_recommendations
            if t.meta_data and 'recommendation' in str(t.meta_data).lower()
        )
        rejected_recommendations = total_recommendations - accepted_recommendations
        
        acceptance_rate = (
            (accepted_recommendations / total_recommendations * 100.0)
            if total_recommendations > 0 else 0.0
        )
        
        # Calculate pattern matching metrics
        patterns_used = db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == tenant_id,
            ExecutionPattern.created_at >= period_start,
            ExecutionPattern.created_at < period_end
        ).all()
        
        total_pattern_searches = len(patterns_used)
        successful_pattern_matches = sum(
            1 for p in patterns_used if p.usage_count > 0
        )
        pattern_match_accuracy = (
            (successful_pattern_matches / total_pattern_searches * 100.0)
            if total_pattern_searches > 0 else 0.0
        )
        
        avg_pattern_match_confidence = None
        if patterns_used:
            confidences = [float(p.success_rate) for p in patterns_used if p.success_rate]
            if confidences:
                avg_pattern_match_confidence = sum(confidences) / len(confidences)
        
        # Calculate confidence score distribution
        # (Simplified - would track actual confidence scores from recommendations)
        high_confidence_count = sum(
            1 for p in patterns_used
            if p.success_rate and float(p.success_rate) >= 80.0
        )
        medium_confidence_count = sum(
            1 for p in patterns_used
            if p.success_rate and 50.0 <= float(p.success_rate) < 80.0
        )
        low_confidence_count = sum(
            1 for p in patterns_used
            if p.success_rate and float(p.success_rate) < 50.0
        )
        
        avg_confidence_score = avg_pattern_match_confidence
        
        # Calculate decision outcomes
        executions = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.started_at >= period_start,
            ExecutionSession.started_at < period_end
        ).all()
        
        auto_execute_count = sum(
            1 for e in executions
            if e.meta_data and 'auto' in str(e.meta_data).lower()
        )
        manual_execute_count = len(executions) - auto_execute_count
        
        # Escalation count (from tickets)
        escalation_count = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.status == 'escalated',
            Ticket.created_at >= period_start,
            Ticket.created_at < period_end
        ).count()
        
        # Resolution success rate
        successful_sessions = sum(
            1 for e in executions
            if e.status == 'completed'
        )
        failed_sessions = len(executions) - successful_sessions
        resolution_success_rate = (
            (successful_sessions / len(executions) * 100.0)
            if executions else 0.0
        )
        
        # Update or create analytics record
        if analytics:
            analytics.total_recommendations = total_recommendations
            analytics.accepted_recommendations = accepted_recommendations
            analytics.rejected_recommendations = rejected_recommendations
            analytics.recommendation_acceptance_rate = acceptance_rate
            analytics.total_pattern_searches = total_pattern_searches
            analytics.successful_pattern_matches = successful_pattern_matches
            analytics.pattern_match_accuracy = pattern_match_accuracy
            analytics.avg_pattern_match_confidence = avg_pattern_match_confidence
            analytics.high_confidence_count = high_confidence_count
            analytics.medium_confidence_count = medium_confidence_count
            analytics.low_confidence_count = low_confidence_count
            analytics.avg_confidence_score = avg_confidence_score
            analytics.auto_execute_count = auto_execute_count
            analytics.manual_execute_count = manual_execute_count
            analytics.escalation_count = escalation_count
            analytics.successful_resolutions = successful_sessions
            analytics.failed_resolutions = failed_sessions
            analytics.resolution_success_rate = resolution_success_rate
            db.add(analytics)
            db.commit()
            db.refresh(analytics)
        else:
            analytics = DecisionAnalytics(
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                total_recommendations=total_recommendations,
                accepted_recommendations=accepted_recommendations,
                rejected_recommendations=rejected_recommendations,
                recommendation_acceptance_rate=acceptance_rate,
                total_pattern_searches=total_pattern_searches,
                successful_pattern_matches=successful_pattern_matches,
                pattern_match_accuracy=pattern_match_accuracy,
                avg_pattern_match_confidence=avg_pattern_match_confidence,
                high_confidence_count=high_confidence_count,
                medium_confidence_count=medium_confidence_count,
                low_confidence_count=low_confidence_count,
                avg_confidence_score=avg_confidence_score,
                auto_execute_count=auto_execute_count,
                manual_execute_count=manual_execute_count,
                escalation_count=escalation_count,
                successful_resolutions=successful_sessions,
                failed_resolutions=failed_sessions,
                resolution_success_rate=resolution_success_rate,
            )
            db.add(analytics)
            db.commit()
            db.refresh(analytics)
        
        logger.info(
            f"Calculated decision analytics for period {period_start} to {period_end}: "
            f"acceptance_rate={acceptance_rate:.2f}%, "
            f"pattern_accuracy={pattern_match_accuracy:.2f}%"
        )
        
        return analytics
    
    async def get_analytics_summary(
        self,
        db: Session,
        tenant_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics summary for recent period
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            Analytics summary dictionary
        """
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=days)
        
        # Calculate analytics for the period
        analytics = await self.calculate_analytics(
            db, tenant_id, period_start, period_end, 'daily'
        )
        
        return {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": days,
            },
            "recommendations": {
                "total": analytics.total_recommendations,
                "accepted": analytics.accepted_recommendations,
                "rejected": analytics.rejected_recommendations,
                "acceptance_rate": float(analytics.recommendation_acceptance_rate),
            },
            "pattern_matching": {
                "total_searches": analytics.total_pattern_searches,
                "successful_matches": analytics.successful_pattern_matches,
                "accuracy": float(analytics.pattern_match_accuracy),
                "avg_confidence": float(analytics.avg_pattern_match_confidence) if analytics.avg_pattern_match_confidence else None,
            },
            "confidence_distribution": {
                "high": analytics.high_confidence_count,
                "medium": analytics.medium_confidence_count,
                "low": analytics.low_confidence_count,
                "avg_confidence": float(analytics.avg_confidence_score) if analytics.avg_confidence_score else None,
            },
            "decision_outcomes": {
                "auto_execute": analytics.auto_execute_count,
                "manual_execute": analytics.manual_execute_count,
                "escalations": analytics.escalation_count,
            },
            "resolution_performance": {
                "successful": analytics.successful_resolutions,
                "failed": analytics.failed_resolutions,
                "success_rate": float(analytics.resolution_success_rate),
            },
        }
    
    async def get_trends(
        self,
        db: Session,
        tenant_id: int,
        period_type: str = 'daily',
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get analytics trends over time
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_type: 'daily', 'weekly', 'monthly'
            limit: Number of periods to return
            
        Returns:
            List of analytics records
        """
        repo = DecisionAnalyticsRepository(db)
        analytics_list = repo.get_recent_analytics(tenant_id, period_type, limit)
        
        return [
            {
                "period_start": a.period_start.isoformat(),
                "period_end": a.period_end.isoformat(),
                "acceptance_rate": float(a.recommendation_acceptance_rate),
                "pattern_accuracy": float(a.pattern_match_accuracy),
                "avg_confidence": float(a.avg_confidence_score) if a.avg_confidence_score else None,
                "resolution_success_rate": float(a.resolution_success_rate),
            }
            for a in analytics_list
        ]








