"""
QuarantineController
Handles HTTP requests for runbook quarantine operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.quarantine_repository import QuarantineRepository
from app.services.execution.quarantine_service import QuarantineService
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuarantineController(BaseController):
    """Controller for runbook quarantine operations"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.quarantine_repo = QuarantineRepository(db)
        self.quarantine_service = QuarantineService()

    def get_quarantine_status(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get quarantine status for a runbook"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            is_quarantined = self.quarantine_service.is_quarantined(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                tenant_id=self.tenant_id,
            )

            if is_quarantined:
                quarantine = self.quarantine_repo.get_active_for_runbook(
                    runbook_id, self.tenant_id, runbook_version_id
                )
                if quarantine:
                    return {
                        "is_quarantined": True,
                        "quarantine_id": quarantine.id,
                        "reason": quarantine.quarantine_reason,
                        "failure_count": quarantine.failure_count,
                        "quarantined_at": quarantine.quarantined_at.isoformat() if quarantine.quarantined_at else None,
                        "review_status": quarantine.review_status,
                    }

            return {"is_quarantined": False}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting quarantine status for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get quarantine status")

    def quarantine_runbook(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int],
        reason: str,
        quarantined_by: int,
        auto_release_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Manually quarantine a runbook"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            quarantine = self.quarantine_service.quarantine_runbook(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                reason=reason,
                tenant_id=self.tenant_id,
                quarantined_by=quarantined_by,
                auto_release_hours=auto_release_hours,
            )

            return {
                "quarantine_id": quarantine.id,
                "runbook_id": runbook_id,
                "runbook_version_id": runbook_version_id,
                "reason": quarantine.quarantine_reason,
                "message": "Runbook quarantined successfully",
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error quarantining runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to quarantine runbook")

    def release_quarantine(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int],
        reviewed_by: int,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Release a runbook from quarantine"""
        try:
            quarantine = self.quarantine_service.release_quarantine(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
                tenant_id=self.tenant_id,
            )
            return {
                "quarantine_id": quarantine.id,
                "runbook_id": runbook_id,
                "runbook_version_id": runbook_version_id,
                "message": "Quarantine released successfully",
            }

        except ValueError:
            raise self.not_found("Quarantine", None)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error releasing quarantine for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to release quarantine")

    def get_pending_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get runbooks pending review"""
        try:
            quarantines = self.quarantine_service.get_pending_reviews(
                db=self.db,
                tenant_id=self.tenant_id,
                limit=limit,
            )

            results = []
            for quarantine in quarantines:
                runbook = self.runbook_repo.get_by_id_and_tenant(
                    quarantine.runbook_id, self.tenant_id
                )
                results.append({
                    "quarantine_id": quarantine.id,
                    "runbook_id": quarantine.runbook_id,
                    "runbook_title": runbook.title if runbook else None,
                    "runbook_version_id": quarantine.runbook_version_id,
                    "reason": quarantine.quarantine_reason,
                    "failure_count": quarantine.failure_count,
                    "quarantined_at": quarantine.quarantined_at.isoformat() if quarantine.quarantined_at else None,
                    "failure_pattern": quarantine.failure_pattern,
                })

            return results

        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            raise self.handle_error(e, "Failed to get pending reviews")

    def get_failure_patterns(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get failure pattern analysis for a runbook"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            return self.quarantine_service.analyze_failure_pattern(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                tenant_id=self.tenant_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting failure patterns for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get failure patterns")
