"""
_AgentDiagnoseMixin — Phase 1 (diagnose) and exclusion wait for AgentExecutor.
"""
import asyncio
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession

logger = get_logger(__name__)

_MAX_DIAGNOSE_ITERATIONS = 8    # 2-4 commands typical; 8 is the hard ceiling
_MAX_OUTPUT_CHARS        = 800  # enough for full du -sh /* output
_EXCLUSION_POLL_INTERVAL = 2
_EXCLUSION_TIMEOUT_S     = 1800


class _AgentDiagnoseMixin:
    """Phase 1: read-only diagnosis loop. Exclusion wait before execute."""

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
        Stores findings + targets in session.meta_data and transitions
        the session to awaiting_exclusions.
        """
        history: List[Dict] = []
        step_number = 1

        for iteration in range(_MAX_DIAGNOSE_ITERATIONS):
            try:
                action = await self._llm_diagnose(
                    issue_description=issue_description,
                    connection_config=connection_config,
                    history=history,
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
                findings = action.get("findings") or {}
                targets  = action.get("targets") or []

                if not targets:
                    history.append({
                        "step": step_number,
                        "command": "(diagnosis_complete)",
                        "output": "[ERROR] diagnosis_complete must include a non-empty targets array. Provide at least one target.",
                        "success": False,
                    })
                    step_number += 1
                    continue

                session.meta_data["diagnosis"]         = findings
                session.meta_data["targets"]           = targets
                session.meta_data["diagnosis_history"] = history
                session.meta_data["phase"]             = "awaiting_exclusions"
                session.status = "awaiting_exclusions"
                flag_modified(session, "meta_data")
                db.commit()

                await self.event_publisher.publish_raw(db, session, {
                    "event_type": "agent.targets_ready",
                    "targets":    targets,
                    "findings":   findings,
                    "message":    "Diagnosis complete. Review the discovered targets and exclude anything you want to protect.",
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

    async def _wait_for_exclusions(self, db: Session, session: ExecutionSession) -> bool:
        """
        Poll until the human submits exclusions and status transitions to 'executing'.
        Returns True when executing, False on timeout or abandon.
        """
        elapsed = 0
        while elapsed < _EXCLUSION_TIMEOUT_S:
            await asyncio.sleep(_EXCLUSION_POLL_INTERVAL)
            elapsed += _EXCLUSION_POLL_INTERVAL

            db.refresh(session)
            if session.status == "abandoned":
                return False

            if session.status == "executing":
                return True

        await self.event_publisher.publish_raw(db, session, {
            "event_type": "agent.error",
            "message":    "Exclusion review timed out. Session abandoned.",
        })
        session.status = "abandoned"
        db.commit()
        return False
