"""
Manages timeout determination for step execution
"""
from typing import Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepTimeoutManager:
    """Manages timeout determination for step execution"""
    
    def get_command_timeout(self, command: str) -> int:
        """
        Determine timeout based on command type.
        
        Args:
            command: Command string to analyze
            
        Returns:
            Timeout in seconds
        """
        if not command:
            return 120
        
        command_lower = command.lower().strip()
        
        # Very long-running commands (30 minutes)
        if any(cmd in command_lower for cmd in [
            'sfc /scannow',
            'dism /online /cleanup-image /restorehealth',
            'chkdsk /f',
            'chkdsk /r'
        ]):
            return 1800
        
        # Long-running commands (10 minutes)
        if any(cmd in command_lower for cmd in [
            'repair-windowsimage',
            'dism /online',
            'windowsupdate'
        ]):
            return 600
        
        # Medium-running commands (5 minutes)
        if any(cmd in command_lower for cmd in [
            'defrag',
            'get-eventlog',
            'get-winevent',
            'get-wmiobject'
        ]):
            return 300
        
        # Default timeout
        return 120
    
    def determine_timeout(
        self,
        validation_result: Optional[Dict[str, Any]],
        command: str
    ) -> int:
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
        return self.get_command_timeout(command)








