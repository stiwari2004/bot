"""
_AgentExecuteMixin — Phase 3 (execute) for AgentExecutor.
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

_MAX_EXECUTE_ITERATIONS = 20   # LLM-driven loop ceiling
_MAX_OUTPUT_CHARS       = 800
_CAUTION_COUNTDOWN_S    = 10
_APPROVAL_POLL_INTERVAL = 2
_APPROVAL_TIMEOUT_S     = 300


class _AgentExecuteMixin:
    """Phase 3: LLM-driven execution with safety gates and human resolution confirmation."""

    async def _execute_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Tuple[bool, str]:
        """
        LLM-driven execution loop.  The approved plan is provided as a guide;
        the LLM decides what to run next after seeing each step's output.
        It reasons about failures and adapts — no hardcoded recovery recipes.

        Safety gates remain:
          Level 2 (CAUTION)     → countdown + auto-proceed
          Level 3 (DESTRUCTIVE) → dry-run preview + explicit human approval
          Level 4 (BLOCKED)     → refused

        Returns (resolved, final_summary) — resolved reflects what the LLM
        declared AND passes the code-level _verify_resolution gate.
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

        for iteration in range(_MAX_EXECUTE_ITERATIONS):
            db.refresh(session)
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
                logger.error("Execute LLM call failed (iter %d): %s", iteration, e)
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message":    f"LLM call failed during execution: {e}",
                })
                break

            if action.get("_parse_error"):
                break

            # ── Agent declares done ───────────────────────────────────────────
            if action.get("action") == "done":
                claimed       = bool(action.get("resolved", False))
                final_summary = action.get("summary", "Execution complete.")

                # Code-level gate: verify the claim is supported by actual output
                if claimed and not self._verify_resolution(history, final_summary):
                    logger.warning(
                        "Execute: LLM claimed resolved=true but metric still critical — "
                        "injecting feedback and continuing"
                    )
                    # Feed back to the LLM as a failed verification so it continues
                    history.append({
                        "step":    step_number,
                        "command": "[VERIFICATION GATE]",
                        "output":  (
                            "Your last verification output still shows the issue as critical. "
                            "Do NOT declare resolved=true yet. "
                            "Run df -h (or free -h / systemctl status) to check the current metric, "
                            "then continue remediation if it has not improved."
                        ),
                        "success": False,
                    })
                    step_number += 1
                    continue

                resolved = claimed
                break

            # ── Agent wants to run a command ──────────────────────────────────
            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                logger.warning("Execute LLM returned empty command at iteration %d", iteration)
                break

            command = self._resolve_placeholders(command, resolved_inputs)
            if not command:
                continue

            classification = self.classifier.classify(command)

            await self.event_publisher.publish_raw(db, session, {
                "event_type":   "agent.reasoning",
                "step_number":  step_number,
                "reasoning":    reasoning,
                "command":      command,
                "safety_level": classification.level,
                "safety_label": classification.label,
            })

            # Level 4 — always blocked
            if classification.level == 4:
                logger.warning("Execute: BLOCKED command: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":  "agent.command_blocked",
                    "step_number": step_number,
                    "command":     command,
                    "reason":      classification.reason,
                })
                history.append({
                    "step":    step_number,
                    "command": command,
                    "output":  f"[BLOCKED — level 4] {classification.reason}. Choose a safer alternative.",
                    "success": False,
                })
                step_number += 1
                continue

            # Level 3 — requires human approval
            if classification.level == 3:
                step_number = await self._handle_destructive(
                    db=db, session=session, connector=connector,
                    connection_config=connection_config,
                    command=command, reasoning=reasoning,
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
            step_db = self._create_step(db, session, step_number, command, reasoning, phase="execute")
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
                "step":    step_number,
                "command": command,
                "output":  output[:_MAX_OUTPUT_CHARS],
                "success": success,
            })
            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.step_completed",
                "step_number":    step_number,
                "command":        command,
                "success":        success,
                "output_preview": output[:200],
            })
            step_number += 1

        if not final_summary:
            final_summary = "Execution complete — all steps ran."

        session.meta_data["agent_summary"]   = final_summary
        session.meta_data["agent_resolved"]  = resolved
        session.meta_data["resolved_inputs"] = resolved_inputs
        flag_modified(session, "meta_data")
        db.commit()

        return resolved, final_summary

    @staticmethod
    def _resolve_placeholders(command: str, resolved_inputs: Dict[str, str]) -> str:
        import re as _re
        result = command
        for var, val in (resolved_inputs or {}).items():
            result = result.replace(f"{{{{{var}}}}}", str(val))
        result = _re.sub(r'\s*\{\{\w+\}\}\s*', ' ', result).strip()
        return result

    @staticmethod
    def _verify_resolution(history: List[Dict], summary: str) -> bool:
        """
        Heuristic gate: returns False if obvious still-critical signals exist
        in recent output or the summary — even if the LLM claims resolved=true.
        Scans the last 5 real commands so a df -h earlier in verification still counts.
        """
        _METRIC_RE = re.compile(
            r'^(df|free|systemctl\s+status|ps\s+aux|ps\s+-ef|service\s+\S+\s+status)',
            re.IGNORECASE,
        )

        real_entries = [
            e for e in history
            if (e.get("command") or "").strip() and e.get("command") != "[SYSTEM]"
               and e.get("command") != "[VERIFICATION GATE]"
        ]
        recent = real_entries[-5:]

        # If any remediation step failed, require a metric check in recent history
        plan_failures = sum(
            1 for e in history
            if not e.get("success", True) and "[BLOCKED" not in (e.get("output") or "")
               and e.get("command") not in ("[SYSTEM]", "[VERIFICATION GATE]")
        )
        if plan_failures > 0:
            has_metric_check = any(_METRIC_RE.match(e.get("command") or "") for e in recent)
            if not has_metric_check:
                logger.warning(
                    "_verify_resolution: %d step(s) failed, no metric check in last 5 — "
                    "refusing resolved=true", plan_failures
                )
                return False

        # Scan recent outputs for still-critical signals
        for entry in recent:
            output = (entry.get("output") or "").lower()
            if re.search(r'\b(100|9[5-9])%', output):
                return False
            if re.search(r'\bactive\s*\(failed\)|\bfailed\b.*\.service', output):
                return False
            if re.search(r'no space left on device|write error.*28', output):
                return False

        # Memory near-zero: check only the most recent real output
        for entry in reversed(real_entries):
            output = (entry.get("output") or "").lower()
            if re.search(r'avail\s+\d+[mk]\b', output, re.IGNORECASE):
                return False
            break

        bad_phrases = [
            "still full", "still at 100", "no space", "not resolved",
            "could not free", "unable to free", "issue persists", "write error",
        ]
        if any(p in summary.lower() for p in bad_phrases):
            return False

        return True

    async def _auto_crystallise(self, db: Session, session: ExecutionSession) -> None:
        steps = (
            db.query(ExecutionStep)
            .filter(ExecutionStep.session_id == session.id)
            .all()
        )
        weed_numbers = [
            s.step_number for s in steps
            if (s.command_payload or {}).get("phase") == "diagnose"
            or ((s.command_payload or {}).get("phase") == "execute" and not s.success)
        ]
        meta  = session.meta_data or {}
        issue = meta.get("issue_description") or meta.get("agent_summary") or f"Session {session.id}"
        title = f"Auto: {issue[:60]}"

        from app.services.execution.runbook_crystalliser import get_runbook_crystalliser
        crystalliser = get_runbook_crystalliser()
        try:
            result = await crystalliser.crystallise(
                db=db, session=session,
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
            logger.info("Auto-crystallised runbook id=%d from session %d",
                        result["runbook_id"], session.id)
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

        elapsed = 0
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
