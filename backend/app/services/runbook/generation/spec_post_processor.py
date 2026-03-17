"""
Post-processing for runbook spec to fix common LLM formatting issues
"""
import re
from typing import Dict, Any

from app.config import runbook_structure
from app.core.logging import get_logger
from app.services.execution.ssh_command_utils import strip_ssh_wrapper
from app.services.runbook.generation.spec_input_fixers_mixin import SpecInputFixersMixin
from app.services.runbook.generation.spec_step_fixers_mixin import SpecStepFixersMixin

logger = get_logger(__name__)


class SpecPostProcessor(SpecInputFixersMixin, SpecStepFixersMixin):
    """Post-processes YAML spec to fix common LLM formatting issues"""

    def post_process(self, spec: Dict[str, Any], issue_description: str, env: str, risk: str) -> Dict[str, Any]:
        """Post-process YAML spec to fix common LLM formatting issues."""
        spec = self._fix_inputs_section(spec)
        spec = self._fix_inputs_dict(spec)
        spec = self._fix_postchecks_dict(spec)
        spec = self._fix_incomplete_checks(spec)
        spec = self._fix_incomplete_steps(spec)
        spec = self._strip_ssh_wrappers_from_commands(spec)

        if "env" not in spec:
            spec["env"] = env
        if "risk" not in spec:
            spec["risk"] = risk

        spec = self._fix_description_field(spec, issue_description)
        spec = self._ensure_server_name_input(spec)
        spec = self._ensure_database_name_input(spec)
        spec = self._auto_add_missing_inputs(spec)
        spec = self._normalize_server_inputs(spec)
        spec = self._auto_fix_step_purposes(spec)
        spec = self._auto_fix_step_ordering(spec)
        spec = self._fix_input_descriptions(spec)
        spec = self._fix_runbook_id(spec)
        return spec

    def _strip_ssh_wrappers_from_commands(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Strip 'ssh host "cmd"' wrappers from commands. Connector handles connection."""
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
                "Parameter: database_name",
            ]
            if any(text in description for text in input_description_texts) or len(description) < 50:
                logger.warning(f"Fixing description field: was '{description[:100]}'")
                spec["description"] = f"The {issue_description.lower()}. This issue requires immediate attention to prevent service disruption and data loss."
                logger.info(f"Fixed description to: {spec['description'][:100]}...")
        return spec

    def _fix_runbook_id(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure runbook_id is properly formatted"""
        if "runbook_id" not in spec or not spec["runbook_id"]:
            title_slug = re.sub(r"[^a-z0-9]+", "-", spec.get("title", "runbook").lower()).strip("-")
            spec["runbook_id"] = f"rb-{spec.get('service', 'unknown')}-{title_slug[:30]}"
            logger.warning(f"Generated missing runbook_id: {spec['runbook_id']}")
        elif not spec["runbook_id"].startswith("rb-"):
            spec["runbook_id"] = f"rb-{spec['runbook_id'].lstrip('rb-')}"
            logger.warning(f"Fixed runbook_id format: {spec['runbook_id']}")
        return spec
