"""
Service to handle timeout and auto-resume for stuck execution sessions.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionTimeoutService:
    """Handles timeout and auto-resume for stuck sessions"""
    
    # Timeout thresholds (in minutes)
    APPROVAL_TIMEOUT_NON_CRITICAL = 30  # 30 minutes for non-critical steps
    APPROVAL_TIMEOUT_CRITICAL = 120  # 2 hours for critical steps
    
    def __init__(self, step_execution_service=None):
        self.step_execution_service = step_execution_service
    
    async def check_and_resume_stuck_sessions(self, db: Session) -> dict:
        """
        Check for stuck sessions and auto-resume non-critical ones.
        
        Returns:
            {
                "checked": int,
                "resumed": int,
                "escalated": int
            }
        """
        stats = {
            "checked": 0,
            "resumed": 0,
            "escalated": 0
        }
        
        # Find sessions stuck in waiting_approval
        stuck_sessions = db.query(ExecutionSession).filter(
            ExecutionSession.status == "waiting_approval",
            ExecutionSession.waiting_for_approval == True,
            ExecutionSession.approval_step_number.isnot(None)
        ).all()
        
        stats["checked"] = len(stuck_sessions)
        
        for session in stuck_sessions:
            try:
                # Get the step waiting for approval
                step = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session.id,
                    ExecutionStep.step_number == session.approval_step_number
                ).first()
                
                if not step:
                    logger.warning(f"Session {session.id} waiting for approval on step {session.approval_step_number} but step not found")
                    continue
                
                # Calculate how long it's been waiting
                if session.started_at:
                    wait_duration = (datetime.now(timezone.utc) - session.started_at).total_seconds() / 60
                else:
                    # Use created_at as fallback
                    wait_duration = (datetime.now(timezone.utc) - session.created_at).total_seconds() / 60
                
                # Determine if step is critical
                is_critical = step.severity in ("dangerous", "critical") or step.step_type == "main"
                timeout_threshold = self.APPROVAL_TIMEOUT_CRITICAL if is_critical else self.APPROVAL_TIMEOUT_NON_CRITICAL
                
                if wait_duration >= timeout_threshold:
                    if is_critical:
                        # Escalate critical steps
                        logger.warning(
                            f"Session {session.id} step {step.step_number} (critical) has been waiting "
                            f"for approval for {wait_duration:.1f} minutes. Escalating..."
                        )
                        session.status = "escalated"
                        session.waiting_for_approval = False
                        session.completed_at = datetime.now(timezone.utc)
                        stats["escalated"] += 1
                    else:
                        # Auto-approve non-critical steps
                        logger.info(
                            f"Session {session.id} step {step.step_number} (non-critical) has been waiting "
                            f"for approval for {wait_duration:.1f} minutes. Auto-approving..."
                        )
                        step.approved = True
                        step.approved_at = datetime.now(timezone.utc)
                        step.approved_by = None  # System auto-approval
                        session.waiting_for_approval = False
                        session.approval_step_number = None
                        session.status = "in_progress"
                        stats["resumed"] += 1
                        
                        # Execute the step
                        if self.step_execution_service:
                            try:
                                await self.step_execution_service.execute_step(db, session, step)
                            except Exception as e:
                                logger.error(f"Error auto-executing step {step.step_number} for session {session.id}: {e}", exc_info=True)
                                session.status = "failed"
                                session.completed_at = datetime.now(timezone.utc)
                    
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error processing stuck session {session.id}: {e}", exc_info=True)
                db.rollback()
        
        return stats




