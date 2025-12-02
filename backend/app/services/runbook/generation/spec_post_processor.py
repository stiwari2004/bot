"""
Post-processing for runbook spec to fix common LLM formatting issues
"""
import re
from typing import Dict, Any
from app.config import runbook_structure
from app.core.logging import get_logger

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
        """Fix incomplete steps"""
        if "steps" in spec and isinstance(spec["steps"], list):
            cleaned_steps = []
            for step in spec["steps"]:
                if isinstance(step, dict):
                    step_type = step.get("type", "command")
                    command_value = step.get("command")
                    
                    if step_type == "command":
                        if not command_value or (isinstance(command_value, str) and not command_value.strip()):
                            logger.warning(f"Removing step with missing/empty command: {step.get('name', 'N/A')}")
                            continue
                    
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

