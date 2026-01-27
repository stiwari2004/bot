"""
Remediation Analytics Service
Calculates MTTR, automation coverage, ROI, and identifies failing steps
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func as sql_func

from app.models.remediation_analytics import RemediationAnalytics
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
from app.core.logging import get_logger

logger = get_logger(__name__)


class RemediationAnalyticsService:
    """Service for calculating remediation effectiveness metrics"""
    
    def calculate_mttr(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[float]:
        """
        Calculate Mean Time To Resolution (MTTR) in minutes
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            
        Returns:
            MTTR in minutes or None
        """
        # Get completed sessions in period
        sessions = db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.status.in_(["completed", "completed_with_errors"]),
            ExecutionSession.completed_at.isnot(None),
            ExecutionSession.started_at.isnot(None),
            ExecutionSession.completed_at >= period_start,
            ExecutionSession.completed_at <= period_end
        ).all()
        
        if not sessions:
            return None
        
        total_minutes = 0
        count = 0
        
        for session in sessions:
            if session.started_at and session.completed_at:
                duration = (session.completed_at - session.started_at).total_seconds() / 60
                total_minutes += duration
                count += 1
        
        return total_minutes / count if count > 0 else None
    
    def calculate_automation_coverage(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Calculate automation coverage percentage
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            
        Returns:
            Dictionary with coverage metrics
        """
        # Get all tickets in period
        tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.created_at >= period_start,
            Ticket.created_at <= period_end
        ).all()
        
        total_incidents = len(tickets)
        auto_resolved = 0
        manual_interventions = 0
        
        for ticket in tickets:
            # Check if ticket was resolved automatically (no manual approval)
            sessions = db.query(ExecutionSession).filter(
                ExecutionSession.ticket_id == ticket.id,
                ExecutionSession.tenant_id == tenant_id
            ).all()
            
            if sessions:
                # Check if any session required manual approval
                has_manual_approval = any(
                    db.query(ExecutionStep).filter(
                        ExecutionStep.session_id == session.id,
                        ExecutionStep.requires_approval == True,
                        ExecutionStep.approved.isnot(None)
                    ).first() is not None
                    for session in sessions
                )
                
                if has_manual_approval:
                    manual_interventions += 1
                else:
                    auto_resolved += 1
        
        coverage_pct = (auto_resolved / total_incidents * 100) if total_incidents > 0 else 0.0
        
        return {
            "total_incidents": total_incidents,
            "auto_resolution_count": auto_resolved,
            "manual_intervention_count": manual_interventions,
            "automation_coverage_pct": coverage_pct
        }
    
    def calculate_roi(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime,
        labor_cost_per_hour: float = 100.0
    ) -> Dict[str, Any]:
        """
        Calculate ROI metrics
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            labor_cost_per_hour: Cost per hour of labor
            
        Returns:
            ROI metrics dictionary
        """
        # Calculate time savings from automation
        coverage = self.calculate_automation_coverage(db, tenant_id, period_start, period_end)
        mttr = self.calculate_mttr(db, tenant_id, period_start, period_end)
        
        if not mttr or coverage["total_incidents"] == 0:
            return {
                "cost_savings": 0.0,
                "time_savings_hours": 0.0,
                "labor_cost_per_hour": labor_cost_per_hour,
                "total_value": 0.0
            }
        
        # Estimate time savings (manual resolution typically takes 2x longer)
        auto_resolved = coverage["auto_resolution_count"]
        time_saved_per_incident = mttr / 60.0  # Convert to hours
        total_time_saved_hours = auto_resolved * time_saved_per_incident
        
        # Calculate cost savings
        cost_savings = total_time_saved_hours * labor_cost_per_hour
        
        return {
            "cost_savings": cost_savings,
            "time_savings_hours": total_time_saved_hours,
            "labor_cost_per_hour": labor_cost_per_hour,
            "total_value": cost_savings
        }
    
    def identify_top_failing_steps(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Identify top failing steps
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            limit: Maximum number of results
            
        Returns:
            List of failing step dictionaries
        """
        # Get failed steps in period
        failed_steps = db.query(ExecutionStep).join(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionStep.success == False,
            ExecutionStep.completed == True,
            ExecutionStep.completed_at >= period_start,
            ExecutionStep.completed_at <= period_end
        ).all()
        
        # Aggregate by step number and error type
        step_failures = {}
        
        for step in failed_steps:
            key = f"{step.session.runbook_id}_{step.step_number}"
            if key not in step_failures:
                step_failures[key] = {
                    "runbook_id": step.session.runbook_id,
                    "step_number": step.step_number,
                    "failure_count": 0,
                    "error_types": {}
                }
            
            step_failures[key]["failure_count"] += 1
            
            # Track error types
            error_type = "unknown"
            if step.error:
                error_lower = step.error.lower()
                if "timeout" in error_lower:
                    error_type = "timeout"
                elif "connection" in error_lower:
                    error_type = "connection_error"
                elif "permission" in error_lower or "unauthorized" in error_lower:
                    error_type = "permission_error"
                elif "not found" in error_lower:
                    error_type = "not_found"
            
            step_failures[key]["error_types"][error_type] = \
                step_failures[key]["error_types"].get(error_type, 0) + 1
        
        # Sort by failure count and return top N
        sorted_failures = sorted(
            step_failures.values(),
            key=lambda x: x["failure_count"],
            reverse=True
        )[:limit]
        
        # Format error types
        for failure in sorted_failures:
            failure["error_types"] = list(failure["error_types"].keys())
        
        return sorted_failures
    
    def get_improvement_trends(
        self,
        db: Session,
        tenant_id: int,
        period_type: str,
        periods: int = 12
    ) -> Dict[str, Any]:
        """
        Get improvement trends over time
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_type: 'daily', 'weekly', 'monthly'
            periods: Number of periods to analyze
            
        Returns:
            Trends dictionary
        """
        now = datetime.now(timezone.utc)
        trends = {
            "mttr_trend": [],
            "coverage_trend": []
        }
        
        # Calculate delta based on period type
        if period_type == "daily":
            delta = timedelta(days=1)
        elif period_type == "weekly":
            delta = timedelta(weeks=1)
        else:  # monthly
            delta = timedelta(days=30)
        
        # Calculate metrics for each period
        for i in range(periods):
            period_end = now - (delta * i)
            period_start = period_end - delta
            
            mttr = self.calculate_mttr(db, tenant_id, period_start, period_end)
            coverage = self.calculate_automation_coverage(db, tenant_id, period_start, period_end)
            
            trends["mttr_trend"].append({
                "date": period_end.isoformat(),
                "mttr": mttr if mttr else None
            })
            
            trends["coverage_trend"].append({
                "date": period_end.isoformat(),
                "coverage": coverage["automation_coverage_pct"]
            })
        
        # Reverse to show chronological order
        trends["mttr_trend"].reverse()
        trends["coverage_trend"].reverse()
        
        return trends
    
    def generate_analytics(
        self,
        db: Session,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime,
        period_type: str
    ) -> RemediationAnalytics:
        """
        Generate complete analytics for a period
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            period_start: Period start time
            period_end: Period end time
            period_type: Period type
            
        Returns:
            RemediationAnalytics object
        """
        mttr = self.calculate_mttr(db, tenant_id, period_start, period_end)
        coverage = self.calculate_automation_coverage(db, tenant_id, period_start, period_end)
        roi = self.calculate_roi(db, tenant_id, period_start, period_end)
        failing_steps = self.identify_top_failing_steps(db, tenant_id, period_start, period_end)
        
        analytics = RemediationAnalytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            mttr_minutes=mttr,
            automation_coverage_pct=coverage["automation_coverage_pct"],
            manual_intervention_count=coverage["manual_intervention_count"],
            auto_resolution_count=coverage["auto_resolution_count"],
            total_incidents=coverage["total_incidents"],
            roi_metrics=roi,
            top_failing_steps=failing_steps
        )
        
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
        
        return analytics
