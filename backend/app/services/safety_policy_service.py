"""
Safety Policy Service
Implements safety controls for autonomous remediation
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.models.runbook import Runbook

logger = get_logger(__name__)


class SafetyPolicyService:
    """Service for enforcing safety policies on autonomous operations"""
    
    def __init__(self, db: Session, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id
    
    def check_dry_run_required(
        self,
        runbook_id: int,
        environment: str,
        severity: str
    ) -> bool:
        """
        Check if dry-run is required before execution
        
        Returns:
            True if dry-run is required
        """
        # Require dry-run for production and critical severity
        if environment == "prod" and severity in ["critical", "high"]:
            return True
        
        # Require dry-run for new runbooks (low usage count)
        runbook = self.db.query(Runbook).filter(Runbook.id == runbook_id).first()
        if runbook and hasattr(runbook, 'usage_count') and (runbook.usage_count or 0) < 3:
            return True
        
        return False
    
    def check_approval_required(
        self,
        runbook_id: int,
        environment: str,
        severity: str,
        risk_score: Optional[float] = None
    ) -> bool:
        """
        Check if approval gate is required
        
        Returns:
            True if approval is required
        """
        # Always require approval for critical severity
        if severity == "critical":
            return True
        
        # Require approval for production high-risk operations
        if environment == "prod" and severity == "high":
            return True
        
        # Require approval for high risk scores
        if risk_score and risk_score > 0.7:
            return True
        
        return False
    
    def check_rate_limit(
        self,
        runbook_id: int,
        target_host: Optional[str] = None,
        window_minutes: int = 60
    ) -> bool:
        """
        Check if rate limit would be exceeded
        
        Returns:
            True if execution is allowed, False if rate limited
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)
        
        # Count recent executions of this runbook
        query = self.db.query(ExecutionSession).filter(
            ExecutionSession.runbook_id == runbook_id,
            ExecutionSession.created_at >= window_start,
            ExecutionSession.status.in_(["completed", "completed_with_errors", "failed"])
        )
        
        if self.tenant_id:
            query = query.filter(ExecutionSession.tenant_id == self.tenant_id)
        
        recent_count = query.count()
        
        # Rate limit: max 5 executions per hour per runbook
        max_executions_per_hour = 5
        if recent_count >= max_executions_per_hour:
            logger.warning(
                f"Rate limit exceeded: {recent_count} executions in last {window_minutes} minutes "
                f"for runbook {runbook_id}"
            )
            return False
        
        # If target_host specified, also check per-host rate limit
        if target_host:
            # This would require tracking target_host in ExecutionSession
            # For now, just check global limit
            pass
        
        return True
    
    def get_rollback_capability(self, runbook_id: int) -> Dict[str, Any]:
        """
        Check if runbook has rollback/compensation steps
        
        Returns:
            Dict with rollback availability and steps
        """
        runbook = self.db.query(Runbook).filter(Runbook.id == runbook_id).first()
        
        if not runbook:
            return {
                "has_rollback": False,
                "rollback_steps": [],
                "message": "Runbook not found"
            }
        
        # Parse runbook YAML to check for rollback steps
        # This is simplified - in production, would parse actual YAML structure
        has_rollback = False
        rollback_steps = []
        
        if runbook.body_md:
            # Simple check for rollback mentions
            if "rollback" in runbook.body_md.lower() or "compensation" in runbook.body_md.lower():
                has_rollback = True
                # In production, would extract actual rollback steps from YAML
        
        return {
            "has_rollback": has_rollback,
            "rollback_steps": rollback_steps,
            "message": "Rollback available" if has_rollback else "No rollback steps defined"
        }
    
    def evaluate_execution_safety(
        self,
        runbook_id: int,
        environment: str,
        severity: str,
        risk_score: Optional[float] = None,
        target_host: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive safety evaluation before execution
        
        Returns:
            Dict with safety checks and recommendations
        """
        checks = {
            "dry_run_required": self.check_dry_run_required(runbook_id, environment, severity),
            "approval_required": self.check_approval_required(runbook_id, environment, severity, risk_score),
            "rate_limit_ok": self.check_rate_limit(runbook_id, target_host),
            "rollback_available": self.get_rollback_capability(runbook_id)["has_rollback"],
        }
        
        # Determine if execution is safe
        is_safe = (
            not checks["dry_run_required"] or  # Dry-run can be bypassed if not required
            checks["approval_required"] or  # Approval provides safety
            checks["rate_limit_ok"]  # Rate limit prevents abuse
        )
        
        recommendations = []
        if checks["dry_run_required"]:
            recommendations.append("Execute in dry-run mode first")
        if checks["approval_required"]:
            recommendations.append("Require human approval before execution")
        if not checks["rate_limit_ok"]:
            recommendations.append("Rate limit exceeded - wait before retrying")
        if not checks["rollback_available"]:
            recommendations.append("Warning: No rollback steps defined")
        
        return {
            "is_safe": is_safe,
            "checks": checks,
            "recommendations": recommendations,
            "can_proceed": is_safe and checks["rate_limit_ok"],
        }
