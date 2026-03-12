"""
Handles event publishing for step execution
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepEventPublisher:
    """Handles event publishing for step execution"""

    def __init__(self, event_service=None):
        self.event_service = event_service

    async def publish_raw(
        self,
        db: Session,
        session: ExecutionSession,
        payload: Dict[str, Any],
    ) -> None:
        """Publish a raw arbitrary event payload (used by agent executor)."""
        if not self.event_service:
            return
        try:
            event_type = payload.get("event_type", "agent.event")
            step_number = payload.get("step_number")
            await self.event_service.publish_event(
                db,
                session=session,
                event_type=event_type,
                payload=payload,
                step_number=step_number,
            )
        except Exception as e:
            logger.warning("Failed to publish agent event: %s", e)

    async def publish_step_failed(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep,
        error_msg: str,
    ) -> None:
        """Publish step failed event."""
        if not self.event_service:
            return
        try:
            await self.event_service.publish_event(
                db,
                session=session,
                event_type="execution.step.failed",
                payload={
                    "step_number": step.step_number,
                    "error": error_msg,
                },
                step_number=step.step_number,
            )
        except Exception as e:
            logger.warning("Failed to publish step.failed event: %s", e)
    
    async def publish_step_started(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ) -> None:
        """Publish step started event"""
        if not self.event_service:
            return
        
        try:
            await self.event_service.publish_event(
                db,
                session=session,
                event_type="execution.step.started",
                payload={
                    "command": step.command,
                    "step_number": step.step_number,
                    "step_type": step.step_type or "main",
                    "description": step.notes or "",
                },
                step_number=step.step_number,
            )
        except Exception as e:
            logger.warning(f"Failed to publish step.started event: {e}")
    
    async def publish_step_output(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep,
        output_text: str,
        error_text: str,
        connector_type: str,
        success: bool
    ) -> None:
        """
        Publish step output event (stdout for success, stderr for failure).
        
        Args:
            db: Database session
            session: Execution session
            step: Execution step
            output_text: Standard output text
            error_text: Error output text
            connector_type: Type of connector used
            success: Whether step succeeded
        """
        if not self.event_service:
            return
        
        try:
            if success:
                # Successful step - publish stdout output
                output_payload = {
                    "output": output_text or "",
                    "step_number": step.step_number,
                    "step_type": step.step_type or "main",
                    "connector_type": connector_type,
                }
                stream_id = await self.event_service.publish_event(
                    db,
                    session=session,
                    event_type="execution.step.output",
                    payload=output_payload,
                    step_number=step.step_number,
                )
                logger.info(
                    f"✅ Published execution.step.output event for step {step.step_number} "
                    f"(stream_id={stream_id}), output length: {len(output_text) if output_text else 0}"
                )
                
                if not output_text:
                    logger.warning(
                        f"⚠️ Step {step.step_number} output is EMPTY! "
                        f"Command: {step.command}"
                    )
            else:
                # Failed step - publish error output (stderr)
                if error_text:
                    error_payload = {
                        "output": error_text,
                        "step_number": step.step_number,
                        "step_type": step.step_type or "main",
                        "connector_type": connector_type,
                        "is_error": True,
                    }
                    stream_id = await self.event_service.publish_event(
                        db,
                        session=session,
                        event_type="execution.step.output",
                        payload=error_payload,
                        step_number=step.step_number,
                    )
                    logger.info(
                        f"✅ Published execution.step.output (error) event for step {step.step_number} "
                        f"(stream_id={stream_id}), error length: {len(error_text)}"
                    )
                else:
                    logger.warning(f"⚠️ Step {step.step_number} failed but has no error text to publish")
        except Exception as e:
            logger.error(f"Failed to publish step output event: {e}")
    
    async def publish_step_completion(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep,
        output_text: str,
        error_text: str,
        success: bool,
        exit_code: int,
        execution_duration_ms: int
    ) -> None:
        """
        Publish step completion event (completed or failed).
        
        Args:
            db: Database session
            session: Execution session
            step: Execution step
            output_text: Standard output text
            error_text: Error output text
            success: Whether step succeeded
            exit_code: Command exit code
            execution_duration_ms: Execution duration in milliseconds
        """
        if not self.event_service:
            return
        
        try:
            event_type = "execution.step.completed" if success else "execution.step.failed"
            await self.event_service.publish_event(
                db,
                session=session,
                event_type=event_type,
                payload={
                    "command": step.command,
                    "output": output_text,
                    "error": error_text,
                    "success": success,
                    "exit_code": exit_code,
                    "duration_ms": execution_duration_ms,
                    "step_number": step.step_number,
                    "step_type": step.step_type or "main",
                    "description": step.notes or "",
                },
                step_number=step.step_number,
            )
            logger.info(f"Published {event_type} event for step {step.step_number}")
        except Exception as e:
            logger.error(f"Failed to publish step completion event: {e}")








