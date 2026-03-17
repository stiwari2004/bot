"""
Quality analytics service - tracks runbook quality metrics
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.models.execution_session import ExecutionSession, ExecutionFeedback
from app.core.logging import get_logger
from app.services.analytics.quality_analytics_runbook_mixin import QualityAnalyticsRunbookMixin

logger = get_logger(__name__)


class QualityAnalytics(QualityAnalyticsRunbookMixin):
    """Service for tracking runbook quality metrics"""

    async def get_quality_metrics(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get quality metrics for runbooks (confidence distribution + success rates)."""
        try:
            confidence_ranges = db.query(
                case(
                    (RunbookUsage.confidence_score >= 0.9, 'high_90-100'),
                    (RunbookUsage.confidence_score >= 0.75, 'medium_75-89'),
                    (RunbookUsage.confidence_score >= 0.50, 'low_50-74'),
                    else_='very_low_0-49'
                ).label('range'),
                func.count(RunbookUsage.id).label('count')
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.confidence_score.isnot(None)
            ).group_by('range').all()

            runbook_success = db.query(
                Runbook.id,
                Runbook.title,
                func.count(RunbookUsage.id).label('total_uses'),
                func.avg(case((RunbookUsage.was_helpful == True, 1), else_=0)).label('success_rate')
            ).join(
                RunbookUsage, Runbook.id == RunbookUsage.runbook_id
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.was_helpful.isnot(None)
            ).group_by(
                Runbook.id, Runbook.title
            ).having(
                func.count(RunbookUsage.id) >= 3
            ).order_by(
                func.avg(case((RunbookUsage.was_helpful == True, 1), else_=0)).desc()
            ).all()

            high_quality = [
                {'id': rb.id, 'title': rb.title, 'total_uses': rb.total_uses, 'success_rate': round(float(rb.success_rate) * 100, 2)}
                for rb in runbook_success if rb.success_rate >= 0.70
            ]

            underperforming = [
                {'id': rb.id, 'title': rb.title, 'total_uses': rb.total_uses, 'success_rate': round(float(rb.success_rate) * 100, 2)}
                for rb in runbook_success if rb.success_rate < 0.50
            ]

            avg_execution = db.query(func.avg(RunbookUsage.execution_time_minutes)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.execution_time_minutes.isnot(None)
            ).scalar()

            return {
                'confidence_distribution': {rng.range: rng.count for rng in confidence_ranges},
                'high_quality_runbooks': high_quality[:10],
                'underperforming_runbooks': underperforming[:10],
                'avg_execution_time_minutes': round(float(avg_execution), 2) if avg_execution else 0,
                'total_runbooks_with_stats': len(runbook_success)
            }

        except Exception as e:
            logger.error(f"Error getting quality metrics: {e}")
            return {}
