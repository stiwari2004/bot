"""
_AgentExecuteMixin — Phase 3 (execute), auto-crystallise, and destructive handler
for AgentExecutor.
"""
import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)

_MAX_EXECUTE_ITERATIONS = 15   # kept; plan now runs deterministically
_MAX_VERIFY_ITERATIONS  = 5    # LLM turns for post-plan verification
_MAX_OUTPUT_CHARS       = 800  # enough to see full df -h / du -sh output
_CAUTION_COUNTDOWN_S    = 10
_APPROVAL_POLL_INTERVAL = 2
_APPROVAL_TIMEOUT_S     = 300

# Read-only verification commands the agent should run before declaring done
_VERIFY_RE = re.compile(
    r'^(df|free|du|ps|top|systemctl\s+status|netstat|ss|lsof|iostat|vmstat|'
    r'cat\s+/proc|uname|uptime|ping|curl|wget|check)',
    re.IGNORECASE,
)


class _AgentExecuteMixin:
    """Phase 3: approved plan execution, auto-crystallise, Level-3 destructive handler."""

    async def _execute_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Tuple[bool, str]:
        """
        Execute the approved plan deterministically — each approved step runs
        in order via SSH.  The LLM is NOT consulted to pick what to run next;
        it is only used to:
          1. Adapt a single step if it fails (one retry attempt)
          2. Run a final verification after all steps complete
          3. Produce a summary
        """
        meta          = session.meta_data or {}
        proposed_plan = meta.get("proposed_plan") or []
        history: List[Dict] = []
        resolved_inputs: Dict[str, str] = {}
        resolved      = False
        final_summary = ""

        max_step = db.query(sqlfunc.max(ExecutionStep.step_number)).filter(
            ExecutionStep.session_id == session.id
        ).scalar() or 0
        step_number = max_step + 1

        # ── Phase A: run every approved plan step in order ────────────────────
        for plan_item in proposed_plan:
            raw_command = (plan_item.get("command") or "").strip()
            intent      = plan_item.get("intent") or plan_item.get("name") or raw_command[:60]

            if not raw_command:
                continue

            command = self._resolve_placeholders(raw_command, resolved_inputs)
            if not command:
                continue

            classification = self.classifier.classify(command)

            await self.event_publisher.publish_raw(db, session, {
                "event_type":   "agent.reasoning",
                "step_number":  step_number,
                "reasoning":    intent,
                "command":      command,
                "safety_level": classification.level,
                "safety_label": classification.label,
            })

            # Level 4 — always blocked
            if classification.level == 4:
                logger.warning("Execute phase: BLOCKED plan step: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":  "agent.command_blocked",
                    "step_number": step_number,
                    "command":     command,
                    "reason":      classification.reason,
                })
                history.append({
                    "step": step_number, "command": command,
                    "output": f"[BLOCKED] {classification.reason}", "success": False,
                })
                step_number += 1
                continue

            # Level 3 — destructive, requires human approval
            if classification.level == 3:
                step_number = await self._handle_destructive(
                    db=db, session=session, connector=connector,
                    connection_config=connection_config,
                    command=command, reasoning=intent,
                    classification=classification,
                    step_number=step_number, history=history,
                    resolved_inputs=resolved_inputs,
                )
                db.refresh(session)
                if session.status == "abandoned":
                    break
                continue

            # Level 2 — caution countdown
            if classification.level == 2:
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":        "agent.caution",
                    "step_number":       step_number,
                    "command":           command,
                    "reason":            classification.reason,
                    "countdown_seconds": _CAUTION_COUNTDOWN_S,
                    "message": (
                        f"State-changing command in {_CAUTION_COUNTDOWN_S}s: {command[:80]}. "
                        "Abandon session to cancel."
                    ),
                })
                await asyncio.sleep(_CAUTION_COUNTDOWN_S)
                db.refresh(session)
                if session.status == "abandoned":
                    break

            # Run the step
            step_db = self._create_step(db, session, step_number, command, intent, phase="execute")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)
            output  = result.get("output") or result.get("error") or ""
            success = result.get("success", False)

            if success and output:
                extracted = self.extractor.extract_from_output(
                    command=command, output=output,
                    needed_vars=self._peek_needed_vars(),
                )
                if extracted:
                    resolved_inputs.update(extracted)

            history.append({
                "step": step_number, "command": command,
                "output": output[:_MAX_OUTPUT_CHARS], "success": success,
            })
            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.step_completed",
                "step_number":    step_number,
                "command":        command,
                "success":        success,
                "output_preview": output[:200],
            })
            step_number += 1

            # If a step failed, ask LLM for a one-shot adaptation
            if not success:
                adapted = await self._adapt_failed_step(
                    plan_item=plan_item, failed_output=output,
                    history=history, resolved_inputs=resolved_inputs,
                    issue_description=issue_description,
                    connection_config=connection_config,
                )
                if adapted:
                    adapted = self._resolve_placeholders(adapted, resolved_inputs)
                    step_db2 = self._create_step(db, session, step_number, adapted, f"[retry] {intent}", phase="execute")
                    result2  = await self._execute_step(connector, connection_config, adapted, step_db2, db, session)
                    out2     = result2.get("output") or result2.get("error") or ""
                    history.append({
                        "step": step_number, "command": adapted,
                        "output": out2[:_MAX_OUTPUT_CHARS], "success": result2.get("success", False),
                    })
                    await self.event_publisher.publish_raw(db, session, {
                        "event_type":     "agent.step_completed",
                        "step_number":    step_number,
                        "command":        adapted,
                        "success":        result2.get("success", False),
                        "output_preview": out2[:200],
                    })
                    step_number += 1

        # ── Phase B: verification ─────────────────────────────────────────────
        # Ask LLM to run a verification command and summarise the result.
        # We allow up to _MAX_VERIFY_ITERATIONS LLM turns for this.
        for _ in range(_MAX_VERIFY_ITERATIONS):
            if session.status == "abandoned":
                break
            try:
                action = await self._llm_execute(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    proposed_plan=proposed_plan,
                    history=history,
                    resolved_inputs=resolved_inputs,
                )
            except Exception as e:
                logger.error("Verification LLM call failed: %s", e)
                break

            if action.get("_parse_error"):
                break

            if action.get("action") == "done":
                claimed = bool(action.get("resolved", False))
                # Code-level gate: if verification output shows issue still critical,
                # do not accept resolved=true
                if claimed and not self._verify_resolution(history, action.get("summary", "")):
                    logger.warning("Execute phase: LLM claimed resolved but metric still critical — marking unresolved")
                    claimed = False
                final_summary = action.get("summary", "Execution complete.")
                resolved      = claimed
                break

            # LLM wants to run a verification command
            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "verification")
            if not command:
                break

            command = self._resolve_placeholders(command, resolved_inputs)
            step_db = self._create_step(db, session, step_number, command, reasoning, phase="execute")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)
            output  = result.get("output") or result.get("error") or ""
            history.append({
                "step": step_number, "command": command,
                "output": output[:_MAX_OUTPUT_CHARS], "success": result.get("success", False),
            })
            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.step_completed",
                "step_number":    step_number,
                "command":        command,
                "success":        result.get("success", False),
                "output_preview": output[:200],
            })
            step_number += 1

        if not final_summary:
            final_summary = "Execution complete — all approved steps ran."

        session.meta_data["agent_summary"]   = final_summary
        session.meta_data["agent_resolved"]  = resolved
        session.meta_data["resolved_inputs"] = resolved_inputs
        flag_modified(session, "meta_data")
        db.commit()

        return resolved, final_summary

    async def _adapt_failed_step(
        self,
        plan_item: Dict[str, Any],
        failed_output: str,
        history: List[Dict],
        resolved_inputs: Dict[str, str],
        issue_description: str,
        connection_config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Ask the LLM for a single alternative command when a plan step fails.
        Returns the adapted command string, or None if no adaptation needed.
        """
        try:
            from app.services.execution.agent_llm_mixin import _AgentLLMMixin
            intent = plan_item.get("intent") or plan_item.get("name") or ""
            original = plan_item.get("command") or ""
            raw = await self._llm._chat_once_with_system(
                system_prompt=(
                    "You are an SRE agent. A remediation step failed. "
                    "Suggest ONE alternative command that achieves the same intent. "
                    "Reply with ONLY a JSON object: {\"command\": \"the alternative command\"}. "
                    "If no alternative is possible, reply: {\"command\": \"\"}."
                ),
                user_prompt=(
                    f"Failed command: {original}\n"
                    f"Intent: {intent}\n"
                    f"Error output: {failed_output[:400]}\n"
                    f"Suggest an alternative:"
                ),
            )
            import json as _json
            data = _json.loads(raw.strip())
            return (data.get("command") or "").strip() or None
        except Exception as e:
            logger.debug("Step adaptation failed: %s", e)
            return None

    @staticmethod
    def _resolve_placeholders(command: str, resolved_inputs: Dict[str, str]) -> str:
        """
        Replace any {{variable}} placeholders in a command with known resolved values.
        Placeholders with no known value are removed (with surrounding whitespace trimmed).
        Returns the resolved command, or empty string if the entire command becomes empty.
        """
        import re as _re
        result = command
        for var, val in (resolved_inputs or {}).items():
            result = result.replace(f"{{{{{var}}}}}", str(val))
        # Strip any remaining unresolvable placeholders
        result = _re.sub(r'\s*\{\{\w+\}\}\s*', ' ', result).strip()
        return result

    @staticmethod
    def _history_has_verification(history: List[Dict]) -> bool:
        """Return True if the last real (non-SYSTEM) command looks like a read-only verification."""
        for entry in reversed(history):
            cmd = (entry.get("command") or "").strip()
            if not cmd or cmd == "[SYSTEM]":
                continue
            return bool(_VERIFY_RE.match(cmd))
        return False

    @staticmethod
    def _verify_resolution(history: List[Dict], summary: str) -> bool:
        """
        Heuristic check: does the recent verification output and summary suggest
        the issue is actually resolved?  Returns False (challenge the claim) if
        obvious still-critical signals are detected.
        """
        # Look at the last real command's output for obvious still-failing signals
        for entry in reversed(history):
            cmd = (entry.get("command") or "").strip()
            if not cmd or cmd == "[SYSTEM]":
                continue
            output = (entry.get("output") or "").lower()
            # Disk: 100% or >=95% usage
            if re.search(r'\b(100|9[5-9])%', output):
                return False
            # Service still failed
            if re.search(r'\bactive\s*\(failed\)|\bfailed\b.*\.service', output):
                return False
            # Memory: 0 or near-0 available
            if re.search(r'avail\s+\d+[mk]\b', output, re.IGNORECASE):
                # very small available memory (M or K range)
                return False
            break  # only check the last real command

        # Also catch obvious "still broken" language in the summary
        bad_phrases = [
            "still full", "still at 100", "no space", "not resolved",
            "could not free", "unable to free", "issue persists",
        ]
        summary_lower = summary.lower()
        if any(p in summary_lower for p in bad_phrases):
            return False

        return True

    async def _auto_crystallise(self, db: Session, session: ExecutionSession) -> None:
        """
        Automatically crystallise the execution into a runbook.
        Diagnose-phase steps and failed execute-phase steps are auto-weeded.
        """
        steps = (
            db.query(ExecutionStep)
            .filter(ExecutionStep.session_id == session.id)
            .all()
        )

        weed_numbers = [
            s.step_number for s in steps
            if (s.command_payload or {}).get("phase") == "diagnose"
            or (
                (s.command_payload or {}).get("phase") == "execute"
                and not s.success
            )
        ]

        meta  = session.meta_data or {}
        issue = meta.get("issue_description") or meta.get("agent_summary") or f"Session {session.id}"
        title = f"Auto: {issue[:60]}"

        from app.services.execution.runbook_crystalliser import get_runbook_crystalliser
        crystalliser = get_runbook_crystalliser()
        try:
            result = await crystalliser.crystallise(
                db=db,
                session=session,
                weed_step_numbers=weed_numbers,
                runbook_title=title,
                tenant_id=session.tenant_id,
            )
            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.runbook_created",
                "runbook_id":     result["runbook_id"],
                "runbook_title":  result["runbook_title"],
                "steps_included": result["steps_included"],
                "message": (
                    f"Runbook saved: '{result['runbook_title']}' "
                    f"({result['steps_included']} steps)"
                ),
            })
            logger.info(
                "Auto-crystallised runbook id=%d from session %d",
                result["runbook_id"], session.id,
            )
        except ValueError as e:
            logger.warning("Auto-crystallise skipped: %s", e)

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
        """Dry-run preview → publish approval-required event → wait for human."""

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

        step_db = self._create_step(
            db, session, step_number, command, reasoning,
            phase="execute", requires_approval=True,
        )
        session.status               = "waiting_approval"
        session.waiting_for_approval = True
        session.approval_step_number = step_number
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type":      "agent.approval_required",
            "step_number":     step_number,
            "command":         command,
            "reason":          classification.reason,
            "dry_run_command": classification.dry_run_command,
            "dry_run_output":  dry_run_output,
            "message": (
                f"APPROVAL REQUIRED: {classification.reason}\n"
                f"Command: {command}\n"
                f"Preview:\n{dry_run_output or '(no preview available)'}"
            ),
        })

        elapsed  = 0
        approved = False
        while elapsed < _APPROVAL_TIMEOUT_S:
            await asyncio.sleep(_APPROVAL_POLL_INTERVAL)
            elapsed += _APPROVAL_POLL_INTERVAL
            db.refresh(step_db)
            db.refresh(session)

            if session.status == "abandoned":
                return step_number

            if step_db.approved is True:
                approved = True
                session.status               = "in_progress"
                session.waiting_for_approval = False
                db.commit()
                break

            if step_db.approved is False:
                step_db.notes = "Rejected by human — marked as weed"
                cmd_payload   = step_db.command_payload or {}
                cmd_payload["weed"] = True
                step_db.command_payload = cmd_payload
                flag_modified(step_db, "command_payload")
                session.status               = "in_progress"
                session.waiting_for_approval = False
                db.commit()
                history.append({
                    "step":    step_number,
                    "command": command,
                    "output":  "[REJECTED BY HUMAN] Skipped.",
                    "success": False,
                })
                return step_number + 1

        if not approved:
            await self.event_publisher.publish_raw(db, session, {
                "event_type":  "agent.approval_timeout",
                "step_number": step_number,
                "message":     "Approval timed out. Step skipped.",
            })
            session.status               = "in_progress"
            session.waiting_for_approval = False
            db.commit()
            return step_number + 1

        result = await self._execute_step(
            connector, connection_config, command, step_db, db, session
        )
        output = result.get("output") or result.get("error") or ""
        history.append({
            "step":    step_number,
            "command": command,
            "output":  output[:_MAX_OUTPUT_CHARS],
            "success": result.get("success", False),
        })
        return step_number + 1
