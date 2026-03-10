"""
Post-processing for runbook spec to fix common LLM formatting issues
"""
import re
from typing import Dict, Any
from app.config import runbook_structure
from app.core.logging import get_logger
from app.services.execution.ssh_command_utils import strip_ssh_wrapper

logger = get_logger(__name__)


class SpecPostProcessor:
    """Post-processes YAML spec to fix common LLM formatting issues"""
    
    def post_process(self, spec: Dict[str, Any], issue_description: str, env: str, risk: str) -> Dict[str, Any]:
        """
        Post-process YAML spec to fix common LLM formatting issues.
        
        Args:
            spec: Parsed YAML spec dictionary
            issue_description: Original issue description
            env: Environment (prod, staging, dev)
            risk: Risk level (low, medium, high)
            
        Returns:
            Post-processed spec dictionary
        """
        # Fix inputs section if it contains commands
        spec = self._fix_inputs_section(spec)
        
        # Fix inputs if it's a dict instead of list
        spec = self._fix_inputs_dict(spec)
        
        # Fix postchecks if it's a single dict instead of a list
        spec = self._fix_postchecks_dict(spec)
        
        # Fix incomplete commands and ensure expected_output for checks
        spec = self._fix_incomplete_checks(spec)
        
        # Fix incomplete steps
        spec = self._fix_incomplete_steps(spec)
        
        # Strip ssh host "..." wrapper from commands - connector handles connection; stored commands must be raw
        spec = self._strip_ssh_wrappers_from_commands(spec)
        
        # Ensure required fields with defaults
        if "env" not in spec:
            spec["env"] = env
        if "risk" not in spec:
            spec["risk"] = risk
        
        # Fix description field if it's copying from inputs
        spec = self._fix_description_field(spec, issue_description)
        
        # Ensure server_name is in inputs if commands use it
        spec = self._ensure_server_name_input(spec)
        
        # Ensure database_name is in inputs if commands use it
        spec = self._ensure_database_name_input(spec)
        
        # Auto-fix: Add any missing inputs that are referenced in commands
        spec = self._auto_add_missing_inputs(spec)
        
        # Server runbooks: keep only server_name input (no node_exporter_port etc.)
        spec = self._normalize_server_inputs(spec)
        
        # Auto-fix: Correct step purposes FIRST (based on command keywords)
        # This must run before step ordering so purposes are correct when we reorder
        spec = self._auto_fix_step_purposes(spec)
        
        # Auto-fix: Reorder steps to follow correct phase order (diagnose → remediate → verify)
        # This runs after purpose correction so steps are ordered by their corrected purposes
        spec = self._auto_fix_step_ordering(spec)
        
        # Ensure all inputs have proper description fields
        spec = self._fix_input_descriptions(spec)
        
        # Ensure runbook_id is properly formatted
        spec = self._fix_runbook_id(spec)
        
        return spec
    
    def _fix_inputs_section(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix inputs section if it contains commands"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            valid_inputs = []
            commands_to_move = []
            
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    if inp.get("type") == "command" or "command" in inp:
                        logger.warning(
                            f"CRITICAL: Found command in inputs section: '{inp.get('name', 'unknown')}'. "
                            f"Moving to steps section."
                        )
                        step = {
                            "name": inp.get("name", "Unknown step"),
                            "type": "command",
                            "command": inp.get("command", ""),
                            "expected_output": inp.get("expected_output", "Command executed successfully"),
                            "skip_in_auto_mode": False,
                            "severity": inp.get("severity", "safe")
                        }
                        commands_to_move.append(step)
                    else:
                        valid_inputs.append(inp)
            
            spec["inputs"] = valid_inputs
            
            if commands_to_move:
                if "steps" not in spec:
                    spec["steps"] = []
                if not isinstance(spec["steps"], list):
                    spec["steps"] = []
                spec["steps"] = commands_to_move + spec["steps"]
                logger.warning(
                    f"Moved {len(commands_to_move)} command(s) from inputs to steps section. "
                    f"Total steps now: {len(spec['steps'])}"
                )
        
        return spec
    
    def _fix_inputs_dict(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix inputs if it's a dict instead of list"""
        if "inputs" in spec and isinstance(spec["inputs"], dict):
            fixed_inputs = []
            for name, value in spec["inputs"].items():
                fixed_inputs.append({
                    "name": name,
                    "type": "string",
                    "required": True,
                    "description": f"Parameter: {name}"
                })
            spec["inputs"] = fixed_inputs
            logger.debug(f"Fixed inputs: converted dict to list format with {len(fixed_inputs)} items")
        
        return spec
    
    def _fix_postchecks_dict(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix postchecks if it's a single dict instead of a list"""
        if "postchecks" in spec and isinstance(spec["postchecks"], dict):
            spec["postchecks"] = [spec["postchecks"]]
            logger.debug("Fixed postchecks: converted single dict to list format")
        
        return spec
    
    def _fix_incomplete_checks(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix incomplete commands and ensure expected_output for checks"""
        for section_name in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_POSTCHECKS]:
            if section_name in spec and isinstance(spec[section_name], list):
                cleaned_checks = []
                for check in spec[section_name]:
                    if isinstance(check, dict):
                        command = check.get("command")
                        if not command or not command.strip():
                            logger.warning(f"Removing {section_name} item with missing command: {check.get('description', 'N/A')}")
                            continue
                        if not check.get("expected_output"):
                            check["expected_output"] = "Command executed successfully"
                            logger.warning(f"Added default expected_output to {section_name} item: {check.get('description', 'N/A')}")
                        cleaned_checks.append(check)
                spec[section_name] = cleaned_checks
        
        return spec
    
    def _fix_incomplete_steps(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix incomplete steps. Use description/name as command fallback before removing."""
        if "steps" in spec and isinstance(spec["steps"], list):
            cleaned_steps = []
            for step in spec["steps"]:
                if isinstance(step, dict):
                    step_type = step.get("type", "command")
                    command_value = step.get("command")
                    if isinstance(command_value, str):
                        command_value = command_value.strip() or None
                    else:
                        command_value = None

                    if step_type == "command" and not command_value:
                        # Keep the step: use description or name as command fallback so we never drop steps
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
                    continue
            
            if not cleaned_steps:
                raise ValueError("All steps were removed due to missing commands")
            spec["steps"] = cleaned_steps
        
        return spec
    
    def _strip_ssh_wrappers_from_commands(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Strip 'ssh host "cmd"' / 'ssh {{server_name}} \"cmd\"' from commands. Connector handles connection."""
        for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
            if section not in spec or not isinstance(spec[section], list):
                continue
            for item in spec[section]:
                if isinstance(item, dict) and item.get("command"):
                    cmd = str(item["command"]).strip()
                    stripped = strip_ssh_wrapper(cmd)
                    if stripped != cmd:
                        item["command"] = stripped
                        logger.info(f"Stripped ssh wrapper from {section} command: ... -> {stripped[:60]}...")
        return spec
    
    def _fix_description_field(self, spec: Dict[str, Any], issue_description: str) -> Dict[str, Any]:
        """Fix description field if it's copying from inputs"""
        if "description" in spec:
            description = str(spec["description"]).strip()
            input_description_texts = [
                "Database name (input parameter for execution)",
                "Name of the database to troubleshoot",
                "Target server hostname or IP address",
                "Database name (required for database issues)",
                "Parameter: server_name",
                "Parameter: database_name"
            ]
            if any(text in description for text in input_description_texts) or len(description) < 50:
                logger.warning(f"Fixing description field: was '{description[:100]}'")
                spec["description"] = f"The {issue_description.lower()}. This issue requires immediate attention to prevent service disruption and data loss."
                logger.info(f"Fixed description to: {spec['description'][:100]}...")
        
        return spec
    
    def _ensure_server_name_input(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure server_name is in inputs if commands use it"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict)]
            all_commands = []
            for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
                if section in spec and isinstance(spec[section], list):
                    for item in spec[section]:
                        if isinstance(item, dict) and "command" in item:
                            all_commands.append(str(item["command"]))
            
            uses_server_name = any("{{server_name}}" in cmd or "__SERVER_NAME__" in cmd for cmd in all_commands)
            if uses_server_name and "server_name" not in input_names:
                logger.warning(f"Adding missing server_name input (commands use {{server_name}})")
                spec["inputs"].insert(0, {
                    "name": "server_name",
                    "type": "string",
                    "required": True,
                    "description": "Target server hostname or IP address"
                })
        
        return spec
    
    def _ensure_database_name_input(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure database_name is in inputs if commands use it"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict)]
            all_commands = []
            for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
                if section in spec and isinstance(spec[section], list):
                    for item in spec[section]:
                        if isinstance(item, dict) and "command" in item:
                            all_commands.append(str(item["command"]))
            
            uses_database_name = any("{{database_name}}" in cmd or "__DATABASE_NAME__" in cmd for cmd in all_commands)
            if uses_database_name and "database_name" not in input_names:
                logger.warning(f"Adding missing database_name input (commands use {{database_name}})")
                spec["inputs"].append({
                    "name": "database_name",
                    "type": "string",
                    "required": True,
                    "description": "Database name (input parameter for execution)"
                })
        
        return spec
    
    def _normalize_server_inputs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """For server runbooks: keep only server_name input; replace port/other placeholders in commands with defaults."""
        service = (spec.get("service") or "").strip().lower()
        if service != "server" or "inputs" not in spec or not isinstance(spec["inputs"], list):
            return spec
        input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict) and inp.get("name")]
        if not input_names:
            return spec
        # Allow only server_name (and database_name for DB-related server runbooks - leave that for now)
        allowed = {"server_name", "database_name"}
        to_keep = [inp for inp in spec["inputs"] if isinstance(inp, dict) and inp.get("name") in allowed]
        if not to_keep and "server_name" not in input_names:
            to_keep = [{"name": "server_name", "type": "string", "required": True, "description": "Target server hostname or IP address"}]
        elif "server_name" not in [inp.get("name") for inp in to_keep if isinstance(inp, dict)]:
            to_keep.insert(0, {"name": "server_name", "type": "string", "required": True, "description": "Target server hostname or IP address"})
        removed = set(input_names) - {inp.get("name") for inp in to_keep if isinstance(inp, dict)}
        if removed:
            logger.info(f"Server runbook: normalizing inputs to server_name only; removed: {removed}")
            spec["inputs"] = to_keep
        # Replace common port placeholders with default so commands still work with one input
        defaults = {"node_exporter_port": "9100", "port": "9100"}
        for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
            if section not in spec or not isinstance(spec[section], list):
                continue
            for item in spec[section]:
                if isinstance(item, dict) and item.get("command"):
                    cmd = str(item["command"])
                    for ph, val in defaults.items():
                        if "{{" + ph + "}}" in cmd and ph in removed:
                            cmd = cmd.replace("{{" + ph + "}}", val)
                            item["command"] = cmd
                            logger.debug(f"Replaced {{{ph}}} with {val} in command")
        return spec
    
    def _auto_add_missing_inputs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fix: Automatically add missing inputs that are referenced in commands.
        This prevents validation errors by adding inputs before validation runs.
        """
        import re
        
        if "inputs" not in spec:
            spec["inputs"] = []
        if not isinstance(spec["inputs"], list):
            return spec
        
        # Get all defined input names
        defined_input_names = {inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict) and inp.get("name")}
        
        # Pattern to match {{variable_name}} placeholders
        placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
        
        # Collect all referenced placeholders from all commands
        referenced_placeholders: set = set()
        
        # Check prechecks, steps, and postchecks
        for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
            if section in spec and isinstance(spec[section], list):
                for item in spec[section]:
                    if isinstance(item, dict):
                        command = item.get("command", "")
                        if command:
                            placeholders = placeholder_pattern.findall(command)
                            referenced_placeholders.update(placeholders)
        
        # Find missing inputs
        missing_inputs = referenced_placeholders - defined_input_names
        
        if missing_inputs:
            logger.info(f"Auto-fixing: Adding {len(missing_inputs)} missing input(s): {sorted(missing_inputs)}")
            
            # Common input descriptions based on name patterns
            input_descriptions = {
                "server_name": "Target server hostname or IP address",
                "database_name": "Database name",
                "vpn_service_name": "Name of the VPN service (e.g., openvpn, strongswan)",
                "vpn_server_ip": "IP address of the VPN server",
                "vpn_server_hostname": "Hostname of the VPN server",
                "host_ip": "Target host IP address",
                "gateway_ip": "Gateway or router IP address",
                "interface": "Network interface name (e.g., eth0, ens33)",
                "client_interface": "Client network interface name",
                "firewall_tool": "Firewall management tool (e.g., ufw, iptables)",
                "app_url": "Application URL",
                "mount_point": "File system mount point",
                "storage_server": "Storage server hostname or IP",
                "share_name": "Network share name",
                "username": "Username for authentication",
                "password": "Password for authentication",
            }
            
            # Add missing inputs with sensible defaults
            for missing_input in sorted(missing_inputs):
                # Skip if it's a common variable that shouldn't be an input
                if missing_input in ["SERVER_NAME", "DATABASE_NAME"]:  # Legacy placeholders
                    continue
                
                description = input_descriptions.get(
                    missing_input,
                    f"{missing_input.replace('_', ' ').title()} parameter"
                )
                
                # Determine if required based on common patterns
                required = missing_input not in ["interface", "client_interface", "firewall_tool", "username", "password"]
                
                # Add default values for common optional inputs
                default_value = None
                if missing_input in ["interface", "client_interface"]:
                    default_value = "eth0"
                elif missing_input == "firewall_tool":
                    default_value = "ufw"
                
                new_input = {
                    "name": missing_input,
                    "type": "string",
                    "required": required,
                    "description": description
                }
                
                if default_value:
                    new_input["default"] = default_value
                
                spec["inputs"].append(new_input)
                logger.info(f"  ✓ Added input: {missing_input} (required={required}, description='{description}')")
        
        return spec
    
    def _auto_fix_step_ordering(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fix: Only reorder steps when there is a clear structural violation.
        Preserves iterative diagnose→remediate→diagnose→remediate→verify patterns.
        Only intervenes when: verify appears before any remediate step.
        """
        from app.config import runbook_validation

        if "steps" not in spec or not isinstance(spec["steps"], list):
            return spec

        steps = spec["steps"]
        if not steps:
            return spec

        phase_order = runbook_validation.PHASE_ORDER

        # Detect if there is a structural violation: verify before any remediate
        first_verify_idx = None
        first_remediate_idx = None
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            purpose = str(step.get("purpose", "")).strip().lower()
            phase = phase_order.get(purpose, 1)
            if phase == 2 and first_verify_idx is None:  # verify/postcheck
                first_verify_idx = idx
            if phase == 1 and first_remediate_idx is None:  # remediate
                first_remediate_idx = idx

        # No violation: preserve LLM's ordering exactly
        if first_verify_idx is None or first_remediate_idx is None:
            return spec
        if first_verify_idx > first_remediate_idx:
            return spec  # verify comes after remediate — correct order, no change needed

        # Violation detected: verify appears before any remediate step
        # Move verify steps to the end, preserve everything else in order
        logger.info(
            f"Auto-fix: verify step found at index {first_verify_idx} before first remediate at "
            f"{first_remediate_idx}. Moving verify steps to end."
        )

        non_verify_steps = []
        verify_steps = []
        for step in steps:
            if not isinstance(step, dict):
                non_verify_steps.append(step)
                continue
            purpose = str(step.get("purpose", "")).strip().lower()
            phase = phase_order.get(purpose, 1)
            if phase == 2:  # verify/postcheck
                verify_steps.append(step)
            else:
                non_verify_steps.append(step)

        reordered_steps = non_verify_steps + verify_steps

        # Renumber step_number fields sequentially
        for new_idx, step in enumerate(reordered_steps, 1):
            if isinstance(step, dict):
                step["step_number"] = new_idx

        spec["steps"] = reordered_steps
        logger.info(
            f"Auto-fix: Reordered steps — {len(non_verify_steps)} non-verify + {len(verify_steps)} verify at end."
        )
        return spec

        def _auto_fix_step_purposes(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-fix: Correct step purposes based on command and name keywords.
        Detects mismatches like:
        - purpose="diagnose" but command has "restart", "kill" → change to "remediate"
        - purpose="remediate" but command has only "get", "show", "list" → change to "diagnose"
        """
        from app.config import runbook_validation
        
        if "steps" not in spec or not isinstance(spec["steps"], list):
            return spec
        
        steps = spec["steps"]
        if not steps:
            return spec
        
        remediation_keywords = runbook_validation.REMEDIATION_KEYWORDS
        diagnostic_keywords = runbook_validation.DIAGNOSTIC_KEYWORDS
        
        corrections_made = 0
        
        for step in steps:
            if not isinstance(step, dict):
                continue
            
            purpose = str(step.get("purpose", "")).strip().lower()
            if not purpose or purpose not in ["diagnose", "remediate", "verify"]:
                continue
            
            # Fix escalation steps: if step name/description contains "escalate" but purpose is "verify",
            # keep it as "verify" (since "escalate" is not a valid purpose) but log it
            step_name = str(step.get("name", "")).lower()
            step_desc = str(step.get("description", "")).lower()
            if "escalate" in step_name or "escalate" in step_desc:
                if purpose == "verify":
                    # This is correct - escalation is a verification/final action
                    # But we can add a note in the description if needed
                    logger.debug(f"Step '{step.get('name')}' is an escalation step with purpose 'verify' (correct)")
            
            command = str(step.get("command", "")).lower()
            name = str(step.get("name", "")).lower()
            combined_text = f"{command} {name}"
            
            # Check for remediation keywords
            has_remediation_keywords = any(
                keyword in combined_text for keyword in remediation_keywords
            )
            
            # Check for diagnostic keywords
            has_diagnostic_keywords = any(
                keyword in combined_text for keyword in diagnostic_keywords
            )
            
            # Also check for common command patterns
            # "status" is diagnostic, "restart", "kill", "stop", "start" are remediation
            if "status" in combined_text or "is-active" in combined_text or "is-enabled" in combined_text:
                has_diagnostic_keywords = True
            if "truncate" in combined_text or "rm " in combined_text or "rm -" in combined_text:
                has_remediation_keywords = True
            
            # Determine what the purpose should be based on keywords
            # If both are present, prioritize remediation (action over observation)
            should_be_remediate = has_remediation_keywords
            should_be_diagnose = has_diagnostic_keywords and not has_remediation_keywords
            
            # Auto-correct mismatches
            corrected_purpose = None
            
            if purpose == "diagnose" and should_be_remediate:
                # Marked as diagnose but has remediation keywords → should be remediate
                corrected_purpose = "remediate"
            elif purpose == "remediate" and should_be_diagnose:
                # Marked as remediate but has only diagnostic keywords → should be diagnose
                corrected_purpose = "diagnose"
            elif purpose == "verify" and should_be_remediate:
                # Marked as verify but has remediation keywords → could be remediate or verify
                # Be conservative: only change if it's clearly a remediation action
                # (e.g., "restart" in verify step might be intentional, but "kill" should be remediate)
                strong_remediation = any(kw in combined_text for kw in ["kill", "delete", "remove", "clear", "fix", "repair"])
                if strong_remediation:
                    corrected_purpose = "remediate"
            
            if corrected_purpose:
                old_purpose = purpose
                step["purpose"] = corrected_purpose
                corrections_made += 1
                step_name = step.get("name", "Unknown")
                logger.info(
                    f"Auto-fix: Corrected purpose for step '{step_name[:50]}': "
                    f"{old_purpose} → {corrected_purpose} "
                    f"(command: {command[:60] if command else 'N/A'})"
                )
        
        if corrections_made > 0:
            logger.info(f"Auto-fix: Corrected {corrections_made} step purpose(s) based on command keywords")
        
        return spec
    
    def _fix_input_descriptions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all inputs have proper description fields"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            default_descriptions = {
                "server_name": "Target server hostname or IP address",
                "database_name": "Database name (input parameter for execution)"
            }
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    name = inp.get("name")
                    if name and not inp.get("description") and name in default_descriptions:
                        logger.warning(f"Adding missing description for input '{name}'")
                        inp["description"] = default_descriptions[name]
        
        return spec
    
    def _fix_runbook_id(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure runbook_id is properly formatted"""
        if "runbook_id" not in spec or not spec["runbook_id"]:
            title_slug = re.sub(r'[^a-z0-9]+', '-', spec.get("title", "runbook").lower()).strip('-')
            spec["runbook_id"] = f"rb-{spec.get('service', 'unknown')}-{title_slug[:30]}"
            logger.warning(f"Generated missing runbook_id: {spec['runbook_id']}")
        elif not spec["runbook_id"].startswith("rb-"):
            spec["runbook_id"] = f"rb-{spec['runbook_id'].lstrip('rb-')}"
            logger.warning(f"Fixed runbook_id format: {spec['runbook_id']}")
        
        return spec





