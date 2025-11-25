"""
Command validation and correction rules for PowerShell commands.
Provides rule-based validation and correction patterns with OS awareness.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


def _detect_os_from_connector(connector_type: str) -> str:
    """
    Detect OS from connector type.
    
    Args:
        connector_type: Connector type (azure_bastion, ssh, local, etc.)
        
    Returns:
        "windows" or "linux"
    """
    if connector_type in ("azure_bastion", "local"):
        return "windows"
    elif connector_type in ("ssh", "gcp_iap"):
        return "linux"
    else:
        # Default to Windows (most common)
        return "windows"


# Rule-based validation patterns (OS-aware)
VALIDATION_RULES: List[Dict[str, Any]] = [
    {
        "name": "Get-EventLog missing -LogName",
        "pattern": r"Get-EventLog\s+-Newest\s+\d+",
        "error_pattern": r"parameter.*cannot.*found|A parameter cannot be found|Missing an argument for parameter",
        "fix": lambda match, os_type: match.group(0).replace("Get-EventLog", "Get-EventLog -LogName System") if os_type == "windows" else match.group(0),
        "description": "Get-EventLog requires -LogName parameter on Windows",
        "os_type": "windows",
        "suggested_timeout": 300,
    },
    {
        "name": "Get-EventLog with CounterSamples property",
        "pattern": r"Select-Object.*CounterSamples",
        "error_pattern": r"CounterSamples.*not.*property|is not a property|Property 'CounterSamples' cannot be found",
        "fix": lambda match, os_type: re.sub(r",\s*CounterSamples|CounterSamples\s*,", "", match.group(0)) if os_type == "windows" else match.group(0),
        "description": "CounterSamples is not a valid property for EventLog entries - removing it",
        "os_type": "windows",
        "suggested_timeout": None,
    },
    {
        "name": "Get-EventLog with invalid property",
        "pattern": r"Get-EventLog.*Select-Object.*TimeCreated",
        "error_pattern": r"TimeCreated.*not.*property|is not a property",
        "fix": lambda match, os_type: match.group(0).replace("TimeCreated", "TimeGenerated") if os_type == "windows" else match.group(0),
        "description": "EventLog entries use TimeGenerated, not TimeCreated",
        "os_type": "windows",
        "suggested_timeout": None,
    },
    {
        "name": "Ping command -c on Windows",
        "pattern": r"ping\s+-c\s+\d+",
        "error_pattern": r"Bad value for option -c|invalid option",
        "fix": lambda match, os_type: match.group(0).replace("-c", "-n") if os_type == "windows" else match.group(0),
        "description": "Ping -c is Linux syntax, use -n on Windows",
        "os_type": "windows",
        "suggested_timeout": None,
    },
    {
        "name": "Ping command -n on Linux",
        "pattern": r"ping\s+-n\s+\d+",
        "error_pattern": r"Bad value for option -n|invalid option",
        "fix": lambda match, os_type: match.group(0).replace("-n", "-c") if os_type == "linux" else match.group(0),
        "description": "Ping -n is Windows syntax, use -c on Linux",
        "os_type": "linux",
        "suggested_timeout": None,
    },
    {
        "name": "Ping command missing target",
        "pattern": r"^ping\s+-[nc]\s+\d+\s*$",
        "error_pattern": r"|",  # Match any error (ping without target always fails)
        "fix": lambda match, os_type: match.group(0),  # Can't fix without context - will need Perplexity
        "description": "Ping command missing target hostname/IP",
        "os_type": "windows",
        "suggested_timeout": None,
    },
    {
        "name": "Ping command missing target (Linux)",
        "pattern": r"^ping\s+-[nc]\s+\d+\s*$",
        "error_pattern": r"|",  # Match any error (ping without target always fails)
        "fix": lambda match, os_type: match.group(0),  # Can't fix without context - will need Perplexity
        "description": "Ping command missing target hostname/IP",
        "os_type": "linux",
        "suggested_timeout": None,
    },
]


# Correction rules (for post-execution failures, OS-aware)
CORRECTION_RULES: List[Dict[str, Any]] = [
    {
        "name": "Get-EventLog missing -LogName",
        "command_pattern": r"Get-EventLog(?!.*-LogName)",
        "error_pattern": r"parameter.*cannot.*found|A parameter cannot be found|Missing an argument for parameter",
        "fix": lambda command, os_type: re.sub(
            r"Get-EventLog\s+",
            "Get-EventLog -LogName System ",
            command
        ) if os_type == "windows" else command,
        "description": "Add -LogName System to Get-EventLog command",
        "os_type": "windows",
    },
    {
        "name": "Get-EventLog CounterSamples property",
        "command_pattern": r".*CounterSamples.*",
        "error_pattern": r"CounterSamples.*not.*property|is not a property|Property 'CounterSamples' cannot be found",
        "fix": lambda command, os_type: re.sub(r",\s*CounterSamples|CounterSamples\s*,", "", command) if os_type == "windows" else command,
        "description": "Remove CounterSamples (not a valid EventLog property)",
        "os_type": "windows",
    },
    {
        "name": "Get-EventLog TimeCreated property",
        "command_pattern": r".*TimeCreated.*",
        "error_pattern": r"TimeCreated.*not.*property|is not a property",
        "fix": lambda command, os_type: re.sub(r"TimeCreated", "TimeGenerated", command) if os_type == "windows" else command,
        "description": "Replace TimeCreated with TimeGenerated for EventLog",
        "os_type": "windows",
    },
    {
        "name": "Ping command -c on Windows",
        "command_pattern": r"ping\s+-c\s+\d+",
        "error_pattern": r"Bad value for option -c|invalid option",
        "fix": lambda command, os_type: re.sub(r"ping\s+-c", "ping -n", command) if os_type == "windows" else command,
        "description": "Fix ping command: -c is Linux, -n is Windows",
        "os_type": "windows",
    },
    {
        "name": "Ping command -n on Linux",
        "command_pattern": r"ping\s+-n\s+\d+",
        "error_pattern": r"Bad value for option -n|invalid option",
        "fix": lambda command, os_type: re.sub(r"ping\s+-n", "ping -c", command) if os_type == "linux" else command,
        "description": "Fix ping command: -n is Windows, -c is Linux",
        "os_type": "linux",
    },
    {
        "name": "Ping command missing target",
        "command_pattern": r"ping\s+-[nc]\s+\d+\s*$",
        "error_pattern": r"|",  # Match any error (ping without target always fails)
        "fix": lambda command, os_type: command,  # Will be handled specially with connection_config
        "description": "Ping command missing target hostname/IP",
        "os_type": "windows",
    },
    {
        "name": "Ping command missing target (Linux)",
        "command_pattern": r"ping\s+-[nc]\s+\d+\s*$",
        "error_pattern": r"|",  # Match any error (ping without target always fails)
        "fix": lambda command, os_type: command,  # Will be handled specially with connection_config
        "description": "Ping command missing target hostname/IP",
        "os_type": "linux",
    },
]


def validate_command_with_rules(command: str, connector_type: str = "local", connection_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate command using rule-based patterns (OS-aware).
    
    Args:
        command: PowerShell command to validate
        connector_type: Connector type to detect OS (azure_bastion=Windows, ssh=Linux)
        connection_config: Optional connection config to extract server name/hostname
        
    Returns:
        {
            "is_valid": bool,
            "corrected_command": Optional[str],
            "validation_method": str,
            "confidence": float,
            "issues": List[str],
            "suggested_timeout": Optional[int]
        }
    """
    if not command or not command.strip():
        return {
            "is_valid": False,
            "corrected_command": None,
            "validation_method": "rule",
            "confidence": 1.0,
            "issues": ["Command is empty"],
            "suggested_timeout": None,
        }
    
    # Detect OS from connector type
    os_type = _detect_os_from_connector(connector_type)
    
    issues: List[str] = []
    corrected_command = command
    suggested_timeout: Optional[int] = None
    
    # Check each validation rule
    for rule in VALIDATION_RULES:
        # Check if rule applies to this OS
        rule_os = rule.get("os_type")
        if rule_os and rule_os != os_type:
            continue  # Skip rules that don't apply to this OS
        
        pattern = rule["pattern"]
        # Strip command for matching (but keep original for correction)
        command_stripped = command.strip()
        match = re.search(pattern, command_stripped, re.IGNORECASE)
        if match:
            # Pattern matches - check if this is a known issue
            # For now, we'll apply the fix preemptively if pattern matches
            # (since we can't check error without executing)
            try:
                fix_func = rule["fix"]
                # Special handling for ping missing target (both Windows and Linux)
                if rule["name"] in ("Ping command missing target", "Ping command missing target (Linux)"):
                    logger.info(f"Ping missing target rule matched for command: '{command}'")
                    # Try to get server name from connection config
                    server_name = None
                    if connection_config:
                        # Check multiple possible fields
                        server_name = (
                            connection_config.get("host") or
                            connection_config.get("vm_name") or
                            connection_config.get("server_name") or
                            connection_config.get("ci_name") or
                            connection_config.get("target_host")
                        )
                        
                        # For Azure, try to extract vm_name from resource_id
                        if not server_name:
                            resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
                            if resource_id:
                                try:
                                    # Parse resource ID: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
                                    parts = resource_id.split("/")
                                    if "virtualMachines" in parts:
                                        vm_index = parts.index("virtualMachines")
                                        if vm_index + 1 < len(parts):
                                            server_name = parts[vm_index + 1]
                                            logger.info(f"Extracted VM name from resource_id: {server_name}")
                                except Exception as e:
                                    logger.warning(f"Failed to extract VM name from resource_id: {e}")
                    
                    if server_name:
                        # Add server name to ping command
                        corrected_command = f"{command} {server_name}"
                        issues.append(f"{rule['description']} - added {server_name}")
                        logger.info(
                            f"Rule '{rule['name']}' matched, corrected command: '{command}' → '{corrected_command}'"
                        )
                        # Continue to next rule (don't apply fix_func)
                        continue
                    else:
                        issues.append(rule["description"])
                        logger.warning(
                            f"Rule '{rule['name']}' matched but no server name available. "
                            f"Connection config: {connection_config if connection_config else 'None'}"
                        )
                        # Continue to next rule even if server name not found
                        continue
                else:
                    # Not a ping missing target rule - apply normal fix function
                    corrected_command = fix_func(match, os_type)
                    if corrected_command != command:
                        issues.append(rule["description"])
                        if rule.get("suggested_timeout"):
                            suggested_timeout = rule["suggested_timeout"]
                        logger.info(f"Rule '{rule['name']}' matched for {os_type}, suggesting correction")
            except Exception as e:
                logger.warning(f"Error applying rule '{rule['name']}': {e}")
    
    is_valid = len(issues) == 0
    
    return {
        "is_valid": is_valid,
        "corrected_command": corrected_command if not is_valid else None,
        "validation_method": "rule",
        "confidence": 0.9 if issues else 1.0,
        "issues": issues,
        "suggested_timeout": suggested_timeout,
    }


