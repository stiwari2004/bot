"""
Pydantic schemas for validating Runbook YAML structure
"""
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


class CommandSeverity(str, Enum):
    """Command severity levels for safety checks"""
    SAFE = "safe"  # Read-only, diagnostic commands
    MODERATE = "moderate"  # Non-destructive writes, restarts
    DANGEROUS = "dangerous"  # Deletes, format, major changes


class InputParameter(BaseModel):
    """Input parameter definition"""
    name: str
    type: str = "string"
    required: bool = True
    description: Optional[str] = None
    default: Optional[str] = None


class CheckItem(BaseModel):
    """Precheck or Postcheck item"""
    description: str
    command: str
    expected_output: str


class RunbookStep(BaseModel):
    """Step in a runbook"""
    name: str
    type: Literal["command", "manual", "prompt"] = "command"
    command: Optional[str] = None
    description: Optional[str] = None
    expected_output: Optional[str] = None
    skip_in_auto_mode: Optional[bool] = False
    timeout: Optional[int] = None
    on_fail: Optional[str] = None
    severity: Optional[CommandSeverity] = None


class RunbookYAML(BaseModel):
    """Complete Runbook YAML schema"""
    runbook_id: str
    version: str
    title: str
    service: str
    env: Literal["prod", "staging", "dev", "Windows", "Linux"]
    risk: Literal["low", "medium", "high"]
    description: Optional[str] = None
    owner: Optional[str] = None
    last_tested: Optional[str] = None
    review_required: Optional[bool] = None
    inputs: List[InputParameter] = []
    prechecks: List[CheckItem] = []
    steps: List[RunbookStep]
    postchecks: List[CheckItem] = []

    @field_validator('steps')
    def validate_steps_not_empty(cls, v):
        if not v:
            raise ValueError("steps list cannot be empty")
        if len(v) > 20:
            raise ValueError("steps list cannot exceed 20 steps")
        return v

    @field_validator('runbook_id')
    def validate_runbook_id(cls, v):
        if not v.startswith("rb-"):
            raise ValueError("runbook_id must start with 'rb-'")
        return v


# Command allow-list for safety validation
ALLOWED_COMMAND_PATTERNS = {
    CommandSeverity.SAFE: [
        # Diagnostic commands
        "ping", "curl", "wget", "traceroute", "dig", "nslookup",
        "top", "htop", "ps", "free", "df", "du", "iostat", "vmstat",
        "netstat", "ss", "ifconfig", "ip addr", "ip route",
        "systemctl status", "systemctl list",
        "tail", "head", "cat", "less", "grep", "awk", "sed",
        "wc", "find", "ls", "stat", "file",
        # Kubernetes diagnostic
        "kubectl get", "kubectl describe", "kubectl logs", "kubectl top",
    ],
    CommandSeverity.MODERATE: [
        # Non-destructive writes
        "systemctl restart", "systemctl reload", "systemctl start",
        "docker restart", "docker start",
        "kubectl rollout restart", "kubectl scale",
        "echo", "touch",
        # Service commands
        "service restart", "service reload",
    ],
    CommandSeverity.DANGEROUS: [
        # Dangerous operations - require explicit approval
        "rm", "rmdir", "unlink", "shred",
        "mv /", "cp /",
        "dd", "mkfs", "fdisk", "parted",
        "chmod -R", "chown -R",
        "kubectl delete", "kubectl apply -f",
        "systemctl stop", "systemctl disable",
    ]
}

BLOCKED_COMMAND_PATTERNS = [
    "sudo rm -rf /",
    "dd if=",
    "mkfs",
    "fdisk",
    "format",
    "shutdown",
    "halt",
    "reboot",
    "poweroff",
    "init 0",
    "init 6",
]


class RunbookValidator:
    """Validates runbook YAML for safety and correctness"""
    
    @staticmethod
    def validate_structure(spec: Dict[str, Any]) -> RunbookYAML:
        """Validate runbook structure against schema"""
        return RunbookYAML(**spec)
    
    @staticmethod
    def classify_command_severity(command: str) -> CommandSeverity:
        """Classify command severity based on allow-list"""
        cmd_lower = command.lower().strip()
        
        # Check blocked patterns first
        for pattern in BLOCKED_COMMAND_PATTERNS:
            if pattern in cmd_lower:
                raise ValueError(f"Command contains blocked pattern: {pattern}")
        
        # Check severity levels from most dangerous to least
        for severity in [CommandSeverity.DANGEROUS, CommandSeverity.MODERATE, CommandSeverity.SAFE]:
            for pattern in ALLOWED_COMMAND_PATTERNS[severity]:
                if pattern in cmd_lower:
                    return severity
        
        # Unknown command - assume moderate risk
        return CommandSeverity.MODERATE
    
    @staticmethod
    def validate_runbook(spec: Dict[str, Any], auto_assign_severity: bool = True) -> tuple[RunbookYAML, List[str]]:
        """
        Fully validate a runbook including command safety
        
        Returns:
            tuple: (validated_runbook, warnings_list)
        """
        warnings = []
        
        # Validate structure
        runbook = RunbookValidator.validate_structure(spec)
        
        # Validate commands
        for step in runbook.steps:
            if step.command:
                try:
                    severity = RunbookValidator.classify_command_severity(step.command)
                    if auto_assign_severity:
                        step.severity = severity
                    else:
                        warnings.append(f"Step '{step.name}': Unknown command pattern")
                except ValueError as e:
                    warnings.append(f"Step '{step.name}': {str(e)}")
        
        # Additional validation
        if runbook.risk == "high" and not runbook.review_required:
            warnings.append("High-risk runbook should have review_required=true")
        
        if len(runbook.steps) > 15:
            warnings.append("Large number of steps may indicate runbook needs splitting")
        
        return runbook, warnings

