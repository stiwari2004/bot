"""
Usage analytics service - tracks runbook usage statistics
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.core.logging import get_logger

logger = get_logger(__name__)


class UsageAnalytics:
    """Service for tracking runbook usage statistics"""
    
    async def get_usage_statistics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics.
        
        Returns:
        - Total runbooks used
        - Most popular runbooks
        - Average confidence scores
        - Success rates
        - User activity
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Total usage count
            total_uses = db.query(func.count(RunbookUsage.id)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).scalar()
            
            # Most popular runbooks (top 10)
            popular_runbooks = db.query(
                Runbook.id,
                Runbook.title,
                func.count(RunbookUsage.id).label('usage_count'),
                func.avg(RunbookUsage.confidence_score).label('avg_confidence')
            ).join(
                RunbookUsage, Runbook.id == RunbookUsage.runbook_id
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).group_by(
                Runbook.id, Runbook.title
            ).order_by(
                func.count(RunbookUsage.id).desc()
            ).limit(10).all()
            
            # Average confidence
            avg_confidence = db.query(func.avg(RunbookUsage.confidence_score)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).scalar()
            
            # Success rate
            success_stats = db.query(
                func.count(RunbookUsage.id).label('total'),
                func.sum(case((RunbookUsage.was_helpful == True, 1), else_=0)).label('successful')
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date,
                RunbookUsage.was_helpful.isnot(None)
            ).first()
            
            success_rate = 0.0
            if success_stats and success_stats.total > 0:
                success_rate = (success_stats.successful / success_stats.total) * 100
            
            return {
                'period_days': days,
                'total_uses': total_uses or 0,
                'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
                'success_rate': round(success_rate, 2),
                'popular_runbooks': [
                    {
                        'id': rb.id,
                        'title': rb.title,
                        'usage_count': rb.usage_count,
                        'avg_confidence': float(rb.avg_confidence) if rb.avg_confidence else 0.0
                    }
                    for rb in popular_runbooks
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}")
            return {}
    
    async def record_runbook_usage(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        issue_description: str,
        confidence_score: float,
        was_helpful: Optional[bool] = None,
        feedback_text: Optional[str] = None,
        execution_time_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record when a runbook is used.
        
        This should be called when a user executes or reviews a runbook.
        """
        try:
            usage = RunbookUsage(
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                issue_description=issue_description[:500],  # Truncate if too long
                confidence_score=confidence_score,
                was_helpful=was_helpful,
                feedback_text=feedback_text,
                execution_time_minutes=execution_time_minutes
            )
            
            db.add(usage)
            db.commit()
            db.refresh(usage)
            
            logger.info(f"Recorded usage for runbook {runbook_id}")
            
            return {
                'usage_id': usage.id,
                'message': 'Usage recorded successfully'
            }
            
        except Exception as e:
            logger.error(f"Error recording runbook usage: {e}")
            db.rollback()
            return {}

