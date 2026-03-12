"""
Agent Executor — agentic execution for issues with no matching runbook.

Runs a ReAct loop (Reason → Act → Observe) where the LLM decides the next
command based on what it has seen so far.  Every command is gated by the
CommandClassifier before execution:

  Level 1 (SAFE)        → auto-proceed
  Level 2 (CAUTION)     → publish countdown event, proceed after delay
  Level 3 (DESTRUCTIVE) → run dry-run preview, publish approval-required event,
                           pause until human approves via existing approval API
  Level 4 (BLOCKED)     → refuse, publish blocked event, ask LLM to try another way

The agent stores every step as a real ExecutionStep in the database so the
existing WebSocket streaming, audit trail, and approval UI all work unchanged.

After completion the session is flagged for crystallisation review:
  session.meta_data["agent_session"] = True
  session.meta_data["pending_review"] = True
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.command_classifier import get_command_classifier
from app.services.execution.output_extractor import get_output_extractor
from app.services.execution.step_event_publisher import StepEventPublisher
from app.services.infrastructure import get_connector

logger = get_logger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────
_MAX_ITERATIONS = 20          # hard cap on agent loop iterations
_CAUTION_COUNTDOWN_S = 10     # seconds before a Level-2 command auto-proceeds
_HISTORY_KEEP_LAST = 5        # keep last N step outputs in prompt (compress older)
_MAX_OUTPUT_CHARS = 400       # truncate individual step outputs in prompt
_APPROVAL_POLL_INTERVAL = 2   # seconds between polls waiting for human approval
_APPROVAL_TIMEOUT_S = 300     # 5 minutes before approval times out


class AgentExecutor:
    """
    Drives agentic execution of an issue when no matching runbook exists.
    Creates ExecutionStep rows dynamically as the agent progresses.
    """

    def __init__(self):
        self.classifier = get_command_classifier()
        self.extractor = get_output_extractor()
        self.event_publisher = StepEventPublisher()

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(
        self,
        db: Session,
        session_id: int,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Dict[str, Any]:
        """Accepts session_id so this can safely run in a background task with its own DB session."""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            logger.error("AgentExecutor: session %d not found", session_id)
            return {"success": False, "summary": "Session not found", "steps_taken": 0,
                    "resolved": False, "pending_review": False}
        return await self._run_session(db, session, connection_config, issue_description)

    async def _run_session(
        self,
        db: Session,
        session: ExecutionSession,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Dict[str, Any]:
        """
        Run the agent loop for the given session.

        Returns a summary dict:
          { "success": bool, "summary": str, "steps_taken": int,
            "resolved": bool, "pending_review": bool }
        """
        session.status = "in_progress"
        session.started_at = datetime.now(timezone.utc)
        if not isinstance(session.meta_data, dict):
            session.meta_data = {}
        session.meta_data["agent_session"] = True
        session.meta_data["pending_review"] = False
        db.commit()

        connector_type = (connection_config.get("connector_type") or "local").lower()
        connector = get_connector(connector_type)
        resolved_inputs: Dict[str, str] = {}
        history: List[Dict[str, str]] = []   # {step, command, output_snippet}
        step_number = 1
        final_summary = ""
        resolved = False

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.started",
            "message": f"Agent started for: {issue_description[:120]}",
        })

        for iteration in range(_MAX_ITERATIONS):
            # ── Ask LLM for next action ──────────────────────────────────────
            try:
                action = await self._ask_llm(
                    issue_description=issue_description,
                    server=connection_config.get("host") or connection_config.get("server_name") or "target",
                    history=history,
                    resolved_inputs=resolved_inputs,
                )
            except Exception as llm_err:
                logger.error("Agent LLM call failed: %s", llm_err)
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message": f"LLM call failed: {llm_err}",
                })
                break

            # ── Agent says it's done ─────────────────────────────────────────
            if action.get("done"):
                final_summary = action.get("summary", "Agent completed.")
                resolved = True
                logger.info("Agent done after %d steps: %s", step_number - 1, final_summary)
                break

            command = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                logger.warning("Agent returned empty command at iteration %d", iteration)
                break

            # Substitute any known resolved inputs into the command
            command = self.extractor.substitute(command, resolved_inputs)

            # ── Classify the command ─────────────────────────────────────────
            classification = self.classifier.classify(command)

            await self.event_publisher.publish_raw(db, session, {
                "event_type": "agent.reasoning",
                "step_number": step_number,
                "reasoning": reasoning,
                "command": command,
                "safety_level": classification.level,
                "safety_label": classification.label,
            })

            # Level 4 — BLOCKED
            if classification.level == 4:
                logger.warning("Agent proposed BLOCKED command: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.command_blocked",
                    "step_number": step_number,
                    "command": command,
                    "reason": classification.reason,
                })
                # Feed the block back into history so LLM tries a different approach
                history.append({
                    "step": step_number,
                    "command": command,
                    "output": f"[BLOCKED] {classification.reason}. Choose a different approach.",
                    "success": False,
                })
                step_number += 1
                continue

            # Level 3 — DESTRUCTIVE: dry-run first, then wait for human approval
            if classification.level == 3:
                step_number = await self._handle_destructive(
                    db=db, session=session, connector=connector,
                    connection_config=connection_config,
                    command=command, reasoning=reasoning,
                    classification=classification,
                    step_number=step_number, history=history,
                    resolved_inputs=resolved_inputs,
                )
                continue

            # Level 2 — CAUTION: countdown window then auto-proceed
            if classification.level == 2:
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.caution",
                    "step_number": step_number,
                    "command": command,
                    "reason": classification.reason,
                    "countdown_seconds": _CAUTION_COUNTDOWN_S,
                    "message": (
                        f"State-changing command in {_CAUTION_COUNTDOWN_S}s: {command[:80]}. "
                        "Click Cancel to skip this step."
                    ),
                })
                await asyncio.sleep(_CAUTION_COUNTDOWN_S)
                # Check if human cancelled during the countdown
                db.refresh(session)
                if session.status == "abandoned":
                    logger.info("Agent session abandoned by human during caution countdown")
                    break

            # Level 1 or post-countdown Level 2: execute
            step_db = self._create_step(
                db=db, session=session, step_number=step_number,
                command=command, reasoning=reasoning,
            )

            result = await self._execute_step(
                connector=connector, connection_config=connection_config,
                command=command, step_db=step_db, db=db, session=session,
            )

            output = result.get("output") or result.get("error") or ""
            success = result.get("success", False)

            # Extract values from output for future steps
            needed_next = self._peek_needed_vars(history, command)
            if success and output:
                extracted = self.extractor.extract_from_output(
                    command=command, output=output, needed_vars=needed_next,
                )
                if extracted:
                    resolved_inputs.update(extracted)
                    logger.info("Agent extracted from output: %s", list(extracted.keys()))

            history.append({
                "step": step_number,
                "command": command,
                "output": output[:_MAX_OUTPUT_CHARS],
                "success": success,
            })
            step_number += 1

            # Publish step completed event
            await self.event_publisher.publish_raw(db, session, {
                "event_type": "agent.step_completed",
                "step_number": step_number - 1,
                "command": command,
                "success": success,
                "output_preview": output[:200],
            })

        # ── Loop ended ────────────────────────────────────────────────────────
        if iteration == _MAX_ITERATIONS - 1 and not resolved:
            final_summary = f"Agent reached maximum iterations ({_MAX_ITERATIONS}) without confirming resolution."
            logger.warning(final_summary)

        # Flag for human review + crystallisation
        from sqlalchemy.orm.attributes import flag_modified
        session.meta_data["pending_review"] = True
        session.meta_data["agent_summary"] = final_summary
        session.meta_data["agent_resolved"] = resolved
        session.meta_data["resolved_inputs"] = resolved_inputs
        session.status = "completed" if resolved else "completed_with_errors"
        session.completed_at = datetime.now(timezone.utc)
        flag_modified(session, "meta_data")
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.completed",
            "resolved": resolved,
            "summary": final_summary,
            "steps_taken": step_number - 1,
            "pending_review": True,
            "message": (
                "Agent finished. Please review the steps and save as runbook "
                "if this resolution should be reused."
            ),
        })

        return {
            "success": resolved,
            "summary": final_summary,
            "steps_taken": step_number - 1,
            "resolved": resolved,
            "pending_review": True,
        }

    # ── Level 3 handling ──────────────────────────────────────────────────────

    async def _handle_destructive(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        command: str,
        reasoning: str,
        classification,
        step_number: int,
        history: List[Dict],
        resolved_inputs: Dict[str, str],
    ) -> int:
        """Run dry-run first, publish approval-required event, wait for human."""

        # Run dry-run preview on the target
        dry_run_output = ""
        if classification.dry_run_command:
            try:
                dry_result = await connector.execute_command(
                    command=classification.dry_run_command,
                    connection_config=connection_config,
                    timeout=30,
                )
                dry_run_output = (dry_result.get("output") or "")[:600]
            except Exception as e:
                dry_run_output = f"(could not run preview: {e})"

        # Create the step in DB with requires_approval=True
        step_db = self._create_step(
            db=db, session=session, step_number=step_number,
            command=command, reasoning=reasoning, requires_approval=True,
        )
        session.status = "waiting_approval"
        session.waiting_for_approval = True
        session.approval_step_number = step_number
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.approval_required",
            "step_number": step_number,
            "command": command,
            "reason": classification.reason,
            "dry_run_command": classification.dry_run_command,
            "dry_run_output": dry_run_output,
            "message": (
                f"APPROVAL REQUIRED: {classification.reason}\n"
                f"Command: {command}\n"
                f"Preview (what would be affected):\n{dry_run_output or '(no preview available)'}"
            ),
        })

        # Poll until human approves, rejects, or timeout
        elapsed = 0
        approved = False
        while elapsed < _APPROVAL_TIMEOUT_S:
            await asyncio.sleep(_APPROVAL_POLL_INTERVAL)
            elapsed += _APPROVAL_POLL_INTERVAL
            db.refresh(step_db)
            db.refresh(session)

            if session.status == "abandoned":
                logger.info("Agent session abandoned during approval wait")
                return step_number

            if step_db.approved is True:
                approved = True
                session.status = "in_progress"
                session.waiting_for_approval = False
                db.commit()
                break
            if step_db.approved is False:
                # Human rejected — mark as weed and continue
                step_db.notes = "Rejected by human — marked as weed"
                from sqlalchemy.orm.attributes import flag_modified
                cmd_payload = step_db.command_payload or {}
                cmd_payload["weed"] = True
                step_db.command_payload = cmd_payload
                flag_modified(step_db, "command_payload")
                session.status = "in_progress"
                session.waiting_for_approval = False
                db.commit()
                history.append({
                    "step": step_number,
                    "command": command,
                    "output": "[REJECTED BY HUMAN] Skipped.",
                    "success": False,
                })
                return step_number + 1

        if not approved:
            await self.event_publisher.publish_raw(db, session, {
                "event_type": "agent.approval_timeout",
                "step_number": step_number,
                "message": "Approval timed out. Step skipped.",
            })
            session.status = "in_progress"
            session.waiting_for_approval = False
            db.commit()
            return step_number + 1

        # Execute the approved destructive command
        result = await self._execute_step(
            connector=connector, connection_config=connection_config,
            command=command, step_db=step_db, db=db, session=session,
        )
        output = result.get("output") or result.get("error") or ""
        history.append({
            "step": step_number,
            "command": command,
            "output": output[:_MAX_OUTPUT_CHARS],
            "success": result.get("success", False),
        })
        return step_number + 1

    # ── LLM call ──────────────────────────────────────────────────────────────

    async def _ask_llm(
        self,
        issue_description: str,
        server: str,
        history: List[Dict],
        resolved_inputs: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Ask the LLM for the next action.
        Returns a dict: { "command": str, "reasoning": str, "done": bool,
                          "summary": str (if done) }
        """
        from app.services.llm_service_gemini import GeminiLLMService
        llm = GeminiLLMService()

        # Condense history: keep full for last N steps, summarise older ones
        if len(history) > _HISTORY_KEEP_LAST:
            older = history[:-_HISTORY_KEEP_LAST]
            recent = history[-_HISTORY_KEEP_LAST:]
            older_summary = "; ".join(
                f"step {h['step']}: {h['command'][:40]} → {'OK' if h['success'] else 'FAIL'}"
                for h in older
            )
            history_text = f"[Earlier steps summary]: {older_summary}\n\n"
            history_text += "\n".join(
                f"Step {h['step']}: $ {h['command']}\n"
                f"Output: {h['output'][:_MAX_OUTPUT_CHARS]}"
                for h in recent
            )
        else:
            history_text = "\n".join(
                f"Step {h['step']}: $ {h['command']}\n"
                f"Output: {h['output'][:_MAX_OUTPUT_CHARS]}"
                for h in history
            ) or "(no steps run yet)"

        resolved_text = ""
        if resolved_inputs:
            resolved_text = f"\nKnown values discovered so far: {json.dumps(resolved_inputs)}"

        system_prompt = (
            "You are an SRE agent diagnosing and fixing a server issue. "
            "Your goal is to identify the root cause and apply the minimal safe fix. "
            "Use read-only commands first to investigate, then targeted fix commands. "
            "Always verify the fix worked. "
            "Never run commands that affect other hosts or modify auth/credential files. "
            "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON."
        )

        user_prompt = f"""Issue to resolve: {issue_description}
Target server: {server}{resolved_text}

Steps completed so far:
{history_text}

What is your next action?

If you need to run another command, respond with:
{{
  "reasoning": "one sentence: what you observed and why you're running this next",
  "command": "exact shell command to run",
  "done": false
}}

If the issue is fully resolved and verified, respond with:
{{
  "reasoning": "what root cause was found and what fixed it",
  "command": null,
  "done": true,
  "summary": "concise description: root cause + action taken + verification result"
}}"""

        raw = await llm._chat_once_with_system(system_prompt, user_prompt)

        # Parse JSON response
        return self._parse_llm_response(raw)

    def _parse_llm_response(self, raw: str) -> Dict[str, Any]:
        """Parse LLM JSON response, tolerating markdown fences."""
        text = raw.strip()
        # Strip markdown code fences if present
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON object
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        logger.warning("Could not parse LLM response as JSON: %s", text[:200])
        return {"command": None, "reasoning": "parse error", "done": True,
                "summary": "Agent could not parse LLM response."}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _create_step(
        self,
        db: Session,
        session: ExecutionSession,
        step_number: int,
        command: str,
        reasoning: str,
        requires_approval: bool = False,
    ) -> ExecutionStep:
        step = ExecutionStep(
            session_id=session.id,
            step_number=step_number,
            step_type="main",
            command=command,
            requires_approval=requires_approval,
            completed=False,
            success=False,
            command_payload={"reasoning": reasoning, "agent_generated": True},
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        return step

    async def _execute_step(
        self,
        connector,
        connection_config: Dict[str, Any],
        command: str,
        step_db: ExecutionStep,
        db: Session,
        session: ExecutionSession,
    ) -> Dict[str, Any]:
        from app.services.security import redact_sensitive_text
        try:
            result = await connector.execute_command(
                command=command,
                connection_config=connection_config,
                timeout=60,
            )
        except Exception as e:
            result = {"success": False, "output": "", "error": str(e), "exit_code": -1}

        step_db.completed = True
        step_db.success = result.get("success", False)
        step_db.output = redact_sensitive_text(result.get("output") or "")
        step_db.error = redact_sensitive_text(result.get("error") or "")
        step_db.completed_at = datetime.now(timezone.utc)
        db.commit()
        return result

    def _peek_needed_vars(self, history: List[Dict], current_command: str) -> List[str]:
        """
        Look at what variables might be needed by looking at patterns in the
        current command and history.  Used to guide output extraction.
        """
        # Common vars the agent might need going forward
        return [
            "mount_point", "largest_dir", "largest_file", "service_name",
            "process_name", "hostname", "port", "log_file",
        ]


import re  # already imported at top but ensure available at module level


# ── Singleton ──────────────────────────────────────────────────────────────────

_agent_executor: Optional[AgentExecutor] = None


def get_agent_executor() -> AgentExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor()
    return _agent_executor
