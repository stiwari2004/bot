"""Sandbox policy validation utilities."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_PROFILES = {
    "prod-critical": {"max_blast_radius": "high", "default_sla_minutes": 5},
    "prod-standard": {"max_blast_radius": "medium", "default_sla_minutes": 10},
    "staging-standard": {"max_blast_radius": "medium", "default_sla_minutes": 15},
    "dev-flex": {"max_blast_radius": "low", "default_sla_minutes": 30},
    "default": {"max_blast_radius": "high", "default_sla_minutes": 30},
}

BLAST_RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}


def _blast_rank(value: Optional[str]) -> int:
    if not value:
        return 0
    return BLAST_RANK.get(value.lower(), 0)


def validate_sandbox_profile(
    profile: str,
    *,
    steps: Iterable[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate sandbox profile selection against step metadata.

    Returns the applied profile metadata (e.g. SLA) for downstream use.
    """
    context = context or {}
    profile_key = profile or "default"
    profile_info = ALLOWED_PROFILES.get(profile_key)
    if not profile_info:
        raise ValueError(f"Unknown sandbox profile '{profile_key}'")

    max_allowed_rank = _blast_rank(profile_info.get("max_blast_radius"))
    for step in steps:
        blast = step.get("blast_radius") or step.get("severity") or step.get("risk")
        if blast and _blast_rank(str(blast)) > max_allowed_rank:
            raise ValueError(
                f"Step {step.get('step_number')} blast radius '{blast}' exceeds profile '{profile_key}' allowance"
            )

    logger.debug(
        "Sandbox profile validated profile=%s tenant=%s",
        profile_key,
        context.get("tenant_id"),
    )
    return profile_info


