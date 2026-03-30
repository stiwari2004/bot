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
            "large inside it. Do NOT propose an approach targeting a path without first understanding "
            "what is inside it.\n"
            "- Once you have drilled into the top contributors and know what is inside, declare diagnosis_complete.\n"
            "BRANCHING RULES for diagnosis_complete:\n"
            "1. Identify the 2-3 biggest contributors to the problem from your actual command output.\n"
            "2. Each approach must target a DIFFERENT contributor — not sub-paths of the same one.\n"
            "3. Order approaches: safest/lowest-risk FIRST, highest-risk LAST.\n"
            "4. Use ACTUAL names, paths, and sizes from your output — do NOT invent or guess values.\n"
            "The human will PICK which approach to run — they cannot see intermediate steps, only the final approaches.\n"
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

2. Declare diagnosis complete with 2–3 alternative approaches (NO steps — steps are generated separately).
   Use ONLY real directory names and sizes from your command output — NO invented or example values:
{{
  "action": "diagnosis_complete",
  "findings": {{
    "root_cause": "concise description of the problem",
    "evidence": ["key fact 1 with actual values from output", "key fact 2"],
    "confidence": "high|medium|low"
  }},
  "approaches": [
    {{
      "id": "A",
      "title": "<ACTUAL resource/component name from your output> (<ACTUAL metric/size> — what you found)",
      "rationale": "<why this is the safest option based on what you found>",
      "risk": "low|medium|high",
      "target": "<ACTUAL path, service, or resource from your output>"
    }},
    {{
      "id": "B",
      "title": "<SECOND contributor from your output> (<ACTUAL metric/size>)",
      "rationale": "<why this is the next option>",
      "risk": "low|medium|high",
      "target": "<ACTUAL path, service, or resource from your output>"
    }}
  ]
}}
RULES:
- The <ACTUAL ...> placeholders above are instructions to YOU — replace them with real values from your command output.
- Each approach targets a DIFFERENT contributor — do NOT create sub-variations of the same thing.
- Do NOT invent or copy example values — use ONLY what YOUR commands returned.
- Order: safest first, most invasive last. Minimum 2 approaches.
- Do NOT include steps — steps are generated after the human picks an approach."""

        logger.info("Diagnose LLM call (history=%d, rejections=%d)", len(history), len(rejection_feedbacks))
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    async def _llm_plan_generate(
        self,
        approach: Dict[str, Any],
        diagnosis: Dict[str, Any],
        diagnosis_history: List[Dict],
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> List[Dict[str, Any]]:
        """
        Second LLM call: given a chosen approach and full diagnosis context,
        produce a complete multi-step remediation plan for that ONE approach.
        """
        server = connection_config.get("host") or connection_config.get("server_name") or "target"

        system_prompt = (
            "You are an SRE agent generating a detailed remediation plan. "
            "The human has already run a diagnosis and chosen which approach to take. "
            "Your job is to produce a complete, step-by-step plan for that ONE approach. "
            "Each step must be a real, executable shell command. "
            "PLAN COMPLETENESS RULES:\n"
            "- Think about ALL the actions needed to fully resolve the issue, not just one command.\n"
            "- Cover every relevant sub-cause under the chosen target: "
            "a thorough plan typically has 3-6 steps.\n"
            "- Include a final read-only verification step to confirm the issue is resolved "
            "(e.g. re-check the metric that was alerting).\n"
            "- Use ONLY the target and paths from the chosen approach — do NOT touch unrelated areas.\n"
            "CRITICAL RULES — COMMANDS MUST BE IMMEDIATELY EXECUTABLE:\n"
            "1. Use ONLY concrete, literal values from the diagnostic output provided. "
            "   Copy exact paths, filenames, and values — do NOT guess or invent them.\n"
            "2. Do NOT use {{placeholder}}, <variable>, or any template syntax. "
            "   Every command must run as-is without any substitution.\n"
            "3. The first step MUST NOT be the server hostname or a read-only check — "
            "   start with the actual remediation.\n"
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        history_text = self._format_history(diagnosis_history)
        root_cause   = (diagnosis or {}).get("root_cause", "")
        evidence     = "\n".join(f"  - {e}" for e in (diagnosis or {}).get("evidence", []))

        user_prompt = f"""Issue: {issue_description}
Server: {server}

Diagnosis findings:
  Root cause: {root_cause}
  Evidence:
{evidence}

Diagnostic commands already run — EXTRACT EXACT VALUES FROM THIS OUTPUT:
{history_text}

Chosen approach:
  ID: {approach.get('id')}
  Title: {approach.get('title')}
  Target: {approach.get('target', '')}
  Rationale: {approach.get('rationale')}
  Risk: {approach.get('risk')}

Generate a complete multi-step plan for this approach. Rules:
1. Read the diagnostic output above carefully — it shows exactly what is large/broken inside the target.
2. Write cleanup/fix commands that target the SPECIFIC files, directories, or services found in that output.
   Do NOT write generic commands that ignore what was actually found.
3. Cover all significant sub-causes visible in the diagnostic output — a thorough plan has 3-6 steps.
4. End with a verification step that re-checks the original symptom (e.g. re-run the metric command).

EXAMPLE of CORRECT step: {{"step": 1, "intent": "what this step achieves", "command": "actual-command --with real-values", "risk": "low"}}
EXAMPLE of WRONG step:   {{"step": 1, "intent": "what this step achieves", "command": "command --flag {{{{some_placeholder}}}}", "risk": "low"}}

Respond with:
{{
  "steps": [
    {{"step": 1, "intent": "what this achieves", "command": "exact literal shell command with no placeholders", "risk": "low|medium|high"}},
    {{"step": 2, "intent": "...", "command": "...", "risk": "..."}}
  ]
}}"""

        logger.info("Plan generate LLM call for approach %s", approach.get("id"))
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        parsed = self._parse_llm_response(raw)
        return parsed.get("steps") or []

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
            "MANDATORY: After completing all remediation steps, you MUST run a read-only verification "
            "command that directly re-checks the original symptom "
            "(e.g. `df -h` for disk space, `free -h` for memory, `systemctl status <svc>` for services). "
            "Only AFTER seeing the verification output should you respond with done.\n"
            "VERIFICATION RULES:\n"
            "- Read the verification output carefully. If the metric that was alerting has NOT improved "
            "  to a healthy level, the issue is NOT resolved — continue with more remediation steps.\n"
            "- Do NOT declare done with resolved=true if the symptom is still present.\n"
            "- Only declare resolved=true when the verification output confirms the problem is gone.\n"
            "- If you have genuinely exhausted all options and the issue persists, "
            "  declare done with resolved=false.\n"
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
