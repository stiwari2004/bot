"""
Repository for execution session data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.execution_session import ExecutionSession, ExecutionStep, ExecutionFeedback
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionRepository(BaseRepository[ExecutionSession]):
    """Repository for execution session CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(ExecutionSession, db)
    
    def get_by_id(self, session_id: int) -> Optional[ExecutionSession]:
        """Get execution session by ID with eager loading"""
        from sqlalchemy.orm import joinedload
        query = self.db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id
        )
        # Eager load relationships
        query = query.options(
            joinedload(ExecutionSession.runbook),
            joinedload(ExecutionSession.ticket),
            joinedload(ExecutionSession.steps)
        )
        return query.first()
    
    def get_by_tenant(
        self,
        tenant_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExecutionSession]:
        """Get all execution sessions for a tenant with pagination"""
        try:
            from sqlalchemy.orm import joinedload
            query = self.db.query(ExecutionSession).filter(
                ExecutionSession.tenant_id == tenant_id
            )
            # Eager load relationships to avoid lazy loading issues
            query = query.options(
                joinedload(ExecutionSession.steps),
                joinedload(ExecutionSession.assignments)
            )
            # Order by created_at (always exists)
            query = query.order_by(ExecutionSession.created_at.desc())
            return query.offset(offset).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting executions by tenant: {e}", exc_info=True)
            # Fallback: return empty list instead of crashing
            return []
    
    def get_by_runbook(
        self,
        runbook_id: int
    ) -> List[ExecutionSession]:
        """Get all execution sessions for a specific runbook"""
        return self.db.query(ExecutionSession).filter(
            ExecutionSession.runbook_id == runbook_id
        ).order_by(ExecutionSession.started_at.desc()).all()
    
    def get_step(
        self,
        session_id: int,
        step_number: int,
        step_type: Optional[str] = None
    ) -> Optional[ExecutionStep]:
        """Get a specific execution step"""
        query = self.db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_number
        )
        if step_type:
            query = query.filter(ExecutionStep.step_type == step_type)
        return query.first()
    
    def create_feedback(
        self,
        session_id: int,
        was_successful: bool,
        issue_resolved: bool,
        rating: int,
        feedback_text: Optional[str] = None,
        suggestions: Optional[str] = None
    ) -> ExecutionFeedback:
        """Create execution feedback"""
        feedback = ExecutionFeedback(
            session_id=session_id,
            was_successful=was_successful,
            issue_resolved=issue_resolved,
            rating=rating,
            feedback_text=feedback_text,
            suggestions=suggestions
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def get_by_ticket_id(
        self,
        ticket_id: int
    ) -> List[ExecutionSession]:
        """Get all execution sessions for a ticket"""
        return self.db.query(ExecutionSession).filter(
            ExecutionSession.ticket_id == ticket_id
        ).order_by(ExecutionSession.created_at.desc()).all()
    
    def update_session(
        self,
        session_id: int,
        **kwargs
    ) -> Optional[ExecutionSession]:
        """Update execution session fields"""
        session = self.get_by_id(session_id)
        if session:
            for key, value in kwargs.items():
                setattr(session, key, value)
            self.db.commit()
            self.db.refresh(session)
        return session
    
    def get_pending_approvals(self, tenant_id: int) -> List[ExecutionSession]:
        """Get all sessions waiting for approval for a tenant"""
        return self.db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == tenant_id,
            ExecutionSession.waiting_for_approval == True,
            ExecutionSession.status == "waiting_approval"
        ).all()


