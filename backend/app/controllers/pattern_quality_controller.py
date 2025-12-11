"""
PatternQualityController
Handles HTTP requests for pattern quality operations
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.decision.pattern_quality_service import PatternQualityService
from app.repositories.execution_pattern_repository import ExecutionPatternRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class PatternQualityController(BaseController):
    """Controller for pattern quality operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.quality_service = PatternQualityService()
        self.pattern_repo = ExecutionPatternRepository(db)
    
    async def deprecate_pattern(
        self,
        pattern_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deprecate a pattern
        
        Args:
            pattern_id: Pattern ID
            reason: Optional deprecation reason
            
        Returns:
            Deprecation result
        """
        try:
            pattern = await self.quality_service.deprecate_pattern(
                db=self.db,
                pattern_id=pattern_id,
                tenant_id=self.tenant_id,
                reason=reason
            )
            
            if not pattern:
                raise self.not_found("Pattern", pattern_id)
            
            return {
                "pattern_id": pattern.id,
                "is_deprecated": pattern.is_deprecated,
                "message": "Pattern deprecated successfully"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deprecating pattern {pattern_id}: {e}")
            raise self.handle_error(e, "Failed to deprecate pattern")
    
    async def restore_pattern(
        self,
        pattern_id: int
    ) -> Dict[str, Any]:
        """
        Restore a deprecated pattern
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Restoration result
        """
        try:
            pattern = await self.quality_service.restore_pattern(
                db=self.db,
                pattern_id=pattern_id,
                tenant_id=self.tenant_id
            )
            
            if not pattern:
                raise self.not_found("Pattern", pattern_id)
            
            return {
                "pattern_id": pattern.id,
                "is_deprecated": pattern.is_deprecated,
                "message": "Pattern restored successfully"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error restoring pattern {pattern_id}: {e}")
            raise self.handle_error(e, "Failed to restore pattern")
    
    async def get_quality_report(
        self,
        min_quality_score: Optional[float] = None,
        include_deprecated: bool = False
    ) -> Dict[str, Any]:
        """
        Get quality report for all patterns
        
        Args:
            min_quality_score: Minimum quality score filter
            include_deprecated: Include deprecated patterns
            
        Returns:
            Quality report
        """
        try:
            report = await self.quality_service.get_quality_report(
                db=self.db,
                tenant_id=self.tenant_id,
                min_quality_score=min_quality_score,
                include_deprecated=include_deprecated
            )
            return report
        
        except Exception as e:
            logger.error(f"Error getting quality report: {e}")
            raise self.handle_error(e, "Failed to get quality report")
    
    async def update_quality_score(
        self,
        pattern_id: int
    ) -> Dict[str, Any]:
        """
        Update quality score for a pattern
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Updated pattern info
        """
        try:
            pattern = await self.quality_service.update_pattern_quality_score(
                db=self.db,
                pattern_id=pattern_id
            )
            
            if not pattern:
                raise self.not_found("Pattern", pattern_id)
            
            return {
                "pattern_id": pattern.id,
                "quality_score": float(pattern.quality_score) if pattern.quality_score else None,
                "success_rate": float(pattern.success_rate),
                "usage_count": pattern.usage_count,
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating quality score for pattern {pattern_id}: {e}")
            raise self.handle_error(e, "Failed to update quality score")
    
    async def prune_low_quality_patterns(
        self,
        max_quality_score: float = 20.0,
        min_age_days: int = 90
    ) -> Dict[str, Any]:
        """
        Automatically deprecate old, low-quality patterns
        
        Args:
            max_quality_score: Maximum quality score to prune
            min_age_days: Minimum age in days before pruning
            
        Returns:
            Pruning result
        """
        try:
            pruned_count = await self.quality_service.prune_low_quality_patterns(
                db=self.db,
                tenant_id=self.tenant_id,
                max_quality_score=max_quality_score,
                min_age_days=min_age_days
            )
            
            return {
                "pruned_count": pruned_count,
                "message": f"Deprecated {pruned_count} low-quality patterns"
            }
        
        except Exception as e:
            logger.error(f"Error pruning patterns: {e}")
            raise self.handle_error(e, "Failed to prune patterns")








