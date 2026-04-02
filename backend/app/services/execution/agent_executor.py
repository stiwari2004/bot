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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.services.execution.agent_llm_mixin     import _AgentLLMMixin
from app.services.execution.agent_step_mixin    import _AgentStepMixin
from app.services.execution.agent_precheck_mixin import _AgentPrecheckMixin
from app.services.execution.agent_diagnose_mixin import _AgentDiagnoseMixin
from app.services.execution.agent_execute_mixin  import _AgentExecuteMixin
from app.services.execution.command_classifier  import get_command_classifier
from app.services.execution.output_extractor    import get_output_extractor
from app.services.execution.step_event_publisher import StepEventPublisher
from app.services.infrastructure import get_connector
from app.services.threshold_service import get_threshold_service

logger = get_logger(__name__)


class AgentExecutor(
    _AgentPrecheckMixin,
    _AgentDiagnoseMixin,
    _AgentExecuteMixin,
    _AgentStepMixin,
    _AgentLLMMixin,
):
    """
    Drives three-phase agentic execution: diagnose → plan approval → execute.
    Creates ExecutionStep rows dynamically as the agent progresses.
    """

    def __init__(self):
        self.classifier         = get_command_classifier()
        self.extractor          = get_output_extractor()
        self.event_publisher    = StepEventPublisher()
        self.threshold_service  = get_threshold_service()
        from app.services.llm_service_gemini import GeminiLLMService
        self._llm = GeminiLLMService()

    # ── Public entry points ───────────────────────────────────────────────────

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
            "agent_session":     True,
            "issue_description": issue_description,
            "connection_config": connection_config,
            "phase":             "precheck",
            "precheck":          {},
            "diagnosis_history": [],
            "diagnosis":         None,
            "targets":           [],
            "approved_targets":  [],
            "excluded_targets":  [],
            "delete_log":        [],
            "resolved_inputs":   {},
            "agent_summary":     "",
            "agent_resolved":    False,
            "pending_review":    False,
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

        # ── Phase 2: Wait for human exclusion review ─────────────────────────
        approved = await self._wait_for_exclusions(db, session)
        if not approved:
            return self._abandoned_result(session)

        # ── Phase 3: Execute ─────────────────────────────────────────────────
        resolved, final_summary = await self._execute_phase(
            db, session, connector, connection_config, issue_description
        )

        if session.status == "abandoned":
            return self._abandoned_result(session)

        # ── Agent done — ask human to confirm resolution ─────────────────────
        # The ticket is NOT closed here. The human confirms whether the issue
        # is truly resolved via POST /confirm-resolution. Only then does the
        # ticket close. This prevents false-positive closures.
        session.status = "awaiting_human_confirmation"
        session.meta_data["phase"]          = "awaiting_human_confirmation"
        session.meta_data["pending_review"] = True
        flag_modified(session, "meta_data")
        db.commit()

        await self.event_publisher.publish_raw(db, session, {
            "event_type":      "agent.awaiting_confirmation",
            "agent_resolved":  resolved,
            "summary":         final_summary,
            "message": (
                f"Agent believes the issue {'is resolved' if resolved else 'could not be fully resolved'}. "
                "Please confirm: is the issue actually fixed on your end?"
            ),
        })

        return {
            "success":        resolved,
            "summary":        final_summary,
            "resolved":       resolved,
            "pending_review": True,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_agent_executor: Optional[AgentExecutor] = None


def get_agent_executor() -> AgentExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor()
    return _agent_executor
