"""
Agent worker controller - handles agent worker management requests
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.controllers.base_controller import BaseController
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a worker and record initial heartbeat"""
        try:
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
            query = db.query(AgentWorkerAssignment).filter(
                AgentWorkerAssignment.session_id == session_id
            )
            if assignment_id:
                query = query.filter(AgentWorkerAssignment.id == assignment_id)
            else:
                query = query.filter(AgentWorkerAssignment.status == "pending")
            
            assignment = query.order_by(AgentWorkerAssignment.id.desc()).first()
            if not assignment:
                raise self.not_found("Assignment", assignment_id)
            
            # Validate session exists
            session_exists = (
                db.query(ExecutionSession.id)
                .filter(ExecutionSession.id == session_id)
                .first()
            )
            if not session_exists:
                raise self.not_found("Execution session", session_id)
            
            assignment.worker_id = worker_id
            assignment.status = "acknowledged"
            assignment.acknowledged_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(assignment)
            
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
            session = (
                db.query(ExecutionSession)
                .filter(ExecutionSession.id == session_id)
                .first()
            )
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



