"""
Centralized configuration for runbook generation and validation.
All hardcoded values related to runbook structure, validation, and processing
should be defined here.
"""
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class RunbookStructureConfig:
    """Configuration for runbook structure requirements"""
    # Section names
    SECTION_PRECHECKS: str = "prechecks"
    SECTION_STEPS: str = "steps"
    SECTION_POSTCHECKS: str = "postchecks"
    SECTION_INPUTS: str = "inputs"
    
    # Required counts
    PRECHECKS_COUNT: int = 3
    STEPS_MIN: int = 5
    STEPS_MAX: int = 6
    POSTCHECKS_COUNT: int = 1
    
    # Remediation requirements
    MIN_REMEDIATION_STEPS: int = 4
    MAX_DIAGNOSTIC_ONLY_STEPS: int = 2


@dataclass
class RunbookValidationConfig:
    """Configuration for runbook validation"""
    # Stop words for keyword matching
    STOP_WORDS: Set[str] = None
    
    # Metric keywords for validation
    METRIC_KEYWORDS: Dict[str, List[str]] = None
    
    # Step purposes and phases
    ALLOWED_PURPOSES: Set[str] = None
    PHASE_ORDER: Dict[str, int] = None
    
    # Remediation keywords
    REMEDIATION_KEYWORDS: List[str] = None
    
    # Diagnostic keywords
    DIAGNOSTIC_KEYWORDS: List[str] = None
    
    def __post_init__(self):
        if self.STOP_WORDS is None:
            self.STOP_WORDS = {
                "fix", "resolve", "troubleshoot", "the", "a", "an", "on", "for", "to", "of",
                "in", "at", "by", "with", "from", "as", "is", "was", "are", "were",
                "be", "been", "being", "have", "has", "had", "do", "does", "did",
                "will", "would", "should", "could", "may", "might", "must", "can"
            }
        
        if self.METRIC_KEYWORDS is None:
            self.METRIC_KEYWORDS = {
                "cpu": ["cpu", "processor", "processor time"],
                "memory": ["memory", "ram", "available mbytes", "committed bytes"],
                "disk": ["disk", "disk space", "free space", "logicaldisk"],
                "network": ["network", "bytes received", "bytes sent", "latency", "throughput"],
                "transaction log": ["transaction log", "log_reuse_wait", "log space"],
                "connection pool": ["connection pool", "connections", "pg_stat_activity"],
                "service": ["service", "daemon", "systemctl", "restart-service"],
            }
        
        if self.ALLOWED_PURPOSES is None:
            self.ALLOWED_PURPOSES = {"precheck", "diagnose", "remediate", "verify", "postcheck"}
        
        if self.PHASE_ORDER is None:
            self.PHASE_ORDER = {
                "diagnose": 0,
                "remediate": 1,
                "verify": 2,
                "postcheck": 2,
                "precheck": 0
            }
        
        if self.REMEDIATION_KEYWORDS is None:
            self.REMEDIATION_KEYWORDS = [
                "kill", "restart", "stop", "start", "clear", "fix", "repair", "remove",
                "delete", "disable", "enable", "reset", "reload", "reconfigure",
                "restore", "recover", "clean", "purge", "terminate", "abort"
            ]
        
        if self.DIAGNOSTIC_KEYWORDS is None:
            self.DIAGNOSTIC_KEYWORDS = [
                "get", "show", "list", "check", "verify", "monitor", "watch", "inspect",
                "examine", "analyze", "query", "read", "view", "display", "print"
            ]


@dataclass
class RunbookProcessingConfig:
    """Configuration for runbook processing and YAML handling"""
    # YAML section indicators
    YAML_SECTION_INDICATORS: List[str] = None
    
    # Common PowerShell parameter fixes
    POWERSHELL_PARAM_FIXES: Dict[str, str] = None
    
    def __post_init__(self):
        if self.YAML_SECTION_INDICATORS is None:
            self.YAML_SECTION_INDICATORS = [
                "name:", "command:", "type:", "step", "steps:", 
                "precheck", "postcheck", "- name:", "- command:"
            ]
        
        if self.POWERSHELL_PARAM_FIXES is None:
            self.POWERSHELL_PARAM_FIXES = {
                "-MaxSamples": "1",
                "-SampleInterval": "1",
                "-Timeout": "30",
                "-Count": "1",
                "-Limit": "10"
            }


# Global configuration instances
runbook_structure = RunbookStructureConfig()
runbook_validation = RunbookValidationConfig()
runbook_processing = RunbookProcessingConfig()

