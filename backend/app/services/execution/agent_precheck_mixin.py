"""
_AgentPrecheckMixin — Phase 0 (triage + symptom verification) for AgentExecutor.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)

_MAX_VERIFY_COMMANDS = 3
_MAX_OUTPUT_CHARS    = 400


class _AgentPrecheckMixin:
    """
    Phase 0: change window triage + symptom verification.

    Returns "proceed" | "suppressed" | "false_positive".
    """

    async def _precheck_phase(
        self,
        db: Session,
        session: ExecutionSession,
        connector,
        connection_config: Dict[str, Any],
        issue_description: str,
    ) -> str:
        """
        1. Change window check via TriageService — suppress if active window.
        2. Symptom verification — up to _MAX_VERIFY_COMMANDS read-only commands.

        Returns "proceed" | "suppressed" | "false_positive".
        """
        # ── 1. Change window (via shared TriageService) ───────────────────
        from app.services.execution.triage_service import get_triage_service
        triage_verdict = get_triage_service().evaluate(db, session)

        if triage_verdict == "suppressed":
            meta              = session.meta_data or {}
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

        verdict, evidence, commands_run, thresholds = await self._verify_symptom(
            db, session, connector, connection_config, issue_description
        )

        session.meta_data["precheck"] = {
            "verdict":      verdict,
            "evidence":     evidence,
            "commands_run": commands_run,
        }
        session.meta_data["thresholds"] = thresholds

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
    ) -> Tuple[str, str, List[str], Dict]:
        """
        Run up to _MAX_VERIFY_COMMANDS read-only commands to confirm the symptom.

        Returns (verdict, evidence, commands_run)
          verdict: "true_positive" | "false_positive" | "uncertain"
        """
        history:      List[Dict] = []
        commands_run: List[str]  = []

        # Fetch thresholds from threshold service (db/runbook/default) for LLM guidance
        environment = "prod"
        service = None
        if session.ticket_id:
            from app.models.ticket import Ticket
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                environment = ticket.environment or "prod"
                service = ticket.service
        thresholds = {}
        for metric in ("disk", "memory", "cpu", "network"):
            t = self.threshold_service.get_thresholds(
                metric=metric,
                environment=environment,
                service=service,
                tenant_id=session.tenant_id,
                runbook=None,
                db=db,
            )
            thresholds[metric] = {"warning": t.get("warning", 80), "critical": t.get("critical", 90)}

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
                    thresholds=thresholds,
                )
            except Exception as e:
                logger.error("Verify LLM call failed: %s", e)
                return ("uncertain", f"LLM call failed during verification: {e}", commands_run, thresholds)

            if action.get("action") == "verdict":
                confirmed = bool(action.get("confirmed", True))
                evidence  = action.get("evidence") or ""
                return (
                    "true_positive" if confirmed else "false_positive",
                    evidence,
                    commands_run,
                    thresholds,
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
        return ("uncertain", "Could not confirm or deny symptom — treating as true positive.", commands_run, thresholds)
