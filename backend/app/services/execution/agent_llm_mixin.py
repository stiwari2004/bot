"""
_AgentLLMMixin — LLM calls and response parsing for AgentExecutor.
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

_HISTORY_KEEP_LAST = 5
_MAX_OUTPUT_CHARS  = 400


class _AgentLLMMixin:
    """LLM call helpers: verify / diagnose / execute + parse + format."""

    async def _llm_verify(
        self,
        issue_description: str,
        connection_config: Dict[str, Any],
        history: List[Dict],
        force_verdict: bool = False,
        thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """LLM call for the symptom verification phase."""
        server     = connection_config.get("host") or connection_config.get("server_name") or "target"
        force_text = (
            "\nIMPORTANT: You must give a verdict now based on what you have seen so far."
            if force_verdict else ""
        )

        # Build threshold guidance from configured thresholds (db/runbook/default)
        thresholds = thresholds or {}
        threshold_lines = []
        for metric, t in thresholds.items():
            w, c = t.get("warning", 80), t.get("critical", 90)
            threshold_lines.append(f"{metric}: >= {w}% = warning (confirmed), >= {c}% = critical (confirmed)")
        threshold_text = "; ".join(threshold_lines) if threshold_lines else "Disk/Memory/CPU: >= 80% = warning, >= 90% = critical (defaults)"

        system_prompt = (
            "You are verifying whether a reported alert is a true positive or false positive. "
            "You are already connected to the target server. "
            "Run the single most direct read-only command that confirms whether the symptom "
            "is currently present (e.g., for 'disk full' run df -h, for 'service down' run "
            "systemctl status <service>). "
            "Do NOT investigate the root cause yet — just confirm if the problem exists right now. "
            f"THRESHOLDS for resource usage (treat as CONFIRMED/true_positive if at or above these): "
            f"{threshold_text}. "
            "Below warning threshold with no other error indicators = false positive. "
            "Respond ONLY with valid JSON."
        )

        user_prompt = f"""Alert to verify: {issue_description}
Server: {server}

Steps run so far:
{self._format_history(history)}{force_text}

Respond with ONE of:

1. Run a targeted read-only verification command:
{{
  "action": "command",
  "command": "exact shell command",
  "reasoning": "what this directly confirms about the reported symptom"
}}

2. Give a verdict once you have enough evidence:
{{
  "action": "verdict",
  "confirmed": true,
  "evidence": "one-line summary — e.g. Disk at 86% on /, above warning threshold, issue confirmed"
}}
or (only when usage is BELOW the warning threshold and no errors):
{{
  "action": "verdict",
  "confirmed": false,
  "evidence": "one-line summary — e.g. Disk at 42%, below warning threshold, no issue present"
}}"""

        logger.info("Verify LLM call (history=%d, force=%s)", len(history), force_verdict)
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    async def _llm_diagnose(
        self,
        issue_description: str,
        connection_config: Dict[str, Any],
        history: List[Dict],
        rejection_feedbacks: List[str],
        force_complete: bool = False,
    ) -> Dict[str, Any]:
        """LLM call for the diagnose phase."""
        server = connection_config.get("host") or connection_config.get("server_name") or "target"

        rejection_text = ""
        if rejection_feedbacks:
            rejection_text = "\n\nPrevious plan rejection feedback from human:\n"
            for i, fb in enumerate(rejection_feedbacks, 1):
                rejection_text += f"  Rejection {i}: {fb}\n"
            rejection_text += "Incorporate this feedback into your revised plan.\n"

        force_text = (
            "\nIMPORTANT: You have sufficient information. "
            "You MUST respond with diagnosis_complete now — do not request another command."
            if force_complete else ""
        )

        system_prompt = (
            "You are an SRE agent in the DIAGNOSIS phase. "
            "You are already connected to the target server — every command runs directly on it. "
            "Your ONLY goal right now is to understand the problem. Do NOT fix anything yet. "
            "Use READ-ONLY commands only: df, du, ls, cat, grep, ps, top, free, "
            "journalctl (read), systemctl status, netstat, lsof, find (without -delete/-exec rm). "
            "When you have identified the root cause and can propose a fix plan, respond with diagnosis_complete. "
            "IMPORTANT: diagnosis_complete MUST always include a non-empty proposed_plan. "
            "The human will review, edit, reorder, and remove steps before approving. "
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        user_prompt = f"""Issue to diagnose: {issue_description}
Server: {server}{rejection_text}
Steps completed so far (all read-only on {server}):
{self._format_history(history)}{force_text}

