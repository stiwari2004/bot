"""
_AgentDiagnoseMixin — Phase 1 (diagnose) and Phase 2 (plan approval) for AgentExecutor.
"""
import asyncio
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.services.infrastructure import get_connector

logger = get_logger(__name__)

_MAX_DIAGNOSE_ITERATIONS = 15
_MAX_REPLAN_COMMANDS     = 5
_MAX_OUTPUT_CHARS        = 400
_APPROVAL_POLL_INTERVAL  = 2
_PLAN_APPROVAL_TIMEOUT_S = 1800


class _AgentDiagnoseMixin:
    """Phase 1: read-only diagnosis loop. Phase 2: plan approval wait + re-plan."""

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
                findings   = action.get("findings") or {}
                approaches = action.get("approaches") or []

                # Backward compat: wrap legacy proposed_plan as a single approach (no steps needed)
                if not approaches:
                    legacy = action.get("proposed_plan") or []
                    if legacy:
                        approaches = [{
                            "id": "A",
                            "title": "Proposed Plan",
                            "rationale": "Agent-generated plan",
                            "risk": "medium",
                            "target": "",
                        }]
                        # Store legacy steps as generated_plan directly
                        session.meta_data["generated_plan"] = legacy

                if not approaches:
                    history.append({
                        "step": step_number,
                        "command": "(diagnosis_complete)",
                        "output": "[ERROR] diagnosis_complete must include an approaches array. Provide at least one approach.",
                        "success": False,
                    })
                    step_number += 1
                    continue

                session.meta_data["diagnosis"]         = findings
                session.meta_data["approaches"]        = approaches
                session.meta_data["proposed_plan"]     = None  # set after user selects approach + plan generated
                session.meta_data["generated_plan"]    = session.meta_data.get("generated_plan")  # preserve if set above
                session.meta_data["diagnosis_history"] = history
                session.meta_data["phase"]             = "awaiting_plan_approval"
                session.status = "awaiting_plan_approval"
                flag_modified(session, "meta_data")
                db.commit()

                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.plan_ready",
                    "diagnosis":  findings,
                    "approaches": approaches,
                    "message":    "Diagnosis complete. Select an approach to generate the remediation plan.",
                })
                return

            # ── Run a command ────────────────────────────────────────────────
            command   = (action.get("command") or "").strip()
            reasoning = (action.get("reasoning") or "")

            if not command:
                logger.warning("Diagnose phase: LLM returned empty command at iteration %d", iteration)
                break

            if not self.classifier.is_readonly(command):
                classification = self.classifier.classify(command)
                logger.warning("Diagnose phase blocked non-readonly command: %s", command[:80])
                await self.event_publisher.publish_raw(db, session, {
                    "event_type":  "agent.command_blocked",
                    "step_number": step_number,
                    "command":     command,
                    "reason":      f"Diagnose phase — read-only only. Blocked: {classification.reason}",
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

        logger.warning("Diagnose phase ended without diagnosis_complete after %d iterations", _MAX_DIAGNOSE_ITERATIONS)
        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.error",
            "message":    "Agent could not reach a diagnosis. Session abandoned.",
        })
        session.status = "abandoned"
        db.commit()

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
                session.meta_data["plan_rejected"] = False
                session.meta_data["plan_approved"] = None
                flag_modified(session, "meta_data")
                db.commit()

                await self._replan(db, session, connection_config, issue_description)
                elapsed = 0   # reset timeout — human gets full window to review new plan
                continue

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
                findings   = action.get("findings") or meta.get("diagnosis") or {}
                approaches = action.get("approaches") or []

                if not approaches:
                    legacy = action.get("proposed_plan") or []
                    if legacy:
                        approaches = [{
                            "id": "A",
                            "title": "Revised Plan",
                            "rationale": "Agent-revised plan based on feedback",
                            "risk": "medium",
                            "target": "",
                        }]

                if not approaches:
                    continue

                rejection_count = meta.get("plan_rejection_count", 0)
                session.meta_data["diagnosis"]         = findings
                session.meta_data["approaches"]        = approaches
                session.meta_data["proposed_plan"]     = None
                session.meta_data["generated_plan"]    = None  # clear previous generated plan
                session.meta_data["diagnosis_history"] = history
                session.meta_data["phase"]             = "awaiting_plan_approval"
                session.status = "awaiting_plan_approval"
                flag_modified(session, "meta_data")
                db.commit()

                await self.event_publisher.publish_raw(db, session, {
                    "event_type":      "agent.plan_revised",
                    "diagnosis":       findings,
                    "approaches":      approaches,
                    "revision_number": rejection_count,
                    "message":         "Approaches revised based on your feedback. Select one to generate the plan.",
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
