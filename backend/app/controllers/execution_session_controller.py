"""
ExecutionSessionController — session lifecycle operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.runbook_usage_repository import RunbookUsageRepository
from app.services.execution_orchestrator import execution_orchestrator
from app.services.idempotency import idempotency_manager
from app.services.ticket_status_service import get_ticket_status_service
from app.core.logging import get_logger
from app.core.transactions import transaction

logger = get_logger(__name__)


class ExecutionSessionController(BaseController):
    """Session lifecycle: create, get, list, complete, abandon, history"""

    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)
        self.runbook_repo = RunbookRepository(db)
        self.runbook_usage_repo = RunbookUsageRepository(db)
        self.ticket_status_service = get_ticket_status_service()

    async def create_execution_session(
        self,
        runbook_id: int,
        issue_description: Optional[str] = None,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        idempotency_key = (idempotency_key or "").strip() or None
        reservation_committed = False
        try:
            runbook = self.runbook_repo.get_approved_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
                if runbook:
                    raise self.bad_request("Runbook must be approved before execution")
                raise self.not_found("Runbook", runbook_id)

            if idempotency_key:
                existing_id = await idempotency_manager.reserve("session", idempotency_key)
                if existing_id:
                    if existing_id == "__PENDING__":
                        raise HTTPException(status_code=409, detail="Session creation already in progress for provided idempotency key.")
                    existing_session = self.execution_repo.get_by_id(int(existing_id))
                    if existing_session:
                        payload = execution_orchestrator.serialize_session(existing_session)
                        payload["runbook_title"] = runbook.title
                        return payload

            session = await execution_orchestrator.enqueue_session(
                self.db, runbook_id=runbook_id, tenant_id=self.tenant_id,
                ticket_id=ticket_id, issue_description=issue_description,
                user_id=user_id, metadata=metadata, idempotency_key=idempotency_key,
            )

            if session.status == "queued":
                with transaction(self.db):
                    session = self.execution_repo.update_session(session_id=session.id, status="pending")

            if ticket_id:
                self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket_id)

            payload = execution_orchestrator.serialize_session(session)
            payload["runbook_title"] = runbook.title

            if idempotency_key:
                await idempotency_manager.commit("session", idempotency_key, str(session.id))
                reservation_committed = True

            return payload
        except HTTPException:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("session", idempotency_key)
            raise
        except ValueError as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("session", idempotency_key)
            self.db.rollback()
            raise self.bad_request(str(e))
        except Exception as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("session", idempotency_key)
            self.db.rollback()
            logger.exception("Failed to enqueue execution session: %s", e)
            raise self.handle_error(e, "Failed to create execution session")

    def get_execution_session(self, session_id: int) -> Dict[str, Any]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            try:
                _ = session.steps
            except Exception as e:
                logger.warning(f"Error loading steps for session {session_id}: {e}")
            try:
                runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
            except Exception as e:
                logger.warning(f"Error loading runbook for session {session_id}: {e}")
                runbook = None
            try:
                payload = execution_orchestrator.serialize_session(session)
            except Exception as e:
                logger.error(f"Error serializing session {session_id}: {e}", exc_info=True)
                payload = {"id": session.id, "tenant_id": session.tenant_id, "runbook_id": session.runbook_id,
                           "status": session.status or "unknown", "current_step": session.current_step,
                           "steps": [], "error": "Failed to fully serialize session data"}
            if runbook:
                payload["runbook_title"] = f"{runbook.title} (Archived)" if runbook.is_active == "archived" else runbook.title
            else:
                payload["runbook_title"] = "Unknown (Runbook Deleted)"
            return payload
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting execution session {session_id}: {e}", exc_info=True)
            raise self.handle_error(e, f"Failed to get execution session {session_id}")

    def list_session_events(self, session_id: int, since_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            limit = max(1, min(limit, 500))
            try:
                return execution_orchestrator.list_events(self.db, session_id=session_id, since_id=since_id, limit=limit) or []
            except Exception as e:
                logger.error(f"Error listing events for session {session_id}: {e}", exc_info=True)
                return []
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in list_session_events for session {session_id}: {e}", exc_info=True)
            return []

    def complete_execution_session(self, session_id: int, was_successful: bool, issue_resolved: bool,
                                   rating: int, feedback_text: Optional[str] = None, suggestions: Optional[str] = None) -> Dict[str, Any]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            completed_at = datetime.now()
            duration_minutes = int((completed_at - session.started_at).total_seconds() / 60) if session.started_at else 0
            session.status = "completed" if was_successful else "failed"
            session.completed_at = completed_at
            session.total_duration_minutes = duration_minutes
            self.execution_repo.create_feedback(session_id=session_id, was_successful=was_successful,
                                                issue_resolved=issue_resolved, rating=rating,
                                                feedback_text=feedback_text, suggestions=suggestions)
            self.runbook_usage_repo.create_usage(runbook_id=session.runbook_id, tenant_id=session.tenant_id,
                                                 user_id=session.user_id, issue_description=session.issue_description,
                                                 confidence_score=0.0, was_helpful=was_successful,
                                                 feedback_text=feedback_text, execution_time_minutes=duration_minutes)
            return {"message": "Execution session completed", "session_id": session_id}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise self.handle_error(e, "Failed to complete execution session")

    def abandon_execution_session(self, session_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            if session.status in ["completed", "failed", "abandoned"]:
                raise self.bad_request(f"Session is already {session.status} and cannot be abandoned")
            completed_at = datetime.now(timezone.utc)
            duration_minutes = int((completed_at - session.started_at).total_seconds() / 60) if session.started_at else None
            self.execution_repo.update_session(session_id=session_id, status="abandoned",
                                               completed_at=completed_at, total_duration_minutes=duration_minutes)
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(self.db, session.ticket_id, "abandoned", issue_resolved=False)
            logger.info(f"Execution session {session_id} abandoned. Reason: {reason or 'No reason provided'}")
            return {"message": "Execution session abandoned", "session_id": session_id}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.exception("Failed to abandon execution session: %s", e)
            raise self.handle_error(e, "Failed to abandon execution session")

    def get_runbook_execution_history(self, runbook_id: int) -> Dict[str, Any]:
        sessions = self.execution_repo.get_by_runbook(runbook_id)
        result: List[Dict[str, Any]] = []
        for session in sessions:
            payload = execution_orchestrator.serialize_session(session)
            payload["steps_count"] = len(session.steps)
            if session.feedback:
                payload["feedback"] = {"was_successful": session.feedback.was_successful,
                                       "issue_resolved": session.feedback.issue_resolved,
                                       "rating": session.feedback.rating,
                                       "feedback_text": session.feedback.feedback_text}
            result.append(payload)
        return {"sessions": result}

    def list_all_executions(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        try:
            limit = max(1, min(limit, 500))
            offset = max(0, offset)
            sessions = self.execution_repo.get_by_tenant(self.tenant_id, limit=limit, offset=offset)
            result: List[Dict[str, Any]] = []
            for session in sessions:
                try:
                    if session not in self.db:
                        self.db.merge(session)
                    payload = execution_orchestrator.serialize_session(session)
                    runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
                    payload["runbook_title"] = (f"{runbook.title} (Archived)" if runbook and runbook.is_active == "archived"
                                                else runbook.title if runbook else "Unknown (Runbook Deleted)")
                    result.append(payload)
                except Exception as e:
                    logger.error(f"Error serializing session {session.id}: {e}", exc_info=True)
            return {"sessions": result}
        except Exception as e:
            logger.exception("Failed to list execution sessions: %s", e)
            return {"sessions": []}

    def get_pending_approvals(self) -> Dict[str, Any]:
        try:
            sessions = self.execution_repo.get_pending_approvals(self.tenant_id)
            result = []
            for session in sessions:
                step = self.execution_repo.get_step(session.id, session.approval_step_number, None)
                runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
                result.append({
                    "session_id": session.id, "runbook_id": session.runbook_id,
                    "runbook_title": runbook.title if runbook else "Unknown",
                    "step_number": session.approval_step_number,
                    "step_type": step.step_type if step else None,
                    "command": step.command if step else None,
                    "issue_description": session.issue_description,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                })
            return {"pending_approvals": result}
        except Exception as e:
            logger.exception("Failed to get pending approvals: %s", e)
            raise self.handle_error(e, "Failed to get pending approvals")
