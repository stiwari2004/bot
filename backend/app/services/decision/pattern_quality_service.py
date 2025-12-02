"""
PatternQualityService
Manages pattern lifecycle, deprecation, and quality control
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.models.execution_pattern import ExecutionPattern
from app.models.pattern_feedback import PatternFeedback
from app.repositories.execution_pattern_repository import ExecutionPatternRepository

logger = get_logger(__name__)


class PatternQualityService:
    """Service for managing pattern quality and lifecycle"""
    
    def __init__(self):
        pass
    
    async def calculate_quality_score(
        self,
        db: Session,
        pattern: ExecutionPattern
    ) -> float:
        """
        Calculate quality score for a pattern (0-100)
        
        Factors:
        - Success rate (40% weight)
        - Usage count (20% weight)
        - Recency (20% weight)
        - Feedback score (20% weight)
        
        Args:
            db: Database session
            pattern: ExecutionPattern object
            
        Returns:
            Quality score between 0.0 and 100.0
        """
        score = 0.0
        
        # 1. Success rate (40% weight)
        success_rate = float(pattern.success_rate or 0.0)
        score += success_rate * 0.4
        
        # 2. Usage count (20% weight) - more usage = more reliable
        usage_count = pattern.usage_count or 0
        usage_score = min(100.0, (usage_count / 10.0) * 100.0)  # Normalize to 100
        score += usage_score * 0.2
        
        # 3. Recency (20% weight) - recent patterns are more relevant
        if pattern.last_used_at:
            days_since_use = (datetime.now(timezone.utc) - pattern.last_used_at).days
            recency_score = max(0.0, 100.0 - (days_since_use / 90.0) * 100.0)  # Decay over 90 days
        else:
            days_since_creation = (datetime.now(timezone.utc) - pattern.created_at).days
            recency_score = max(0.0, 100.0 - (days_since_creation / 90.0) * 100.0)
        score += recency_score * 0.2
        
        # 4. Feedback score (20% weight)
        feedback_list = db.query(PatternFeedback).filter(
            PatternFeedback.pattern_id == pattern.id
        ).all()
        
        if feedback_list:
            thumbs_up = sum(1 for f in feedback_list if f.feedback_type == "thumbs_up")
            thumbs_down = sum(1 for f in feedback_list if f.feedback_type == "thumbs_down")
            total_feedback = len(feedback_list)
            
            if total_feedback > 0:
                feedback_score = ((thumbs_up - thumbs_down) / total_feedback) * 50.0 + 50.0  # Scale to 0-100
                feedback_score = max(0.0, min(100.0, feedback_score))
            else:
                feedback_score = 50.0  # Neutral if no feedback
        else:
            feedback_score = 50.0  # Neutral if no feedback
        
        score += feedback_score * 0.2
        
        return min(100.0, max(0.0, score))
    
    async def update_pattern_quality_score(
        self,
        db: Session,
        pattern_id: int
    ) -> Optional[ExecutionPattern]:
        """
        Update quality score for a pattern
        
        Args:
            db: Database session
            pattern_id: Pattern ID
            
        Returns:
            Updated ExecutionPattern or None if not found
        """
        pattern = db.query(ExecutionPattern).filter(
            ExecutionPattern.id == pattern_id
        ).first()
        
        if not pattern:
            return None
        
        quality_score = await self.calculate_quality_score(db, pattern)
        pattern.quality_score = quality_score
        
        db.add(pattern)
        db.commit()
        db.refresh(pattern)
        
        logger.info(f"Updated quality score for pattern {pattern_id}: {quality_score:.2f}")
        return pattern
    
    async def deprecate_pattern(
        self,
        db: Session,
        pattern_id: int,
        tenant_id: int,
        reason: Optional[str] = None
    ) -> Optional[ExecutionPattern]:
        """
        Deprecate a pattern
        
        Args:
            db: Database session
            pattern_id: Pattern ID
            tenant_id: Tenant ID
            reason: Optional deprecation reason
            
        Returns:
            Updated ExecutionPattern or None if not found
        """
        repo = ExecutionPatternRepository(db)
        pattern = repo.get_by_tenant(tenant_id, limit=1000)
        pattern = next((p for p in pattern if p.id == pattern_id), None)
        
        if not pattern:
            return None
        
        pattern.is_deprecated = 'true'
        pattern.last_reviewed_at = datetime.now(timezone.utc)
        
        # Store reason in context if provided
        if reason and pattern.context:
            if not isinstance(pattern.context, dict):
                pattern.context = {}
            pattern.context['deprecation_reason'] = reason
        
        db.add(pattern)
        db.commit()
        db.refresh(pattern)
        
        logger.info(f"Deprecated pattern {pattern_id}: {reason}")
        return pattern
    
    async def restore_pattern(
        self,
        db: Session,
        pattern_id: int,
        tenant_id: int
    ) -> Optional[ExecutionPattern]:
        """
        Restore a deprecated pattern
        
        Args:
            db: Database session
            pattern_id: Pattern ID
            tenant_id: Tenant ID
            
        Returns:
            Updated ExecutionPattern or None if not found
        """
        repo = ExecutionPatternRepository(db)
        pattern = repo.get_by_tenant(tenant_id, limit=1000)
        pattern = next((p for p in pattern if p.id == pattern_id), None)
        
        if not pattern:
            return None
        
        pattern.is_deprecated = 'false'
        pattern.last_reviewed_at = datetime.now(timezone.utc)
        
        db.add(pattern)
        db.commit()
        db.refresh(pattern)
        
        logger.info(f"Restored pattern {pattern_id}")
        return pattern
    
    async def get_quality_report(
        self,
        db: Session,
        tenant_id: int,
        min_quality_score: Optional[float] = None,
        include_deprecated: bool = False
    ) -> Dict[str, Any]:
        """
        Get quality report for all patterns
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            min_quality_score: Minimum quality score filter
            include_deprecated: Include deprecated patterns
            
        Returns:
            Quality report dictionary
        """
        repo = ExecutionPatternRepository(db)
        
        # Get all patterns
        patterns = repo.get_by_tenant(
            tenant_id,
            is_deprecated=None if include_deprecated else 'false',
            min_quality_score=min_quality_score
        )
        
        # Calculate quality scores for patterns that don't have them
        for pattern in patterns:
            if pattern.quality_score is None:
                await self.update_pattern_quality_score(db, pattern.id)
                db.refresh(pattern)
        
        # Categorize patterns
        high_quality = [p for p in patterns if p.quality_score and p.quality_score >= 70.0]
        medium_quality = [p for p in patterns if p.quality_score and 40.0 <= p.quality_score < 70.0]
        low_quality = [p for p in patterns if p.quality_score and p.quality_score < 40.0]
        deprecated = [p for p in patterns if p.is_deprecated == 'true']
        
        return {
            "total_patterns": len(patterns),
            "high_quality_count": len(high_quality),
            "medium_quality_count": len(medium_quality),
            "low_quality_count": len(low_quality),
            "deprecated_count": len(deprecated),
            "avg_quality_score": sum(
                p.quality_score for p in patterns if p.quality_score
            ) / len([p for p in patterns if p.quality_score]) if any(p.quality_score for p in patterns) else 0.0,
            "high_quality_patterns": [
                {
                    "pattern_id": p.id,
                    "pattern_type": p.pattern_type,
                    "quality_score": float(p.quality_score) if p.quality_score else None,
                    "success_rate": float(p.success_rate),
                    "usage_count": p.usage_count,
                }
                for p in high_quality[:10]
            ],
            "low_quality_patterns": [
                {
                    "pattern_id": p.id,
                    "pattern_type": p.pattern_type,
                    "quality_score": float(p.quality_score) if p.quality_score else None,
                    "success_rate": float(p.success_rate),
                    "usage_count": p.usage_count,
                }
                for p in low_quality[:10]
            ],
            "deprecated_patterns": [
                {
                    "pattern_id": p.id,
                    "pattern_type": p.pattern_type,
                    "last_reviewed_at": p.last_reviewed_at.isoformat() if p.last_reviewed_at else None,
                }
                for p in deprecated[:10]
            ],
        }
    
    async def prune_low_quality_patterns(
        self,
        db: Session,
        tenant_id: int,
        max_quality_score: float = 20.0,
        min_age_days: int = 90
    ) -> int:
        """
        Automatically deprecate old, low-quality patterns
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            max_quality_score: Maximum quality score to prune
            min_age_days: Minimum age in days before pruning
            
        Returns:
            Number of patterns pruned
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=min_age_days)
        
        patterns = db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == tenant_id,
            ExecutionPattern.is_deprecated == 'false',
            ExecutionPattern.created_at <= cutoff_date,
            ExecutionPattern.quality_score < max_quality_score
        ).all()
        
        pruned_count = 0
        for pattern in patterns:
            # Update quality score first
            await self.update_pattern_quality_score(db, pattern.id)
            db.refresh(pattern)
            
            # If still low quality, deprecate
            if pattern.quality_score and pattern.quality_score < max_quality_score:
                pattern.is_deprecated = 'true'
                pattern.last_reviewed_at = datetime.now(timezone.utc)
                db.add(pattern)
                pruned_count += 1
        
        if pruned_count > 0:
            db.commit()
            logger.info(f"Pruned {pruned_count} low-quality patterns for tenant {tenant_id}")
        
        return pruned_count

