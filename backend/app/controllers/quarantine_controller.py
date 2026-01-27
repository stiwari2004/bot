"""
QuarantineController
Handles HTTP requests for runbook quarantine operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.models.runbook_quarantine import RunbookQuarantine
from app.models.runbook import Runbook
from app.services.execution.quarantine_service import QuarantineService
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuarantineController(BaseController):
    """Controller for runbook quarantine operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.quarantine_service = QuarantineService()
    
    def get_quarantine_status(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get quarantine status for a runbook
        
        Args:
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            
        Returns:
            Quarantine status dictionary
        """
        try:
            # Verify runbook belongs to tenant
            runbook = self.db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == self.tenant_id
            ).first()
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            is_quarantined = self.quarantine_service.is_quarantined(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                tenant_id=self.tenant_id
            )
            
            if is_quarantined:
                query = self.db.query(RunbookQuarantine).filter(
                    RunbookQuarantine.runbook_id == runbook_id,
                    RunbookQuarantine.tenant_id == self.tenant_id,
                    RunbookQuarantine.review_status.in_(["pending_review", "reviewed"])
                )
                
                if runbook_version_id:
                    query = query.filter(
                        RunbookQuarantine.runbook_version_id == runbook_version_id
                    )
                
                quarantine = query.first()
                
                if quarantine:
                    return {
                        "is_quarantined": True,
                        "quarantine_id": quarantine.id,
                        "reason": quarantine.quarantine_reason,
                        "failure_count": quarantine.failure_count,
                        "quarantined_at": quarantine.quarantined_at.isoformat() if quarantine.quarantined_at else None,
                        "review_status": quarantine.review_status
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
        auto_release_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Manually quarantine a runbook
        
        Args:
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            reason: Quarantine reason
            quarantined_by: User ID who quarantined
            auto_release_hours: Optional hours until auto-release
            
        Returns:
            Quarantine result dictionary
        """
        try:
            # Verify runbook belongs to tenant
            runbook = self.db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == self.tenant_id
            ).first()
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            quarantine = self.quarantine_service.quarantine_runbook(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                reason=reason,
                tenant_id=self.tenant_id,
                quarantined_by=quarantined_by,
                auto_release_hours=auto_release_hours
            )
            
            return {
                "quarantine_id": quarantine.id,
                "runbook_id": runbook_id,
                "runbook_version_id": runbook_version_id,
                "reason": quarantine.quarantine_reason,
                "message": "Runbook quarantined successfully"
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
        review_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Release a runbook from quarantine
        
        Args:
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            reviewed_by: User ID who reviewed
            review_notes: Optional review notes
            
        Returns:
            Release result dictionary
        """
        try:
            quarantine = self.quarantine_service.release_quarantine(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
                tenant_id=self.tenant_id
            )
            
            return {
                "quarantine_id": quarantine.id,
                "runbook_id": runbook_id,
                "runbook_version_id": runbook_version_id,
                "message": "Quarantine released successfully"
            }
        
        except ValueError as e:
            raise self.not_found("Quarantine", None)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error releasing quarantine for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to release quarantine")
    
    def get_pending_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get runbooks pending review
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of quarantine records
        """
        try:
            quarantines = self.quarantine_service.get_pending_reviews(
                db=self.db,
                tenant_id=self.tenant_id,
                limit=limit
            )
            
            results = []
            for quarantine in quarantines:
                runbook = self.db.query(Runbook).filter(Runbook.id == quarantine.runbook_id).first()
                
                results.append({
                    "quarantine_id": quarantine.id,
                    "runbook_id": quarantine.runbook_id,
                    "runbook_title": runbook.title if runbook else None,
                    "runbook_version_id": quarantine.runbook_version_id,
                    "reason": quarantine.quarantine_reason,
                    "failure_count": quarantine.failure_count,
                    "quarantined_at": quarantine.quarantined_at.isoformat() if quarantine.quarantined_at else None,
                    "failure_pattern": quarantine.failure_pattern
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            raise self.handle_error(e, "Failed to get pending reviews")
    
    def get_failure_patterns(
        self,
        runbook_id: int,
        runbook_version_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get failure pattern analysis for a runbook
        
        Args:
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            
        Returns:
            Failure pattern analysis dictionary
        """
        try:
            # Verify runbook belongs to tenant
            runbook = self.db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == self.tenant_id
            ).first()
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            analysis = self.quarantine_service.analyze_failure_pattern(
                db=self.db,
                runbook_id=runbook_id,
                runbook_version_id=runbook_version_id,
                tenant_id=self.tenant_id
            )
            
            return analysis
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting failure patterns for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get failure patterns")
