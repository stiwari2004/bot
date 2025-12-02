"""
RunbookQualityMetricsService
Business logic for calculating and managing runbook quality metrics
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.models.runbook import Runbook
from app.models.runbook_metrics import RunbookMetrics
from app.models.execution_session import ExecutionSession, ExecutionFeedback, ExecutionStep
from app.repositories.runbook_metrics_repository import RunbookMetricsRepository

logger = get_logger(__name__)


class RunbookQualityMetricsService:
    """Service for calculating and managing runbook quality metrics"""
    
    def __init__(self):
        pass
    
    async def calculate_runbook_metrics(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        days: int = 30
    ) -> RunbookMetrics:
        """
        Calculate and cache metrics for a specific runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            RunbookMetrics object (created or updated)
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all executions for this runbook
        executions = db.query(ExecutionSession).filter(
            ExecutionSession.runbook_id == runbook_id,
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.started_at >= cutoff_date
        ).all()
        
        if not executions:
            # Return empty metrics
            repo = RunbookMetricsRepository(db)
            existing = repo.get_by_runbook(runbook_id, tenant_id)
            if existing:
                return existing
            
            return RunbookMetrics(
                tenant_id=tenant_id,
                runbook_id=runbook_id,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                success_rate=0.0,
                calculation_period_days=days,
            )
        
        # Calculate execution metrics
        total_executions = len(executions)
        successful_executions = sum(
            1 for e in executions 
            if e.status == "completed" or (e.feedback and e.feedback.was_successful)
        )
        failed_executions = total_executions - successful_executions
        success_rate = (successful_executions / total_executions * 100.0) if total_executions > 0 else 0.0
        
        # Calculate time metrics
        durations = [e.total_duration_minutes for e in executions if e.total_duration_minutes]
        avg_execution_time = sum(durations) / len(durations) if durations else None
        min_execution_time = min(durations) if durations else None
        max_execution_time = max(durations) if durations else None
        
        # Calculate quality metrics
        ratings = [
            e.feedback.rating for e in executions 
            if e.feedback and e.feedback.rating
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        resolved_count = sum(
            1 for e in executions 
            if e.feedback and e.feedback.issue_resolved
        )
        issue_resolution_rate = (resolved_count / total_executions * 100.0) if total_executions > 0 else None
        
        # Calculate step completion rate
        all_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id.in_([e.id for e in executions])
        ).all()
        completed_steps = sum(1 for s in all_steps if s.completed)
        step_completion_rate = (completed_steps / len(all_steps) * 100.0) if all_steps else None
        
        # Calculate rollback frequency
        rollback_count = sum(1 for e in executions if e.status == "rolled_back")
        rollback_frequency = (rollback_count / total_executions * 100.0) if total_executions > 0 else None
        
        # Get or create metrics record
        repo = RunbookMetricsRepository(db)
        metrics = repo.get_by_runbook(runbook_id, tenant_id)
        
        if metrics:
            # Update existing
            metrics.total_executions = total_executions
            metrics.successful_executions = successful_executions
            metrics.failed_executions = failed_executions
            metrics.success_rate = success_rate
            metrics.avg_execution_time_minutes = avg_execution_time
            metrics.min_execution_time_minutes = min_execution_time
            metrics.max_execution_time_minutes = max_execution_time
            metrics.avg_rating = avg_rating
            metrics.issue_resolution_rate = issue_resolution_rate
            metrics.step_completion_rate = step_completion_rate
            metrics.rollback_frequency = rollback_frequency
            metrics.last_calculated_at = datetime.now(timezone.utc)
            metrics.calculation_period_days = days
            db.add(metrics)
            db.commit()
            db.refresh(metrics)
        else:
            # Create new
            metrics = RunbookMetrics(
                tenant_id=tenant_id,
                runbook_id=runbook_id,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                success_rate=success_rate,
                avg_execution_time_minutes=avg_execution_time,
                min_execution_time_minutes=min_execution_time,
                max_execution_time_minutes=max_execution_time,
                avg_rating=avg_rating,
                issue_resolution_rate=issue_resolution_rate,
                step_completion_rate=step_completion_rate,
                rollback_frequency=rollback_frequency,
                calculation_period_days=days,
            )
            db.add(metrics)
            db.commit()
            db.refresh(metrics)
        
        logger.info(f"Calculated metrics for runbook {runbook_id}: success_rate={success_rate:.2f}%")
        return metrics
    
    async def get_all_runbook_metrics(
        self,
        db: Session,
        tenant_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quality metrics for all runbooks
        
        Returns:
            Dictionary with overall stats and runbook-specific metrics
        """
        # Calculate/update metrics for all runbooks with executions
        runbooks_with_executions = db.query(Runbook.id).join(
            ExecutionSession, Runbook.id == ExecutionSession.runbook_id
        ).filter(
            Runbook.tenant_id == tenant_id
        ).distinct().all()
        
        all_metrics = []
        for (runbook_id,) in runbooks_with_executions:
            metrics = await self.calculate_runbook_metrics(db, runbook_id, tenant_id, days)
            all_metrics.append(metrics)
        
        # Calculate overall statistics
        if all_metrics:
            total_runbooks = len(all_metrics)
            avg_success_rate = sum(m.success_rate for m in all_metrics) / total_runbooks
            avg_execution_time = sum(
                m.avg_execution_time_minutes for m in all_metrics 
                if m.avg_execution_time_minutes
            ) / sum(1 for m in all_metrics if m.avg_execution_time_minutes) if any(m.avg_execution_time_minutes for m in all_metrics) else None
            avg_rating = sum(
                m.avg_rating for m in all_metrics 
                if m.avg_rating
            ) / sum(1 for m in all_metrics if m.avg_rating) if any(m.avg_rating for m in all_metrics) else None
            
            # Top performers
            top_performers = sorted(
                [m for m in all_metrics if m.total_executions >= 3],
                key=lambda x: x.success_rate,
                reverse=True
            )[:10]
            
            # Needs attention
            needs_attention = sorted(
                [m for m in all_metrics if m.total_executions >= 2 and m.success_rate < 50.0],
                key=lambda x: x.success_rate
            )[:10]
        else:
            total_runbooks = 0
            avg_success_rate = 0.0
            avg_execution_time = None
            avg_rating = None
            top_performers = []
            needs_attention = []
        
        return {
            "overall": {
                "total_runbooks": total_runbooks,
                "avg_success_rate": float(avg_success_rate) if avg_success_rate else 0.0,
                "avg_execution_time_minutes": float(avg_execution_time) if avg_execution_time else None,
                "avg_rating": float(avg_rating) if avg_rating else None,
            },
            "top_performers": [
                {
                    "runbook_id": m.runbook_id,
                    "success_rate": float(m.success_rate),
                    "total_executions": m.total_executions,
                    "avg_execution_time_minutes": float(m.avg_execution_time_minutes) if m.avg_execution_time_minutes else None,
                }
                for m in top_performers
            ],
            "needs_attention": [
                {
                    "runbook_id": m.runbook_id,
                    "success_rate": float(m.success_rate),
                    "total_executions": m.total_executions,
                    "avg_execution_time_minutes": float(m.avg_execution_time_minutes) if m.avg_execution_time_minutes else None,
                }
                for m in needs_attention
            ],
            "all_runbooks": [
                {
                    "runbook_id": m.runbook_id,
                    "success_rate": float(m.success_rate),
                    "total_executions": m.total_executions,
                    "failed_executions": m.failed_executions,
                    "avg_execution_time_minutes": float(m.avg_execution_time_minutes) if m.avg_execution_time_minutes else None,
                    "avg_rating": float(m.avg_rating) if m.avg_rating else None,
                    "issue_resolution_rate": float(m.issue_resolution_rate) if m.issue_resolution_rate else None,
                }
                for m in all_metrics
            ],
            "period_days": days,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def get_runbook_detailed_metrics(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed metrics for a specific runbook including trends
        
        Returns:
            Dictionary with detailed metrics and time-series data
        """
        # Calculate current metrics
        metrics = await self.calculate_runbook_metrics(db, runbook_id, tenant_id, days)
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get executions for trend analysis
        executions = db.query(ExecutionSession).filter(
            ExecutionSession.runbook_id == runbook_id,
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.started_at >= cutoff_date
        ).order_by(ExecutionSession.started_at.asc()).all()
        
        # Build time-series data (daily aggregates)
        daily_stats = {}
        for execution in executions:
            date_key = execution.started_at.date().isoformat() if execution.started_at else datetime.now(timezone.utc).date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "date": date_key,
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_duration": 0.0,
                    "durations": [],
                }
            
            daily_stats[date_key]["total"] += 1
            if execution.status == "completed" or (execution.feedback and execution.feedback.was_successful):
                daily_stats[date_key]["successful"] += 1
            else:
                daily_stats[date_key]["failed"] += 1
            
            if execution.total_duration_minutes:
                daily_stats[date_key]["durations"].append(execution.total_duration_minutes)
        
        # Calculate daily averages
        trends = []
        for date_key, stats in sorted(daily_stats.items()):
            avg_duration = sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0.0
            success_rate = (stats["successful"] / stats["total"] * 100.0) if stats["total"] > 0 else 0.0
            
            trends.append({
                "date": date_key,
                "total_executions": stats["total"],
                "successful_executions": stats["successful"],
                "failed_executions": stats["failed"],
                "success_rate": success_rate,
                "avg_duration_minutes": avg_duration,
            })
        
        # Get runbook info
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id
        ).first()
        
        return {
            "runbook_id": runbook_id,
            "runbook_title": runbook.title if runbook else None,
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": float(metrics.success_rate),
                "avg_execution_time_minutes": float(metrics.avg_execution_time_minutes) if metrics.avg_execution_time_minutes else None,
                "min_execution_time_minutes": float(metrics.min_execution_time_minutes) if metrics.min_execution_time_minutes else None,
                "max_execution_time_minutes": float(metrics.max_execution_time_minutes) if metrics.max_execution_time_minutes else None,
                "avg_rating": float(metrics.avg_rating) if metrics.avg_rating else None,
                "issue_resolution_rate": float(metrics.issue_resolution_rate) if metrics.issue_resolution_rate else None,
                "step_completion_rate": float(metrics.step_completion_rate) if metrics.step_completion_rate else None,
                "rollback_frequency": float(metrics.rollback_frequency) if metrics.rollback_frequency else None,
            },
            "trends": trends,
            "period_days": days,
            "last_calculated_at": metrics.last_calculated_at.isoformat() if metrics.last_calculated_at else None,
        }

