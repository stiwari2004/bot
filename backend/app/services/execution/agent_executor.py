"""
Agent Executor — three-phase agentic execution for issues with no matching runbook.

Phase 1 — DIAGNOSE
  Runs read-only (Level 1 only) discovery commands until the LLM declares
  diagnosis_complete, producing structured findings + a proposed plan.
  The session moves to awaiting_plan_approval and waits for a human decision.

Phase 2 — PLAN APPROVAL (human gate)
  Human reviews findings + plan together, then either:
    approve  → execute phase begins
    reject   → one LLM re-plan call with existing context + rejection feedback,
               back to awaiting_plan_approval (no new server commands needed)

Phase 3 — EXECUTE
  Runs the approved plan step by step.  All safety levels apply:
    Level 2 (CAUTION)     → countdown + auto-proceed
    Level 3 (DESTRUCTIVE) → dry-run preview + explicit human approval
    Level 4 (BLOCKED)     → refused, LLM tries alternative
  On completion the session is auto-crystallised into a runbook if resolved=True.

Step tagging: command_payload["phase"] = "diagnose" | "execute"
  Diagnose steps are auto-weeded during crystallisation (discovery, not runbook steps).
"""
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.command_classifier import get_command_classifier
from app.services.execution.output_extractor import get_output_extractor
from app.services.execution.step_event_publisher import StepEventPublisher
from app.services.infrastructure import get_connector

logger = get_logger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────
_MAX_VERIFY_COMMANDS     = 3      # max read-only commands for symptom verification
_MAX_DIAGNOSE_ITERATIONS = 15     # hard cap on diagnose-phase commands
_MAX_EXECUTE_ITERATIONS  = 15     # hard cap on execute-phase commands
_MAX_REPLAN_COMMANDS     = 5      # extra commands allowed during a re-plan call
_CAUTION_COUNTDOWN_S     = 10     # seconds before Level-2 command auto-proceeds
_HISTORY_KEEP_LAST       = 5      # keep last N step outputs in full in prompt
_MAX_OUTPUT_CHARS        = 400    # truncate individual step outputs in prompt
_APPROVAL_POLL_INTERVAL  = 2      # seconds between approval polls
_APPROVAL_TIMEOUT_S      = 300    # 5 min timeout for Level-3 step approval
_PLAN_APPROVAL_TIMEOUT_S = 1800   # 30 min timeout for plan approval


