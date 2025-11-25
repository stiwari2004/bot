"""
Step execution service - CLEAN REWRITE
Simple, minimal implementation for executing individual runbook steps
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.infrastructure import get_connector
from app.services.security import redact_sensitive_text
from app.core.logging import get_logger
from app.services.execution.command_validator import CommandValidator
from app.services.execution.command_error_detector import CommandErrorDetector, FailureType
from app.services.execution.command_corrector import CommandCorrector
from app.services.runbook.runbook_updater import RunbookUpdater

logger = get_logger(__name__)


class StepExecutionService:
    """Handles execution of individual steps"""
    
    def __init__(self, connection_service, rollback_service, ticket_status_service, resolution_verification_service, event_service=None):
        self.connection_service = connection_service
        self.rollback_service = rollback_service
        self.ticket_status_service = ticket_status_service
        self.resolution_verification_service = resolution_verification_service
        self.event_service = event_service
        
        # Initialize self-healing services
        self.command_validator = CommandValidator()
        self.error_detector = CommandErrorDetector()
        self.command_corrector = CommandCorrector()
        self.runbook_updater = RunbookUpdater()
    
    def _get_command_timeout(self, command: str) -> int:
        """Determine timeout based on command type"""
        if not command:
            return 120
        
        command_lower = command.lower().strip()
        
        # Very long-running commands (30 minutes)
        if any(cmd in command_lower for cmd in ['sfc /scannow', 'dism /online /cleanup-image /restorehealth', 'chkdsk /f', 'chkdsk /r']):
            return 1800
        
        # Long-running commands (10 minutes)
        if any(cmd in command_lower for cmd in ['repair-windowsimage', 'dism /online', 'windowsupdate']):
            return 600
        
        # Medium-running commands (5 minutes)
        if any(cmd in command_lower for cmd in ['defrag', 'get-eventlog', 'get-winevent', 'get-wmiobject']):
            return 300
        
        # Default timeout
        return 120
    
    def _determine_timeout_from_validation(self, validation_result: dict, command: str) -> int:
        """
        Determine timeout from validation result, falling back to pattern-based timeout.
        
        Args:
            validation_result: Result from command validation
            command: Original command
            
        Returns:
            Timeout in seconds
        """
        # Use validation-suggested timeout if available
        if validation_result and validation_result.get("suggested_timeout"):
            suggested = validation_result["suggested_timeout"]
            logger.debug(f"Using validation-suggested timeout: {suggested}s")
            return suggested
        
        # Fall back to pattern-based timeout
        return self._get_command_timeout(command)
    
    async def execute_step(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ):
        """Execute a single step"""
        logger.info(f"Executing step {step.step_number} for session {session.id}")
        
        # Update session status
        if session.status != "in_progress" and session.status != "waiting_approval":
            session.status = "in_progress"
        
        if not session.started_at:
            session.started_at = datetime.now(timezone.utc)
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get connection configuration
            connection_config = await self.connection_service.get_connection_config(db, session, step)
            connector_type = connection_config.get("connector_type", "local")
            
            # Get connector
            connector = get_connector(connector_type)
            
            # Publish step started event
            if self.event_service:
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
            
            # Pre-execution validation
            validation_result = None
            original_command = step.command
            
            try:
                validation_result = await self.command_validator.validate_command(
                    command=step.command or "",
                    step_type=step.step_type or "main",
                    connector_type=connector_type,
                    connection_config=connection_config
                )
                
                if not validation_result.get("is_valid") and validation_result.get("corrected_command"):
                    # Command is invalid, correct it before execution
                    corrected_command = validation_result["corrected_command"]
                    logger.warning(
                        f"Pre-execution validation failed for step {step.step_number}: "
                        f"{validation_result.get('issues', [])}"
                    )
                    logger.info(
                        f"Correcting command: {original_command[:100] if original_command else 'N/A'} → "
                        f"{corrected_command[:100]}"
                    )
                    
                    # Update runbook in database
                    try:
                        await self.runbook_updater.update_runbook_step(
                            runbook_id=session.runbook_id,
                            step_number=step.step_number,
                            corrected_command=corrected_command,
                            db=db
                        )
                    except Exception as update_error:
                        logger.warning(f"Failed to update runbook in database: {update_error}, using in-memory correction")
                    
                    # Update step.command for execution
                    step.command = corrected_command
                    
                    # Publish validation event
                    if self.event_service:
                        try:
                            await self.event_service.publish_event(
                                db,
                                session=session,
                                event_type="execution.step.validated",
                                payload={
                                    "step_number": step.step_number,
                                    "original_command": original_command,
                                    "corrected_command": corrected_command,
                                    "issues": validation_result.get("issues", []),
                                    "validation_method": validation_result.get("validation_method", "unknown"),
                                },
                                step_number=step.step_number,
                            )
                            logger.info(f"Published execution.step.validated event for step {step.step_number}")
                        except Exception as e:
                            logger.warning(f"Failed to publish validation event: {e}")
            except Exception as validation_error:
                logger.warning(f"Pre-execution validation failed: {validation_error}, proceeding with original command")
                # Fail-safe: continue with original command if validation fails
            
            # Determine timeout (use validation result if available)
            timeout = self._determine_timeout_from_validation(validation_result, step.command or "") if validation_result else self._get_command_timeout(step.command or "")
            
            # Execute command
            logger.info(f"Executing command: {step.command[:100] if step.command else 'N/A'}...")
            result = await connector.execute_command(
                command=step.command,
                connection_config=connection_config,
                timeout=timeout,
            )
            
            # Calculate duration
            execution_duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Get raw output before redaction for logging
            raw_output = result.get("output", "")
            raw_error = result.get("error", "")
            
            logger.info(
                f"Step {step.step_number} execution result: success={result.get('success')}, "
                f"output_length={len(raw_output)}, error_length={len(raw_error)}, "
                f"output_preview={raw_output[:200] if raw_output else 'EMPTY'}..."
            )
            
            # Redact sensitive data
            output_text = redact_sensitive_text(raw_output)
            error_text = redact_sensitive_text(raw_error)
            
            # Log redaction results
            if raw_output and not output_text:
                logger.warning(
                    f"Step {step.step_number}: Output was redacted completely! "
                    f"Raw length: {len(raw_output)}, Redacted length: {len(output_text) if output_text else 0}"
                )
            
            # Log if output is empty (this shouldn't happen for successful commands)
            if result.get("success") and not output_text and not error_text:
                logger.warning(
                    f"Step {step.step_number} succeeded but has no output or error text. "
                    f"Raw result keys: {list(result.keys())}, "
                    f"Raw output type: {type(raw_output)}, Raw error type: {type(raw_error)}"
                )
            
            # Update step
            step.credentials_used = []
            credential_id = connection_config.get("credential_id")
            if credential_id:
                step.credentials_used = [credential_id]
            step.completed = True
            step.success = result["success"]
            step.output = output_text
            step.error = error_text
            step.completed_at = datetime.now(timezone.utc)
            
            # Commit step completion to database BEFORE publishing events
            # This ensures step state is persisted before we proceed
            db.commit()
            db.refresh(step)
            
            # Publish telemetry events (matching worker format)
            # IMPORTANT: Publish output event BEFORE completion event so frontend sees output first
            if self.event_service:
                try:
                    # ALWAYS publish output event for successful steps (even if empty)
                    # This ensures frontend shows the output card
                    # For failed steps, we publish error output separately
                    if result["success"]:
                        # Successful step - publish stdout output
                        # IMPORTANT: Always publish output, even if empty, so frontend shows the output card
                        output_payload = {
                            "output": output_text or "",  # Ensure it's always a string, never None
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
                            f"(stream_id={stream_id}), output length: {len(output_text) if output_text else 0}, "
                            f"output preview: {output_text[:300] if output_text else 'EMPTY'}..."
                        )
                        
                        # If output is empty, log a warning with full context
                        if not output_text:
                            logger.warning(
                                f"⚠️ Step {step.step_number} output is EMPTY! "
                                f"Command: {step.command}, "
                                f"Raw output length: {len(raw_output) if raw_output else 0}, "
                                f"Raw error length: {len(raw_error) if raw_error else 0}, "
                                f"Exit code: {result.get('exit_code', 'N/A')}"
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
                    
                    # Publish completion event
                    event_type = "execution.step.completed" if result["success"] else "execution.step.failed"
                    await self.event_service.publish_event(
                        db,
                        session=session,
                        event_type=event_type,
                        payload={
                            "command": step.command,
                            "output": output_text,  # Full output for telemetry
                            "error": error_text,    # Full error for telemetry
                            "success": result["success"],
                            "exit_code": result.get("exit_code", 0),
                            "duration_ms": execution_duration_ms,
                            "step_number": step.step_number,
                            "step_type": step.step_type or "main",
                            "description": step.notes or "",
                        },
                        step_number=step.step_number,
                    )
                    logger.info(f"Published {event_type} event for step {step.step_number}")
                    
                    # Commit events to database so they're immediately available
                    try:
                        db.commit()
                        logger.debug(f"Committed events to database for step {step.step_number}")
                    except Exception as commit_error:
                        logger.warning(f"Failed to commit events to database: {commit_error}")
                except Exception as e:
                    logger.error(f"Failed to publish step telemetry events: {e}", exc_info=True)
            
            # CRITICAL: For Azure connector, add delay to allow RunCommandExtension to clean up
            # This prevents "409 Conflict" errors when starting the next command
            if connector_type == "azure_bastion":
                cleanup_delay = 3  # 3 seconds for Azure to clean up RunCommandExtension processes
                logger.info(f"Waiting {cleanup_delay}s for Azure RunCommandExtension cleanup before next step...")
                await asyncio.sleep(cleanup_delay)
                logger.info(f"Cleanup delay complete, ready for next step")
            
            # Handle step result
            if not result["success"]:
                # Detect failure type for self-healing
                failure_type = self.error_detector.detect_failure_type(
                    result,
                    error_text,
                    result.get("exit_code", -1)
                )
                
                # Check retry count to prevent infinite loops
                # Store retry count in step's command_payload or notes metadata
                retry_count = 0
                if step.command_payload and isinstance(step.command_payload, dict):
                    retry_count = step.command_payload.get("retry_count", 0)
                max_retries = 1  # Allow 1 retry attempt per step
                
                # Attempt self-healing for command errors (not Azure conflicts, timeouts, or connection errors)
                if failure_type == FailureType.COMMAND_ERROR and retry_count < max_retries:
                    logger.info(
                        f"Step {step.step_number} failed with command error, attempting self-healing "
                        f"(retry {retry_count + 1}/{max_retries})"
                    )
                    
                    try:
                        # Attempt command correction (pass connector_type for OS detection and connection_config for server name)
                        correction_result = await self.command_corrector.correct_command(
                            command=step.command or "",
                            error_text=error_text,
                            step_type=step.step_type or "main",
                            connector_type=connector_type,
                            connection_config=connection_config
                        )
                        
                        if correction_result.get("corrected_command"):
                            corrected_command = correction_result["corrected_command"]
                            logger.info(
                                f"Self-healing correction found: {step.command[:100] if step.command else 'N/A'} → "
                                f"{corrected_command[:100]}"
                            )
                            
                            # Update runbook in database
                            try:
                                await self.runbook_updater.update_runbook_step(
                                    runbook_id=session.runbook_id,
                                    step_number=step.step_number,
                                    corrected_command=corrected_command,
                                    db=db
                                )
                            except Exception as update_error:
                                logger.warning(f"Failed to update runbook in database: {update_error}, using in-memory correction")
                            
                            # Update step.command
                            step.command = corrected_command
                            
                            # Update retry count
                            if not step.command_payload:
                                step.command_payload = {}
                            if not isinstance(step.command_payload, dict):
                                step.command_payload = {}
                            step.command_payload["retry_count"] = retry_count + 1
                            step.command_payload["correction_history"] = step.command_payload.get("correction_history", [])
                            step.command_payload["correction_history"].append({
                                "original_command": original_command,
                                "corrected_command": corrected_command,
                                "correction_method": correction_result.get("correction_method", "unknown"),
                                "error": error_text[:500] if error_text else "",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                            
                            # Perform Azure cleanup if needed (if connector is azure_bastion)
                            # This is a precautionary cleanup before reattempting corrected commands
                            if connector_type == "azure_bastion":
                                logger.info(f"Performing precautionary Azure cleanup before reattempting step {step.step_number}")
                                # Add a small delay to allow any pending operations to complete
                                await asyncio.sleep(2)
                                logger.info(f"Cleanup delay complete, ready for reattempt")
                            
                            # Publish correction event
                            if self.event_service:
                                try:
                                    await self.event_service.publish_event(
                                        db,
                                        session=session,
                                        event_type="execution.step.corrected",
                                        payload={
                                            "step_number": step.step_number,
                                            "original_command": original_command,
                                            "corrected_command": corrected_command,
                                            "correction_method": correction_result.get("correction_method", "unknown"),
                                            "error": error_text[:500] if error_text else "",
                                            "retry_count": retry_count + 1,
                                        },
                                        step_number=step.step_number,
                                    )
                                    logger.info(f"Published execution.step.corrected event for step {step.step_number}")
                                except Exception as e:
                                    logger.warning(f"Failed to publish correction event: {e}")
                            
                            # Reattempt with corrected command
                            logger.info(f"Reattempting step {step.step_number} with corrected command...")
                            db.commit()
                            db.refresh(step)
                            return await self.execute_step(db, session, step)  # Recursive retry
                        else:
                            logger.warning(f"Self-healing could not correct command for step {step.step_number}")
                    except Exception as correction_error:
                        logger.error(f"Self-healing correction failed: {correction_error}", exc_info=True)
                        # Continue with normal failure handling
                
                # Step failed - use type-based failure handling
                step.completed = True
                step.success = False
                step.error = error_text
                step.completed_at = datetime.now(timezone.utc)
                db.commit()
                
                # CRITICAL: Connection errors always stop execution (regardless of step type)
                # Connection errors indicate infrastructure issues that need immediate attention
                is_connection_error = result.get("connection_error", False)
                
                if is_connection_error:
                    # Connection error - always stop execution
                    logger.error(
                        f"Step {step.step_number} failed with connection error - stopping execution. "
                        f"Error: {(error_text or '')[:200]}"
                    )
                    session.status = "failed"
                    session.completed_at = datetime.now(timezone.utc)
                    await self.rollback_service.rollback_execution(db, session)
                    
                    if session.ticket_id:
                        self.ticket_status_service.update_ticket_on_execution_complete(
                            db, session.ticket_id, "failed", issue_resolved=False
                        )
                    
                    # Publish connection error event
                    if self.event_service:
                        try:
                            await self.event_service.publish_event(
                                db,
                                session=session,
                                event_type="execution.step.failed",
                                payload={
                                    "command": step.command,
                                    "error": error_text,
                                    "success": False,
                                    "exit_code": result.get("exit_code", -1),
                                    "duration_ms": execution_duration_ms,
                                    "step_number": step.step_number,
                                    "step_type": step.step_type or "main",
                                    "description": step.notes or "",
                                    "connection_error": True,
                                    "reason": "Connection error - execution stopped",
                                },
                                step_number=step.step_number,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish connection error event: {e}")
                    
                    db.commit()
                    return
                
                # Type-based failure handling for non-connection errors:
                # - precheck/postcheck: Continue execution (diagnostic/verification steps)
                # - main: Stop execution (critical steps)
                is_diagnostic = step.step_type in ("precheck", "postcheck")
                
                if is_diagnostic:
                    # Continue execution for diagnostic steps
                    logger.warning(
                        f"Step {step.step_number} ({step.step_type}) failed but continuing execution. "
                        f"Error: {(error_text or '')[:200]}"
                    )
                    
                    # Publish diagnostic failure event
                    if self.event_service:
                        try:
                            await self.event_service.publish_event(
                                db,
                                session=session,
                                event_type="execution.step.failed_continued",
                                payload={
                                    "command": step.command,
                                    "error": error_text,
                                    "success": False,
                                    "exit_code": result.get("exit_code", -1),
                                    "duration_ms": execution_duration_ms,
                                    "step_number": step.step_number,
                                    "step_type": step.step_type or "main",
                                    "description": step.notes or "",
                                    "reason": "Diagnostic step failure - continuing execution",
                                },
                                step_number=step.step_number,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish step.failed_continued event: {e}")
                    
                    # Continue to next step (same logic as success path)
                    next_step = db.query(ExecutionStep).filter(
                        ExecutionStep.session_id == session.id,
                        ExecutionStep.step_number == step.step_number + 1,
                        ExecutionStep.completed == False
                    ).first()
                    
                    if next_step:
                        if next_step.requires_approval:
                            session.status = "waiting_approval"
                            session.waiting_for_approval = True
                            session.approval_step_number = next_step.step_number
                            session.current_step = next_step.step_number
                            db.commit()
                            logger.info(f"Step {step.step_number} failed but continuing, waiting for approval on step {next_step.step_number}")
                        else:
                            db.commit()
                            db.refresh(session)
                            db.refresh(step)
                            logger.info(f"Step {step.step_number} failed but continuing, starting step {next_step.step_number}")
                            session.current_step = next_step.step_number
                            db.commit()
                            db.refresh(session)
                            await self.execute_step(db, session, next_step)
                    else:
                        # All steps completed (with some failures)
                        await self._finalize_session_with_errors(db, session)
                else:
                    # Stop execution for main steps (fail-fast for safety)
                    logger.error(
                        f"Step {step.step_number} (main) failed, stopping execution. "
                        f"Error: {(error_text or '')[:200]}"
                    )
                    session.status = "failed"
                    session.completed_at = datetime.now(timezone.utc)
                    await self.rollback_service.rollback_execution(db, session)
                    
                    if session.ticket_id:
                        self.ticket_status_service.update_ticket_on_execution_complete(
                            db, session.ticket_id, "failed", issue_resolved=False
                        )
            else:
                # Step succeeded - check for next step
                next_step = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session.id,
                    ExecutionStep.step_number == step.step_number + 1,
                    ExecutionStep.completed == False
                ).first()
                
                if next_step:
                    if next_step.requires_approval:
                        # Wait for approval
                        session.status = "waiting_approval"
                        session.waiting_for_approval = True
                        session.approval_step_number = next_step.step_number
                        session.current_step = next_step.step_number
                        db.commit()
                        logger.info(f"Step {step.step_number} completed, waiting for approval on step {next_step.step_number}")
                    else:
                        # CRITICAL: Ensure step is fully committed and cleaned up before starting next
                        # This prevents Azure RunCommandExtension conflicts
                        db.commit()
                        db.refresh(session)
                        db.refresh(step)
                        
                        # Verify step completed successfully before proceeding
                        if not step.completed:
                            logger.error(f"Step {step.step_number} marked as not completed, aborting next step")
                            session.status = "failed"
                            session.completed_at = datetime.now(timezone.utc)
                            db.commit()
                            return
                        
                        logger.info(f"Step {step.step_number} fully completed, starting step {next_step.step_number}")
                        session.current_step = next_step.step_number
                        db.commit()
                        db.refresh(session)
                        
                        # Check if we just finished all prechecks - analyze before proceeding to main steps
                        # This should trigger after ANY precheck completes, not just when transitioning to main
                        if step.step_type == "precheck":
                            all_prechecks_done = await self._check_all_prechecks_complete(db, session)
                            if all_prechecks_done:
                                logger.info(f"All precheck steps completed for session {session.id}, triggering precheck analysis")
                                
                                # Check if there's a next step - if not, we still need to analyze
                                if not next_step:
                                    logger.info(f"No next step after prechecks, analyzing prechecks now")
                                    # We'll handle this case below after the next_step check
                                # Analyze prechecks before proceeding
                                from app.services.precheck_analysis_service import get_precheck_analysis_service
                                from app.services.ticketing_integration_service import get_ticketing_integration_service
                                from app.models.ticket import Ticket
                                from app.models.runbook import Runbook
                                
                                precheck_service = get_precheck_analysis_service()
                                ticketing_service = get_ticketing_integration_service()
                                
                                if session.ticket_id:
                                    ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
                                    runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first() if session.runbook_id else None
                                    
                                    if ticket:
                                        analysis_result = await precheck_service.analyze_precheck_outputs(
                                            db=db,
                                            ticket=ticket,
                                            session=session,
                                            runbook=runbook
                                        )
                                        
                                        analysis_status = analysis_result.get("analysis_status", "success")
                                        is_false_positive = analysis_result.get("is_false_positive", False)
                                        confidence = analysis_result.get("confidence", 0.0)
                                        reasoning = analysis_result.get("reasoning", "")
                                        
                                        # Store analysis result
                                        ticket.precheck_analysis_result = analysis_result
                                        ticket.precheck_executed_at = datetime.now(timezone.utc)
                                        ticket.precheck_status = analysis_status
                                        
                                        # Handle different scenarios
                                        if analysis_status == "failed":
                                            # Precheck execution failed - mark for manual review
                                            ticket.status = "in_progress"
                                            ticket.escalation_reason = f"Precheck execution failed: {reasoning}"
                                            db.commit()
                                            await ticketing_service.mark_for_manual_review(
                                                db=db,
                                                ticket=ticket,
                                                reason=f"Precheck execution failed: {reasoning}"
                                            )
                                            session.status = "completed"
                                            session.completed_at = datetime.now(timezone.utc)
                                            db.commit()
                                            logger.info(f"Precheck execution failed, stopping: {reasoning}")
                                            return
                                        
                                        elif analysis_status == "ambiguous":
                                            # Ambiguous output - escalate
                                            ticket.status = "escalated"
                                            ticket.escalation_reason = f"Ambiguous precheck output: {reasoning}"
                                            db.commit()
                                            await ticketing_service.escalate_ticket(
                                                db=db,
                                                ticket=ticket,
                                                escalation_reason=f"Ambiguous precheck output: {reasoning}"
                                            )
                                            session.status = "completed"
                                            session.completed_at = datetime.now(timezone.utc)
                                            db.commit()
                                            logger.info(f"Ambiguous precheck output, escalating: {reasoning}")
                                            return
                                        
                                        elif is_false_positive and confidence >= 0.7:
                                            # False positive detected - close ticket
                                            ticket.status = "closed"
                                            ticket.classification = "false_positive"
                                            ticket.classification_confidence = "high" if confidence >= 0.8 else "medium"
                                            ticket.resolved_at = datetime.now(timezone.utc)
                                            db.commit()
                                            await ticketing_service.close_ticket(
                                                db=db,
                                                ticket=ticket,
                                                reason=f"False positive detected: {reasoning}"
                                            )
                                            session.status = "completed"
                                            session.completed_at = datetime.now(timezone.utc)
                                            db.commit()
                                            logger.info(f"False positive detected, closing ticket: {reasoning}")
                                            return
                                        else:
                                            # True positive - proceed
                                            ticket.status = "in_progress"
                                            ticket.classification = "true_positive" if not is_false_positive else "uncertain"
                                            db.commit()
                                            logger.info(f"Precheck analysis: proceeding with main steps - {reasoning}")
                        
                        # Execute next step
                        await self.execute_step(db, session, next_step)
                else:
                    # No next step - check if we just finished all prechecks
                    if step.step_type == "precheck":
                        all_prechecks_done = await self._check_all_prechecks_complete(db, session)
                        if all_prechecks_done:
                            logger.info(f"All precheck steps completed (no main steps), triggering precheck analysis")
                            # Trigger precheck analysis even if no main steps exist
                            from app.services.precheck_analysis_service import get_precheck_analysis_service
                            from app.services.ticketing_integration_service import get_ticketing_integration_service
                            from app.models.ticket import Ticket
                            from app.models.runbook import Runbook
                            
                            precheck_service = get_precheck_analysis_service()
                            ticketing_service = get_ticketing_integration_service()
                            
                            if session.ticket_id:
                                ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
                                runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first() if session.runbook_id else None
                                
                                if ticket:
                                    analysis_result = await precheck_service.analyze_precheck_outputs(
                                        db=db,
                                        ticket=ticket,
                                        session=session,
                                        runbook=runbook
                                    )
                                    
                                    analysis_status = analysis_result.get("analysis_status", "success")
                                    is_false_positive = analysis_result.get("is_false_positive", False)
                                    confidence = analysis_result.get("confidence", 0.0)
                                    reasoning = analysis_result.get("reasoning", "")
                                    
                                    # Store analysis result
                                    ticket.precheck_analysis_result = analysis_result
                                    ticket.precheck_executed_at = datetime.now(timezone.utc)
                                    ticket.precheck_status = analysis_status
                                    
                                    # Handle different scenarios
                                    if analysis_status == "failed":
                                        ticket.status = "in_progress"
                                        ticket.escalation_reason = f"Precheck execution failed: {reasoning}"
                                        db.commit()
                                        await ticketing_service.mark_for_manual_review(
                                            db=db,
                                            ticket=ticket,
                                            reason=f"Precheck execution failed: {reasoning}"
                                        )
                                        session.status = "completed"
                                        session.completed_at = datetime.now(timezone.utc)
                                        db.commit()
                                        logger.info(f"Precheck execution failed, stopping: {reasoning}")
                                        return
                                    
                                    elif analysis_status == "ambiguous":
                                        ticket.status = "escalated"
                                        ticket.escalation_reason = f"Ambiguous precheck output: {reasoning}"
                                        db.commit()
                                        await ticketing_service.escalate_ticket(
                                            db=db,
                                            ticket=ticket,
                                            escalation_reason=f"Ambiguous precheck output: {reasoning}"
                                        )
                                        session.status = "completed"
                                        session.completed_at = datetime.now(timezone.utc)
                                        db.commit()
                                        logger.info(f"Ambiguous precheck output, escalating: {reasoning}")
                                        return
                                    
                                    elif is_false_positive and confidence >= 0.7:
                                        ticket.status = "closed"
                                        ticket.classification = "false_positive"
                                        ticket.classification_confidence = "high" if confidence >= 0.8 else "medium"
                                        ticket.resolved_at = datetime.now(timezone.utc)
                                        db.commit()
                                        await ticketing_service.close_ticket(
                                            db=db,
                                            ticket=ticket,
                                            reason=f"False positive detected: {reasoning}"
                                        )
                                        session.status = "completed"
                                        session.completed_at = datetime.now(timezone.utc)
                                        db.commit()
                                        logger.info(f"False positive detected, closing ticket: {reasoning}")
                                        return
                                    else:
                                        ticket.status = "in_progress"
                                        ticket.classification = "true_positive" if not is_false_positive else "uncertain"
                                        db.commit()
                                        logger.info(f"Precheck analysis complete (no main steps): {reasoning}")
                    
                    # All steps completed - check for failures
                    await self._finalize_session(db, session)
        
        except Exception as e:
            logger.error(f"Error executing step {step.step_number}: {e}", exc_info=True)
            error_text = redact_sensitive_text(str(e))
            step.completed = True
            step.success = False
            step.error = error_text
            step.completed_at = datetime.now(timezone.utc)
            session.status = "failed"
            session.completed_at = datetime.now(timezone.utc)
            
            # Publish step failed event
            if self.event_service:
                try:
                    execution_duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    await self.event_service.publish_event(
                        db,
                        session=session,
                        event_type="execution.step.failed",
                        payload={
                            "command": step.command,
                            "error": error_text,
                            "success": False,
                            "exit_code": -1,
                            "duration_ms": execution_duration_ms,
                            "step_number": step.step_number,
                            "step_type": step.step_type or "main",
                        },
                        step_number=step.step_number,
                    )
                except Exception as event_error:
                    logger.warning(f"Failed to publish step.failed event: {event_error}")
            
            # Rollback and update ticket
            await self.rollback_service.rollback_execution(db, session)
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, session.ticket_id, "failed", issue_resolved=False
                )
        
        db.commit()
        logger.info(f"Completed execution of step {step.step_number} for session {session.id}")
    
    async def _finalize_session(self, db: Session, session: ExecutionSession):
        """Finalize session when all steps complete - check for failures"""
        # Get all failed steps
        failed_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.completed == True,
            ExecutionStep.success == False
        ).all()
        
        failed_step_numbers = [s.step_number for s in failed_steps]
        
        # Determine final status
        if not failed_steps:
            # All steps succeeded
            session.status = "completed"
            logger.info(f"Session {session.id} completed successfully - all steps passed")
        else:
            # Some steps failed - check if only diagnostic steps failed
            failed_main_steps = [s for s in failed_steps if s.step_type == "main"]
            
            if failed_main_steps:
                # Critical main step failed - should have been caught earlier, but handle gracefully
                session.status = "failed"
                logger.error(
                    f"Session {session.id} failed - main steps failed: {[s.step_number for s in failed_main_steps]}"
                )
            else:
                # Only diagnostic steps (precheck/postcheck) failed
                session.status = "completed_with_errors"
                logger.warning(
                    f"Session {session.id} completed with errors - diagnostic steps failed: {failed_step_numbers}"
                )
        
        session.completed_at = datetime.now(timezone.utc)
        
        # Calculate duration
        if session.started_at:
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            completed = session.completed_at
            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            duration = (completed - started).total_seconds() / 60
            session.total_duration_minutes = int(duration)
        
        # Publish session completion event
        if self.event_service:
            try:
                event_payload = {
                    "status": session.status,
                    "total_steps": session.total_steps,
                    "failed_steps": failed_step_numbers,
                    "duration_minutes": session.total_duration_minutes,
                }
                if failed_steps:
                    event_payload["failure_summary"] = [
                        {
                            "step_number": s.step_number,
                            "step_type": s.step_type,
                            "error": s.error[:200] if s.error else "Unknown error",
                        }
                        for s in failed_steps
                    ]
                
                await self.event_service.publish_event(
                    db,
                    session=session,
                    event_type="execution.session.completed",
                    payload=event_payload,
                )
            except Exception as e:
                logger.warning(f"Failed to publish session.completed event: {e}")
        
        # Verify resolution
        if session.ticket_id:
            issue_resolved = session.status == "completed"  # Only fully resolved if no errors
            verification_result = await self.resolution_verification_service.verify_resolution(
                db, session.id, session.ticket_id
            )
            logger.info(f"Resolution verification: resolved={verification_result['resolved']}")
            
            self.ticket_status_service.update_ticket_on_execution_complete(
                db, session.ticket_id, session.status, issue_resolved=issue_resolved
            )
        
        db.commit()
    
    async def _finalize_session_with_errors(self, db: Session, session: ExecutionSession):
        """Finalize session when all steps complete but some diagnostic steps failed"""
        # This is called when diagnostic steps failed but we continued
        # Final status will be "completed_with_errors"
        await self._finalize_session(db, session)
    
    async def _check_all_prechecks_complete(self, db: Session, session: ExecutionSession) -> bool:
        """
        Check if all precheck steps are complete
        
        Args:
            db: Database session
            session: Execution session
            
        Returns:
            True if all prechecks are complete, False otherwise
        """
        precheck_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.step_type == "precheck"
        ).all()
        
        if not precheck_steps:
            return False  # No prechecks defined
        
        # Check if all prechecks are completed
        all_complete = all(step.completed for step in precheck_steps)
        return all_complete