Respond with ONE of:

1. Run a read-only command:
{{
  "action": "command",
  "command": "exact shell command (read-only only)",
  "reasoning": "what you are looking for and why"
}}

2. Declare diagnosis complete with 2–3 alternative approaches:
{{
  "action": "diagnosis_complete",
  "findings": {{
    "root_cause": "concise description of the problem",
    "evidence": ["key fact 1", "key fact 2"],
    "confidence": "high|medium|low"
  }},
  "approaches": [
    {{
      "id": "A",
      "title": "Short label for this approach (≤8 words)",
      "rationale": "Why this approach, what it targets, expected impact",
      "risk": "low|medium|high",
      "steps": [
        {{"step": 1, "intent": "what this achieves", "command": "exact command", "risk": "low|medium|high"}}
      ]
    }},
    {{
      "id": "B",
      "title": "Second approach title",
      "rationale": "Different strategy or different target",
      "risk": "low|medium|high",
      "steps": [
        {{"step": 1, "intent": "what this achieves", "command": "exact command", "risk": "low|medium|high"}}
      ]
    }}
  ]
}}
IMPORTANT: Always provide at least 2 approaches ordered from safest/least invasive to most invasive. The human will PICK which approach to run — do NOT collapse them into one plan."""

        logger.info("Diagnose LLM call (history=%d, rejections=%d)", len(history), len(rejection_feedbacks))
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    async def _llm_execute(
        self,
        issue_description: str,
        connection_config: Dict[str, Any],
        proposed_plan: List[Dict],
        history: List[Dict],
        resolved_inputs: Dict[str, str],
    ) -> Dict[str, Any]:
        """LLM call for the execute phase."""
        server = connection_config.get("host") or connection_config.get("server_name") or "target"

        plan_text = "\n".join(
            f"  Step {p.get('step', i+1)}: [{p.get('risk','?').upper()}] "
            f"{p.get('intent','?')} → {p.get('command','?')}"
            for i, p in enumerate(proposed_plan)
        )

        resolved_text = (
            f"\nKnown values discovered so far: {json.dumps(resolved_inputs)}"
            if resolved_inputs else ""
        )

        system_prompt = (
            "You are an SRE agent in the EXECUTION phase. "
            "You are already connected to the target server — every command runs directly on it. "
            "Execute the approved plan step by step. "
            "Adapt if a step fails — try an alternative that achieves the same intent. "
            "After completing all steps, verify the fix worked, then respond with done. "
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        user_prompt = f"""Issue: {issue_description}
Server: {server}{resolved_text}

Approved plan:
{plan_text}

Execution history so far:
{self._format_history(history)}

Respond with ONE of:

1. Execute the next step:
{{
  "action": "command",
  "command": "exact shell command",
  "reasoning": "which plan step this implements and expected outcome"
}}

2. Mark complete when the issue is verified resolved:
{{
  "action": "done",
  "summary": "root cause + what was done + verification result",
  "resolved": true
}}

If the issue cannot be resolved after best efforts:
{{
  "action": "done",
  "summary": "what was attempted and why it could not be resolved",
  "resolved": false
}}"""

        logger.info("Execute LLM call (history=%d)", len(history))
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    # ── Parsing / formatting ───────────────────────────────────────────────────

    def _parse_llm_response(self, raw: str) -> Dict[str, Any]:
        """Parse LLM JSON/YAML response, tolerating markdown fences."""
        import yaml

        text = (raw or "").strip()
        text = re.sub(r'^```(?:json|yaml)?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse LLM response: %s", text[:200])
        return {"action": "done", "summary": "Agent could not parse LLM response.",
                "resolved": False, "done": True, "_parse_error": True}

    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return "(no steps run yet)"
        if len(history) > _HISTORY_KEEP_LAST:
            older  = history[:-_HISTORY_KEEP_LAST]
            recent = history[-_HISTORY_KEEP_LAST:]
            older_summary = "; ".join(
                f"step {h['step']}: {h['command'][:40]} → {'OK' if h['success'] else 'FAIL'}"
                for h in older
            )
            text  = f"[Earlier steps summary]: {older_summary}\n\n"
            text += "\n".join(
                f"Step {h['step']}: $ {h['command']}\nOutput: {h['output'][:_MAX_OUTPUT_CHARS]}"
                for h in recent
            )
            return text
        return "\n".join(
            f"Step {h['step']}: $ {h['command']}\nOutput: {h['output'][:_MAX_OUTPUT_CHARS]}"
            for h in history
        )
