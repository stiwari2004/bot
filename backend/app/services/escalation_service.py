"""
Escalation service for determining escalation levels and assignment groups
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class EscalationService:
    """Service for determining escalation levels and assignment groups"""
    
    # Escalation level configuration
    ESCALATION_LEVELS = {
        "standard": {
            "assignment_group": "tier2_support",
            "priority": "3",  # Moderate
            "urgency": "2",   # High
            "impact": "3",    # Low
            "description": "Standard escalation - issue not resolved after automated attempts"
        },
        "urgent": {
            "assignment_group": "tier3_support",
            "priority": "2",  # High
            "urgency": "1",  # Critical
            "impact": "2",  # Medium
            "description": "Urgent escalation - critical issue or multiple retry failures"
        },
        "critical": {
            "assignment_group": "on_call_engineers",
            "priority": "1",  # Critical
            "urgency": "1",  # Critical
            "impact": "1",  # High
            "description": "Critical escalation - production outage or severe impact"
        }
    }
    
    def determine_escalation_level(
        self,
        db: Session,
        ticket: Ticket,
        escalation_reason: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine escalation level based on ticket severity, retry count, and context
        
        Args:
            db: Database session
            ticket: Ticket object
            escalation_reason: Reason for escalation
            execution_context: Optional context with execution logs, retry count, etc.
            
        Returns:
            Dict with escalation_level, assignment_group, priority, urgency, impact, and context
        """
        execution_context = execution_context or {}
        
        # Get retry count from execution sessions
        retry_count = self._get_retry_count(db, ticket.id)
        
        # Get ticket severity
        severity = ticket.severity or "medium"
        
        # Determine escalation level based on multiple factors
        escalation_level = "standard"
        
        # Critical severity always escalates to critical level
        if severity == "critical":
            escalation_level = "critical"
        # High severity with multiple retries escalates to urgent
        elif severity == "high" and retry_count >= 2:
            escalation_level = "urgent"
        # High severity escalates to urgent
        elif severity == "high":
            escalation_level = "urgent"
        # Multiple retries (3+) escalates to urgent regardless of severity
        elif retry_count >= 3:
            escalation_level = "urgent"
        # Production environment with high severity escalates to urgent
        elif ticket.environment == "prod" and severity in ["high", "critical"]:
            escalation_level = "urgent"
        
        # Get escalation configuration
        escalation_config = self.ESCALATION_LEVELS.get(escalation_level, self.ESCALATION_LEVELS["standard"])
        
        # Build escalation context
        escalation_context = {
            "escalation_level": escalation_level,
            "assignment_group": escalation_config["assignment_group"],
            "priority": escalation_config["priority"],
            "urgency": escalation_config["urgency"],
            "impact": escalation_config["impact"],
            "retry_count": retry_count,
            "ticket_severity": severity,
            "ticket_environment": ticket.environment,
            "escalation_reason": escalation_reason,
            "execution_context": execution_context
        }
        
        logger.info(
            f"Determined escalation level '{escalation_level}' for ticket {ticket.id}: "
            f"severity={severity}, retry_count={retry_count}, environment={ticket.environment}"
        )
        
        return escalation_context
    
    def _get_retry_count(self, db: Session, ticket_id: int) -> int:
        """Get number of execution attempts for this ticket"""
        from app.models.execution_session import ExecutionSession
        
        # Count execution sessions that completed (successfully or not)
        sessions = db.query(ExecutionSession).filter(
            ExecutionSession.ticket_id == ticket_id,
            ExecutionSession.status.in_(["completed", "failed", "abandoned"])
        ).count()
        
        return sessions
    
    def build_escalation_comment(
        self,
        escalation_reason: str,
        escalation_context: Dict[str, Any],
        execution_logs: Optional[str] = None
    ) -> str:
        """
        Build detailed escalation comment with context
        
        Args:
            escalation_reason: Base reason for escalation
            escalation_context: Escalation context from determine_escalation_level
            execution_logs: Optional execution logs to include
            
        Returns:
            Formatted escalation comment
        """
        comment_parts = [
            f"🚨 ESCALATION: {escalation_context.get('escalation_level', 'standard').upper()}",
            "",
            f"Reason: {escalation_reason}",
            "",
            "Context:",
            f"  - Severity: {escalation_context.get('ticket_severity', 'unknown')}",
            f"  - Environment: {escalation_context.get('ticket_environment', 'unknown')}",
            f"  - Retry Attempts: {escalation_context.get('retry_count', 0)}",
            f"  - Escalation Level: {escalation_context.get('escalation_level', 'standard')}",
        ]
        
        # Add execution context if available
        exec_context = escalation_context.get("execution_context", {})
        if exec_context:
            comment_parts.append("")
            comment_parts.append("Execution Summary:")
            comment_parts.append(f"  - Total Steps: {exec_context.get('total_steps', 0)}")
            comment_parts.append(f"  - Successful: {exec_context.get('successful_steps', 0)}")
            comment_parts.append(f"  - Failed: {exec_context.get('failed_steps', 0)}")
            comment_parts.append(f"  - Success Rate: {exec_context.get('success_rate', 0.0):.1%}")
            comment_parts.append(f"  - Verification Method: {exec_context.get('verification_method', 'unknown')}")
            comment_parts.append(f"  - Confidence: {exec_context.get('confidence', 0.0):.1%}")
            
            # Add failed step details
            failed_step_details = exec_context.get("failed_step_details", [])
            if failed_step_details:
                comment_parts.append("")
                comment_parts.append("Failed Steps:")
                for i, step_detail in enumerate(failed_step_details[:3], 1):  # Limit to 3 steps
                    step_name = step_detail.get("step_name", "Unknown Step")
                    error = step_detail.get("error", "No error message")
                    comment_parts.append(f"  {i}. {step_name}: {error[:200]}")  # Truncate long errors
            
            if exec_context.get("error_message"):
                comment_parts.append(f"  - Error: {exec_context.get('error_message')[:500]}")
        
        # Add execution logs if provided
        if execution_logs:
            comment_parts.extend([
                "",
                "Execution Logs:",
                execution_logs[:2000]  # Limit to 2000 chars for ServiceNow
            ])
        
        return "\n".join(comment_parts)

