"""
Mixin: correction safety validation for StepExecutionService
"""
import re
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepExecutionValidatorMixin:
    """Correction safety validation for StepExecutionService."""

    def _validate_correction_safety(self, original_command: str, corrected_command: str, error_text: str) -> bool:
        """
        Validate that a correction is safe to apply.

        Rejects corrections that:
        1. Break valid PowerShell syntax
        2. Change valid counter paths to invalid ones
        3. Remove required parameters
        4. Are clearly wrong based on error context

        Args:
            original_command: Original command that failed
            corrected_command: Proposed correction
            error_text: Error message from original command

        Returns:
            True if correction is safe, False if it should be rejected
        """
        # Guardrail 1: Reject corrections that break valid PowerShell counter paths
        # Original: Get-Counter -Counter '\Processor(_Total)\% Processor Time'
        # Bad correction: Get-Counter -Counter \\Processor(_Total)\\PercentProcessorTime
        # The original is correct, correction is wrong
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
            # Check if correction breaks the counter path
            corrected_has_valid_counter = any(
                re.search(pattern, corrected_command, re.IGNORECASE)
                for pattern in valid_counter_patterns
            )

            # If original has valid counter but correction doesn't, reject
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
        # If original has -MaxSamples and correction removes it, reject
        if "-MaxSamples" in original_command and "-MaxSamples" not in corrected_command:
            logger.warning(
                f"REJECTED: Correction removes required -MaxSamples parameter. "
                f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
            )
            return False

        # Guardrail 3: Reject corrections that change -SampleInterval to -MaxSamplingRate incorrectly
        # -SampleInterval is valid, -MaxSamplingRate is different parameter
        if "-SampleInterval" in original_command and "-MaxSamplingRate" in corrected_command:
            # Only reject if the error wasn't about SampleInterval being wrong
            if "SampleInterval" not in error_text:
                logger.warning(
                    f"REJECTED: Correction changes -SampleInterval to -MaxSamplingRate without error context. "
                    f"Original: {original_command[:200]}, Corrected: {corrected_command[:200]}"
                )
                return False

        # Guardrail 4: Reject corrections that are clearly wrong based on error
        # If error says "is not recognized as the name", the correction shouldn't change valid syntax
        if "is not recognized as the name" in error_text.lower():
            # This usually means a typo or wrong command, not a syntax issue
            # If correction changes valid syntax, reject it
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

        # Correction passed all guardrails
        logger.debug(f"Correction passed safety validation: {original_command[:100]} → {corrected_command[:100]}")
        return True
