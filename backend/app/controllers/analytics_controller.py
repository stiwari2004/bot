"""
Analytics controller - handles analytics API requests
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.controllers.base_controller import BaseController
from app.services.analytics_service import AnalyticsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsController(BaseController):
    """Controller for analytics endpoints"""
    
    def __init__(self):
        self.analytics_service = AnalyticsService()
    
    async def get_usage_statistics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics for a tenant"""
        try:
            return await self.analytics_service.get_usage_statistics(
                tenant_id=tenant_id,
                db=db,
                days=days
            )
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get usage statistics")
    
    async def get_quality_metrics(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get quality metrics for a tenant"""
        try:
            return await self.analytics_service.get_quality_metrics(
                tenant_id=tenant_id,
                db=db
            )
        except Exception as e:
            logger.error(f"Error getting quality metrics: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get quality metrics")
    
    async def get_coverage_analysis(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get runbook coverage analysis for a tenant"""
        try:
            return await self.analytics_service.get_coverage_analysis(
                tenant_id=tenant_id,
                db=db
            )
        except Exception as e:
            logger.error(f"Error getting coverage analysis: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get coverage analysis")
    
    async def get_search_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get search quality metrics for a tenant"""
        try:
            return await self.analytics_service.get_search_quality_metrics(
                tenant_id=tenant_id,
                db=db,
                days=days
            )
        except Exception as e:
            logger.error(f"Error getting search quality metrics: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get search quality metrics")
    
    async def record_runbook_usage(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        issue_description: str,
        confidence_score: float,
        was_helpful: bool = None,
        feedback_text: str = None,
        execution_time_minutes: int = None
    ) -> Dict[str, Any]:
        """Record runbook usage for analytics"""
        try:
            return await self.analytics_service.record_runbook_usage(
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                db=db,
                issue_description=issue_description,
                confidence_score=confidence_score,
                was_helpful=was_helpful,
                feedback_text=feedback_text,
                execution_time_minutes=execution_time_minutes
            )
        except Exception as e:
            logger.error(f"Error recording runbook usage: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to record runbook usage")
    
    async def get_runbook_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive quality metrics for all runbooks"""
        try:
            return await self.analytics_service.get_runbook_quality_metrics(
                tenant_id=tenant_id,
                db=db,
                days=days
            )
        except Exception as e:
            logger.error(f"Error getting runbook quality metrics: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get runbook quality metrics")
    
    async def get_runbook_metrics(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed metrics for a specific runbook"""
        try:
            return await self.analytics_service.get_runbook_metrics(
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                db=db,
                days=days
            )
        except Exception as e:
            logger.error(f"Error getting runbook metrics: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get runbook metrics")



