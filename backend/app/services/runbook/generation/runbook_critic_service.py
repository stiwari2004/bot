"""
Runbook Critic Service — structured quality assessment of generated runbooks.

Returns a CriticResult with:
  - passed / severity (pass | minor | major)
  - gaps: list of specific fixable problems with section + index + fix_hint
  - overall_assessment: human-readable summary

Replaces the old keyword-counting RunbookQualityValidator and RunbookCommandValidator
as the primary quality gate. Severity drives what happens next:
  pass   → store as-is
  minor  → RunbookRefinerService patches gaps, then flag for human review
  major  → flag for human review only (no auto-patch)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result types (stable contract — refiner and human feedback both depend on this)
# ---------------------------------------------------------------------------

@dataclass
class CriticGap:
    section: str    # prechecks | steps | postchecks
    index: int      # 0-based
    problem: str    # what is wrong
    fix_hint: str   # concrete instruction for the refiner / human


@dataclass
class CriticResult:
    passed: bool
    severity: str                              # "pass" | "minor" | "major"
    gaps: List[CriticGap] = field(default_factory=list)
    overall_assessment: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "severity": self.severity,
            "gaps": [
                {"section": g.section, "index": g.index,
                 "problem": g.problem, "fix_hint": g.fix_hint}
                for g in self.gaps
            ],
            "overall_assessment": self.overall_assessment,
            "confidence": self.confidence,
        }

    @staticmethod
    def passing() -> "CriticResult":
        return CriticResult(passed=True, severity="pass", confidence=1.0,
                            overall_assessment="Runbook looks good.")


# ---------------------------------------------------------------------------
# Critic service
# ---------------------------------------------------------------------------

_CRITIC_SYSTEM = (
    "You are a senior SRE reviewing a runbook before it is approved for production use. "
    "Your job is to identify concrete, fixable problems — not stylistic preferences. "
    "Return ONLY a JSON object."
)

_CRITIC_USER_TMPL = """ISSUE TYPE: {issue_type}
SERVICE: {service}
OS: {os_type}
ISSUE DESCRIPTION: {issue_description}

RUNBOOK SPEC (summary):
{spec_summary}

Assess the runbook and return JSON:
{{
  "passed": true/false,
  "severity": "pass|minor|major",
  "gaps": [
    {{
      "section": "prechecks|steps|postchecks",
      "index": 0,
      "problem": "concise description of what is wrong with this step",
      "fix_hint": "concrete instruction: what command / change would fix it"
    }}
  ],
  "overall_assessment": "1-2 sentence summary",
  "confidence": 0.0
}}

SEVERITY RULES:
- "pass"  : runbook will resolve the issue, no significant gaps
- "minor" : 1-3 fixable gaps (missing remediation command, wrong purpose label, weak postcheck) — auto-patchable
- "major" : fundamental problems (wrong OS commands, steps don't address issue_type, no remediation at all) — needs human review

WHAT TO CHECK:
1. Does at least one step actually FIX the {issue_type} condition (not just diagnose it)?
2. Does the postcheck verify the SAME metric the precheck measured?
3. Are commands appropriate for {os_type} and {issue_type}?
4. Do steps reference inputs that are defined (no undefined {{{{placeholders}}}})?
5. Is there a logical flow: diagnose → remediate → verify?

Only report gaps that are genuinely wrong, not nitpicks. Max 4 gaps.
If the runbook is sound, return passed=true, severity="pass", gaps=[]."""


class RunbookCriticService:
    """LLM-based structured critique of generated runbooks."""

    def __init__(self, llm_service_instance=None):
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                from app.services.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning("Could not initialise LLM service for critic: %s", e)
                self.llm_service = None

    async def critique(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        issue_type: str = "general_issue",
        os_type: Optional[str] = None,
        tenant_id: int = 1,
    ) -> CriticResult:
        """
        Critique the runbook spec. Always returns a CriticResult — fails open on error.
        """
        if not self.llm_service:
            logger.warning("Critic: LLM unavailable — passing runbook through")
            return CriticResult.passing()

        spec_summary = _summarise_spec(spec)
        user_msg = _CRITIC_USER_TMPL.format(
            issue_type=issue_type,
            service=spec.get("service", "server"),
            os_type=os_type or spec.get("env", "Linux"),
            issue_description=issue_description[:500],
            spec_summary=spec_summary,
        )

        try:
            raw = await self.llm_service._chat_once_with_system(
                _CRITIC_SYSTEM, user_msg, tenant_id=tenant_id
            )
            if not raw:
                return CriticResult.passing()

            data = _parse_json(raw)
            if not data:
                logger.warning("Critic: could not parse JSON response — passing through")
                return CriticResult.passing()

            gaps = [
                CriticGap(
                    section=str(g.get("section", "steps")),
                    index=int(g.get("index", 0)),
                    problem=str(g.get("problem", "")),
                    fix_hint=str(g.get("fix_hint", "")),
                )
                for g in (data.get("gaps") or [])
                if isinstance(g, dict)
            ]

            passed = bool(data.get("passed", True))
            severity = str(data.get("severity", "pass"))
            if severity not in ("pass", "minor", "major"):
                severity = "pass" if passed else "minor"

            result = CriticResult(
                passed=passed,
                severity=severity,
                gaps=gaps,
                overall_assessment=str(data.get("overall_assessment", "")),
                confidence=float(data.get("confidence", 0.8)),
            )
            logger.info(
                "Critic result: passed=%s severity=%s gaps=%d assessment=%r",
                result.passed, result.severity, len(result.gaps),
                result.overall_assessment[:80],
            )
            return result

        except Exception as exc:
            logger.warning("Critic error — passing through: %s", exc)
            return CriticResult.passing()

    # ------------------------------------------------------------------
    # Legacy compatibility shim (old callers used critique_runbook)
    # ------------------------------------------------------------------

    async def critique_runbook(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        tenant_id: int = 1,
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper. New code should call critique() directly."""
        result = await self.critique(spec, issue_description, tenant_id=tenant_id)
        return {
            "is_valid": result.passed,
            "confidence": result.confidence,
            "issues": [g.problem for g in result.gaps if result.severity == "major"],
            "warnings": [g.problem for g in result.gaps if result.severity == "minor"],
            "suggestions": [g.fix_hint for g in result.gaps],
            "regeneration_needed": result.severity == "major",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarise_spec(spec: Dict[str, Any]) -> str:
    """Compact spec summary so the critic prompt stays small."""
    lines: List[str] = []
    lines.append(f"title: {spec.get('title', 'N/A')}")
    lines.append(f"service: {spec.get('service', 'N/A')}  env: {spec.get('env', 'N/A')}  risk: {spec.get('risk', 'N/A')}")
    lines.append("")

    for section in ("prechecks", "steps", "postchecks"):
        items = spec.get(section, [])
        if not items:
            continue
        lines.append(f"{section.upper()} ({len(items)}):")
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("description") or f"item {i}"
            cmd = (item.get("command") or "")[:120]
            purpose = item.get("purpose", "")
            lines.append(f"  [{i}] {name}  purpose={purpose}")
            if cmd:
                lines.append(f"       cmd: {cmd}")
        lines.append("")

    return "\n".join(lines)


def _parse_json(text: str) -> Optional[dict]:
    import yaml as _yaml
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json|yaml)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    try:
        result = _yaml.safe_load(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return None
