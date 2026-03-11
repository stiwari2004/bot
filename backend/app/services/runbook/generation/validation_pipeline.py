"""
Validation pipeline for generated runbooks.

Simplified to two stages:
  1. Schema validation  — structural contract (RunbookValidator), mechanical
  2. Critic + Refiner   — LLM quality gate with targeted auto-patching

Keyword-counting layers (RunbookQualityValidator, RunbookCommandValidator) are
no longer invoked here. The critic understands quality better than keyword counts.
"""
from __future__ import annotations

import yaml
from typing import Any, Dict, Optional, Tuple

from app.core.logging import get_logger
from app.services.runbook.generation.runbook_critic_service import (
    RunbookCriticService, CriticResult,
)
from app.services.runbook.generation.runbook_refiner_service import RunbookRefinerService

logger = get_logger(__name__)


class ValidationPipeline:
    """Orchestrates critic → conditional refiner for generated runbooks."""

    def __init__(self):
        self.critic = RunbookCriticService()
        self.refiner = RunbookRefinerService()

    async def run(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        issue_type: str,
        os_type: Optional[str],
        tenant_id: int,
    ) -> Tuple[Dict[str, Any], CriticResult]:
        """
        Run the full validation pipeline.

        Returns:
            (spec, critic_result)
            - spec may be patched if critic found minor gaps
            - critic_result.severity drives how the caller stores the runbook:
                "pass"  → store, no review required
                "minor" → store with review_required=True (refiner already patched)
                "major" → store with review_required=True (no auto-patch)
        """
        # Stage 1: schema validation (structural contract, no LLM)
        spec = self._schema_validate(spec)

        # Stage 2: LLM critic
        critic_result = await self.critic.critique(
            spec=spec,
            issue_description=issue_description,
            issue_type=issue_type,
            os_type=os_type,
            tenant_id=tenant_id,
        )

        # Stage 3: auto-refine minor gaps
        if not critic_result.passed and critic_result.severity == "minor" and critic_result.gaps:
            logger.info("Validation: minor gaps found — running refiner on %d gap(s)", len(critic_result.gaps))
            spec = await self.refiner.refine(
                spec=spec,
                gaps=critic_result.gaps,
                issue_description=issue_description,
                os_type=os_type,
                tenant_id=tenant_id,
            )

        return spec, critic_result

    # ------------------------------------------------------------------
    # Schema validation — structural contract only
    # ------------------------------------------------------------------

    @staticmethod
    def _schema_validate(spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run RunbookValidator schema check. Returns validated spec.
        Warnings are logged; errors are logged but do not raise
        (critic handles quality, schema handles contract).
        """
        try:
            from app.schemas.runbook_yaml import RunbookValidator
            validated, warnings = RunbookValidator.validate_runbook(spec, auto_assign_severity=True)
            if warnings:
                logger.warning("Schema validation warnings: %s", warnings)
            return validated.model_dump(mode="json", exclude_none=True)
        except Exception as exc:
            logger.warning("Schema validation failed (continuing): %s", exc)
            return spec

    # ------------------------------------------------------------------
    # Legacy shims — kept so any existing callers don't break immediately
    # ------------------------------------------------------------------

    def validate_structure(self, spec, issue_description, issue_type=None):
        """Deprecated. Schema validation now happens inside run(). Returns (True, [])."""
        logger.debug("validate_structure called — now handled inside ValidationPipeline.run()")
        return True, []

    async def validate_commands(self, spec, issue_description, env, os_type=None):
        """Deprecated. Command quality now assessed by critic. Returns pass result."""
        logger.debug("validate_commands called — now handled by RunbookCriticService")
        return {"is_valid": True}

    async def critique_runbook(self, spec, issue_description, tenant_id):
        """Deprecated shim. Use run() instead. Calls critic directly."""
        result = await self.critic.critique(spec, issue_description, tenant_id=tenant_id)
        return result.to_dict()
