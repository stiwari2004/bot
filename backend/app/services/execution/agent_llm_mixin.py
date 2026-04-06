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
_MAX_OUTPUT_CHARS  = 800   # enough for full du -sh /* output


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
        force_complete: bool = False,
    ) -> Dict[str, Any]:
        """LLM call for the diagnose phase."""
        server = connection_config.get("host") or connection_config.get("server_name") or "target"

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
            "EFFICIENCY RULES:\n"
            "- Use the most direct commands to identify the root cause and its top contributors.\n"
            "- Follow the evidence: each command must be informed by the previous output.\n"
            "- Do NOT repeat the same or a near-identical command (e.g. 'df -h' and 'df -h /' are duplicates).\n"
            "- Do NOT run more than 6 commands total.\n"
            "- When running du, always suppress errors and sort largest-first so you can read the output: "
            "du -sh /path/* 2>/dev/null | sort -rh | head -20\n"
            "- DRILL DEEPER before concluding: if a command reveals one path is significantly larger than "
            "the others, run ONE more command to look inside that specific path "
            "(e.g. du -sh /thatpath/* 2>/dev/null | sort -rh | head -20) so you know exactly what is "
            "large inside it.\n"
            "- Once you have drilled into the top contributors and know what is inside, declare diagnosis_complete.\n"
            "RULES for diagnosis_complete targets array:\n"
            "- List every significant contributor to the problem as a targets array.\n"
            "- Use ONLY actual paths and sizes from your command output — never invent values.\n"
            "- Order by size descending.\n"
            "- Each target: { path, size, type, description } where type is one of: "
            "system_logs, package_cache, temp_files, app_data, app_logs, core_dumps, other\n"
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        user_prompt = f"""Issue to diagnose: {issue_description}
Server: {server}
Steps completed so far (all read-only on {server}):
{self._format_history(history)}{force_text}

Respond with ONE of:

1. Run a read-only command:
{{
  "action": "command",
  "command": "exact shell command (read-only only)",
  "reasoning": "what you are looking for and why"
}}

2. Declare diagnosis complete with all significant contributors:
{{
  "action": "diagnosis_complete",
  "findings": {{
    "root_cause": "concise description of the problem",
    "evidence": ["key fact 1 with actual values from output", "key fact 2"],
    "confidence": "high|medium|low"
  }},
  "targets": [
    {{
      "path": "/actual/path/from/output",
      "size": "actual size from output (e.g. 4.2G)",
      "type": "system_logs|package_cache|temp_files|app_data|app_logs|core_dumps|other",
      "description": "what this is and why it contributes to the problem"
    }}
  ]
}}
RULES:
- Use ONLY real paths and sizes from your command output — do NOT invent values.
- Order targets by size descending (largest first).
- Include every significant contributor, not just the top one."""

        logger.info("Diagnose LLM call (history=%d)", len(history))
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    async def _llm_execute(
        self,
        issue_description: str,
        connection_config: Dict[str, Any],
        approved_targets: List[Dict],
        excluded_targets: List[str],
        diagnosis_findings: Dict[str, Any],
        thresholds: Dict[str, Any],
        history: List[Dict],
        resolved_inputs: Dict[str, str],
    ) -> Dict[str, Any]:
        """LLM call for the execute phase."""
        server = connection_config.get("host") or connection_config.get("server_name") or "target"

        approved_text = "\n".join(
            f"  - [{t.get('type', '?').upper()}] {t.get('path', '?')} ({t.get('size', '?')}): {t.get('description', '')}"
            for t in approved_targets
        )

        excluded_text = (
            "\n".join(f"  - {p}" for p in excluded_targets)
            if excluded_targets else "  (none)"
        )

        resolved_text = (
            f"\nKnown values discovered so far: {json.dumps(resolved_inputs)}"
            if resolved_inputs else ""
        )

        system_prompt = (
            "You are an SRE agent in the EXECUTION phase. "
            "You are already connected to the target server — every command runs directly on it. "
            "The human has approved a set of targets for remediation. "
            "You MUST attempt remediation on EVERY approved target before running verification or declaring done. "
            "Do not stop early after acting on only some targets — work through the full approved list first, "
            "then verify. Adapt if a step fails — read the error output carefully and reason about why it "
            "failed before choosing an alternative. The cause is always visible in the output.\n"
            "MANDATORY VERIFICATION: After ALL approved targets have been acted on, run the single most "
            "direct command that confirms whether the original symptom is now gone "
            "(e.g. df -h for disk, free -h for memory, systemctl status <service> for service issues, "
            "top/ps for CPU or process issues). Choose the command based on what the issue actually is.\n"
            "VERIFICATION RULES:\n"
            "- Run a command that directly measures the symptom — not one that shows intermediate state.\n"
            "- Read the verification output carefully: if it still shows the problem condition, "
            "  continue with more remediation steps.\n"
            "- Do NOT declare done with resolved=true unless the verification output explicitly confirms "
            "  the issue is no longer present.\n"
            "- If you have genuinely exhausted all approved targets and the issue persists, "
            "  declare done with resolved=false.\n"
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        diagnosis_text = ""
        if diagnosis_findings:
            root_cause = diagnosis_findings.get("root_cause") or ""
            evidence   = diagnosis_findings.get("evidence") or []
            evidence_lines = "\n".join(f"  - {e}" for e in evidence) if evidence else "  (none)"
            diagnosis_text = f"""
Diagnosis findings (from read-only investigation phase):
  Root cause: {root_cause}
  Evidence:
{evidence_lines}
"""

        threshold_text = ""
        if thresholds:
            lines = []
            for metric, t in thresholds.items():
                w, c = t.get("warning", 80), t.get("critical", 90)
                lines.append(f"  {metric}: warning={w}%, critical={c}%")
            threshold_text = (
                "\nResolution targets (from configured thresholds):\n"
                + "\n".join(lines)
                + "\n  Goal: bring the relevant metric below its WARNING threshold."
                + "\n  Minimum acceptable: below CRITICAL threshold (moves alert from critical to warning)."
            )

        user_prompt = f"""Issue: {issue_description}
Server: {server}{resolved_text}
{diagnosis_text}{threshold_text}

Approved targets for remediation:
{approved_text}

Excluded paths (DO NOT TOUCH these):
{excluded_text}

Execution history so far:
{self._format_history(history)}

Respond with ONE of:

1. Execute the next step:
{{
  "action": "command",
  "command": "exact shell command",
  "reasoning": "what this does within the approved scope and expected outcome"
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

    async def _llm_check_resolution(
        self,
        history: List[Dict],
        summary: str,
        issue_description: str = "",
        initial_evidence: str = "",
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        LLM-driven resolution verification gate.
        Called when the executing agent declares resolved=true — challenges that claim
        based solely on actual command outputs in the history.
        Uses initial_evidence (from precheck) and configured thresholds for before/after comparison.
        Returns {"resolved": bool, "reasoning": str, "next_step": str}.
        Defaults to resolved=False on any failure (conservative).
        """
        system_prompt = (
            "You are a strict SRE verification judge. "
            "The executing agent has claimed the issue is resolved. "
            "Your job is to validate or challenge that claim by comparing the BEFORE state "
            "(captured at alert time) with the AFTER state (from the most recent verification output), "
            "using the configured warning and critical thresholds as your reference points. "
            "Be conservative: if the metric has not improved to at least below the CRITICAL threshold, "
            "return resolved=false. "
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        before_text = f"\nInitial state at alert time: {initial_evidence}" if initial_evidence else ""

        threshold_rules = ""
        if thresholds:
            lines = []
            for metric, t in thresholds.items():
                w, c = t.get("warning", 80), t.get("critical", 90)
                lines.append(
                    f"  {metric}: resolved=true if current < {w}% (warning); "
                    f"resolved=false if current >= {c}% (still critical)"
                )
            threshold_rules = "\nConfigured thresholds:\n" + "\n".join(lines)

        user_prompt = f"""Original issue: {issue_description or "(not specified)"}{before_text}{threshold_rules}

Agent's final summary: {summary}

Recent execution history (last 5 steps):
{self._format_history(history[-5:])}

Compare the initial state with the most recent verification output against the thresholds above.

Respond with:
{{
  "resolved": true or false,
  "reasoning": "one sentence: cite the initial reading, the current reading from the output, and the relevant threshold",
  "next_step": "if resolved=false: the single most direct command to re-verify or continue remediation; if resolved=true: empty string"
}}

Rules:
- resolved=true ONLY if the verification output shows the metric is below the WARNING threshold
- resolved=false if the metric is still at or above the CRITICAL threshold (no meaningful improvement)
- resolved=false if the metric improved but is still between WARNING and CRITICAL — keep going if more targets remain
- resolved=false if no verification command was run after the last remediation step
- resolved=false if the last command failed or produced an error"""

        logger.info("Resolution check LLM call (history=%d)", len(history))
        try:
            raw = await asyncio.wait_for(
                self._llm._chat_once_with_system(system_prompt, user_prompt),
                timeout=60.0,
            )
            result = self._parse_llm_response(raw)
            if result.get("_parse_error"):
                logger.warning("_llm_check_resolution: parse error — defaulting resolved=False")
                return {
                    "resolved": False,
                    "reasoning": "could not parse verification response",
                    "next_step": "Run the appropriate verification command for this issue type.",
                }
            return result
        except Exception as e:
            logger.warning("_llm_check_resolution failed (%s) — defaulting resolved=False", e)
            return {
                "resolved": False,
                "reasoning": str(e),
                "next_step": "Run the appropriate verification command for this issue type.",
            }

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
        """
        Format the command history for the LLM.
        ALL steps include their output — older steps are truncated to 300 chars
        so the LLM retains the facts (which dir was large, what the error was)
        even when the list grows long.
        """
        if not history:
            return "(no steps run yet)"
        lines = []
        for i, h in enumerate(history):
            is_recent = i >= len(history) - _HISTORY_KEEP_LAST
            max_chars = _MAX_OUTPUT_CHARS if is_recent else 300
            output = (h.get("output") or "").strip()
            lines.append(
                f"Step {h['step']}: $ {h['command']}\n"
                f"Output: {output[:max_chars]}"
                + (" [truncated]" if len(output) > max_chars else "")
            )
        return "\n\n".join(lines)
