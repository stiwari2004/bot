"""
Step execution service - CLEAN REWRITE
Simple, minimal implementation for executing individual runbook steps
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.infrastructure import get_connector
from app.services.security import redact_sensitive_text
from app.core.logging import get_logger
from app.services.execution.command_validator import CommandValidator
from app.services.execution.command_error_detector import CommandErrorDetector, FailureType
from app.services.execution.command_corrector import CommandCorrector
from app.services.runbook.runbook_updater import RunbookUpdater
from app.services.execution.step_timeout_manager import StepTimeoutManager
from app.services.execution.step_event_publisher import StepEventPublisher
from app.services.execution.step_self_healing import StepSelfHealing
from app.services.execution.step_precheck_handler import StepPrecheckHandler
from app.services.execution.step_session_finalizer import StepSessionFinalizer
from app.services.ticket_step_tracker import get_ticket_step_tracker
from app.services.execution.ssh_command_utils import strip_ssh_wrapper
from app.services.execution.command_learning_service import CommandLearningService
from app.services.execution.output_extractor import get_output_extractor, OutputExtractor
from app.services.execution.step_execution_utils import (
    _RESOLVED_INPUTS_KEY,
    _get_resolved_inputs,
    _save_resolved_inputs,
    _find_needed_vars,
    _is_command_not_found_or_wrong_shell,
    _get_next_step_with_branching,
)
from app.services.execution.step_execution_validator_mixin import StepExecutionValidatorMixin

logger = get_logger(__name__)


class StepExecutionService(StepExecutionValidatorMixin):
    """Handles execution of individual steps"""
    
    def __init__(self, connection_service, rollback_service, ticket_status_service, resolution_verification_service, event_service=None):
        self.connection_service = connection_service
        self.rollback_service = rollback_service
        self.ticket_status_service = ticket_status_service
        self.resolution_verification_service = resolution_verification_service
        self.event_service = event_service
        
        # Initialize specialized services
        self.command_validator = CommandValidator()
        self.timeout_manager = StepTimeoutManager()
        self.event_publisher = StepEventPublisher(event_service)
        self.self_healing = StepSelfHealing()
        self.precheck_handler = StepPrecheckHandler()
        self.command_learning = CommandLearningService()
        self.session_finalizer = StepSessionFinalizer(
            event_service,
            ticket_status_service,
            resolution_verification_service,
            connection_service
        )
    
    # Timeout management methods removed - now handled by StepTimeoutManager
    
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
            # This will raise ValueError if node is not in InfrastructureConnection
            try:
                connection_config = await self.connection_service.get_connection_config(db, session, step)
            except ValueError as ve:
                # Node not found - fail the step with clear error message
                error_msg = str(ve)
                logger.warning(f"Step {step.step_number}: {error_msg}")
                step.completed = True
                step.success = False
                step.output = ""
                step.error = error_msg
                step.completed_at = datetime.now(timezone.utc)
                session.status = "failed"
                db.commit()
                
                # Publish step failed event
                await self.event_publisher.publish_step_failed(
                    db, session, step, error_msg
                )
                return  # Stop execution
            
            connector_type = connection_config.get("connector_type", "local")
            
            # Get connector
            connector = get_connector(connector_type)
            
            # Publish step started event
            await self.event_publisher.publish_step_started(db, session, step)
            
            # Pre-execution validation - ONLY rule-based (fast, safe), NO Perplexity (can produce wrong corrections)
            # We'll let the command execute first, then correct if it fails
            original_command = step.command
            
            try:
                # Only use rule-based validation (fast, safe patterns like SampleInterval fix)
                # Skip Perplexity validation to avoid wrong corrections before execution
                from app.services.execution.command_rules import validate_command_with_rules
                rule_result = validate_command_with_rules(
                    step.command or "",
                    connector_type,
                    connection_config
                )
                
                # Only apply rule-based corrections (known safe patterns)
                if not rule_result.get("is_valid") and rule_result.get("corrected_command"):
                    corrected_command = rule_result["corrected_command"]
                    logger.info(
                        f"Step {step.step_number}: Rule-based pre-validation found safe correction: "
                        f"{original_command[:100] if original_command else 'N/A'} → {corrected_command[:100]}"
                    )
                    
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
                                    "validation_method": "rule",
                                    "issues": rule_result.get("issues", []),
                                },
                                step_number=step.step_number,
                            )
                            logger.info(f"Published execution.step.validated event for step {step.step_number}")
                        except Exception as e:
                            logger.warning(f"Failed to publish validation event: {e}")
            except Exception as validation_error:
                logger.warning(f"Pre-execution validation failed: {validation_error}, proceeding with original command")
                # Fail-safe: continue with original command if validation fails
            
            # Determine timeout (use rule result if available, otherwise default)
            rule_result_local = rule_result if 'rule_result' in locals() else None
            timeout = self.timeout_manager.determine_timeout(rule_result_local, step.command or "")
            
            # Backup network device config before making changes (if this is a network device)
            if connector_type == "network_device":
                backup_config = await self.rollback_service.backup_network_device_config(
                    db, session, step, connection_config
                )
                if backup_config:
                    logger.info(f"Backed up network device config before step {step.step_number}")
            
            # ----------------------------------------------------------------
            # OUTPUT-DRIVEN VARIABLE RESOLUTION
            # Load accumulated resolved inputs from previous steps and
            # substitute any {{variable}} placeholders before executing.
            # ----------------------------------------------------------------
            extractor = get_output_extractor()
            resolved_inputs = _get_resolved_inputs(session)

            # Apply smart defaults for any vars still unresolved (last resort)
            needed_now = extractor.find_unresolved(step.command or "")
            still_missing = [v for v in needed_now if v not in resolved_inputs]
            if still_missing:
                defaults = extractor.apply_smart_defaults(still_missing)
                if defaults:
                    resolved_inputs.update(defaults)
                    _save_resolved_inputs(session, resolved_inputs, db)
                    logger.info(
                        "Step %s: applied smart defaults for %s",
                        step.step_number, list(defaults.keys())
                    )

            # Execute command (SSH connector: strip "ssh host ..." wrapper - connector handles connection)
            command_to_run = step.command or ""

            # Substitute resolved values into command
            if resolved_inputs:
                command_to_run = extractor.substitute(command_to_run, resolved_inputs)
                unresolved_remaining = extractor.find_unresolved(command_to_run)
                if unresolved_remaining:
                    logger.warning(
                        "Step %s: still-unresolved placeholders after substitution: %s — "
                        "will be resolved from step output as execution proceeds.",
                        step.step_number, unresolved_remaining
                    )
                elif needed_now:
                    logger.info(
                        "Step %s: resolved %s from session context → command: %s",
                        step.step_number, needed_now, command_to_run[:120]
                    )

            if connector_type == "ssh":
                stripped = strip_ssh_wrapper(command_to_run)
                if stripped != command_to_run:
                    logger.info(f"Step {step.step_number}: Stripped ssh wrapper for SSH connector, running: {stripped[:80]}...")
                    command_to_run = stripped
            logger.info(f"Executing command: {command_to_run[:100] if command_to_run else 'N/A'}...")
            result = await connector.execute_command(
                command=command_to_run,
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
            
            # ----------------------------------------------------------------
            # POST-EXECUTION: extract values from this step's output for
            # use in subsequent steps (output-driven variable resolution).
            # ----------------------------------------------------------------
            if result.get("success") and raw_output:
                try:
                    needed_by_future = _find_needed_vars(db, session, step.step_number + 1)
                    if needed_by_future:
                        newly_extracted = extractor.extract_from_output(
                            command=step.command or "",
                            output=raw_output,
                            needed_vars=needed_by_future,
                        )
                        if newly_extracted:
                            current_resolved = _get_resolved_inputs(session)
                            current_resolved.update(newly_extracted)
                            _save_resolved_inputs(session, current_resolved, db)
                            logger.info(
                                "Step %s: extracted %s from output → cached for future steps",
                                step.step_number,
                                {k: v[:40] if len(str(v)) > 40 else v for k, v in newly_extracted.items()},
                            )
                except Exception as extract_err:
                    logger.debug("Non-critical: output extraction failed: %s", extract_err)

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

            # Learning loop: save successful remediation commands as known-good patterns
            try:
                if result["success"]:
                    step_purpose = (step.command_payload or {}).get("purpose", "")
                    step_type_val = step.step_type or ""
                    # Save if this is a remediation step (main step with remediate purpose)
                    if step_purpose == "remediate" or (step_type_val == "main" and not step_purpose):
                        issue_desc = session.meta_data.get("issue_description", "") if isinstance(session.meta_data, dict) else ""
                        connector_type_for_learning = connector_type
                        self.command_learning.save_success(
                            db=db,
                            tenant_id=session.tenant_id,
                            command=step.command or "",
                            output_text=output_text,
                            connector_type=connector_type_for_learning,
                            session_id=session.id,
                            runbook_id=session.runbook_id,
                            step_number=step.step_number,
                            step_type=step_type_val,
                            issue_description=issue_desc,
                        )
            except Exception as learning_err:
                logger.debug(f"Non-critical: failed to save step success to learning: {learning_err}")

            # Track step in ticket metadata and external systems
            if session.ticket_id:
                try:
                    step_tracker = get_ticket_step_tracker()
                    # Track in ticket metadata (synchronous, uses current db session)
                    step_tracker.track_step_in_ticket(
                        db=db,
                        ticket_id=session.ticket_id,
                        step=step,
                        connector_type=connector_type
                    )
                    # Add comment to external ticketing system (async, don't block)
                    # Create background task with new db session
                    async def add_external_comment():
                        from app.core.database import SessionLocal
                        background_db = SessionLocal()
                        try:
                            await step_tracker.add_step_comment_to_external_ticket(
                                db=background_db,
                                ticket_id=session.ticket_id,
                                step=step,
                                connector_type=connector_type
                            )
                        except Exception as e:
                            logger.warning(f"Failed to add external comment: {e}", exc_info=True)
                        finally:
                            background_db.close()
                    
                    # Schedule background task (fire and forget)
                    asyncio.create_task(add_external_comment())
                except Exception as e:
                    logger.warning(f"Failed to track step in ticket: {e}", exc_info=True)
                    # Don't fail step execution if tracking fails
            
            # Publish telemetry events (matching worker format)
            # IMPORTANT: Publish output event BEFORE completion event so frontend sees output first
            await self.event_publisher.publish_step_output(
                db, session, step, output_text, error_text, connector_type, result["success"]
            )
            
            # Check conditional logic for next action (rollback/escalate)
            try:
                from app.services.decision import ConditionalLogicService
                conditional_logic = ConditionalLogicService()
                # Get step output as string
                step_output_text = step.output if isinstance(step.output, str) else str(step.output) if step.output else None
                next_action = await conditional_logic.decide_next_action(
                    session, step_output_text, db
                )
                
                if next_action.get("action") == "rollback":
                    logger.warning(
                        f"Conditional logic triggered rollback for session {session.id}: "
                        f"{next_action.get('reason')}"
                    )
                    # Trigger rollback
                    if step.rollback_command:
                        try:
                            await self.rollback_service.rollback_step(
                                db, session, step
                            )
                        except Exception as rollback_error:
                            logger.error(f"Rollback failed: {rollback_error}")
                
                elif next_action.get("action") == "escalate":
                    logger.warning(
                        f"Conditional logic triggered escalation for session {session.id}: "
                        f"{next_action.get('reason')}"
                    )
                    session.status = "escalated"
                    if session.ticket_id:
                        from app.models.ticket import Ticket
                        ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
                        if ticket:
                            ticket.status = "escalated"
                            ticket.escalation_reason = next_action.get("reason", "Multiple failures detected")
                            db.commit()
            except Exception as e:
                logger.warning(f"Error in conditional logic check: {e}")
                # Don't fail execution if conditional logic fails
            
            # Publish completion event
            await self.event_publisher.publish_step_completion(
                db, session, step, output_text, error_text,
                result["success"], result.get("exit_code", 0), execution_duration_ms
            )
            
            # Commit events to database so they're immediately available
            try:
                db.commit()
                logger.debug(f"Committed events to database for step {step.step_number}")
            except Exception as commit_error:
                logger.warning(f"Failed to commit events to database: {commit_error}")
            
            # Note: Sequential execution is already ensured by the flow (next step only starts after previous completes)
            # No delay needed - commands execute immediately after previous completes
            if connector_type == "azure_bastion":
                # Minimal delay only if we detect a conflict (handled in azure_connector)
                logger.debug(f"Step {step.step_number} completed, proceeding to next step immediately")
            
            # Handle step result
            if not result["success"]:
                # Detect failure type for self-healing
                failure_type = self.self_healing.detect_failure_type(
                    result,
                    error_text,
                    result.get("exit_code", -1)
                )
                
                # Check retry count to prevent infinite loops
                retry_count = self.self_healing.get_retry_count(step)
                max_retries = 1  # Allow 1 retry attempt per step
                
                # Attempt self-healing for command errors (not Azure conflicts, timeouts, or connection errors)
                if self.self_healing.should_attempt_healing(failure_type, retry_count, max_retries):
                    logger.info(
                        f"Step {step.step_number} failed with command error, attempting self-healing "
                        f"(retry {retry_count + 1}/{max_retries})"
                    )
                    
                    try:
                        # Save failure to DB for iterative refinement (no hardcoded rules)
                        learning_id = self.command_learning.save_failure(
                            db=db,
                            tenant_id=session.tenant_id,
                            command=step.command or "",
                            error_text=error_text,
                            output_text=step.output,
                            connector_type=connector_type,
                            session_id=session.id,
                            runbook_id=session.runbook_id,
                            step_number=step.step_number,
                            step_type=step.step_type,
                            connection_config=connection_config,
                            issue_description=session.issue_description,
                        )
                        # Attempt command correction (DB first, then Perplexity - OS-aware, no hardcoded rules)
                        correction_result = await self.command_corrector.correct_command(
                            command=step.command or "",
                            error_text=error_text,
                            step_type=step.step_type or "main",
                            connector_type=connector_type,
                            connection_config=connection_config,
                            db=db,
                            tenant_id=session.tenant_id,
                        )
                        
                        if correction_result.get("corrected_command"):
                            corrected_command = correction_result["corrected_command"]
                            
                            # GUARDRAIL: Validate correction before applying
                            if not self._validate_correction_safety(original_command, corrected_command, error_text):
                                logger.warning(
                                    f"Step {step.step_number}: REJECTED unsafe correction. "
                                    f"Original: {original_command[:200] if original_command else 'N/A'}\n"
                                    f"Corrected: {corrected_command[:200]}\n"
                                    f"Error: {error_text[:200] if error_text else 'N/A'}"
                                )
                                # Don't apply correction - mark step as failed
                                step.completed = True
                                step.success = False
                                step.error = f"Command failed and correction was rejected as unsafe. Original error: {error_text[:500] if error_text else 'Unknown error'}"
                                step.completed_at = datetime.now(timezone.utc)
                                db.commit()
                                return  # Exit without retry
                            
                            logger.info(
                                f"Self-healing correction validated: {step.command[:100] if step.command else 'N/A'} → "
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
                            
                            # Note: Cleanup is only done after postcheck completes, not before each step or retry
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
                            
                            # Reattempt with corrected command (this will verify it works)
                            logger.info(f"Reattempting step {step.step_number} with corrected command to verify it works...")
                            db.commit()
                            db.refresh(step)
                            await self.execute_step(db, session, step)  # Recursive retry - verify correction
                            db.refresh(step)
                            # Update our learning record with success_after_fix when retry succeeds
                            if learning_id and step.success and corrected_command:
                                self.command_learning.update_with_fix(
                                    db, learning_id, corrected_command,
                                    correction_result.get("correction_method", "perplexity"),
                                    True,
                                )
                            return
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
                db.refresh(step)
                
                # Track failed step in ticket metadata and external systems
                if session.ticket_id:
                    try:
                        step_tracker = get_ticket_step_tracker()
                        # Track in ticket metadata (synchronous, uses current db session)
                        step_tracker.track_step_in_ticket(
                            db=db,
                            ticket_id=session.ticket_id,
                            step=step,
                            connector_type=connector_type
                        )
                        # Add comment to external ticketing system (async, don't block)
                        # Create background task with new db session
                        async def add_external_comment():
                            from app.core.database import SessionLocal
                            background_db = SessionLocal()
                            try:
                                await step_tracker.add_step_comment_to_external_ticket(
                                    db=background_db,
                                    ticket_id=session.ticket_id,
                                    step=step,
                                    connector_type=connector_type
                                )
                            except Exception as e:
                                logger.warning(f"Failed to add external comment for failed step: {e}", exc_info=True)
                            finally:
                                background_db.close()
                        
                        # Schedule background task (fire and forget)
                        asyncio.create_task(add_external_comment())
                    except Exception as e:
                        logger.warning(f"Failed to track failed step in ticket: {e}", exc_info=True)
                        # Don't fail step execution if tracking fails
                
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
                # - main: Stop execution (critical steps), unless failure is "command not found"
                #   / wrong shell — then continue (failure is inconclusive, not a real server failure)
                is_diagnostic = step.step_type in ("precheck", "postcheck")
                is_command_not_found = _is_command_not_found_or_wrong_shell(error_text)
                continue_on_failure = is_diagnostic or (
                    not is_diagnostic and is_command_not_found
                )

                if continue_on_failure:
                    reason = (
                        "Diagnostic step failure - continuing execution"
                        if is_diagnostic
                        else "Command not found / wrong shell - continuing execution (inconclusive)"
                    )
                    logger.warning(
                        f"Step {step.step_number} ({step.step_type or 'main'}) failed but continuing execution. "
                        f"{reason} Error: {(error_text or '')[:200]}"
                    )

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
                                    "reason": reason,
                                },
                                step_number=step.step_number,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish step.failed_continued event: {e}")

                    next_step = _get_next_step_with_branching(
                        db, session, step, step_succeeded=False
                    )

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
                        failed_steps = db.query(ExecutionStep).filter(
                            ExecutionStep.session_id == session.id,
                            ExecutionStep.completed == True,
                            ExecutionStep.success == False
                        ).all()
                        await self.session_finalizer.finalize_session(db, session, failed_steps)
                else:
                    # Stop execution for main steps (real failure, not command-not-found)
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
                # Step succeeded - check for next step (with branching support)
                next_step = _get_next_step_with_branching(
                    db, session, step, step_succeeded=True
                )
                
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
                            all_prechecks_done = await self.precheck_handler.check_all_prechecks_complete(db, session)
                            if all_prechecks_done:
                                logger.info(f"All precheck steps completed for session {session.id}, triggering precheck analysis")
                                
                                # Analyze prechecks before proceeding
                                result = await self.precheck_handler.analyze_and_handle_prechecks(db, session)
                                if result == "stop":
                                    return  # Execution stopped (failed, ambiguous, or false positive)
                        
                        # Execute next step
                        await self.execute_step(db, session, next_step)
                else:
                    # No next step - check if we just finished all prechecks
                    if step.step_type == "precheck":
                        all_prechecks_done = await self.precheck_handler.check_all_prechecks_complete(db, session)
                        if all_prechecks_done:
                            logger.info(f"All precheck steps completed (no main steps), triggering precheck analysis")
                            result = await self.precheck_handler.analyze_and_handle_prechecks(db, session)
                            if result == "stop":
                                return  # Execution stopped
                    
                    # All steps completed - check for failures
                    failed_steps = db.query(ExecutionStep).filter(
                        ExecutionStep.session_id == session.id,
                        ExecutionStep.completed == True,
                        ExecutionStep.success == False
                    ).all()
                    await self.session_finalizer.finalize_session(db, session, failed_steps)
        
        except Exception as e:
            logger.error(f"Error executing step {step.step_number}: {e}", exc_info=True)
            error_text = redact_sensitive_text(str(e))
            step.completed = True
            step.success = False
            step.error = error_text
            step.completed_at = datetime.now(timezone.utc)
            session.status = "failed"
            session.completed_at = datetime.now(timezone.utc)
            
            # Track failure for quarantine
            try:
                if not session.runbook_id:
                    raise ValueError("session has no runbook_id, skipping quarantine")

                from app.services.execution.quarantine_service import QuarantineService
                from app.services.runbook.versioning_service import VersioningService

                quarantine_service = QuarantineService()
                versioning_service = VersioningService()

                # Get current runbook version
                runbook_version_id = None
                current_version = versioning_service.get_current_version(
                    db=db,
                    runbook_id=session.runbook_id,
                    tenant_id=session.tenant_id
                )
                if current_version:
                    runbook_version_id = current_version.id
                
                error_details = {
                    "error": error_text[:500],
                    "step_number": step.step_number,
                    "error_type": "execution_failure"
                }
                
                quarantine_service.track_failure(
                    db=db,
                    runbook_id=session.runbook_id,
                    runbook_version_id=runbook_version_id,
                    session_id=session.id,
                    error_details=error_details,
                    tenant_id=session.tenant_id
                )
            except Exception as quarantine_error:
                logger.warning(f"Failed to track failure for quarantine: {quarantine_error}")
            
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
    
    # Session finalization methods removed - now handled by StepSessionFinalizer
    # Precheck handling methods removed - now handled by StepPrecheckHandler
    # Correction safety validation - now provided by StepExecutionValidatorMixin
