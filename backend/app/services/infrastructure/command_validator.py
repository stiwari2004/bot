"""
Command validation service to prevent command injection (MF-4)
"""
import re
from typing import List, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)


class CommandValidator:
    """Validates commands to prevent injection attacks"""
    
    # Dangerous SQL patterns (MF-4)
    DANGEROUS_SQL_PATTERNS = [
        r'\bDROP\s+(DATABASE|TABLE|SCHEMA|USER)\b',
        r'\bDELETE\s+FROM\s+\w+\s*(?:;|$)',  # DELETE without WHERE
        r'\bTRUNCATE\s+TABLE\b',
        r'\bALTER\s+(DATABASE|TABLE|SCHEMA)\b',
        r'\bCREATE\s+(DATABASE|USER|ROLE)\b',
        r'\bGRANT\b.*\bTO\b',
        r'\bREVOKE\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r';\s*DROP\s+',
        r';\s*DELETE\s+',
        r';\s*TRUNCATE\s+',
        r';\s*ALTER\s+',
        r';\s*CREATE\s+',
    ]
    
    # Dangerous shell patterns (MF-4)
    DANGEROUS_SHELL_PATTERNS = [
        r'[;&|`$]',  # Command chaining
        r'\$\(',  # Command substitution
        r'`[^`]*`',  # Backtick execution
        r'rm\s+-rf\s+/',  # Dangerous rm
        r'mkfs\s+',  # Format disk
        r'fdisk\s+',  # Partition disk
        r'dd\s+if=',  # Disk dump
        r'>\s*/dev/',  # Redirect to device
        r'nc\s+',  # Netcat
        r'wget\s+',  # Download
        r'curl\s+',  # Download
    ]
    
    # Dangerous PowerShell patterns (MF-4)
    DANGEROUS_PS_PATTERNS = [
        r'Remove-Item\s+.*-Recurse\s+.*-Force\s+.*[A-Z]:\\',  # Dangerous Remove-Item with drive root (any param order)
        r'Remove-Item\s+.*-Path\s+[A-Z]:\\\s+.*-Recurse',  # Dangerous Remove-Item with -Path and drive root
        r'Remove-Item\s+.*-Recurse\s+.*-Path\s+[A-Z]:\\',  # Dangerous Remove-Item with -Recurse before -Path
        r'Remove-Item\s+.*-Force\s+.*-Path\s+[A-Z]:\\\s+.*-Recurse',  # Dangerous Remove-Item with -Force before -Path
        r'Format-Volume\s+',  # Format volume
        r'Invoke-Expression\s+',  # Invoke-Expression
        r'Invoke-Command\s+',  # Invoke-Command
        r'Start-Process\s+.*-FilePath\s+',  # Start-Process with file
        r'[;&|]',  # Command chaining
        r'\$\(',  # Command substitution
    ]
    
    @classmethod
    def validate_sql_command(cls, command: str) -> Tuple[bool, str]:
        """
        Validate SQL command for dangerous patterns (MF-4)
        Returns: (is_safe, error_message)
        """
        # Check for empty command
        if not command or not command.strip():
            return False, "Command is empty"
        
        command_upper = command.upper().strip()
        
        # Check for command chaining (any semicolon followed by any command)
        if ';' in command_upper:
            # Split by semicolon and check if there are multiple commands
            parts = [p.strip() for p in command_upper.split(';') if p.strip()]
            if len(parts) > 1:
                logger.warning("Rejected SQL command with chaining")
                return False, "Command chaining detected (multiple commands separated by semicolon)"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_SQL_PATTERNS:
            if re.search(pattern, command_upper, re.IGNORECASE):
                logger.warning(f"Rejected dangerous SQL command pattern: {pattern}")
                return False, f"Command contains dangerous SQL pattern: {pattern}"
        
        # Allow only SELECT, SHOW, DESCRIBE, EXPLAIN, WITH (CTE) for read operations
        # Allow INSERT, UPDATE with WHERE for write operations (if needed)
        allowed_prefixes = ['SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'WITH']
        
        # Check if command starts with allowed prefix
        first_word = command_upper.split()[0] if command_upper.split() else ""
        if first_word not in allowed_prefixes:
            # Allow INSERT/UPDATE only if they have proper WHERE clauses (for runbooks)
            if first_word in ['INSERT', 'UPDATE']:
                # Basic check - UPDATE must have WHERE
                if first_word == 'UPDATE' and 'WHERE' not in command_upper:
                    return False, "UPDATE commands must include WHERE clause"
                # Allow if it's a runbook-generated command (trusted source)
                logger.info(f"Allowing {first_word} command (runbook-generated)")
            else:
                return False, f"Command must start with one of: {', '.join(allowed_prefixes)}"
        
        return True, ""
    
    @classmethod
    def validate_shell_command(cls, command: str) -> Tuple[bool, str]:
        """
        Validate shell command for dangerous patterns (MF-4)
        Returns: (is_safe, error_message)
        """
        # Check for empty command
        if not command or not command.strip():
            return False, "Command is empty"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_SHELL_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(f"Rejected dangerous shell command pattern: {pattern}")
                return False, f"Command contains dangerous shell pattern: {pattern}"
        
        return True, ""
    
    @classmethod
    def validate_powershell_command(cls, command: str) -> Tuple[bool, str]:
        """
        Validate PowerShell command for dangerous patterns (MF-4)
        Returns: (is_safe, error_message)
        """
        # Check for empty command
        if not command or not command.strip():
            return False, "Command is empty"
        
        command_upper = command.upper()
        
        # Special check for Remove-Item with dangerous combination: -Recurse -Force and drive root
        if 'REMOVE-ITEM' in command_upper:
            has_recurse = '-RECURSE' in command_upper
            has_force = '-FORCE' in command_upper
            has_drive_root = re.search(r'[A-Z]:\\', command_upper) is not None
            
            if has_recurse and has_force and has_drive_root:
                logger.warning("Rejected dangerous Remove-Item command with -Recurse -Force on drive root")
                return False, "Remove-Item with -Recurse -Force on drive root is dangerous"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(f"Rejected dangerous PowerShell command pattern: {pattern}")
                return False, f"Command contains dangerous PowerShell pattern: {pattern}"
        
        return True, ""
    
    @classmethod
    def validate_command(cls, command: str, command_type: str = "auto") -> Tuple[bool, str]:
        """
        Validate command based on type (MF-4)
        command_type: "sql", "shell", "powershell", or "auto" (detect)
        Returns: (is_safe, error_message)
        """
        if command_type == "auto":
            # Auto-detect command type
            command_lower = command.lower().strip()
            if any(keyword in command_lower for keyword in ['select', 'from', 'where', 'insert', 'update']):
                command_type = "sql"
            elif command_lower.startswith('get-') or 'powershell' in command_lower or '-Object' in command:
                command_type = "powershell"
            else:
                command_type = "shell"
        
        if command_type == "sql":
            return cls.validate_sql_command(command)
        elif command_type == "powershell":
            return cls.validate_powershell_command(command)
        elif command_type == "shell":
            return cls.validate_shell_command(command)
        else:
            return False, f"Unknown command type: {command_type}"




