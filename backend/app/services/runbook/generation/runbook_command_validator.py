"""
Runbook Command Validator - Validates all commands in generated runbooks using web search.
Ensures commands are grounded in documentation and properly classified as remediation vs diagnostic.
"""
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.services.runbook.generation.runbook_command_validator_llm_mixin import CommandValidatorLLMMixin

logger = get_logger(__name__)


class RunbookCommandValidator(CommandValidatorLLMMixin):
    """Validates all commands in a generated runbook using Perplexity web search for grounding"""

    def __init__(self, llm_service_instance=None):
        """Initialize validator with optional LLM service (Perplexity for web search)"""
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                llm_service = get_llm_service()
                if hasattr(llm_service, 'model') and 'online' in getattr(llm_service, 'model', '').lower():
                    self.llm_service = llm_service
                else:
                    from app.services.llm_service import PerplexityLLMService
                    import os
                    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
                    if perplexity_key:
                        self.llm_service = PerplexityLLMService(api_key=perplexity_key)
                    else:
                        self.llm_service = llm_service
            except Exception as e:
                logger.warning(f"Could not initialize LLM service for command validation: {e}")
                self.llm_service = None

    async def validate_runbook_commands(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        os_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate all commands in runbook using web search grounding.

        Returns:
            {
                "is_valid": bool,
                "invalid_commands": List[Dict],
                "diagnostic_mislabeled": List[Dict],
                "missing_remediation": bool,
                "suggestions": List[str],
                "validation_summary": str
            }
        """
        if not self.llm_service:
            logger.warning("LLM service not available for command validation - skipping web search validation")
            return {
                "is_valid": True,
                "invalid_commands": [],
                "diagnostic_mislabeled": [],
                "missing_remediation": False,
                "suggestions": ["Web search validation unavailable - commands not verified"],
                "validation_summary": "Skipped (service unavailable)"
            }

        # Auto-detect OS type if not provided
        if not os_type:
            issue_lower = issue_description.lower()
            if any(kw in issue_lower for kw in ['windows', 'powershell', 'get-process', 'get-counter']):
                os_type = "Windows"
            elif any(kw in issue_lower for kw in ['linux', 'ubuntu', 'centos', 'systemctl', 'journalctl']):
                os_type = "Linux"
            else:
                env = spec.get("env", "").lower()
                if "windows" in env:
                    os_type = "Windows"
                elif "linux" in env:
                    os_type = "Linux"
                else:
                    os_type = "Windows"

        issue_type = self._detect_issue_type(issue_description)

        invalid_commands = []
        diagnostic_mislabeled = []
        remediation_commands_found = []

        # Validate prechecks
        prechecks = spec.get("prechecks", [])
        for idx, precheck in enumerate(prechecks):
            if isinstance(precheck, dict):
                command = precheck.get("command", "").strip()
                if command:
                    validation = await self._validate_command_existence(command, os_type)
                    if not validation["exists"]:
                        invalid_commands.append({
                            "section": "precheck",
                            "index": idx + 1,
                            "command": command,
                            "issue": validation.get("issue", "Command not found in documentation"),
                            "suggested_fix": validation.get("suggested_command")
                        })

        # Validate main steps
        steps = spec.get("steps", [])
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            command = step.get("command", "").strip()
            if not command:
                continue
            step_name = step.get("name", f"Step {idx + 1}")
            purpose = step.get("purpose", "").lower()

            existence_validation = await self._validate_command_existence(command, os_type)
            if not existence_validation["exists"]:
                invalid_commands.append({
                    "section": "steps",
                    "index": idx + 1,
                    "name": step_name,
                    "command": command,
                    "issue": existence_validation.get("issue", "Command not found in documentation"),
                    "suggested_fix": existence_validation.get("suggested_command")
                })
                continue

            is_marked_remediation = (
                purpose == "remediate" or
                "remediate" in step_name.lower() or
                "fix" in step_name.lower() or
                "kill" in step_name.lower() or
                "restart" in step_name.lower()
            )

            if is_marked_remediation:
                remediation_validation = await self._validate_remediation_command(command, issue_type, os_type)
                if not remediation_validation["is_remediation"]:
                    diagnostic_mislabeled.append({
                        "section": "steps",
                        "index": idx + 1,
                        "name": step_name,
                        "command": command,
                        "issue": f"Command marked as remediation but is actually diagnostic: {remediation_validation.get('explanation', '')}",
                        "suggested_fix": remediation_validation.get("suggested_remediation")
                    })
                elif not remediation_validation.get("can_fix_issue", False):
                    diagnostic_mislabeled.append({
                        "section": "steps",
                        "index": idx + 1,
                        "name": step_name,
                        "command": command,
                        "issue": f"Remediation command exists but cannot fix {issue_type}: {remediation_validation.get('explanation', '')}",
                        "suggested_fix": remediation_validation.get("suggested_remediation")
                    })
                else:
                    remediation_commands_found.append({
                        "index": idx + 1,
                        "name": step_name,
                        "command": command
                    })

        # Validate postchecks
        postchecks = spec.get("postchecks", [])
        for idx, postcheck in enumerate(postchecks):
            if isinstance(postcheck, dict):
                command = postcheck.get("command", "").strip()
                if command:
                    validation = await self._validate_command_existence(command, os_type)
                    if not validation["exists"]:
                        invalid_commands.append({
                            "section": "postcheck",
                            "index": idx + 1,
                            "command": command,
                            "issue": validation.get("issue", "Command not found in documentation"),
                            "suggested_fix": validation.get("suggested_command")
                        })

        from app.config.runbook_config import runbook_structure
        min_remediation = runbook_structure.MIN_REMEDIATION_STEPS
        remediation_ratio = runbook_structure.REMEDIATION_RATIO
        total_steps = len(steps)

        remediation_count_ok = len(remediation_commands_found) >= min_remediation
        remediation_ratio_ok = (len(remediation_commands_found) / total_steps) >= remediation_ratio if total_steps > 0 else False

        missing_remediation = not (remediation_count_ok and remediation_ratio_ok)
        has_invalid_commands = len(invalid_commands) > 0
        has_mislabeled = len(diagnostic_mislabeled) > 0
        is_valid = not (has_invalid_commands or has_mislabeled or missing_remediation)

        suggestions = []
        if missing_remediation:
            remediation_ratio_pct = runbook_structure.REMEDIATION_RATIO * 100
            current_ratio = (len(remediation_commands_found) / total_steps * 100) if total_steps > 0 else 0.0
            suggestions.append(
                f"CRITICAL: Only {len(remediation_commands_found)} remediation command(s) found. "
                f"Need at least {min_remediation} remediation steps AND at least {remediation_ratio_pct:.0f}% of steps must be remediation. "
                f"Runbook must include actual fix actions (kill, restart, stop, clear, etc.), not just diagnostics. "
                f"Current: {len(remediation_commands_found)}/{total_steps} steps are remediation ({current_ratio:.0f}%)."
            )
        if has_invalid_commands:
            suggestions.append(
                f"Found {len(invalid_commands)} invalid command(s) that don't exist or have syntax errors. "
                f"These commands will fail during execution."
            )
        if has_mislabeled:
            suggestions.append(
                f"Found {len(diagnostic_mislabeled)} command(s) marked as remediation but are actually diagnostic. "
                f"These won't fix the issue."
            )

        validation_summary = (
            f"Validated {len(steps)} steps: "
            f"{len(remediation_commands_found)} remediation, "
            f"{len(invalid_commands)} invalid, "
            f"{len(diagnostic_mislabeled)} mislabeled"
        )

        return {
            "is_valid": is_valid,
            "invalid_commands": invalid_commands,
            "diagnostic_mislabeled": diagnostic_mislabeled,
            "missing_remediation": missing_remediation,
            "remediation_commands_found": remediation_commands_found,
            "suggestions": suggestions,
            "validation_summary": validation_summary
        }
