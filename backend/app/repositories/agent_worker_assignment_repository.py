"""
Repository for agent worker assignment data access
"""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.execution_session import AgentWorkerAssignment, ExecutionSession
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentWorkerAssignmentRepository(BaseRepository[AgentWorkerAssignment]):
    """Repository for agent worker assignment CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(AgentWorkerAssignment, db)
    
    def get_by_session_id(
        self,
        session_id: int,
        assignment_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Optional[AgentWorkerAssignment]:
        """Get assignment by session ID, optionally filtered by assignment_id or status"""
        query = self.db.query(AgentWorkerAssignment).filter(
            AgentWorkerAssignment.session_id == session_id
        )
        
        if assignment_id:
            query = query.filter(AgentWorkerAssignment.id == assignment_id)
        elif status:
            query = query.filter(AgentWorkerAssignment.status == status)
        
        return query.order_by(AgentWorkerAssignment.id.desc()).first()
    
    def session_exists(self, session_id: int) -> bool:
        """Check if execution session exists"""
        return self.db.query(ExecutionSession.id).filter(
            ExecutionSession.id == session_id
        ).first() is not None
    
    def update_assignment(
        self,
        assignment_id: int,
        **kwargs
    ) -> Optional[AgentWorkerAssignment]:
        """Update assignment fields"""
        assignment = self.get(assignment_id)
        if assignment:
            for key, value in kwargs.items():
                setattr(assignment, key, value)
            self.db.commit()
            self.db.refresh(assignment)
        return assignment








