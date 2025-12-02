"""
Pattern Matching Service
Matches current issues with historical execution patterns
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from datetime import datetime, timezone

from app.models.execution_pattern import ExecutionPattern
from app.models.ticket import Ticket
from app.core.logging import get_logger

logger = get_logger(__name__)


class PatternMatchingService:
    """Service for matching issues with historical patterns"""
    
    def __init__(self):
        pass
    
    async def find_matching_patterns(
        self,
        issue_description: str,
        context: Dict[str, Any],
        db: Session,
        pattern_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[ExecutionPattern, float]]:
        """
        Find patterns matching the issue description and context
        
        Args:
            issue_description: Issue description text
            context: Context dictionary (environment, service, severity, etc.)
            db: Database session
            pattern_type: Optional pattern type filter ('execution', 'resolution', 'rollback')
            limit: Maximum number of patterns to return
            
        Returns:
            List of tuples (pattern, match_score) sorted by score descending
        """
        # Build base query
        query = db.query(ExecutionPattern)
        
        # Filter by pattern type if specified
        if pattern_type:
            query = query.filter(ExecutionPattern.pattern_type == pattern_type)
        
        # Filter by context if available
        if context.get("tenant_id"):
            query = query.filter(ExecutionPattern.tenant_id == context["tenant_id"])
        
        # Filter by environment if available
        if context.get("environment"):
            query = query.filter(
                ExecutionPattern.context['environment'].astext == context["environment"]
            )
        
        # Filter by service if available
        if context.get("service"):
            query = query.filter(
                ExecutionPattern.context['service'].astext == context["service"]
            )
        
        # Get all matching patterns
        patterns = query.all()
        
        # Score each pattern
        scored_patterns = []
        for pattern in patterns:
            score = await self.score_pattern_match(pattern, issue_description, context)
            scored_patterns.append((pattern, score))
        
        # Sort by score descending
        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return scored_patterns[:limit]
    
    async def score_pattern_match(
        self,
        pattern: ExecutionPattern,
        issue_description: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Score how well a pattern matches the issue
        
        Args:
            pattern: ExecutionPattern object
            issue_description: Issue description text
            context: Context dictionary
            
        Returns:
            Match score between 0.0 and 1.0
        """
        score = 0.0
        max_score = 0.0
        
        # 1. Issue signature similarity (40% weight)
        if pattern.issue_signature:
            signature_similarity = self._calculate_text_similarity(
                pattern.issue_signature.lower(),
                issue_description.lower()
            )
            score += signature_similarity * 0.4
        max_score += 0.4
        
        # 2. Context matching (30% weight)
        context_match = self._match_context(pattern.context, context)
        score += context_match * 0.3
        max_score += 0.3
        
        # 3. Success rate (20% weight)
        if pattern.success_rate:
            # Higher success rate = better match
            success_score = pattern.success_rate / 100.0
            score += success_score * 0.2
        max_score += 0.2
        
        # 4. Usage count (10% weight) - more usage = more reliable
        if pattern.usage_count:
            # Normalize usage count (log scale)
            usage_score = min(1.0, (pattern.usage_count / 10.0) * 0.1)
            score += usage_score * 0.1
        max_score += 0.1
        
        # Normalize score
        if max_score > 0:
            score = score / max_score
        
        return min(1.0, max(0.0, score))
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity using word overlap
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _match_context(
        self,
        pattern_context: Optional[Dict[str, Any]],
        issue_context: Dict[str, Any]
    ) -> float:
        """
        Match context fields between pattern and issue
        
        Args:
            pattern_context: Pattern context dictionary
            issue_context: Issue context dictionary
            
        Returns:
            Context match score between 0.0 and 1.0
        """
        if not pattern_context:
            return 0.5  # Neutral score if no pattern context
        
        match_count = 0
        total_fields = 0
        
        # Match environment
        if "environment" in issue_context:
            total_fields += 1
            if pattern_context.get("environment") == issue_context["environment"]:
                match_count += 1
        
        # Match service
        if "service" in issue_context:
            total_fields += 1
            if pattern_context.get("service") == issue_context["service"]:
                match_count += 1
        
        # Match severity
        if "severity" in issue_context:
            total_fields += 1
            if pattern_context.get("severity") == issue_context["severity"]:
                match_count += 1
        
        if total_fields == 0:
            return 0.5  # Neutral score if no fields to match
        
        return match_count / total_fields
    
    async def get_best_pattern(
        self,
        patterns: List[Tuple[ExecutionPattern, float]],
        min_score: float = 0.5
    ) -> Optional[Tuple[ExecutionPattern, float]]:
        """
        Get the best matching pattern from a list
        
        Args:
            patterns: List of (pattern, score) tuples
            min_score: Minimum score threshold
            
        Returns:
            Best pattern tuple or None if no pattern meets threshold
        """
        if not patterns:
            return None
        
        best_pattern = patterns[0]
        if best_pattern[1] >= min_score:
            return best_pattern
        
        return None
    
    async def find_patterns_by_runbook(
        self,
        runbook_id: int,
        db: Session,
        limit: int = 10
    ) -> List[ExecutionPattern]:
        """
        Find patterns associated with a specific runbook
        
        Args:
            runbook_id: Runbook ID
            db: Database session
            limit: Maximum number of patterns to return
            
        Returns:
            List of execution patterns
        """
        patterns = db.query(ExecutionPattern).filter(
            ExecutionPattern.runbook_id == runbook_id
        ).order_by(
            ExecutionPattern.success_rate.desc(),
            ExecutionPattern.usage_count.desc()
        ).limit(limit).all()
        
        return patterns

