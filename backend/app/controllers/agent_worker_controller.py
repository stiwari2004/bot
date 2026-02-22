"""
Agent worker controller - handles agent worker management requests
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.controllers.base_controller import BaseController
from app.repositories.agent_worker_assignment_repository import AgentWorkerAssignmentRepository
from app.repositories.execution_repository import ExecutionRepository
from app.services.agent_worker_manager import agent_worker_manager
from app.services.execution_orchestrator import execution_orchestrator
from app.models.execution_session import AgentWorkerAssignment, ExecutionSession
from app.core.logging import get_logger
from app.core import metrics
from fastapi import HTTPException

logger = get_logger(__name__)


class AgentWorkerController(BaseController):
    """Controller for agent worker management endpoints"""
    
    def register_worker(
        self,
        worker_id: str,
        capabilities: List[str],
        network_segment: Optional[str] = None,
        environment: Optional[str] = None,
        max_concurrency: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        activation_token: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Register a worker and record initial heartbeat. If activation_token provided, validate before allowing."""
        try:
            if activation_token and db:
                from app.services.license.license_service import LicenseService
                license_svc = LicenseService(db)
                success, error, _ = license_svc.activate(activation_token)
                if not success:
                    raise HTTPException(status_code=403, detail=error or "Invalid activation token")
            state = agent_worker_manager.register_worker(
                worker_id=worker_id,
                capabilities=capabilities,
                network_segment=network_segment,
                environment=environment,
                max_concurrency=max_concurrency,
                metadata=metadata or {}
            )
            logger.info("Worker registered worker_id=%s environment=%s", state.worker_id, state.environment)
            return state.to_dict()
        except Exception as e:
            logger.error(f"Error registering worker: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to register worker")
    
    def heartbeat_worker(
        self,
        worker_id: str,
        current_load: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update worker heartbeat and current load"""
        try:
            state = agent_worker_manager.heartbeat(worker_id, current_load)
            if not state:
                raise self.not_found("Worker", None)
            return state.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating worker heartbeat: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to update worker heartbeat")
    
    def list_workers(
        self,
        capabilities: Optional[List[str]] = None,
        environment: Optional[str] = None,
        network_segment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return active workers filtered by optional criteria"""
        try:
            workers = agent_worker_manager.list_active_workers(
                capabilities=capabilities,
                environment=environment,
                network_segment=network_segment
            )
            return [worker.to_dict() for worker in workers]
        except Exception as e:
            logger.error(f"Error listing workers: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to list workers")
    
    def acknowledge_assignment(
        self,
        session_id: int,
        worker_id: str,
        assignment_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Mark the latest pending assignment for a session as acknowledged by worker"""
        try:
            assignment_repo = AgentWorkerAssignmentRepository(db)
            execution_repo = ExecutionRepository(db)
            
            # Get assignment using repository
            status_filter = None if assignment_id else "pending"
            assignment = assignment_repo.get_by_session_id(
                session_id=session_id,
                assignment_id=assignment_id,
                status=status_filter
            )
            if not assignment:
                raise self.not_found("Assignment", assignment_id)
            
            # Validate session exists using repository
            if not assignment_repo.session_exists(session_id):
                raise self.not_found("Execution session", session_id)
            
            # Update assignment using repository
            assignment = assignment_repo.update_assignment(
                assignment_id=assignment.id,
                worker_id=worker_id,
                status="acknowledged",
                acknowledged_at=datetime.now(timezone.utc)
            )
            
            agent_worker_manager.heartbeat(worker_id)
            metrics.record_assignment(assignment.status)
            
            return {
                "assignment_id": assignment.id,
                "status": assignment.status,
                "acknowledged_at": assignment.acknowledged_at.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error acknowledging assignment: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to acknowledge assignment")
    
    async def record_worker_event(
        self,
        session_id: int,
        event: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Allow workers to publish execution events back to orchestrator"""
        try:
            execution_repo = ExecutionRepository(db)
            
            # Get session using repository
            session = execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            stream_id = await execution_orchestrator.record_event(
                db,
                session_id=session_id,
                event_type=event,
                payload=payload,
                step_number=step_number
            )
            db.commit()
            
            return {
                "stream_id": stream_id,
                "event": event,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error recording worker event: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to record worker event")



