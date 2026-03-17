"""
Mixin: input-related post-processing fixes for SpecPostProcessor
"""
import re
from typing import Dict, Any

from app.config import runbook_structure
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpecInputFixersMixin:
    """Input-related fix operations for SpecPostProcessor."""

    def _fix_inputs_section(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix inputs section if it contains commands"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            valid_inputs = []
            commands_to_move = []
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    if inp.get("type") == "command" or "command" in inp:
                        logger.warning(f"CRITICAL: Found command in inputs section: '{inp.get('name', 'unknown')}'. Moving to steps section.")
                        commands_to_move.append({
                            "name": inp.get("name", "Unknown step"),
                            "type": "command",
                            "command": inp.get("command", ""),
                            "expected_output": inp.get("expected_output", "Command executed successfully"),
                            "skip_in_auto_mode": False,
                            "severity": inp.get("severity", "safe"),
                        })
                    else:
                        valid_inputs.append(inp)
            spec["inputs"] = valid_inputs
            if commands_to_move:
                if "steps" not in spec or not isinstance(spec["steps"], list):
                    spec["steps"] = []
                spec["steps"] = commands_to_move + spec["steps"]
                logger.warning(f"Moved {len(commands_to_move)} command(s) from inputs to steps section. Total steps now: {len(spec['steps'])}")
        return spec

    def _fix_inputs_dict(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Fix inputs if it's a dict instead of list"""
        if "inputs" in spec and isinstance(spec["inputs"], dict):
            fixed_inputs = [
                {"name": name, "type": "string", "required": True, "description": f"Parameter: {name}"}
                for name in spec["inputs"]
            ]
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
                logger.warning("Adding missing server_name input (commands use {server_name})")
                spec["inputs"].insert(0, {"name": "server_name", "type": "string", "required": True, "description": "Target server hostname or IP address"})
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
                logger.warning("Adding missing database_name input (commands use {database_name})")
                spec["inputs"].append({"name": "database_name", "type": "string", "required": True, "description": "Database name (input parameter for execution)"})
        return spec

    def _normalize_server_inputs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """For server runbooks: keep only server_name input; replace port/other placeholders with defaults."""
        service = (spec.get("service") or "").strip().lower()
        if service != "server" or "inputs" not in spec or not isinstance(spec["inputs"], list):
            return spec
        input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict) and inp.get("name")]
        if not input_names:
            return spec
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
        """Auto-fix: Automatically add missing inputs that are referenced in commands."""
        if "inputs" not in spec:
            spec["inputs"] = []
        if not isinstance(spec["inputs"], list):
            return spec
        defined_input_names = {inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict) and inp.get("name")}
        placeholder_pattern = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
        referenced_placeholders: set = set()
        for section in [runbook_structure.SECTION_PRECHECKS, runbook_structure.SECTION_STEPS, runbook_structure.SECTION_POSTCHECKS]:
            if section in spec and isinstance(spec[section], list):
                for item in spec[section]:
                    if isinstance(item, dict):
                        command = item.get("command", "")
                        if command:
                            referenced_placeholders.update(placeholder_pattern.findall(command))
        missing_inputs = referenced_placeholders - defined_input_names
        if missing_inputs:
            logger.info(f"Auto-fixing: Adding {len(missing_inputs)} missing input(s): {sorted(missing_inputs)}")
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
            for missing_input in sorted(missing_inputs):
                if missing_input in ["SERVER_NAME", "DATABASE_NAME"]:
                    continue
                description = input_descriptions.get(missing_input, f"{missing_input.replace('_', ' ').title()} parameter")
                required = missing_input not in ["interface", "client_interface", "firewall_tool", "username", "password"]
                default_value = None
                if missing_input in ["interface", "client_interface"]:
                    default_value = "eth0"
                elif missing_input == "firewall_tool":
                    default_value = "ufw"
                new_input = {"name": missing_input, "type": "string", "required": required, "description": description}
                if default_value:
                    new_input["default"] = default_value
                spec["inputs"].append(new_input)
                logger.info(f"  Added input: {missing_input} (required={required}, description='{description}')")
        return spec

    def _fix_input_descriptions(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all inputs have proper description fields"""
        if "inputs" in spec and isinstance(spec["inputs"], list):
            default_descriptions = {
                "server_name": "Target server hostname or IP address",
                "database_name": "Database name (input parameter for execution)",
            }
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    name = inp.get("name")
                    if name and not inp.get("description") and name in default_descriptions:
                        logger.warning(f"Adding missing description for input '{name}'")
                        inp["description"] = default_descriptions[name]
        return spec
