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
        """Get execution session by ID"""
        return self.db.query(ExecutionSession).filter(
            ExecutionSession.id == session_id
        ).first()
    
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
        step_type: str
    ) -> Optional[ExecutionStep]:
        """Get a specific execution step"""
        return self.db.query(ExecutionStep).filter(
            and_(
                ExecutionStep.session_id == session_id,
                ExecutionStep.step_number == step_number,
                ExecutionStep.step_type == step_type
            )
        ).first()
    
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


