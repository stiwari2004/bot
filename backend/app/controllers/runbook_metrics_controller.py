"""
RunbookMetricsController
Handles HTTP requests for runbook metrics operations
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.analytics.runbook_quality_metrics_service import RunbookQualityMetricsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookMetricsController(BaseController):
    """Controller for runbook metrics operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.metrics_service = RunbookQualityMetricsService()
    
    async def get_all_metrics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quality metrics for all runbooks
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with overall stats and runbook metrics
        """
        try:
            metrics = await self.metrics_service.get_all_runbook_metrics(
                db=self.db,
                tenant_id=self.tenant_id,
                days=days
            )
            return metrics
        
        except Exception as e:
            logger.error(f"Error getting all runbook metrics: {e}")
            raise self.handle_error(e, "Failed to get runbook metrics")
    
    async def get_runbook_metrics(
        self,
        runbook_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed metrics for a specific runbook
        
        Args:
            runbook_id: Runbook ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with detailed metrics and trends
        """
        try:
            metrics = await self.metrics_service.get_runbook_detailed_metrics(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                days=days
            )
            return metrics
        
        except Exception as e:
            logger.error(f"Error getting runbook metrics for {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get runbook metrics")
    
    async def calculate_metrics(
        self,
        runbook_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate and cache metrics for a runbook
        
        Args:
            runbook_id: Runbook ID
            days: Number of days to analyze
            
        Returns:
            Calculated metrics
        """
        try:
            metrics = await self.metrics_service.calculate_runbook_metrics(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                days=days
            )
            return {
                "runbook_id": metrics.runbook_id,
                "success_rate": float(metrics.success_rate),
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "avg_execution_time_minutes": float(metrics.avg_execution_time_minutes) if metrics.avg_execution_time_minutes else None,
                "avg_rating": float(metrics.avg_rating) if metrics.avg_rating else None,
                "last_calculated_at": metrics.last_calculated_at.isoformat() if metrics.last_calculated_at else None,
            }
        
        except Exception as e:
            logger.error(f"Error calculating metrics for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to calculate metrics")








