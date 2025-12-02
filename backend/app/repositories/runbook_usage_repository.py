"""
Repository for runbook usage data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.runbook_usage import RunbookUsage
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookUsageRepository(BaseRepository[RunbookUsage]):
    """Repository for runbook usage CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(RunbookUsage, db)
    
    def create_usage(
        self,
        runbook_id: int,
        tenant_id: int,
        user_id: Optional[int],
        issue_description: Optional[str],
        confidence_score: float,
        was_helpful: Optional[bool],
        feedback_text: Optional[str],
        execution_time_minutes: Optional[int]
    ) -> RunbookUsage:
        """Create a new runbook usage record"""
        usage = RunbookUsage(
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            user_id=user_id,
            issue_description=issue_description,
            confidence_score=confidence_score,
            was_helpful=was_helpful,
            feedback_text=feedback_text,
            execution_time_minutes=execution_time_minutes
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