def correct_command_with_rules(command: str, error_text: str, connector_type: str = "local", connection_config: Optional[Dict[str, Any]] = None) -> Optional[Tuple[str, str]]:
    """
    Attempt to correct command using rule-based patterns based on error message (OS-aware).
    Applies ALL matching corrections sequentially.
    
    Args:
        command: Original command that failed
        error_text: Error message from execution
        connector_type: Connector type to detect OS (azure_bastion=Windows, ssh=Linux)
        connection_config: Optional connection config to extract server name/hostname
        
    Returns:
        Tuple of (corrected_command, rule_name) if correction found, None otherwise
    """
    if not command or not error_text:
        return None
    
    # Detect OS from connector type
    os_type = _detect_os_from_connector(connector_type)
    
    error_lower = error_text.lower()
    corrected_command = command
    applied_rules = []
    
    # Apply ALL matching corrections sequentially (important for Get-EventLog which may need multiple fixes)
    for rule in CORRECTION_RULES:
        # Check if rule applies to this OS
        rule_os = rule.get("os_type")
        if rule_os and rule_os != os_type:
            continue  # Skip rules that don't apply to this OS
        
        command_pattern = rule["command_pattern"]
        error_pattern = rule["error_pattern"]
        
        # Check if command matches pattern and error matches error pattern
        # For ping missing target, error_pattern is "|" which matches any error
        error_matches = (error_pattern == "|") or re.search(error_pattern, error_lower, re.IGNORECASE)
        
        # Use current corrected_command for pattern matching (so fixes chain together)
        if re.search(command_pattern, corrected_command, re.IGNORECASE) and error_matches:
            try:
                # Special handling for ping missing target (check before applying fix_func)
                if "ping" in corrected_command.lower() and not re.search(r"ping\s+-[nc]\s+\d+\s+\S+", corrected_command, re.IGNORECASE):
                    # Try to get server name from connection config
                    server_name = None
                    if connection_config:
                        # Check multiple possible fields
                        server_name = (
                            connection_config.get("host") or
                            connection_config.get("vm_name") or
                            connection_config.get("server_name") or
                            connection_config.get("ci_name") or
                            connection_config.get("target_host")
                        )
                        
                        # For Azure, try to extract vm_name from resource_id
                        if not server_name:
                            resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
                            if resource_id:
                                try:
                                    # Parse resource ID: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
                                    parts = resource_id.split("/")
                                    if "virtualMachines" in parts:
                                        vm_index = parts.index("virtualMachines")
                                        if vm_index + 1 < len(parts):
                                            server_name = parts[vm_index + 1]
                                            logger.info(f"Extracted VM name from resource_id for correction: {server_name}")
                                except Exception as e:
                                    logger.warning(f"Failed to extract VM name from resource_id: {e}")
                    
                    if server_name:
                        # Add server name to ping command
                        new_corrected = f"{corrected_command} {server_name}"
                        logger.info(f"Rule 'Ping missing target' applied, added server name: {server_name}")
                        applied_rules.append("Ping command missing target")
                        corrected_command = new_corrected
                        continue  # Continue to next rule to check for other issues
                    else:
                        logger.warning(
                            f"Ping command missing target but no server name available. "
                            f"Connection config keys: {list(connection_config.keys()) if connection_config else 'None'}"
                        )
                        # Continue to next rule
                
                # Apply rule's fix function
                fix_func = rule["fix"]
                new_corrected = fix_func(corrected_command, os_type)
                
                if new_corrected != corrected_command:
                    logger.info(f"Rule '{rule['name']}' applied for {os_type}: {corrected_command[:100]} → {new_corrected[:100]}")
                    applied_rules.append(rule["name"])
                    corrected_command = new_corrected
            except Exception as e:
                logger.warning(f"Error applying correction rule '{rule['name']}': {e}")
    
    if applied_rules:
        rule_name = ", ".join(applied_rules) if len(applied_rules) > 1 else applied_rules[0]
        return (corrected_command, rule_name)
    
    return None

