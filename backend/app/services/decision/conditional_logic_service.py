"""
Conditional Logic Service
Lightweight rule-based decision making without heavy LLM calls
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConditionalLogicService:
    """Service for rule-based conditional decisions"""
    
    def __init__(self):
        # Default thresholds
        self.rollback_threshold_failures = 2  # Number of consecutive failures before rollback
        self.escalation_threshold_confidence = 0.3  # Confidence below which to escalate
        self.escalation_threshold_failures = 3  # Number of failures before escalation
    
    async def evaluate_condition(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a conditional expression
        
        Args:
            condition: Condition dictionary with type and parameters
            context: Context dictionary with values to evaluate against
            
        Returns:
            True if condition is met, False otherwise
        """
        condition_type = condition.get("type")
        
        if condition_type == "equals":
            field = condition.get("field")
            value = condition.get("value")
            return context.get(field) == value
        
        elif condition_type == "not_equals":
            field = condition.get("field")
            value = condition.get("value")
            return context.get(field) != value
        
        elif condition_type == "greater_than":
            field = condition.get("field")
            value = condition.get("value")
            return context.get(field, 0) > value
        
        elif condition_type == "less_than":
            field = condition.get("field")
            value = condition.get("value")
            return context.get(field, 0) < value
        
        elif condition_type == "contains":
            field = condition.get("field")
            value = condition.get("value")
            field_value = str(context.get(field, ""))
            return value in field_value
        
        elif condition_type == "not_contains":
            field = condition.get("field")
            value = condition.get("value")
            field_value = str(context.get(field, ""))
            return value not in field_value
        
        elif condition_type == "and":
            sub_conditions = condition.get("conditions", [])
            return all(
                await self.evaluate_condition(sub_cond, context)
                for sub_cond in sub_conditions
            )
        
        elif condition_type == "or":
            sub_conditions = condition.get("conditions", [])
            return any(
                await self.evaluate_condition(sub_cond, context)
                for sub_cond in sub_conditions
            )
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False
    
    async def decide_next_action(
        self,
        session: ExecutionSession,
        step_output: Optional[str],
        db: Session
    ) -> Dict[str, Any]:
        """
        Decide next action based on step output and session state
        
        Args:
            session: ExecutionSession object
            step_output: Output from the last step (optional)
            db: Database session
            
        Returns:
            Action dictionary with type and parameters
        """
        # Get recent steps
        recent_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.completed == True
        ).order_by(ExecutionStep.step_number.desc()).limit(5).all()
        
        # Count failures
        failure_count = sum(1 for step in recent_steps if step.success == False)
        
        # Check for rollback
        if await self.should_rollback(session, recent_steps, db):
            return {
                "action": "rollback",
                "reason": f"Detected {failure_count} consecutive failures",
                "step_number": recent_steps[0].step_number if recent_steps else None
            }
        
        # Check for escalation
        if await self.should_escalate(session, recent_steps, db):
            return {
                "action": "escalate",
                "reason": f"Multiple failures ({failure_count}) or low confidence",
                "step_number": recent_steps[0].step_number if recent_steps else None
            }
        
        # Check output-based branching
        if step_output:
            branch_action = await self._check_output_branching(step_output, session)
            if branch_action:
                return branch_action
        
        # Default: continue
        return {
            "action": "continue",
            "reason": "No conditions met for rollback or escalation"
        }
    
    async def should_rollback(
        self,
        session: ExecutionSession,
        steps: List[ExecutionStep],
        db: Session
    ) -> bool:
        """
        Determine if rollback should be triggered
        
        Args:
            session: ExecutionSession object
            steps: List of recent execution steps
            db: Database session
            
        Returns:
            True if should rollback, False otherwise
        """
        if not steps:
            return False
        
        # Check for consecutive failures
        consecutive_failures = 0
        for step in reversed(steps):  # Check from oldest to newest
            if step.success == False:
                consecutive_failures += 1
            else:
                break  # Stop counting if we hit a success
        
        # Rollback if we have enough consecutive failures
        if consecutive_failures >= self.rollback_threshold_failures:
            logger.info(
                f"Rollback triggered for session {session.id}: "
                f"{consecutive_failures} consecutive failures"
            )
            return True
        
        # Check for critical errors in output
        for step in steps:
            if step.error and self._is_critical_error(step.error):
                logger.info(
                    f"Rollback triggered for session {session.id}: "
                    f"Critical error detected: {step.error[:100]}"
                )
                return True
        
        return False
    
    async def should_escalate(
        self,
        session: ExecutionSession,
        steps: List[ExecutionStep],
        db: Session
    ) -> bool:
        """
        Determine if issue should be escalated
        
        Args:
            session: ExecutionSession object
            steps: List of recent execution steps
            db: Database session
            
        Returns:
            True if should escalate, False otherwise
        """
        if not steps:
            return False
        
        # Count total failures
        failure_count = sum(1 for step in steps if step.success == False)
        
        # Escalate if too many failures
        if failure_count >= self.escalation_threshold_failures:
            logger.info(
                f"Escalation triggered for session {session.id}: "
                f"{failure_count} failures"
            )
            return True
        
        # Check session status
        if session.status in ["failed", "abandoned"]:
            return True
        
        # Check for timeout or other critical issues
        if session.status == "escalated":
            return True
        
        return False
    
    def _is_critical_error(self, error_text: str) -> bool:
        """Check if error text indicates a critical error"""
        if not error_text:
            return False
        
        error_lower = error_text.lower()
        
        # Critical error patterns
        critical_patterns = [
            "data loss",
            "corruption",
            "cannot recover",
            "fatal error",
            "system crash",
            "out of memory",
            "disk full",
            "connection refused",
            "permission denied",
            "access denied"
        ]
        
        return any(pattern in error_lower for pattern in critical_patterns)
    
    async def _check_output_branching(
        self,
        step_output: str,
        session: ExecutionSession
    ) -> Optional[Dict[str, Any]]:
        """
        Check if step output triggers branching logic
        
        Args:
            step_output: Step output text
            session: ExecutionSession object
            
        Returns:
            Action dictionary if branching triggered, None otherwise
        """
        output_lower = step_output.lower()
        
        # Check for success indicators
        success_indicators = ["success", "completed", "ok", "done", "finished"]
        if any(indicator in output_lower for indicator in success_indicators):
            return {
                "action": "continue",
                "reason": "Output indicates success"
            }
        
        # Check for failure indicators
        failure_indicators = ["error", "failed", "failure", "exception", "timeout"]
        if any(indicator in output_lower for indicator in failure_indicators):
            return {
                "action": "retry",
                "reason": "Output indicates failure, may retry"
            }
        
        # Check for specific conditions that require different actions
        if "rollback" in output_lower or "revert" in output_lower:
            return {
                "action": "rollback",
                "reason": "Output indicates rollback needed"
            }
        
        return None








