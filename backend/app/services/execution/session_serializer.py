"""
Session Serializer — converts ExecutionSession ORM objects to response payloads
"""
from typing import Dict, Any
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)


class SessionSerializer:
    """Transforms ExecutionSession ORM instances into JSON-serializable response payloads"""

    def __init__(self, metadata_service):
        self.metadata_service = metadata_service

    def serialize_session(self, session: ExecutionSession) -> Dict[str, Any]:
        """Transform ExecutionSession into response payload"""
        steps_list = []
        try:
            if hasattr(session, "steps") and session.steps:
                steps_list = [
                    self._serialize_step(step)
                    for step in sorted(session.steps, key=lambda s: s.step_number)
                ]
        except Exception as e:
            logger.warning(f"Error accessing steps for session {session.id}: {e}")

        payload: Dict[str, Any] = {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "status": session.status or "unknown",
            "current_step": session.current_step,
            "waiting_for_approval": session.waiting_for_approval or False,
            "transport_channel": session.transport_channel,
            "last_event_seq": session.last_event_seq,
            "sandbox_profile": session.sandbox_profile,
            "assignment_retry_count": session.assignment_retry_count or 0,
            "issue_description": session.issue_description,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": steps_list,
        }

        try:
            metadata = self._latest_assignment_metadata(session)
            if metadata:
                sanitized_metadata = self.metadata_service.sanitize_metadata(metadata)
                payload["connection"] = sanitized_metadata.get("connection") or sanitized_metadata
        except Exception as e:
            logger.warning(f"Error getting assignment metadata for session {session.id}: {e}")

        # Agent-session fields — expose review/crystallise context to the UI
        try:
            meta = session.meta_data or {}
            if meta.get("agent_session"):
                payload["agent_summary"]   = meta.get("agent_summary", "")
                payload["agent_resolved"]  = meta.get("agent_resolved", False)
                payload["pending_review"]  = meta.get("pending_review", False)
                payload["issue_description"] = meta.get("issue_description") or session.issue_description
        except Exception as e:
            logger.warning(f"Error adding agent fields for session {session.id}: {e}")

        return payload

    def _serialize_step(self, step: ExecutionStep) -> Dict[str, Any]:
        try:
            return {
                "id": step.id,
                "step_number": step.step_number,
                "step_type": step.step_type,
                "command": step.command,
                "rollback_command": step.rollback_command,
                "requires_approval": step.requires_approval,
                "approved": step.approved,
                "approved_at": step.approved_at.isoformat() if step.approved_at else None,
                "sandbox_profile": step.sandbox_profile,
                "blast_radius": step.blast_radius,
                "approval_policy": step.approval_policy,
                "completed": step.completed,
                "success": step.success,
                "output": step.output,
                "error": step.error,
                "notes": step.notes,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }
        except Exception as e:
            logger.warning(f"Error serializing step {step.id if step else 'unknown'}: {e}")
            return {
                "id": step.id if step else None,
                "step_number": step.step_number if step else 0,
                "error": "Failed to serialize step",
            }

    def _latest_assignment_metadata(self, session: ExecutionSession) -> Dict[str, Any]:
        """Return the most recent assignment metadata/details for the session"""
        try:
            if not hasattr(session, "assignments") or not session.assignments:
                return {}
            for assignment in sorted(session.assignments, key=lambda a: a.id, reverse=True):
                if assignment and hasattr(assignment, "details") and assignment.details:
                    return assignment.details
            return {}
        except Exception as e:
            logger.warning(f"Error accessing assignment metadata: {e}")
            return {}
