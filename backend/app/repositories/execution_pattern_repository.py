"""
ExecutionPatternRepository
Data access layer for ExecutionPattern model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.execution_pattern import ExecutionPattern


class ExecutionPatternRepository(BaseRepository[ExecutionPattern]):
    """Repository for ExecutionPattern operations"""
    
    def __init__(self, db: Session):
        super().__init__(ExecutionPattern, db)
    
    def get_by_tenant(
        self,
        tenant_id: int,
        pattern_type: Optional[str] = None,
        is_deprecated: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 100
    ) -> List[ExecutionPattern]:
        """Get patterns for a tenant with filters"""
        query = self.db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == tenant_id
        )
        
        if pattern_type:
            query = query.filter(ExecutionPattern.pattern_type == pattern_type)
        
        if is_deprecated:
            query = query.filter(ExecutionPattern.is_deprecated == is_deprecated)
        
        if min_quality_score is not None:
            query = query.filter(ExecutionPattern.quality_score >= min_quality_score)
        
        return query.order_by(
            ExecutionPattern.quality_score.desc().nulls_last(),
            ExecutionPattern.success_rate.desc()
        ).limit(limit).all()
    
    def get_deprecated_patterns(
        self,
        tenant_id: int,
        limit: int = 50
    ) -> List[ExecutionPattern]:
        """Get deprecated patterns"""
        return self.db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == tenant_id,
            ExecutionPattern.is_deprecated == 'true'
        ).order_by(ExecutionPattern.last_reviewed_at.desc()).limit(limit).all()
    
    def get_low_quality_patterns(
        self,
        tenant_id: int,
        max_quality_score: float = 30.0,
        limit: int = 50
    ) -> List[ExecutionPattern]:
        """Get patterns with low quality scores"""
        return self.db.query(ExecutionPattern).filter(
            ExecutionPattern.tenant_id == tenant_id,
            ExecutionPattern.quality_score < max_quality_score,
            ExecutionPattern.is_deprecated == 'false'
        ).order_by(ExecutionPattern.quality_score.asc()).limit(limit).all()

