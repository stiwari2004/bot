"""
RunbookSpecHelper — pure algorithm helpers for runbook spec manipulation
"""
import json
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookSpecHelper:
    """Stateless helpers for working with runbook spec data structures"""

    @staticmethod
    def command_review_complete(meta_data: Dict[str, Any]) -> Tuple[bool, int]:
        """Check if all steps with invalid/pending_review validation are approved by human.
        Returns (ready, steps_pending_review count).
        """
        spec = meta_data.get("runbook_spec") or meta_data
        if not spec:
            return True, 0
        pending = 0
        for section_key in ("prechecks", "steps", "postchecks"):
            for step in spec.get(section_key, []):
                if not isinstance(step, dict):
                    continue
                status = step.get("command_validation_status")
                review = step.get("command_review_status")
                if status in ("invalid", "pending_review") and review != "approved_by_human":
                    pending += 1
        return pending == 0, pending

    @staticmethod
    def get_step_at(spec: Dict[str, Any], section: str, index: int) -> Optional[Dict[str, Any]]:
        """Get step dict at section and 0-based index. Returns None if out of range."""
        section_key = section if section in ("prechecks", "steps", "postchecks") else None
        if not section_key:
            return None
        items = spec.get(section_key, [])
        if not isinstance(items, list) or index < 0 or index >= len(items):
            return None
        step = items[index]
        return step if isinstance(step, dict) else None

    @staticmethod
    def body_md_from_spec(spec: Dict[str, Any]) -> str:
        """Build body_md YAML code fence from spec."""
        import yaml
        order = [
            "runbook_id", "version", "title", "service", "env", "risk", "description",
            "owner", "last_tested", "review_required", "inputs", "prechecks", "steps", "postchecks",
        ]
        ordered = OrderedDict()
        for key in order:
            if key in spec:
                ordered[key] = spec[key]
        for key, value in spec.items():
            if key not in ordered:
                ordered[key] = value
        runbook_yaml = yaml.safe_dump(dict(ordered), sort_keys=False, default_flow_style=False, width=120)
        return f"""# Agent Runbook (YAML)\n\n```yaml\n{runbook_yaml}```\n"""
