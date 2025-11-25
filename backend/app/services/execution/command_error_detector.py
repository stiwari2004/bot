"""
Command error detector service for post-execution failure classification.
Distinguishes between command syntax errors, Azure conflicts, timeouts, and connection errors.
"""
from enum import Enum
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class FailureType(Enum):
    """Types of execution failures"""
    COMMAND_ERROR = "command_error"  # Syntax/parameter issues
    AZURE_CONFLICT = "azure_conflict"  # 409 Conflict
    TIMEOUT = "timeout"  # Command timed out
    CONNECTION_ERROR = "connection_error"  # VM unreachable
    UNKNOWN = "unknown"


class CommandErrorDetector:
    """Detects and classifies command execution failures"""
    
    def detect_failure_type(
        self,
        result: Dict[str, Any],
        error_text: str,
        exit_code: int
    ) -> FailureType:
        """
        Classify failure type based on result, error text, and exit code.
        
        Args:
            result: Execution result dictionary
            error_text: Error message from execution
            exit_code: Exit code from command execution
            
        Returns:
            FailureType enum value
        """
        # Check for connection errors first (highest priority)
        if result.get("connection_error", False):
            logger.debug("Failure classified as CONNECTION_ERROR")
            return FailureType.CONNECTION_ERROR
        
        # Check for Azure conflicts
        error_str = (error_text or "").lower()
        is_conflict = (
            "conflict" in error_str or
            "execution is in progress" in error_str or
            "run command extension" in error_str or
            (hasattr(result, 'status_code') and getattr(result, 'status_code', None) == 409) or
            result.get("status_code") == 409
        )
        
        if is_conflict:
            logger.debug("Failure classified as AZURE_CONFLICT")
            return FailureType.AZURE_CONFLICT
        
        # Check for timeout
        is_timeout = (
            "timed out" in error_str or
            "timeout" in error_str or
            exit_code == -1 and "timeout" in error_str.lower()
        )
        
        if is_timeout:
            logger.debug("Failure classified as TIMEOUT")
            return FailureType.TIMEOUT
        
        # Check for command syntax/parameter errors
        if self.is_command_syntax_error(error_text, exit_code):
            logger.debug("Failure classified as COMMAND_ERROR")
            return FailureType.COMMAND_ERROR
        
        # Unknown failure type
        logger.debug(f"Failure classified as UNKNOWN (error: {error_text[:100]})")
        return FailureType.UNKNOWN
    
    def is_command_syntax_error(self, error_text: str, exit_code: int) -> bool:
        """
        Determine if error is a command syntax/parameter issue.
        
        Args:
            error_text: Error message from execution
            exit_code: Exit code from command execution
            
        Returns:
            True if error appears to be a command syntax/parameter issue
        """
        if not error_text:
            return False
        
        error_lower = error_text.lower()
        
        # PowerShell-specific error patterns
        command_error_patterns = [
            "parameter cannot be found",
            "a parameter cannot be found",
            "missing an argument for parameter",
            "the specified object was not found",
            "cannot find parameter",
            "is not a property",
            "property.*cannot be found",
            "cannot bind argument to parameter",
            "invalid argument",
            "syntax error",
            "parse error",
            "unexpected token",
            "the term.*is not recognized",
            "cmdlet.*not found",
        ]
        
        # Check if any pattern matches
        for pattern in command_error_patterns:
            if pattern in error_lower:
                logger.debug(f"Command syntax error detected: pattern '{pattern}' matched")
                return True
        
        # Check for PowerShell-specific error codes that indicate command issues
        # Exit code 1 with specific error text often indicates command errors
        if exit_code == 1 and any(
            keyword in error_lower
            for keyword in ["parameter", "property", "cmdlet", "syntax", "parse"]
        ):
            return True
        
        return False




