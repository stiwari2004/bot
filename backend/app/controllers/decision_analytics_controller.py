"""
DecisionAnalyticsController
Handles HTTP requests for decision analytics operations
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.decision.decision_analytics_service import DecisionAnalyticsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class DecisionAnalyticsController(BaseController):
    """Controller for decision analytics operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.analytics_service = DecisionAnalyticsService()
    
    async def get_analytics_summary(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics summary for recent period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics summary
        """
        try:
            summary = await self.analytics_service.get_analytics_summary(
                db=self.db,
                tenant_id=self.tenant_id,
                days=days
            )
            return summary
        
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            raise self.handle_error(e, "Failed to get analytics summary")
    
    async def get_trends(
        self,
        period_type: str = 'daily',
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get analytics trends over time
        
        Args:
            period_type: 'daily', 'weekly', 'monthly'
            limit: Number of periods to return
            
        Returns:
            List of trend data
        """
        try:
            trends = await self.analytics_service.get_trends(
                db=self.db,
                tenant_id=self.tenant_id,
                period_type=period_type,
                limit=limit
            )
            return trends
        
        except Exception as e:
            logger.error(f"Error getting analytics trends: {e}")
            raise self.handle_error(e, "Failed to get analytics trends")

