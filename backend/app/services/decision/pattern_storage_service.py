"""
PatternStorageService
---------------------

Responsible for persisting and updating `ExecutionPattern` records.

This service is intentionally simple for Phase 1:
- Store patterns after successful executions / resolutions / rollbacks
- Retrieve patterns by issue signature, type, and context
- Maintain basic success metrics (usage_count, success_rate)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.logging import get_logger
from app.models.execution_pattern import ExecutionPattern

logger = get_logger(__name__)


class PatternStorageService:
    """CRUD + metrics for `ExecutionPattern`."""

    def create_pattern(
        self,
        db: Session,
        *,
        tenant_id: int,
        pattern_type: str,
        runbook_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        session_id: Optional[int] = None,
        issue_signature: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        pattern_data: Optional[Dict[str, Any]] = None,
        initial_success: Optional[bool] = True,
    ) -> ExecutionPattern:
        """
        Create a new execution pattern.

        For Phase 1 we treat the first creation as a successful use by default.
        """
        if not pattern_data:
            pattern_data = {}

        pattern = ExecutionPattern(
            tenant_id=tenant_id,
            pattern_type=pattern_type,
            runbook_id=runbook_id,
            ticket_id=ticket_id,
            session_id=session_id,
            issue_signature=(issue_signature or "")[:10_000],
            context=context or {},
            pattern_data=pattern_data,
            usage_count=1 if initial_success else 0,
            success_rate=100.0 if initial_success else 0.0,
            last_used_at=datetime.now(timezone.utc) if initial_success else None,
        )

        db.add(pattern)
        db.commit()
        db.refresh(pattern)

        logger.info(
            "Created execution pattern id=%s type=%s runbook_id=%s ticket_id=%s",
            pattern.id,
            pattern.pattern_type,
            pattern.runbook_id,
            pattern.ticket_id,
        )
        return pattern

    def record_pattern_use(
        self,
        db: Session,
        *,
        pattern: ExecutionPattern,
        was_successful: bool,
    ) -> ExecutionPattern:
        """
        Update usage_count and success_rate for an existing pattern.

        success_rate is stored as a simple running ratio:
            success_rate = (prev_successes + (1 if success else 0)) / usage_count * 100
        """
        prev_usage = pattern.usage_count or 0
        prev_rate = float(pattern.success_rate or 0.0)

        prev_successes = int(round((prev_rate / 100.0) * prev_usage))

        new_usage = prev_usage + 1
        new_successes = prev_successes + (1 if was_successful else 0)
        new_rate = (new_successes / new_usage) * 100.0 if new_usage > 0 else 0.0

        pattern.usage_count = new_usage
        pattern.success_rate = new_rate
        pattern.last_used_at = datetime.now(timezone.utc)

        db.add(pattern)
        db.commit()
        db.refresh(pattern)

        logger.debug(
            "Updated pattern id=%s usage_count=%s success_rate=%.2f (was_successful=%s)",
            pattern.id,
            pattern.usage_count,
            float(pattern.success_rate),
            was_successful,
        )
        return pattern

    def get_pattern_by_id(self, db: Session, pattern_id: int) -> Optional[ExecutionPattern]:
        """Fetch a single pattern by id."""
        return (
            db.query(ExecutionPattern)
            .filter(ExecutionPattern.id == pattern_id)
            .first()
        )

    def list_patterns(
        self,
        db: Session,
        *,
        tenant_id: int,
        pattern_type: Optional[str] = None,
        limit: int = 50,
        min_success_rate: Optional[float] = None,
    ) -> List[ExecutionPattern]:
        """List patterns for a tenant with simple filters."""
        q = db.query(ExecutionPattern).filter(ExecutionPattern.tenant_id == tenant_id)

        if pattern_type:
            q = q.filter(ExecutionPattern.pattern_type == pattern_type)

        if min_success_rate is not None:
            q = q.filter(ExecutionPattern.success_rate >= min_success_rate)

        return (
            q.order_by(ExecutionPattern.success_rate.desc(), ExecutionPattern.usage_count.desc())
            .limit(limit)
            .all()
        )

    def find_candidate_patterns(
        self,
        db: Session,
        *,
        tenant_id: int,
        issue_signature: Optional[str] = None,
        pattern_type: Optional[str] = None,
        context_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[ExecutionPattern]:
        """
        Find candidate patterns for a given issue + context.

        Phase 1 uses very lightweight filters:
        - same tenant
        - optional type filter
        - simple LIKE match on issue_signature
        - optional equality matches on a few context keys
        """
        q = db.query(ExecutionPattern).filter(ExecutionPattern.tenant_id == tenant_id)

        if pattern_type:
            q = q.filter(ExecutionPattern.pattern_type == pattern_type)

        if issue_signature:
            # Use ILIKE for a cheap text match; pg GIN index helps here
            sig = f"%{issue_signature[:256]}%"
            q = q.filter(ExecutionPattern.issue_signature.ilike(sig))

        if context_filters:
            for key, value in context_filters.items():
                # JSONB containment: context @> {'key': 'value'}
                q = q.filter(ExecutionPattern.context.op("@>")({key: value}))

        return (
            q.order_by(ExecutionPattern.success_rate.desc(), ExecutionPattern.usage_count.desc())
            .limit(limit)
            .all()
        )









