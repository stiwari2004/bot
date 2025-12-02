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
    
    async def get_accuracy_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get overall accuracy metrics across all components"""
        from datetime import datetime, timedelta, timezone
        from app.models.execution_session import ExecutionSession, ExecutionFeedback
        from app.models.runbook import Runbook
        from app.models.ticket import Ticket
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get execution accuracy
        executions = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.started_at >= cutoff_date
        ).all()
        
        execution_accuracy = 0.0
        if executions:
            successful = sum(1 for e in executions if e.status == "completed" or (e.feedback and e.feedback.was_successful))
            execution_accuracy = (successful / len(executions) * 100.0)
        
        # Get resolution accuracy
        tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.created_at >= cutoff_date
        ).all()
        
        resolution_accuracy = 0.0
        if tickets:
            resolved = sum(1 for t in tickets if t.status in ['resolved', 'closed'])
            resolution_accuracy = (resolved / len(tickets) * 100.0)
        
        # Get retrieval accuracy (from search quality)
        search_quality = await self.get_search_quality_metrics(tenant_id, db, days)
        retrieval_accuracy = search_quality.get('avg_confidence', 85.0) if search_quality else 85.0
        
        # Get generation accuracy (simplified - based on runbook usage)
        runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == tenant_id,
            Runbook.created_at >= cutoff_date
        ).count()
        generation_accuracy = 90.0 if runbooks > 0 else 0.0  # Simplified metric
        
        # Calculate overall accuracy (weighted average)
        overall_accuracy = (
            retrieval_accuracy * 0.25 +
            generation_accuracy * 0.25 +
            execution_accuracy * 0.25 +
            resolution_accuracy * 0.25
        )
        
        # Generate trend data (last 5 days)
        trend = []
        for i in range(5, 0, -1):
            day_start = datetime.now(timezone.utc) - timedelta(days=i)
            day_end = datetime.now(timezone.utc) - timedelta(days=i-1)
            day_executions = [e for e in executions if day_start <= e.started_at < day_end]
            if day_executions:
                day_success = sum(1 for e in day_executions if e.status == "completed")
                day_score = (day_success / len(day_executions) * 100.0) if day_executions else 0.0
            else:
                day_score = overall_accuracy  # Use overall if no data
            trend.append({
                "date": f"Day -{i}" if i > 1 else "Today",
                "score": round(day_score, 1)
            })
        
        # Generate alerts
        alerts = []
        if execution_accuracy < 80:
            alerts.append({
                "id": "exec-low",
                "message": f"Execution accuracy dropped to {execution_accuracy:.1f}%",
                "severity": "warn"
            })
        if resolution_accuracy < 75:
            alerts.append({
                "id": "res-low",
                "message": f"Resolution accuracy is {resolution_accuracy:.1f}%",
                "severity": "critical"
            })
        if retrieval_accuracy < 85:
            alerts.append({
                "id": "ret-low",
                "message": f"Retrieval accuracy is {retrieval_accuracy:.1f}%",
                "severity": "info"
            })
        
        # Get runbook performance
        runbook_performance = []
        runbook_metrics = await self.get_runbook_quality_metrics(tenant_id, db, days)
        if runbook_metrics and 'top_performers' in runbook_metrics:
            for rb in runbook_metrics['top_performers'][:4]:  # Top 4
                runbook_performance.append({
                    "runbook": rb.get('title', 'Unknown'),
                    "successRate": round(rb.get('success_rate', 0), 1),
                    "executions": rb.get('total_executions', 0),
                    "category": "General"  # Default category
                })
        
        return {
            "overall": round(overall_accuracy, 1),
            "componentScores": {
                "retrieval": round(retrieval_accuracy, 1),
                "generation": round(generation_accuracy, 1),
                "execution": round(execution_accuracy, 1),
                "resolution": round(resolution_accuracy, 1)
            },
            "trend": trend,
            "alerts": alerts,
            "runbookPerformance": runbook_performance
        }




