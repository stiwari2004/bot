"""
Step execution service for running individual execution steps
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.infrastructure import get_connector
from app.services.security import redact_sensitive_text
from app.core import metrics
from app.core.tracing import tracing_span
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepExecutionService:
    """Handles execution of individual steps"""
    
    def __init__(self, connection_service, rollback_service, ticket_status_service, resolution_verification_service):
        self.connection_service = connection_service
        self.rollback_service = rollback_service
        self.ticket_status_service = ticket_status_service
        self.resolution_verification_service = resolution_verification_service
    
    async def execute_step(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ):
        """Execute a single step"""
        logger.info(f"[EXECUTE_STEP] Starting execution of step {step.step_number} (type: {step.step_type}) for session {session.id}")
        logger.info(f"[EXECUTE_STEP] Command: {step.command[:100] if step.command else 'N/A'}...")
        logger.info(f"[EXECUTE_STEP] Session status: {session.status}, Step requires_approval: {step.requires_approval}")
        
        if session.status != "in_progress" and session.status != "waiting_approval":
            session.status = "in_progress"
        
        if not session.started_at:
            session.started_at = datetime.utcnow()
        
        start_time = datetime.utcnow()
        connector_type = "local"
        previous_status = session.status or "unknown"

        with tracing_span(
            "execution.step",
            {
                "session_id": session.id,
                "step_number": step.step_number,
                "step_type": step.step_type or "main",
            },
        ):
            try:
                # Get connection configuration
                connection_config = await self.connection_service.get_connection_config(db, session, step)

                # Determine connector type from connection config or step type
                connector_type = connection_config.get("connector_type", "local")

                # Get connector
                connector = get_connector(connector_type)

                # Execute command
                logger.info(f"[EXECUTE_STEP] Executing command via connector '{connector_type}' on session {session.id}, step {step.step_number}")
                logger.info(f"[EXECUTE_STEP] Connection config keys: {list(connection_config.keys())}")
                result = await connector.execute_command(
                    command=step.command,
                    connection_config=connection_config,
                    timeout=30,
                )
                logger.info(f"[EXECUTE_STEP] Command execution result: success={result.get('success')}, has_output={bool(result.get('output'))}, has_error={bool(result.get('error'))}")

                # Update step
                step.credentials_used = []
                credential_id = connection_config.get("credential_id")
                if credential_id:
                    step.credentials_used = [credential_id]
                step.completed = True
                step.success = result["success"]
                step.output = redact_sensitive_text(result.get("output"))
                step.error = redact_sensitive_text(result.get("error"))
                step.completed_at = datetime.utcnow()

                # If step failed, mark session as failed and trigger rollback
                if not result["success"]:
                    session.status = "failed"
                    session.completed_at = datetime.utcnow()

                    # Trigger rollback of all executed steps
                    await self.rollback_service.rollback_execution(db, session)

                    # Update ticket status on failure
                    if session.ticket_id:
                        self.ticket_status_service.update_ticket_on_execution_complete(
                            db, session.ticket_id, "failed", issue_resolved=False
                        )
                else:
                    # Step succeeded - check if there are more steps to execute
                    next_step = db.query(ExecutionStep).filter(
                        ExecutionStep.session_id == session.id,
                        ExecutionStep.step_number == step.step_number + 1,
                        ExecutionStep.completed == False
                    ).first()
                    
                    if next_step:
                        if next_step.requires_approval:
                            # Next step requires approval - wait for it
                            session.status = "waiting_approval"
                            session.waiting_for_approval = True
                            session.approval_step_number = next_step.step_number
                            session.current_step = next_step.step_number
                            logger.info(f"Step {step.step_number} completed. Waiting for approval on step {next_step.step_number}")
                        else:
                            # Auto-execute next step
                            session.current_step = next_step.step_number
                            logger.info(f"Step {step.step_number} completed. Auto-executing step {next_step.step_number}")
                            # Commit current step before executing next
                            db.commit()
                            db.refresh(session)
                            # Recursively execute next step
                            await self.execute_step(db, session, next_step)
                    else:
                        # All steps completed
                        session.status = "completed"
                        session.completed_at = datetime.utcnow()
                        if session.started_at:
                            duration = (session.completed_at - session.started_at).total_seconds() / 60
                            session.total_duration_minutes = int(duration)
                        
                        logger.info(f"All steps completed for session {session.id}")
                        
                        # Verify resolution and update ticket status
                        if session.ticket_id:
                            verification_result = await self.resolution_verification_service.verify_resolution(
                                db, session.id, session.ticket_id
                            )
                            logger.info(
                                f"Resolution verification for session {session.id}: "
                                f"resolved={verification_result['resolved']}, "
                                f"confidence={verification_result['confidence']:.2f}"
                            )

            except Exception as e:
                logger.error(f"Error executing step {step.step_number}: {e}")
                step.completed = True
                step.success = False
                step.error = redact_sensitive_text(str(e))
                step.completed_at = datetime.utcnow()
                session.status = "failed"
                session.completed_at = datetime.utcnow()

                # Trigger rollback on exception
                await self.rollback_service.rollback_execution(db, session)

                # Update ticket status on exception
                if session.ticket_id:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, session.ticket_id, "failed", issue_resolved=False
                    )

        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics.observe_step_duration(connector_type, duration)
        if previous_status != session.status:
            metrics.record_state_transition(previous_status, session.status or "unknown")
        
        db.commit()
        logger.info(f"[EXECUTE_STEP] Completed execution of step {step.step_number} for session {session.id}")


