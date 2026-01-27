"""
Quarantine Service for runbook quarantine management
Prevents automation storms by quarantining failing runbooks
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.runbook_quarantine import RunbookQuarantine
from app.models.execution_session import ExecutionSession
from app.models.execution_step import ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuarantineService:
    """Service for managing runbook quarantines"""
    
    # Configuration
    DEFAULT_FAILURE_THRESHOLD = 3  # Auto-quarantine after 3 consecutive failures
    DEFAULT_AUTO_RELEASE_HOURS = 24  # Auto-release after 24 hours
    
    def __init__(self, failure_threshold: int = None, auto_release_hours: int = None):
        self.failure_threshold = failure_threshold or self.DEFAULT_FAILURE_THRESHOLD
        self.auto_release_hours = auto_release_hours or self.DEFAULT_AUTO_RELEASE_HOURS
    
    def is_quarantined(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ) -> bool:
        """
        Check if a runbook (or version) is currently quarantined
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID (for version-aware quarantine)
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            True if quarantined, False otherwise
        """
        query = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id,
            RunbookQuarantine.review_status.in_(["pending_review", "reviewed"])
        )
        
        if runbook_version_id:
            query = query.filter(
                or_(
                    RunbookQuarantine.runbook_version_id == runbook_version_id,
                    RunbookQuarantine.runbook_version_id.is_(None)  # Global quarantine
                )
            )
        else:
            # Check for version-specific or global quarantine
            query = query.filter(
                RunbookQuarantine.runbook_version_id.is_(None)
            )
        
        if tenant_id:
            query = query.filter(RunbookQuarantine.tenant_id == tenant_id)
        
        quarantine = query.first()
        
        if quarantine:
            # Check if auto-release time has passed
            if quarantine.auto_release_after and datetime.now(timezone.utc) > quarantine.auto_release_after:
                # Auto-release
                quarantine.review_status = "auto_released"
                quarantine.reviewed_at = datetime.now(timezone.utc)
                db.commit()
                return False
        
        return quarantine is not None
    
    def track_failure(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int],
        session_id: int,
        error_details: Dict[str, Any],
        tenant_id: int
    ) -> Optional[RunbookQuarantine]:
        """
        Track a failure and auto-quarantine if threshold is reached
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            runbook_version_id: Runbook version ID
            session_id: Execution session ID that failed
            error_details: Error details dictionary with 'error', 'step_number', etc.
            tenant_id: Tenant ID
            
        Returns:
            RunbookQuarantine object if quarantined, None otherwise
        """
        # Get or create quarantine record
        quarantine = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id,
            RunbookQuarantine.runbook_version_id == runbook_version_id,
            RunbookQuarantine.tenant_id == tenant_id,
            RunbookQuarantine.review_status.in_(["pending_review", "reviewed"])
        ).first()
        
        if not quarantine:
            # Check if we should create a new quarantine
            # Count recent consecutive failures
            failure_count = self._count_consecutive_failures(
                db, runbook_id, runbook_version_id, tenant_id
            )
            
            if failure_count >= self.failure_threshold:
                # Auto-quarantine
                quarantine = self.quarantine_runbook(
                    db=db,
                    runbook_id=runbook_id,
                    runbook_version_id=runbook_version_id,
                    reason="auto_quarantine",
                    failure_data={
                        "failure_count": failure_count,
                        "last_error": error_details
                    },
                    tenant_id=tenant_id
                )
                logger.warning(
                    f"Auto-quarantined runbook {runbook_id} (version {runbook_version_id}) "
                    f"after {failure_count} consecutive failures"
                )
                return quarantine
        else:
            # Update existing quarantine
            quarantine.failure_count += 1
            
            # Update failure pattern
            if not quarantine.failure_pattern:
                quarantine.failure_pattern = {
                    "errors": [],
                    "error_types": [],
                    "same_error": True,
                    "varied_errors": False
                }
            
            error_type = error_details.get("error_type", "unknown")
            error_message = error_details.get("error", "")
            
            quarantine.failure_pattern["errors"].append({
                "error": error_message[:500],  # Truncate long errors
                "error_type": error_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "step_number": error_details.get("step_number"),
                "session_id": session_id
            })
            
            # Track error types
            if error_type not in quarantine.failure_pattern["error_types"]:
                quarantine.failure_pattern["error_types"].append(error_type)
            
            # Analyze if errors are same or varied
            errors = quarantine.failure_pattern["errors"]
            if len(errors) > 1:
                first_error_type = errors[0].get("error_type")
                all_same = all(e.get("error_type") == first_error_type for e in errors)
                quarantine.failure_pattern["same_error"] = all_same
                quarantine.failure_pattern["varied_errors"] = not all_same
            
            db.commit()
        
        return None
    
    def quarantine_runbook(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int],
        reason: str,
        failure_data: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[int] = None,
        quarantined_by: Optional[int] = None,
        auto_release_hours: Optional[int] = None
    ) -> RunbookQuarantine:
        """
        Manually quarantine a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            reason: Quarantine reason ('auto_quarantine', 'manual', 'review_flag')
            failure_data: Optional failure data dictionary
            tenant_id: Tenant ID
            quarantined_by: User ID who quarantined (for manual quarantine)
            auto_release_hours: Hours until auto-release (None = no auto-release)
            
        Returns:
            RunbookQuarantine object
        """
        # Check if already quarantined
        existing = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id,
            RunbookQuarantine.runbook_version_id == runbook_version_id,
            RunbookQuarantine.review_status.in_(["pending_review", "reviewed"])
        ).first()
        
        if existing:
            return existing
        
        # Get tenant_id from runbook if not provided
        if not tenant_id:
            from app.models.runbook import Runbook
            runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if runbook:
                tenant_id = runbook.tenant_id
            else:
                raise ValueError(f"Runbook {runbook_id} not found")
        
        # Calculate auto-release time
        auto_release_after = None
        if auto_release_hours:
            auto_release_after = datetime.now(timezone.utc) + timedelta(hours=auto_release_hours)
        elif reason == "auto_quarantine":
            # Default auto-release for auto-quarantines
            auto_release_after = datetime.now(timezone.utc) + timedelta(hours=self.auto_release_hours)
        
        quarantine = RunbookQuarantine(
            tenant_id=tenant_id,
            runbook_id=runbook_id,
            runbook_version_id=runbook_version_id,
            quarantine_reason=reason,
            failure_count=failure_data.get("failure_count", 0) if failure_data else 0,
            failure_pattern=failure_data.get("failure_pattern") if failure_data else None,
            quarantined_at=datetime.now(timezone.utc),
            quarantined_by=quarantined_by,
            review_status="pending_review",
            auto_release_after=auto_release_after
        )
        
        db.add(quarantine)
        db.commit()
        db.refresh(quarantine)
        
        logger.info(
            f"Quarantined runbook {runbook_id} (version {runbook_version_id}) "
            f"reason: {reason}"
        )
        
        return quarantine
    
    def release_quarantine(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int],
        reviewed_by: int,
        review_notes: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> RunbookQuarantine:
        """
        Release a runbook from quarantine
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            reviewed_by: User ID who reviewed
            review_notes: Optional review notes
            tenant_id: Optional tenant ID
            
        Returns:
            RunbookQuarantine object
        """
        query = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id,
            RunbookQuarantine.runbook_version_id == runbook_version_id,
            RunbookQuarantine.review_status.in_(["pending_review", "reviewed"])
        )
        
        if tenant_id:
            query = query.filter(RunbookQuarantine.tenant_id == tenant_id)
        
        quarantine = query.first()
        
        if not quarantine:
            raise ValueError(
                f"Runbook {runbook_id} (version {runbook_version_id}) is not quarantined"
            )
        
        quarantine.review_status = "reviewed"
        quarantine.reviewed_by = reviewed_by
        quarantine.reviewed_at = datetime.now(timezone.utc)
        quarantine.review_notes = review_notes
        
        db.commit()
        db.refresh(quarantine)
        
        logger.info(
            f"Released quarantine for runbook {runbook_id} (version {runbook_version_id}) "
            f"by user {reviewed_by}"
        )
        
        return quarantine
    
    def analyze_failure_pattern(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze failure patterns for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            runbook_version_id: Optional runbook version ID
            tenant_id: Optional tenant ID
            
        Returns:
            Failure pattern analysis dictionary
        """
        query = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.runbook_id == runbook_id
        )
        
        if runbook_version_id:
            query = query.filter(RunbookQuarantine.runbook_version_id == runbook_version_id)
        
        if tenant_id:
            query = query.filter(RunbookQuarantine.tenant_id == tenant_id)
        
        quarantine = query.order_by(RunbookQuarantine.quarantined_at.desc()).first()
        
        if not quarantine or not quarantine.failure_pattern:
            return {
                "has_pattern": False,
                "message": "No failure pattern data available"
            }
        
        pattern = quarantine.failure_pattern
        
        return {
            "has_pattern": True,
            "failure_count": quarantine.failure_count,
            "error_types": pattern.get("error_types", []),
            "same_error": pattern.get("same_error", False),
            "varied_errors": pattern.get("varied_errors", False),
            "recent_errors": pattern.get("errors", [])[-5:],  # Last 5 errors
            "quarantine_reason": quarantine.quarantine_reason,
            "quarantined_at": quarantine.quarantined_at.isoformat() if quarantine.quarantined_at else None
        }
    
    def _count_consecutive_failures(
        self,
        db: Session,
        runbook_id: int,
        runbook_version_id: Optional[int],
        tenant_id: int
    ) -> int:
        """Count consecutive failures for a runbook"""
        # Get recent execution sessions for this runbook
        query = db.query(ExecutionSession).filter(
            ExecutionSession.runbook_id == runbook_id,
            ExecutionSession.tenant_id == tenant_id
        ).order_by(ExecutionSession.created_at.desc())
        
        sessions = query.limit(10).all()  # Check last 10 sessions
        
        consecutive_failures = 0
        
        for session in sessions:
            if session.status in ["failed", "completed_with_errors", "abandoned"]:
                consecutive_failures += 1
            elif session.status == "completed":
                # Success - break the chain
                break
            # Skip pending/in_progress sessions
        
        return consecutive_failures
    
    def get_pending_reviews(
        self,
        db: Session,
        tenant_id: Optional[int] = None,
        limit: int = 50
    ) -> List[RunbookQuarantine]:
        """
        Get runbooks pending review
        
        Args:
            db: Database session
            tenant_id: Optional tenant ID
            limit: Maximum number of results
            
        Returns:
            List of RunbookQuarantine objects
        """
        query = db.query(RunbookQuarantine).filter(
            RunbookQuarantine.review_status == "pending_review"
        )
        
        if tenant_id:
            query = query.filter(RunbookQuarantine.tenant_id == tenant_id)
        
        return query.order_by(RunbookQuarantine.quarantined_at.desc()).limit(limit).all()