class AgentExecutor:
    """
    Drives three-phase agentic execution: diagnose → plan approval → execute.
    Creates ExecutionStep rows dynamically as the agent progresses.
    """

    def __init__(self):
        self.classifier    = get_command_classifier()
        self.extractor     = get_output_extractor()
        self.event_publisher = StepEventPublisher()
        from app.services.llm_service_gemini import GeminiLLMService
        self._llm = GeminiLLMService()

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(
        self,
        db: Session,
        session_id: int,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Dict[str, Any]:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            logger.error("AgentExecutor: session %d not found", session_id)
            return {"success": False, "summary": "Session not found", "steps_taken": 0,
                    "resolved": False, "pending_review": False}
        return await self._run_session(db, session, connection_config, issue_description)

    # ── Orchestrator ──────────────────────────────────────────────────────────

    async def _run_session(
        self,
        db: Session,
        session: ExecutionSession,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Dict[str, Any]:

        # Merge into existing meta_data — preserves creation-time context
        # (connection_id, ticket source, etc. set by create_agent_session)
        existing_meta = session.meta_data or {}
        session.status     = "precheck"
        session.started_at = datetime.now(timezone.utc)
        session.meta_data  = {
            **existing_meta,
            "agent_session":           True,
            "issue_description":       issue_description,
            "phase":                   "precheck",
            "precheck":                {},
            "diagnosis_history":       [],
            "diagnosis":               None,
            "proposed_plan":           None,
            "plan_approved":           None,
            "plan_rejected":           False,
            "plan_rejection_count":    0,
            "plan_rejection_feedback": [],
            "resolved_inputs":         {},
            "agent_summary":           "",
            "agent_resolved":          False,
            "pending_review":          False,
        }
        db.commit()

        connector_type = (connection_config.get("connector_type") or "local").lower()
        connector = get_connector(connector_type)

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.started",
            "message": f"Agent started for: {issue_description[:120]}",
        })

        # ── Phase 0: Triage (change window + symptom verification) ───────────
        precheck_verdict = await self._precheck_phase(
            db, session, connector, connection_config, issue_description
        )
        if precheck_verdict != "proceed":
            return {
                "success":        precheck_verdict == "false_positive",
                "summary":        f"Session closed during triage: {precheck_verdict}.",
                "resolved":       False,
                "pending_review": False,
            }

        # ── Phase 1: Diagnose ────────────────────────────────────────────────
        session.status = "diagnosing"
        session.meta_data["phase"] = "diagnosing"
        flag_modified(session, "meta_data")
        db.commit()
        await self._diagnose_phase(db, session, connector, connection_config, issue_description)

        if session.status == "abandoned":
            return self._abandoned_result(session)

        # ── Phase 2: Plan approval (with re-plan loop on rejection) ──────────
        approved = await self._wait_for_plan_approval(
            db, session, connection_config, issue_description
        )
        if not approved:
            return self._abandoned_result(session)

        # ── Phase 3: Execute ─────────────────────────────────────────────────
        resolved, final_summary = await self._execute_phase(
            db, session, connector, connection_config, issue_description
        )

        if session.status == "abandoned":
            return self._abandoned_result(session)

        # ── Auto-crystallise if resolved ─────────────────────────────────────
        if resolved:
            await self._auto_crystallise(db, session)

        session.status     = "completed" if resolved else "completed_with_errors"
        session.completed_at = datetime.now(timezone.utc)
        session.meta_data["pending_review"] = not resolved   # only unresolved needs manual review
        session.meta_data["phase"] = "done"
        flag_modified(session, "meta_data")
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.completed",
            "resolved":   resolved,
            "summary":    final_summary,
            "message":    (
                "Issue resolved and runbook saved."
                if resolved else
                "Execution finished with errors — please review the steps."
            ),
        })

        return {
            "success":        resolved,
            "summary":        final_summary,
            "resolved":       resolved,
            "pending_review": not resolved,
        }

    # ── Phase 0: Triage ───────────────────────────────────────────────────────

    async def _precheck_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> str:
        """
        Validate the alert before spending any diagnosis tokens.

        1. Change window check — if an active change window covers this
           service/environment the alert is expected behaviour; suppress the
           ticket and abort silently.

        2. Symptom verification — run up to _MAX_VERIFY_COMMANDS read-only
           commands to confirm the reported symptom exists right now.
             confirmed  → "proceed"        (true positive)
             not found  → "false_positive" (close ticket, no further action)
             uncertain  → "proceed"        (safe default — don't miss a real issue)

        Returns: "proceed" | "suppressed" | "false_positive"
        """
        # ── 1. Change window (via shared TriageService) ───────────────────
        from app.services.execution.triage_service import get_triage_service
        triage_verdict = get_triage_service().evaluate(db, session)

        if triage_verdict == "suppressed":
            # TriageService already set session.status=suppressed and committed.
            # Publish the event so the WebSocket stream shows context.
            meta = session.meta_data or {}
            change_ticket_ext = meta.get("suppressed_by_change_ticket_ext", "unknown")
            reason            = meta.get("suppression_reason", "Active change window")
            session.meta_data["precheck"] = {"verdict": "suppressed", "reason": reason}
            session.meta_data["phase"]    = "done"
            flag_modified(session, "meta_data")
            db.commit()

            await self.event_publisher.publish_raw(db, session, {
                "event_type":    "agent.suppressed",
                "change_ticket": change_ticket_ext,
                "reason":        reason,
                "message": (
                    f"Alert suppressed — {reason}. "
                    "Monitor will retrigger this session after the change window ends "
                    "if the alert is still firing."
                ),
            })
            return "suppressed"

        # ── 2. Symptom verification ───────────────────────────────────────
        session.meta_data["phase"] = "verifying"
        flag_modified(session, "meta_data")
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.verifying",
            "message":    "Verifying whether the reported symptom is currently present on the server...",
        })

        verdict, evidence, commands_run = await self._verify_symptom(
            db, session, connector, connection_config, issue_description
        )

        session.meta_data["precheck"] = {
            "verdict":      verdict,
            "evidence":     evidence,
            "commands_run": commands_run,
        }

        if verdict == "false_positive":
            session.status       = "closed_false_positive"
            session.completed_at = datetime.now(timezone.utc)
            session.meta_data["phase"] = "done"
            flag_modified(session, "meta_data")

            if session.ticket_id:
                from app.models.ticket import Ticket
                ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
                if ticket:
                    ticket.classification = "false_positive"
                    ticket.status         = "closed"
                    ticket.resolved_at    = datetime.now(timezone.utc)
            db.commit()

            await self.event_publisher.publish_raw(db, session, {
                "event_type": "agent.false_positive",
                "evidence":   evidence,
                "message": (
                    f"False positive — symptom not present on server. "
                    f"{evidence}. Ticket closed, no action taken."
                ),
            })
            logger.info("Session %d closed as false positive: %s", session.id, evidence)
            return "false_positive"

        # True positive or uncertain — proceed with diagnosis
        if session.ticket_id:
            from app.models.ticket import Ticket
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                ticket.classification = "true_positive"
                ticket.status         = "in_progress"
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.true_positive",
            "evidence":   evidence,
            "verdict":    verdict,
            "message":    f"Issue confirmed on server: {evidence}. Proceeding with diagnosis.",
        })
        return "proceed"

    async def _verify_symptom(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Tuple[str, str, List[str]]:
        """
        Run up to _MAX_VERIFY_COMMANDS read-only commands to confirm the symptom.

        Returns (verdict, evidence, commands_run)
          verdict: "true_positive" | "false_positive" | "uncertain"
        """
        history:      List[Dict] = []
        commands_run: List[str]  = []

        max_step = db.query(sqlfunc.max(ExecutionStep.step_number)).filter(
            ExecutionStep.session_id == session.id
        ).scalar() or 0
        step_number = max_step + 1

        for attempt in range(_MAX_VERIFY_COMMANDS):
            force_verdict = (attempt == _MAX_VERIFY_COMMANDS - 1)
            try:
                action = await self._llm_verify(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    history=history,
                    force_verdict=force_verdict,
                )
            except Exception as e:
                logger.error("Verify LLM call failed: %s", e)
                return ("uncertain", f"LLM call failed during verification: {e}", commands_run)

            if action.get("action") == "verdict":
                confirmed = bool(action.get("confirmed", True))
                evidence  = action.get("evidence") or ""
                return (
                    "true_positive" if confirmed else "false_positive",
                    evidence,
                    commands_run,
                )

            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                break

            if not self.classifier.is_readonly(command):
                history.append({
                    "step":    step_number,
                    "command": command,
                    "output":  "[BLOCKED — verification is read-only]",
                    "success": False,
                })
                step_number += 1
                continue

            step_db = self._create_step(db, session, step_number, command, reasoning, phase="diagnose")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)
            output  = result.get("output") or result.get("error") or ""

            history.append({
                "step":    step_number,
                "command": command,
                "output":  output[:_MAX_OUTPUT_CHARS],
                "success": result.get("success", False),
            })
            commands_run.append(command)

            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.verify_step",
                "step_number":    step_number,
                "command":        command,
                "output_preview": output[:200],
            })
            step_number += 1

        # Could not determine — safe default is to treat as true positive
        return ("uncertain", "Could not confirm or deny symptom — treating as true positive.", commands_run)

    async def _llm_verify(
        self,
        issue_description: str,
        connection_config: Dict[str, Any],
        history: List[Dict],
        force_verdict: bool = False,
    ) -> Dict[str, Any]:
        """LLM call for the symptom verification phase."""
        server     = connection_config.get("host") or connection_config.get("server_name") or "target"
        force_text = (
            "\nIMPORTANT: You must give a verdict now based on what you have seen so far."
            if force_verdict else ""
        )

        system_prompt = (
            "You are verifying whether a reported alert is a true positive or false positive. "
            "You are already connected to the target server. "
            "Run the single most direct read-only command that confirms whether the symptom "
            "is currently present (e.g., for 'disk full' run df -h, for 'service down' run "
            "systemctl status <service>). "
            "Do NOT investigate the root cause yet — just confirm if the problem exists right now. "
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
  "evidence": "one-line summary — e.g. Disk at 95% on /dev/sda1, issue is real"
}}
or
{{
  "action": "verdict",
  "confirmed": false,
  "evidence": "one-line summary — e.g. Disk at 42%, no issue present"
}}"""

        logger.info("Verify LLM call (history=%d, force=%s)", len(history), force_verdict)
        raw = await asyncio.wait_for(
            self._llm._chat_once_with_system(system_prompt, user_prompt),
            timeout=60.0,
        )
        return self._parse_llm_response(raw)

    # ── Phase 1: Diagnose ─────────────────────────────────────────────────────

    async def _diagnose_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> None:
        """
        Run read-only discovery commands until LLM declares diagnosis_complete.
        Stores findings + proposed_plan in session.meta_data and transitions
        the session to awaiting_plan_approval.
        """
        history: List[Dict] = []
        step_number = 1

        for iteration in range(_MAX_DIAGNOSE_ITERATIONS):
            rejection_feedbacks = session.meta_data.get("plan_rejection_feedback", [])

            try:
                action = await self._llm_diagnose(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    history=history,
                    rejection_feedbacks=rejection_feedbacks,
                    force_complete=(iteration == _MAX_DIAGNOSE_ITERATIONS - 1),
                )
            except Exception as e:
                logger.error("Diagnose LLM call failed: %s", e)
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message": f"LLM call failed during diagnosis: {e}",
                })
                break

            if action.get("_parse_error"):
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message":    "Could not parse LLM response during diagnosis — ending session.",
                })
                break

            if action.get("action") == "diagnosis_complete":
                findings      = action.get("findings") or {}
                proposed_plan = action.get("proposed_plan") or []

                if not proposed_plan:
                    # Invalid — feed back and keep diagnosing
                    history.append({
                        "step": step_number,
                        "command": "(diagnosis_complete)",
                        "output": "[ERROR] diagnosis_complete must include a proposed_plan. Provide one.",
                        "success": False,
                    })
                    step_number += 1
                    continue

                session.meta_data["diagnosis"]         = findings
                session.meta_data["proposed_plan"]     = proposed_plan
                session.meta_data["diagnosis_history"] = history
                session.meta_data["phase"]             = "awaiting_plan_approval"
                session.status = "awaiting_plan_approval"
                flag_modified(session, "meta_data")
                db.commit()

                await self.event_publisher.publish_raw(db, session, {
                    "event_type":    "agent.plan_ready",
                    "diagnosis":     findings,
                    "proposed_plan": proposed_plan,
                    "message":       "Diagnosis complete. Review and approve the plan to proceed.",
                })
                return

            # ── Run a command ────────────────────────────────────────────────
            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                logger.warning("Diagnose phase: LLM returned empty command at iteration %d", iteration)
                break

            # Enforce read-only
            if not self.classifier.is_readonly(command):
                classification = self.classifier.classify(command)
                logger.warning("Diagnose phase blocked non-readonly command: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":    "agent.command_blocked",
                    "step_number":   step_number,
                    "command":       command,
                    "reason":        f"Diagnose phase — read-only only. Blocked: {classification.reason}",
                })
                history.append({
                    "step":    step_number,
                    "command": command,
                    "output":  f"[DIAGNOSE PHASE — READ-ONLY ONLY] Blocked: {classification.reason}. Use a read-only alternative.",
                    "success": False,
                })
                step_number += 1
                continue

            step_db = self._create_step(db, session, step_number, command, reasoning, phase="diagnose")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)

            output  = result.get("output") or result.get("error") or ""
            success = result.get("success", False)

            history.append({
                "step":    step_number,
                "command": command,
                "output":  output[:_MAX_OUTPUT_CHARS],
                "success": success,
            })

            await self.event_publisher.publish_raw(db, session, {
                "event_type":     "agent.diagnose_step",
                "step_number":    step_number,
                "command":        command,
                "success":        success,
                "output_preview": output[:200],
            })
            step_number += 1

        # Fell through without diagnosis_complete — publish failure
        logger.warning("Diagnose phase ended without diagnosis_complete after %d iterations", _MAX_DIAGNOSE_ITERATIONS)
        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.error",
            "message":    "Agent could not reach a diagnosis. Session abandoned.",
        })
        session.status = "abandoned"
        db.commit()

    # ── Phase 2: Wait for plan approval ───────────────────────────────────────

    async def _wait_for_plan_approval(
        self,
        db: Session,
        session: ExecutionSession,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> bool:
        """
        Poll for plan_approved / plan_rejected flags set by the HTTP endpoints.
        On rejection: run one LLM re-plan call and loop back to wait.
        Returns True if approved, False on timeout or abandon.
        """
        elapsed = 0
        while elapsed < _PLAN_APPROVAL_TIMEOUT_S:
            await asyncio.sleep(_APPROVAL_POLL_INTERVAL)
            elapsed += _APPROVAL_POLL_INTERVAL

            db.refresh(session)
            if session.status == "abandoned":
                return False

            meta = session.meta_data or {}

            if meta.get("plan_approved") is True:
                session.meta_data["phase"] = "executing"
                flag_modified(session, "meta_data")
                db.commit()
                return True

            if meta.get("plan_rejected") is True:
                # Clear flag first to prevent re-entry
                session.meta_data["plan_rejected"] = False
                session.meta_data["plan_approved"] = None
                flag_modified(session, "meta_data")
                db.commit()

                await self._replan(db, session, connection_config, issue_description)
                elapsed = 0   # reset timeout — human gets full window to review new plan
                continue

        # Timeout
        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.plan_approval_timeout",
            "message":    "Plan approval timed out. Session abandoned.",
        })
        session.status = "abandoned"
        db.commit()
        return False

    async def _replan(
        self,
        db: Session,
        session: ExecutionSession,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> None:
        """
        One LLM call (force_complete=True) to produce a new plan using the
        existing diagnosis history + all accumulated rejection feedback.
        Optionally allows up to _MAX_REPLAN_COMMANDS extra read-only commands
        if the LLM genuinely needs a new fact before it can re-plan.
        """
        meta                = session.meta_data or {}
        history: List[Dict] = list(meta.get("diagnosis_history") or [])
        rejection_feedbacks = meta.get("plan_rejection_feedback", [])
        step_number         = len(history) + 1

        connector_type = (connection_config.get("connector_type") or "local").lower()
        connector      = get_connector(connector_type)

        for attempt in range(_MAX_REPLAN_COMMANDS + 1):
            force = (attempt == _MAX_REPLAN_COMMANDS)
            try:
                action = await self._llm_diagnose(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    history=history,
                    rejection_feedbacks=rejection_feedbacks,
                    force_complete=force,
                )
            except Exception as e:
                logger.error("Re-plan LLM call failed: %s", e)
                break

            if action.get("action") == "diagnosis_complete":
                findings      = action.get("findings") or meta.get("diagnosis") or {}
                proposed_plan = action.get("proposed_plan") or []

                if not proposed_plan:
                    # Still no plan — keep trying
                    continue

                rejection_count = meta.get("plan_rejection_count", 0)
                session.meta_data["diagnosis"]         = findings
                session.meta_data["proposed_plan"]     = proposed_plan
                session.meta_data["diagnosis_history"] = history
                session.meta_data["phase"]             = "awaiting_plan_approval"
                session.status = "awaiting_plan_approval"
                flag_modified(session, "meta_data")
                db.commit()

                await self.event_publisher.publish_raw(db, session, {
                    "event_type":       "agent.plan_revised",
                    "diagnosis":        findings,
                    "proposed_plan":    proposed_plan,
                    "revision_number":  rejection_count,
                    "message":          "Plan revised based on your feedback. Please review.",
                })
                return

            # LLM wants one more read-only command before committing
            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command or not self.classifier.is_readonly(command):
                continue

            step_db = self._create_step(db, session, step_number, command, reasoning, phase="diagnose")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)
            output  = result.get("output") or result.get("error") or ""
            history.append({
                "step":    step_number,
                "command": command,
                "output":  output[:_MAX_OUTPUT_CHARS],
                "success": result.get("success", False),
            })
            step_number += 1

    # ── Phase 3: Execute ──────────────────────────────────────────────────────

    async def _execute_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> Tuple[bool, str]:
        """
        Execute the approved plan.  Returns (resolved, final_summary).
        """
        meta          = session.meta_data or {}
        proposed_plan = meta.get("proposed_plan") or []
        history: List[Dict] = []
        resolved_inputs: Dict[str, str] = {}
        final_summary = ""
        resolved      = False

        max_step = db.query(sqlfunc.max(ExecutionStep.step_number)).filter(
            ExecutionStep.session_id == session.id
        ).scalar() or 0
        step_number = max_step + 1

        for iteration in range(_MAX_EXECUTE_ITERATIONS):
            try:
                action = await self._llm_execute(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    proposed_plan=proposed_plan,
                    history=history,
                    resolved_inputs=resolved_inputs,
                )
            except Exception as e:
                logger.error("Execute LLM call failed: %s", e)
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message":    f"LLM call failed during execution: {e}",
                })
                break

            if action.get("_parse_error"):
                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.error",
                    "message":    "Could not parse LLM response during execution — ending session.",
                })
                break

            if action.get("action") == "done":
                final_summary = action.get("summary", "Execution complete.")
                resolved      = bool(action.get("resolved", True))
                logger.info("Execute phase done after %d steps: %s", step_number - (max_step + 1), final_summary)
                break

            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                logger.warning("Execute phase: LLM returned empty command at iteration %d", iteration)
                break

            classification = self.classifier.classify(command)

            await self.event_publisher.publish_raw(db, session, {
                "event_type":   "agent.reasoning",
                "step_number":  step_number,
                "reasoning":    reasoning,
                "command":      command,
                "safety_level": classification.level,
                "safety_label": classification.label,
            })

            # Level 4 — BLOCKED
            if classification.level == 4:
                logger.warning("Execute phase: BLOCKED command: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":  "agent.command_blocked",
                    "step_number": step_number,
                    "command":     command,
                    "reason":      classification.reason,
                })
                history.append({
                    "step":    step_number,
                    "command": command,
                    "output":  f"[BLOCKED] {classification.reason}. Choose a different approach.",
                    "success": False,
                })
                step_number += 1
                continue

            # Level 3 — DESTRUCTIVE
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

            # Level 2 — CAUTION
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

            # Level 1 or post-countdown Level 2
            step_db = self._create_step(db, session, step_number, command, reasoning, phase="execute")
            result  = await self._execute_step(connector, connection_config, command, step_db, db, session)

            output  = result.get("output") or result.get("error") or ""
            success = result.get("success", False)

            # Extract values from output for future substitution
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

        if not resolved and not final_summary:
            final_summary = f"Agent reached maximum iterations ({_MAX_EXECUTE_ITERATIONS}) without confirming resolution."
            logger.warning(final_summary)

        session.meta_data["agent_summary"]  = final_summary
        session.meta_data["agent_resolved"] = resolved
        session.meta_data["resolved_inputs"] = resolved_inputs
        flag_modified(session, "meta_data")
        db.commit()

        return resolved, final_summary

    # ── Auto-crystallise ──────────────────────────────────────────────────────

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

    # ── Level-3 destructive handler ───────────────────────────────────────────

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

    # ── LLM calls ─────────────────────────────────────────────────────────────

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
            "When you have identified the root cause and can propose a safe, targeted fix plan, "
            "respond with diagnosis_complete. "
            "IMPORTANT: diagnosis_complete MUST always include a non-empty proposed_plan. "
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

2. Declare diagnosis complete (include BOTH findings AND plan):
{{
  "action": "diagnosis_complete",
  "findings": {{
    "root_cause": "concise description of the problem",
    "evidence": ["key fact 1", "key fact 2"],
    "safe_targets": ["paths or services that are safe to modify"],
    "risky_targets": ["paths or services to avoid — with reason"],
    "confidence": "high|medium|low"
  }},
  "proposed_plan": [
    {{"step": 1, "intent": "what this achieves", "command": "exact command", "risk": "low|medium|high"}}
  ]
}}"""

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

    # ── Helpers ───────────────────────────────────────────────────────────────

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

    def _create_step(
        self,
        db: Session,
        session: ExecutionSession,
        step_number: int,
        command: str,
        reasoning: str,
        phase: str = "execute",
        requires_approval: bool = False,
    ) -> ExecutionStep:
        step = ExecutionStep(
            session_id         = session.id,
            step_number        = step_number,
            step_type          = "main",
            command            = command,
            requires_approval  = requires_approval,
            completed          = False,
            success            = False,
            command_payload    = {
                "reasoning":       reasoning,
                "agent_generated": True,
                "phase":           phase,
            },
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

        step_db.completed    = True
        step_db.success      = result.get("success", False)
        step_db.output       = redact_sensitive_text(result.get("output") or "")
        step_db.error        = redact_sensitive_text(result.get("error") or "")
        step_db.completed_at = datetime.now(timezone.utc)
        db.commit()
        return result

    def _peek_needed_vars(self) -> List[str]:
        return [
            "mount_point", "largest_dir", "largest_file", "service_name",
            "process_name", "hostname", "port", "log_file",
        ]

    def _abandoned_result(self, session: ExecutionSession) -> Dict[str, Any]:
        return {
            "success": False, "summary": "Session abandoned.",
            "resolved": False, "pending_review": False,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_agent_executor: Optional[AgentExecutor] = None


def get_agent_executor() -> AgentExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor()
    return _agent_executor
