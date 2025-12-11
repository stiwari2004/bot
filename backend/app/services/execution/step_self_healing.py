"""
Handles self-healing logic for step execution (error detection, correction, retry)
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.command_error_detector import CommandErrorDetector, FailureType
from app.services.execution.command_corrector import CommandCorrector
from app.services.runbook.runbook_updater import RunbookUpdater
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepSelfHealing:
    """Handles self-healing logic for step execution"""
    
    def __init__(self):
        self.error_detector = CommandErrorDetector()
        self.command_corrector = CommandCorrector()
        self.runbook_updater = RunbookUpdater()
    
    def detect_failure_type(
        self,
        result: Dict[str, Any],
        error_text: str,
        exit_code: int
    ) -> FailureType:
        """
        Detect the type of failure.
        
        Args:
            result: Execution result dictionary
            error_text: Error output text
            exit_code: Command exit code
            
        Returns:
            FailureType enum value
        """
        return self.error_detector.detect_failure_type(
            result,
            error_text,
            exit_code
        )
    
    def get_retry_count(self, step: ExecutionStep) -> int:
        """
        Get current retry count for a step.
        
        Args:
            step: Execution step
            
        Returns:
            Current retry count
        """
        retry_count = 0
        if step.command_payload and isinstance(step.command_payload, dict):
            retry_count = step.command_payload.get("retry_count", 0)
        return retry_count
    
    def increment_retry_count(self, step: ExecutionStep) -> None:
        """
        Increment retry count for a step.
        
        Args:
            step: Execution step
        """
        if not step.command_payload:
            step.command_payload = {}
        if not isinstance(step.command_payload, dict):
            step.command_payload = {}
        
        step.command_payload["retry_count"] = self.get_retry_count(step) + 1
    
    def should_attempt_healing(
        self,
        failure_type: FailureType,
        retry_count: int,
        max_retries: int = 1
    ) -> bool:
        """
        Determine if self-healing should be attempted.
        
        Args:
            failure_type: Type of failure detected
            retry_count: Current retry count
            max_retries: Maximum retry attempts
            
        Returns:
            True if healing should be attempted
        """
        # Only attempt healing for command errors, not Azure conflicts, timeouts, or connection errors
        return failure_type == FailureType.COMMAND_ERROR and retry_count < max_retries
    
    async def attempt_command_correction(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep,
        error_text: str,
        result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Attempt to correct a failed command.
        
        Args:
            db: Database session
            session: Execution session
            step: Execution step
            error_text: Error output text
            result: Execution result dictionary
            
        Returns:
            Corrected command if correction was made, None otherwise
        """
        try:
            corrected_command = await self.command_corrector.correct_command(
                original_command=step.command,
                error_text=error_text,
                context={
                    "session_id": session.id,
                    "step_number": step.step_number,
                    "exit_code": result.get("exit_code", -1)
                }
            )
            
            if corrected_command and corrected_command != step.command:
                # Validate correction safety
                if self._validate_correction_safety(step.command, corrected_command, error_text):
                    logger.info(
                        f"Step {step.step_number}: Command correction applied. "
                        f"Original: {step.command[:100]}..., "
                        f"Corrected: {corrected_command[:100]}..."
                    )
                    
                    # Update runbook if correction is successful
                    try:
                        await self.runbook_updater.update_runbook_command(
                            db=db,
                            runbook_id=session.runbook_id,
                            step_number=step.step_number,
                            old_command=step.command,
                            new_command=corrected_command,
                            reason="Self-healing correction"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update runbook with correction: {e}")
                    
                    return corrected_command
                else:
                    logger.warning(
                        f"Step {step.step_number}: Correction rejected as unsafe. "
                        f"Original: {step.command[:100]}..., "
                        f"Corrected: {corrected_command[:100]}..."
                    )
            
            return None
        except Exception as e:
            logger.error(f"Error attempting command correction: {e}")
            return None
    
    def _validate_correction_safety(
        self,
        original_command: str,
        corrected_command: str,
        error_text: str
    ) -> bool:
        """
        Validate that a correction is safe to apply.
        
        Args:
            original_command: Original command that failed
            corrected_command: Proposed correction
            error_text: Error message from original command
            
        Returns:
            True if correction is safe, False if it should be rejected
        """
        import re
        
        # Guardrail 1: Reject corrections that break valid PowerShell counter paths
        valid_counter_patterns = [
            r"\\Processor\(_Total\)\\% Processor Time",
            r"\\Memory\\Available MBytes",
            r"\\PhysicalDisk\(_Total\)",
            r"\\LogicalDisk\([^)]+\)",
        ]
        
        original_has_valid_counter = any(
            re.search(pattern, original_command, re.IGNORECASE)
            for pattern in valid_counter_patterns
        )
        
        if original_has_valid_counter:
            corrected_has_valid_counter = any(
                re.search(pattern, corrected_command, re.IGNORECASE)
                for pattern in valid_counter_patterns
            )
            
            if not corrected_has_valid_counter:
                logger.warning(
                    f"REJECTED: Correction breaks valid counter path. "
                    f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False
            
            # Check for suspicious changes to counter paths
            if "PercentProcessorTime" in corrected_command and "% Processor Time" in original_command:
                logger.warning(
                    f"REJECTED: Correction changes valid '% Processor Time' to 'PercentProcessorTime'. "
                    f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False
            
            # Check for double backslashes (wrong escaping)
            if "\\\\Processor" in corrected_command and "\\Processor" in original_command:
                logger.warning(
                    f"REJECTED: Correction adds wrong escaping (double backslashes). "
                    f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False
        
        # Guardrail 2: Reject corrections that remove required parameters
        if "-MaxSamples" in original_command and "-MaxSamples" not in corrected_command:
            logger.warning(
                f"REJECTED: Correction removes required -MaxSamples parameter. "
                f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
            )
            return False
        
        # Guardrail 3: Reject corrections that change -SampleInterval to -MaxSamplingRate incorrectly
        if "-SampleInterval" in original_command and "-MaxSamplingRate" in corrected_command:
            if "SampleInterval" not in error_text:
                logger.warning(
                    f"REJECTED: Correction changes -SampleInterval to -MaxSamplingRate without error context. "
                    f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False
        
        # Guardrail 4: Reject corrections that are clearly wrong based on error
        if "is not recognized as the name" in error_text.lower():
            if original_has_valid_counter and not any(
                re.search(pattern, corrected_command, re.IGNORECASE)
                for pattern in valid_counter_patterns
            ):
                logger.warning(
                    f"REJECTED: Correction changes valid syntax when error suggests typo/name issue. "
                    f"Error: {error_text[:200]}, Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False
        
        # Guardrail 5: Reject corrections that are identical to original (no-op)
        if original_command.strip() == corrected_command.strip():
            logger.warning(f"REJECTED: Correction is identical to original command")
            return False
        
        return True








