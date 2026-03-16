"""
_AgentStepMixin — step creation, execution, and small helpers for AgentExecutor.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)


class _AgentStepMixin:
    """Create/execute ExecutionStep rows and misc helper methods."""

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
            session_id        = session.id,
            step_number       = step_number,
            step_type         = "main",
            command           = command,
            requires_approval = requires_approval,
            completed         = False,
            success           = False,
            command_payload   = {
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
