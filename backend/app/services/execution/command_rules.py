"""
Command rules - minimal pass-through (no hardcoded fix rules).
Fixes are driven by DB learnings and Perplexity web search only.
"""
from typing import Dict, List, Optional, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

# No hardcoded VALIDATION_RULES or CORRECTION_RULES - all fixes come from DB + Perplexity


def validate_command_with_rules(
    command: str,
    connector_type: str = "local",
    connection_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Pre-execution validation. No hardcoded rules - returns is_valid=True.
    Actual corrections happen post-execution via DB learnings and Perplexity.
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
    return {
        "is_valid": True,
        "corrected_command": None,
        "validation_method": "rule",
        "confidence": 1.0,
        "issues": [],
        "suggested_timeout": None,
    }


def correct_command_with_rules(
    command: str,
    error_text: str,
    connector_type: str = "local",
    connection_config: Optional[Dict[str, Any]] = None,
) -> Optional[tuple]:
    """
    Post-execution correction. No hardcoded rules - returns None.
    Use CommandCorrector (DB + Perplexity) for corrections.
    """
    return None
