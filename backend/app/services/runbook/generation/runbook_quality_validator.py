"""
RunbookQualityValidator centralizes structural and grounding checks for LLM-generated runbooks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.core.logging import get_logger
from app.config import runbook_structure, runbook_validation


class RunbookQualityValidator:
    """Validate generated runbook specs before persisting/executing them."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def validate(self, spec: Dict[str, Any], issue_description: str) -> tuple[bool, List[str]]:
        """Validate generated runbook structure and content."""
        errors: List[str] = []

        inputs = spec.get("inputs", [])
        defined_input_names: Set[str] = set()
        if isinstance(inputs, list):
            for inp in inputs:
                if isinstance(inp, dict):
                    input_name = inp.get("name", "")
                    if input_name:
                        defined_input_names.add(input_name)
                    
                    if "command" in inp:
                        errors.append(
                            f"CRITICAL: inputs section contains a command '{inp.get('name', 'unknown')}' - "
                            f"commands belong in prechecks/steps/postchecks, NOT in inputs! "
                            f"Inputs should only have: name, type, required, description"
                        )
                    if inp.get("type") == "command":
                        errors.append(
                            f"CRITICAL: input '{inp.get('name', 'unknown')}' has type='command' - "
                            f"inputs should have type='string', not 'command'! "
                            f"Commands belong in prechecks/steps/postchecks sections"
                        )
        
        # Validate that all referenced placeholders are defined in inputs
        input_validation_errors = self._validate_input_references(spec, defined_input_names)
        errors.extend(input_validation_errors)

        prechecks = spec.get(runbook_structure.SECTION_PRECHECKS, [])
        if not isinstance(prechecks, list):
            errors.append("CRITICAL: prechecks must be a list")
        elif not (runbook_structure.PRECHECKS_MIN <= len(prechecks) <= runbook_structure.PRECHECKS_MAX):
            errors.append(
                f"prechecks must have between {runbook_structure.PRECHECKS_MIN} and {runbook_structure.PRECHECKS_MAX} steps, "
                f"found {len(prechecks)}."
            )

        steps = spec.get(runbook_structure.SECTION_STEPS, [])
        if not isinstance(steps, list):
            errors.append("CRITICAL: steps must be a list")
        elif len(steps) < runbook_structure.STEPS_MIN or len(steps) > runbook_structure.STEPS_MAX:
            errors.append(
                f"CRITICAL: steps must have EXACTLY {runbook_structure.STEPS_MIN}-{runbook_structure.STEPS_MAX} steps, found {len(steps)}. "
                f"This is a hard requirement - the runbook will be rejected if not {runbook_structure.STEPS_MIN}-{runbook_structure.STEPS_MAX} steps."
            )

        postchecks = spec.get(runbook_structure.SECTION_POSTCHECKS, [])
        if not isinstance(postchecks, list):
            errors.append("CRITICAL: postchecks must be a list")
        elif not (runbook_structure.POSTCHECKS_MIN <= len(postchecks) <= runbook_structure.POSTCHECKS_MAX):
            errors.append(
                f"postchecks must have between {runbook_structure.POSTCHECKS_MIN} and {runbook_structure.POSTCHECKS_MAX} steps, "
                f"found {len(postchecks)}."
            )

        issue_lower = issue_description.lower()
        metric_keywords = runbook_validation.METRIC_KEYWORDS

        detected_metric: Optional[str] = None
        for metric, keywords in metric_keywords.items():
            if any(keyword in issue_lower for keyword in keywords):
                detected_metric = metric
                break

        if detected_metric:
            precheck_commands = [str(p.get("command", "")).lower() for p in prechecks if isinstance(p, dict)]
            metric_found = self._contains_metric(precheck_commands, metric_keywords.get(detected_metric, []))
            if not metric_found:
                errors.append(
                    f"precheck should check the actual metric '{detected_metric}' mentioned in issue, "
                    f"but no precheck command mentions it"
                )

        if detected_metric and postchecks:
            postcheck_commands = [str(p.get("command", "")).lower() for p in postchecks if isinstance(p, dict)]
            metric_found = self._contains_metric(postcheck_commands, metric_keywords.get(detected_metric, []))
            if not metric_found:
                errors.append(
                    f"postcheck should verify resolution of '{detected_metric}', "
                    f"but postcheck command doesn't mention it"
                )

        (
            remediation_count,
            diagnostic_only_count,
            step_errors,
        ) = self._validate_step_metadata(steps, detected_metric)
        errors.extend(step_errors)

        if remediation_count < runbook_structure.MIN_REMEDIATION_STEPS:
            errors.append(
                f"CRITICAL: steps section must include at least {runbook_structure.MIN_REMEDIATION_STEPS} REMEDIATION actions "
                f"(kill, restart, stop, clear, fix, repair, etc.), but found only {remediation_count}. "
                f"With {runbook_structure.STEPS_MIN}-{runbook_structure.STEPS_MAX} total steps, at least {runbook_structure.MIN_REMEDIATION_STEPS} must be remediation to ensure the issue is actually solved. "
                f"Purely diagnostic runbooks are INVALID and will be REJECTED. "
                f"Your runbook must SOLVE the problem, not just investigate it."
            )

        if runbook_structure.MAX_DIAGNOSTIC_ONLY_STEPS is not None and diagnostic_only_count > runbook_structure.MAX_DIAGNOSTIC_ONLY_STEPS:
            errors.append(
                f"WARNING: Found {diagnostic_only_count} diagnostic-only steps. "
                f"Runbooks should focus on REMEDIATION (fixing the issue), not just investigation."
            )

        title = spec.get("title", "").lower()
        if title and issue_description:
            issue_words = set(issue_description.lower().split())
            title_words = set(title.split())
            stop_words = runbook_validation.STOP_WORDS
            issue_keywords = issue_words - stop_words
            title_keywords = title_words - stop_words

            if issue_keywords and not (issue_keywords & title_keywords):
                errors.append(
                    f"title '{spec.get('title')}' doesn't match issue description keywords"
                )

        return len(errors) == 0, errors

    @staticmethod
    def _contains_metric(commands: List[str], keywords: List[str]) -> bool:
        return any(keyword in cmd for keyword in keywords for cmd in commands)

    def _validate_step_metadata(
        self,
        steps: List[Dict[str, Any]],
        detected_metric: Optional[str],
    ) -> tuple[int, int, List[str]]:
        allowed_purposes = runbook_validation.ALLOWED_PURPOSES
        phase_order = runbook_validation.PHASE_ORDER
        current_phase = 0
        remediation_count = 0
        diagnostic_only_count = 0
        available_variables: Set[str] = set()
        errors: List[str] = []

        remediation_keywords = runbook_validation.REMEDIATION_KEYWORDS
        diagnostic_keywords = runbook_validation.DIAGNOSTIC_KEYWORDS

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"CRITICAL: step {idx + 1} is not a dictionary")
                continue

            purpose = str(step.get("purpose", "")).strip().lower()
            if not purpose:
                errors.append(
                    f"CRITICAL: step {idx + 1} ('{step.get('name', 'unknown')}') is missing the 'purpose' field."
                )
            elif purpose not in allowed_purposes:
                errors.append(
                    f"CRITICAL: step {idx + 1} ('{step.get('name', 'unknown')}') has invalid purpose '{purpose}'. "
                    f"Allowed values: {', '.join(sorted(allowed_purposes))}"
                )
            else:
                step_phase = phase_order.get(purpose, current_phase)
                # Only block verify/postcheck before any remediation — allow diagnose after remediate (iterative pattern)
                if purpose in {"verify", "postcheck"} and remediation_count == 0:
                    errors.append(
                        f"CRITICAL: step {idx + 1} ('{step.get('name', 'unknown')}') — "
                        "verify/postcheck steps cannot appear before any remediation steps."
                    )
                # Allow diagnose steps to appear after remediate steps (diagnose→remediate→diagnose→remediate→verify is valid)
                # Only block if a verify step appears before the end
                current_phase = max(current_phase, step_phase) if purpose not in {"diagnose", "precheck"} else current_phase

            command_text = str(step.get("command", "")).lower()
            name_text = str(step.get("name", "")).lower()

            is_remediation = purpose == "remediate"
            is_diagnostic = purpose in {"diagnose", "precheck"}

            if not purpose:
                if any(keyword in command_text or keyword in name_text for keyword in remediation_keywords):
                    is_remediation = True
                elif any(keyword in command_text or keyword in name_text for keyword in diagnostic_keywords):
                    is_diagnostic = True

            if is_remediation:
                remediation_count += 1
            elif is_diagnostic:
                diagnostic_only_count += 1

            deps = step.get("depends_on")
            if deps:
                if not isinstance(deps, list):
                    errors.append(
                        f"CRITICAL: step {idx + 1} depends_on must be a list of variable names."
                    )
                else:
                    for dep in deps:
                        if not isinstance(dep, str):
                            errors.append(
                                f"CRITICAL: step {idx + 1} has non-string dependency '{dep}'."
                            )
                            continue
                        if dep not in available_variables:
                            errors.append(
                                f"CRITICAL: step {idx + 1} references dependency '{dep}' "
                                f"which has not been captured by any prior step."
                            )

            captured_var = step.get("captures_variable")
            if captured_var:
                if not isinstance(captured_var, str):
                    errors.append(
                        f"CRITICAL: step {idx + 1} captures_variable must be a string."
                    )
                elif captured_var in available_variables:
                    errors.append(
                        f"CRITICAL: variable '{captured_var}' is captured multiple times. "
                        f"Variable names must be unique."
                    )
                else:
                    available_variables.add(captured_var)

            requires_metric = step.get("requires_metric")
            if requires_metric and detected_metric:
                metric_str = str(requires_metric).lower()
                if detected_metric not in metric_str:
                    errors.append(
                        f"WARNING: step {idx + 1} expects metric '{requires_metric}' "
                        f"but detected issue metric is '{detected_metric}'."
                    )

        return remediation_count, diagnostic_only_count, errors
    
    def _validate_input_references(
        self,
        spec: Dict[str, Any],
        defined_input_names: Set[str]
    ) -> List[str]:
        """
        Validate that all placeholders ({{variable_name}}) used in commands
        are defined in the inputs section.
        
        Args:
            spec: Runbook specification
            defined_input_names: Set of input names defined in inputs section
            
        Returns:
            List of error messages for missing input references
        """
        import re
        errors: List[str] = []
        
        # Pattern to match {{variable_name}} placeholders
        placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
        
        # Check prechecks
        prechecks = spec.get("prechecks", [])
        for idx, precheck in enumerate(prechecks, 1):
            if isinstance(precheck, dict):
                command = precheck.get("command", "")
                if command:
                    placeholders = placeholder_pattern.findall(command)
                    for placeholder in placeholders:
                        if placeholder not in defined_input_names:
                            errors.append(
                                f"CRITICAL: precheck {idx} references undefined input '{{{{{placeholder}}}}}'. "
                                f"Add '{placeholder}' to the inputs section with: name, type: string, required, description"
                            )
        
        # Check steps
        steps = spec.get("steps", [])
        
        # Collect all valid step numbers once (for branching validation)
        valid_step_numbers: Set[int] = set()
        for step_idx, s in enumerate(steps, 1):
            if isinstance(s, dict):
                explicit_step_num = s.get("step_number")
                if explicit_step_num is not None:
                    valid_step_numbers.add(explicit_step_num)
                else:
                    # If no explicit step_number, use sequential index
                    valid_step_numbers.add(step_idx)
        
        for idx, step in enumerate(steps, 1):
            if isinstance(step, dict):
                step_name = step.get("name", f"Step {idx}")
                command = step.get("command", "")
                if command:
                    placeholders = placeholder_pattern.findall(command)
                    for placeholder in placeholders:
                        if placeholder not in defined_input_names:
                            errors.append(
                                f"CRITICAL: step {idx} ('{step_name}') references undefined input '{{{{{placeholder}}}}}'. "
                                f"Add '{placeholder}' to the inputs section with: name, type: string, required, description"
                            )
                
                # Validate branching step numbers reference valid steps
                on_success = step.get("on_success")
                on_failure = step.get("on_failure")
                
                if on_success is not None:
                    if on_success not in valid_step_numbers:
                        errors.append(
                            f"CRITICAL: step {idx} ('{step_name}') has on_success={on_success}, "
                            f"but no step with step_number={on_success} exists. "
                            f"Valid step numbers are: {sorted(valid_step_numbers)}. "
                            f"All branching targets must reference valid step numbers."
                        )
                
                if on_failure is not None:
                    if on_failure not in valid_step_numbers:
                        errors.append(
                            f"CRITICAL: step {idx} ('{step_name}') has on_failure={on_failure}, "
                            f"but no step with step_number={on_failure} exists. "
                            f"Valid step numbers are: {sorted(valid_step_numbers)}. "
                            f"All branching targets must reference valid step numbers."
                        )
        
        # Check postchecks
        postchecks = spec.get("postchecks", [])
        for idx, postcheck in enumerate(postchecks, 1):
            if isinstance(postcheck, dict):
                command = postcheck.get("command", "")
                if command:
                    placeholders = placeholder_pattern.findall(command)
                    for placeholder in placeholders:
                        if placeholder not in defined_input_names:
                            errors.append(
                                f"CRITICAL: postcheck {idx} references undefined input '{{{{{placeholder}}}}}'. "
                                f"Add '{placeholder}' to the inputs section with: name, type: string, required, description"
                            )
        
        return errors

