"""
RemediationAnalyticsController
Handles HTTP requests for remediation analytics operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.analytics.remediation_analytics_service import RemediationAnalyticsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RemediationAnalyticsController(BaseController):
    """Controller for remediation analytics operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.analytics_service = RemediationAnalyticsService()
    
    def get_effectiveness(
        self,
        period_start: Optional[datetime],
        period_end: Optional[datetime],
        period_type: str = "monthly"
    ) -> Dict[str, Any]:
        """Get remediation effectiveness metrics"""
        try:
            if not period_start or not period_end:
                # Default to last 30 days
                period_end = datetime.now(timezone.utc)
                period_start = period_end - timedelta(days=30)
            
            mttr = self.analytics_service.calculate_mttr(
                db=self.db,
                tenant_id=self.tenant_id,
                period_start=period_start,
                period_end=period_end
            )
            
            coverage = self.analytics_service.calculate_automation_coverage(
                db=self.db,
                tenant_id=self.tenant_id,
                period_start=period_start,
                period_end=period_end
            )
            
            roi = self.analytics_service.calculate_roi(
                db=self.db,
                tenant_id=self.tenant_id,
                period_start=period_start,
                period_end=period_end
            )
            
            return {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "mttr_minutes": float(mttr) if mttr else None,
                "automation_coverage": coverage,
                "roi": roi
            }
        
        except Exception as e:
            logger.error(f"Error getting effectiveness metrics: {e}")
            raise self.handle_error(e, "Failed to get effectiveness metrics")
    
    def get_trends(self, period_type: str = "monthly", periods: int = 12) -> Dict[str, Any]:
        """Get improvement trends"""
        try:
            trends = self.analytics_service.get_improvement_trends(
                db=self.db,
                tenant_id=self.tenant_id,
                period_type=period_type,
                periods=periods
            )
            return trends
        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            raise self.handle_error(e, "Failed to get trends")
    
    def get_failing_steps(
        self,
        period_start: Optional[datetime],
        period_end: Optional[datetime],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top failing steps"""
        try:
            if not period_start or not period_end:
                period_end = datetime.now(timezone.utc)
                period_start = period_end - timedelta(days=30)
            
            failing_steps = self.analytics_service.identify_top_failing_steps(
                db=self.db,
                tenant_id=self.tenant_id,
                period_start=period_start,
                period_end=period_end,
                limit=limit
            )
            
            return failing_steps
        except Exception as e:
            logger.error(f"Error getting failing steps: {e}")
            raise self.handle_error(e, "Failed to get failing steps")
