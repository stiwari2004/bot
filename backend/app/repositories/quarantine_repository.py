"""
Repository for runbook quarantine data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.runbook_quarantine import RunbookQuarantine
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuarantineRepository(BaseRepository[RunbookQuarantine]):
    """Repository for RunbookQuarantine CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(RunbookQuarantine, db)

    def get_active_for_runbook(
        self,
        runbook_id: int,
        tenant_id: int,
        runbook_version_id: Optional[int] = None,
    ) -> Optional[RunbookQuarantine]:
        """Get active quarantine record for a runbook (pending or reviewed)"""
        query = self.db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id,
            RunbookQuarantine.tenant_id == tenant_id,
            RunbookQuarantine.review_status.in_(["pending_review", "reviewed"]),
        )
        if runbook_version_id is not None:
            query = query.filter(RunbookQuarantine.runbook_version_id == runbook_version_id)
        return query.first()

    def get_pending_reviews(self, tenant_id: int, limit: int = 50) -> List[RunbookQuarantine]:
        """Get quarantine records pending review for a tenant"""
        return self.db.query(RunbookQuarantine).filter(
            RunbookQuarantine.tenant_id == tenant_id,
            RunbookQuarantine.review_status == "pending_review",
        ).limit(limit).all()
