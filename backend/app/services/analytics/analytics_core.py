"""
Analytics core service - orchestrates analytics services
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.services.analytics.usage_analytics import UsageAnalytics
from app.services.analytics.quality_analytics import QualityAnalytics
from app.services.analytics.coverage_analytics import CoverageAnalytics
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Main analytics service that orchestrates specialized analytics services"""
    
    def __init__(self):
        self.usage_analytics = UsageAnalytics()
        self.quality_analytics = QualityAnalytics()
        self.coverage_analytics = CoverageAnalytics()
    
    async def get_usage_statistics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        return await self.usage_analytics.get_usage_statistics(tenant_id, db, days)
    
    async def get_quality_metrics(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get quality metrics for runbooks"""
        return await self.quality_analytics.get_quality_metrics(tenant_id, db)
    
    async def get_coverage_analysis(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Analyze runbook coverage for different issue types"""
        return await self.coverage_analytics.get_coverage_analysis(tenant_id, db)
    
    async def get_search_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Track search quality and recommendation accuracy"""
        return await self.coverage_analytics.get_search_quality_metrics(tenant_id, db, days)
    
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
        """Record when a runbook is used"""
        return await self.usage_analytics.record_runbook_usage(
            runbook_id, tenant_id, db, issue_description, confidence_score,
            was_helpful, feedback_text, execution_time_minutes
        )
    
    async def get_runbook_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive quality metrics for all runbooks"""
        return await self.quality_analytics.get_runbook_quality_metrics(tenant_id, db, days)
    
    async def get_runbook_metrics(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed metrics for a specific runbook"""
        return await self.quality_analytics.get_runbook_metrics(runbook_id, tenant_id, db, days)




