"""
Mixin: step-related post-processing fixes for SpecPostProcessor
"""
from typing import Dict, Any

from app.config import runbook_structure
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpecStepFixersMixin:
    """Step-related fix operations for SpecPostProcessor."""

    def _fix_incomplete_steps(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix incomplete steps. Use description/name as command fallback before removing."""
        if "steps" in spec and isinstance(spec["steps"], list):
            cleaned_steps = []
            for step in spec["steps"]:
                if isinstance(step, dict):
                    step_type = step.get("type", "command")
                    command_value = step.get("command")
                    command_value = command_value.strip() if isinstance(command_value, str) else None

                    if step_type == "command" and not command_value:
                        desc = (step.get("description") or "").strip()
                        name = (step.get("name") or "").strip()
                        if desc and len(desc) > 2:
                            command_value = desc
                            step["command"] = desc
                            logger.info(f"Using description as command for step: {step.get('name', 'N/A')[:50]}")
                        elif name and len(name) > 2:
                            command_value = name
                            step["command"] = name
                            logger.info(f"Using name as command for step: {name[:50]}")
                        if not command_value:
                            step["command"] = "echo 'Step placeholder - update command'"
                            command_value = step["command"]
                            logger.warning(f"Step had no command/desc/name; set placeholder to keep step: {step.get('name', 'N/A')[:50]}")

                    if step_type == "command" and command_value and not step.get("expected_output"):
                        step["expected_output"] = "Command executed successfully"
                        logger.warning(f"Added default expected_output to step: {step.get('name', 'N/A')}")

                    cleaned_steps.append(step)
                else:
                    logger.warning(f"Skipping invalid step entry: {step}")

            if not cleaned_steps:
                raise ValueError("All steps were removed due to missing commands")
            spec["steps"] = cleaned_steps
        return spec

    def _auto_fix_step_ordering(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fix: Only reorder steps when there is a clear structural violation.
        Only intervenes when verify appears before any remediate step.
        """
        from app.config import runbook_validation

        if "steps" not in spec or not isinstance(spec["steps"], list) or not spec["steps"]:
            return spec

        phase_order = runbook_validation.PHASE_ORDER
        first_verify_idx = None
        first_remediate_idx = None

        for idx, step in enumerate(spec["steps"]):
            if not isinstance(step, dict):
                continue
            purpose = str(step.get("purpose", "")).strip().lower()
            phase = phase_order.get(purpose, 1)
            if phase == 2 and first_verify_idx is None:
                first_verify_idx = idx
            if phase == 1 and first_remediate_idx is None:
                first_remediate_idx = idx

        if first_verify_idx is None or first_remediate_idx is None:
            return spec
        if first_verify_idx > first_remediate_idx:
            return spec

        logger.info(f"Auto-fix: verify step found at index {first_verify_idx} before first remediate at {first_remediate_idx}. Moving verify steps to end.")

        non_verify_steps = []
        verify_steps = []
        for step in spec["steps"]:
            if not isinstance(step, dict):
                non_verify_steps.append(step)
                continue
            purpose = str(step.get("purpose", "")).strip().lower()
            if phase_order.get(purpose, 1) == 2:
                verify_steps.append(step)
            else:
                non_verify_steps.append(step)

        reordered_steps = non_verify_steps + verify_steps
        for new_idx, step in enumerate(reordered_steps, 1):
            if isinstance(step, dict):
                step["step_number"] = new_idx

        spec["steps"] = reordered_steps
        logger.info(f"Auto-fix: Reordered steps — {len(non_verify_steps)} non-verify + {len(verify_steps)} verify at end.")
        return spec

    def _auto_fix_step_purposes(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fix: Correct step purposes based on command and name keywords.
        Detects mismatches like purpose="diagnose" but command has "restart".
        """
        from app.config import runbook_validation

        if "steps" not in spec or not isinstance(spec["steps"], list) or not spec["steps"]:
            return spec

        remediation_keywords = runbook_validation.REMEDIATION_KEYWORDS
        diagnostic_keywords = runbook_validation.DIAGNOSTIC_KEYWORDS
        corrections_made = 0

        for step in spec["steps"]:
            if not isinstance(step, dict):
                continue
            purpose = str(step.get("purpose", "")).strip().lower()
            if not purpose or purpose not in ["diagnose", "remediate", "verify"]:
                continue

            step_name = str(step.get("name", "")).lower()
            step_desc = str(step.get("description", "")).lower()
            if "escalate" in step_name or "escalate" in step_desc:
                if purpose == "verify":
                    logger.debug(f"Step '{step.get('name')}' is an escalation step with purpose 'verify' (correct)")

            command = str(step.get("command", "")).lower()
            name = str(step.get("name", "")).lower()
            combined_text = f"{command} {name}"

            has_remediation_keywords = any(kw in combined_text for kw in remediation_keywords)
            has_diagnostic_keywords = any(kw in combined_text for kw in diagnostic_keywords)

            if "status" in combined_text or "is-active" in combined_text or "is-enabled" in combined_text:
                has_diagnostic_keywords = True
            if "truncate" in combined_text or "rm " in combined_text or "rm -" in combined_text:
                has_remediation_keywords = True

            should_be_remediate = has_remediation_keywords
            should_be_diagnose = has_diagnostic_keywords and not has_remediation_keywords

            corrected_purpose = None
            if purpose == "diagnose" and should_be_remediate:
                corrected_purpose = "remediate"
            elif purpose == "remediate" and should_be_diagnose:
                corrected_purpose = "diagnose"
            elif purpose == "verify" and should_be_remediate:
                strong_remediation = any(kw in combined_text for kw in ["kill", "delete", "remove", "clear", "fix", "repair"])
                if strong_remediation:
                    corrected_purpose = "remediate"

            if corrected_purpose:
                old_purpose = purpose
                step["purpose"] = corrected_purpose
                corrections_made += 1
                logger.info(f"Auto-fix: Corrected purpose for step '{step.get('name', 'Unknown')[:50]}': {old_purpose} → {corrected_purpose} (command: {command[:60] or 'N/A'})")

        if corrections_made > 0:
            logger.info(f"Auto-fix: Corrected {corrections_made} step purpose(s) based on command keywords")
        return spec
