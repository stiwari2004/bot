"""
Runbook Refiner Service — patches specific gaps in a generated runbook.

Used in two contexts:
  1. Auto-refine: called by ValidationPipeline when critic returns severity="minor"
  2. Human feedback: called by RunbookController when a human submits step-level feedback

In both cases the unit of work is a single step. The refiner calls the LLM with
just that step + a problem description + a fix instruction. It never regenerates
the full runbook — only patches the flagged items.
"""
from __future__ import annotations

import yaml
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.runbook.generation.runbook_critic_service import CriticGap

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request type for human feedback (also used internally)
# ---------------------------------------------------------------------------

class FeedbackItem:
    """One piece of human (or critic) feedback targeting a single step."""

    def __init__(self, section: str, index: int, feedback: str, problem: str = ""):
        self.section = section   # prechecks | steps | postchecks
        self.index = index       # 0-based
        self.feedback = feedback # human natural-language instruction
        self.problem = problem   # optional: what is currently wrong (from critic)

    @staticmethod
    def from_critic_gap(gap: CriticGap) -> "FeedbackItem":
        return FeedbackItem(
            section=gap.section,
            index=gap.index,
            feedback=gap.fix_hint,
            problem=gap.problem,
        )


# ---------------------------------------------------------------------------
# Refiner
# ---------------------------------------------------------------------------

_REFINER_SYSTEM = (
    "You are a runbook step fixer. You receive a single runbook step in YAML and a "
    "specific instruction to improve it. Return ONLY the corrected step as a YAML "
    "mapping — same fields as the input, with the fix applied. No fences, no prose."
)

_REFINER_USER_TMPL = """STEP TO FIX (YAML):
{step_yaml}

WHAT IS WRONG: {problem}
HOW TO FIX IT: {fix_hint}

CONTEXT:
- Issue being resolved: {issue_description}
- OS / environment: {os_type}

Return the corrected step as a YAML mapping. Keep all existing fields (name, type,
description, expected_output, purpose, severity, skip_in_auto_mode) — only change
what the fix instruction requires."""


class RunbookRefinerService:
    """Patches specific steps in a runbook spec based on critic gaps or human feedback."""

    def __init__(self, llm_service_instance=None):
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                from app.services.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning("Could not initialise LLM service for refiner: %s", e)
                self.llm_service = None

    # ------------------------------------------------------------------
    # Auto-refine from critic gaps
    # ------------------------------------------------------------------

    async def refine(
        self,
        spec: Dict[str, Any],
        gaps: List[CriticGap],
        issue_description: str,
        os_type: Optional[str],
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        Apply critic-identified gaps to the spec. Patches up to 3 gaps.
        Returns the patched spec (original is not mutated).
        """
        import copy
        spec = copy.deepcopy(spec)
        items = [FeedbackItem.from_critic_gap(g) for g in gaps[:3]]
        return await self._apply_feedback_items(spec, items, issue_description, os_type, tenant_id)

    # ------------------------------------------------------------------
    # Human feedback
    # ------------------------------------------------------------------

    async def apply_human_feedback(
        self,
        spec: Dict[str, Any],
        feedback_items: List[FeedbackItem],
        issue_description: str,
        os_type: Optional[str],
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        Apply human-provided step feedback. Each item targets one step.
        Returns the patched spec.
        """
        import copy
        spec = copy.deepcopy(spec)
        return await self._apply_feedback_items(spec, feedback_items, issue_description, os_type, tenant_id)

    # ------------------------------------------------------------------
    # Core — applies a list of FeedbackItems to a spec
    # ------------------------------------------------------------------

    async def _apply_feedback_items(
        self,
        spec: Dict[str, Any],
        items: List[FeedbackItem],
        issue_description: str,
        os_type: Optional[str],
        tenant_id: int,
    ) -> Dict[str, Any]:
        for item in items:
            try:
                step = self._get_step(spec, item.section, item.index)
                if step is None:
                    logger.warning(
                        "Refiner: step not found — section=%s index=%d, skipping",
                        item.section, item.index,
                    )
                    continue

                patched = await self._refine_step(
                    step=step,
                    problem=item.problem or "See fix instruction.",
                    fix_hint=item.feedback,
                    issue_description=issue_description,
                    os_type=os_type or "Linux",
                    tenant_id=tenant_id,
                )
                if patched:
                    self._set_step(spec, item.section, item.index, patched)
                    logger.info(
                        "Refiner: patched %s[%d] — %s",
                        item.section, item.index, item.feedback[:80],
                    )
            except Exception as exc:
                logger.warning(
                    "Refiner: failed to patch %s[%d]: %s",
                    item.section, item.index, exc,
                )
        return spec

    async def _refine_step(
        self,
        step: Dict[str, Any],
        problem: str,
        fix_hint: str,
        issue_description: str,
        os_type: str,
        tenant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Call LLM to fix a single step. Returns patched step dict or None on failure."""
        if not self.llm_service:
            logger.warning("Refiner: LLM unavailable — skipping step patch")
            return None

        step_yaml = yaml.safe_dump(step, default_flow_style=False, width=120).strip()
        user_msg = _REFINER_USER_TMPL.format(
            step_yaml=step_yaml,
            problem=problem[:300],
            fix_hint=fix_hint[:400],
            issue_description=issue_description[:300],
            os_type=os_type,
        )

        try:
            raw = await self.llm_service._chat_once_with_system(
                _REFINER_SYSTEM, user_msg, tenant_id=tenant_id
            )
            if not raw or not raw.strip():
                return None

            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(
                    l for l in lines
                    if not l.strip().startswith("```")
                ).strip()

            patched = yaml.safe_load(raw)
            if not isinstance(patched, dict):
                logger.warning("Refiner: LLM returned non-dict for step — skipping")
                return None

            # Preserve review status fields
            patched["command_review_status"] = "revised"
            patched.pop("command_validation_issue", None)
            patched.pop("command_suggested_fix", None)
            return patched

        except Exception as exc:
            logger.warning("Refiner: LLM call failed for step: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Spec helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_step(spec: Dict[str, Any], section: str, index: int) -> Optional[Dict[str, Any]]:
        items = spec.get(section, [])
        if isinstance(items, list) and 0 <= index < len(items):
            step = items[index]
            return step if isinstance(step, dict) else None
        return None

    @staticmethod
    def _set_step(spec: Dict[str, Any], section: str, index: int, step: Dict[str, Any]) -> None:
        items = spec.get(section, [])
        if isinstance(items, list) and 0 <= index < len(items):
            items[index] = step
