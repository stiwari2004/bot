"""
Recommendation Engine
Generates actionable recommendations based on patterns and context
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.execution_pattern import ExecutionPattern
from app.services.decision.context_correlation_service import ContextCorrelationService
from app.services.decision.pattern_matching_service import PatternMatchingService
from app.core.logging import get_logger

logger = get_logger(__name__)


class Recommendation:
    """Recommendation data class"""
    def __init__(
        self,
        runbook_id: Optional[int] = None,
        runbook: Optional[Runbook] = None,
        confidence: float = 0.0,
        pattern: Optional[ExecutionPattern] = None,
        reasoning: str = "",
        should_auto_execute: bool = False,
        should_escalate: bool = False,
        context_signals: Optional[Dict[str, Any]] = None
    ):
        self.runbook_id = runbook_id
        self.runbook = runbook
        self.confidence = confidence
        self.pattern = pattern
        self.reasoning = reasoning
        self.should_auto_execute = should_auto_execute
        self.should_escalate = should_escalate
        self.context_signals = context_signals or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            "runbook_id": self.runbook_id,
            "runbook_title": self.runbook.title if self.runbook else None,
            "confidence": self.confidence,
            "pattern_id": self.pattern.id if self.pattern else None,
            "pattern_success_rate": self.pattern.success_rate if self.pattern else None,
            "reasoning": self.reasoning,
            "should_auto_execute": self.should_auto_execute,
            "should_escalate": self.should_escalate,
            "context_signals": self.context_signals
        }


class RecommendationEngine:
    """Service for generating recommendations based on patterns and context"""
    
    def __init__(self):
        self.context_correlation_service = ContextCorrelationService()
        self.pattern_matching_service = PatternMatchingService()
    
    async def recommend_runbook(
        self,
        ticket: Ticket,
        db: Session,
        min_confidence: float = 0.5
    ) -> Recommendation:
        """
        Generate runbook recommendation for a ticket
        
        Args:
            ticket: Ticket object
            db: Database session
            min_confidence: Minimum confidence threshold
            
        Returns:
            Recommendation object
        """
        # Correlate context
        context_data = await self.context_correlation_service.correlate_ticket_context(
            ticket.id, db
        )
        
        # Extract context for pattern matching
        context = {
            "tenant_id": ticket.tenant_id,
            "environment": ticket.environment,
            "service": ticket.service,
            "severity": ticket.severity,
        }
        
        # Find matching patterns
        issue_description = ticket.description or ticket.title
        matching_patterns = await self.pattern_matching_service.find_matching_patterns(
            issue_description,
            context,
            db,
            pattern_type="execution",
            limit=5
        )
        
        # Get best pattern
        best_pattern_tuple = await self.pattern_matching_service.get_best_pattern(
            matching_patterns,
            min_score=min_confidence
        )
        
        # Build recommendation
        if best_pattern_tuple:
            pattern, match_score = best_pattern_tuple
            
            # Get runbook
            runbook = None
            if pattern.runbook_id:
                runbook = db.query(Runbook).filter(Runbook.id == pattern.runbook_id).first()
            
            # Calculate confidence
            confidence = await self.calculate_confidence(
                pattern, match_score, context_data["signals"]
            )
            
            # Determine actions
            should_auto_execute = await self.should_auto_execute(confidence, pattern, context_data)
            should_escalate = await self.should_escalate(confidence, pattern, context_data)
            
            # Build reasoning
            reasoning = self._build_reasoning(pattern, match_score, confidence, context_data)
            
            return Recommendation(
                runbook_id=pattern.runbook_id,
                runbook=runbook,
                confidence=confidence,
                pattern=pattern,
                reasoning=reasoning,
                should_auto_execute=should_auto_execute,
                should_escalate=should_escalate,
                context_signals=context_data["signals"]
            )
        else:
            # No good pattern found
            return Recommendation(
                confidence=0.0,
                reasoning="No matching patterns found. Manual review recommended.",
                should_escalate=True,
                context_signals=context_data["signals"]
            )
    
    async def calculate_confidence(
        self,
        pattern: ExecutionPattern,
        match_score: float,
        context_signals: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score for a recommendation
        
        Args:
            pattern: ExecutionPattern object
            match_score: Pattern match score (0-1)
            context_signals: Context signals dictionary
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0
        
        # 1. Pattern match score (50% weight)
        confidence += match_score * 0.5
        
        # 2. Pattern success rate (30% weight)
        if pattern.success_rate:
            success_rate_normalized = pattern.success_rate / 100.0
            confidence += success_rate_normalized * 0.3
        
        # 3. Pattern usage count (10% weight) - log normalization for better scaling
        if pattern.usage_count:
            import math
            # Log normalization: log(1 + usage_count) / log(1 + max_expected_usage)
            # Using max_expected_usage = 100 for reasonable scaling
            # This gives: 1 use = 0.15, 10 uses = 0.50, 50 uses = 0.85, 100+ uses = 1.0
            max_expected_usage = 100
            usage_score = min(1.0, math.log(1 + pattern.usage_count) / math.log(1 + max_expected_usage))
            confidence += usage_score * 0.1
        
        # 4. Context match (10% weight)
        context_match = 1.0  # Assume good context match if we got here
        if context_signals.get("recent_execution_success_rate") is not None:
            context_match = context_signals["recent_execution_success_rate"]
        confidence += context_match * 0.1
        
        return min(1.0, max(0.0, confidence))
    
    async def should_auto_execute(
        self,
        confidence: float,
        pattern: Optional[ExecutionPattern],
        context_data: Dict[str, Any]
    ) -> bool:
        """
        Determine if runbook should be auto-executed
        
        Args:
            confidence: Confidence score
            pattern: ExecutionPattern object (optional)
            context_data: Context correlation data
            
        Returns:
            True if should auto-execute, False otherwise
        """
        # High confidence threshold
        if confidence < 0.85:
            return False
        
        # Check pattern success rate
        if pattern and pattern.success_rate < 90:
            return False
        
        # Check context signals
        signals = context_data.get("signals", {})
        
        # Don't auto-execute if there are active alerts
        if signals.get("has_active_alerts"):
            return False
        
        # Don't auto-execute critical issues without human review
        if signals.get("severity") == "critical":
            return False
        
        return True
    
    async def should_escalate(
        self,
        confidence: float,
        pattern: Optional[ExecutionPattern],
        context_data: Dict[str, Any]
    ) -> bool:
        """
        Determine if issue should be escalated
        
        Args:
            confidence: Confidence score
            pattern: ExecutionPattern object (optional)
            context_data: Context correlation data
            
        Returns:
            True if should escalate, False otherwise
        """
        # Low confidence = escalate
        if confidence < 0.3:
            return True
        
        # No pattern found = escalate
        if not pattern:
            return True
        
        # Check context signals
        signals = context_data.get("signals", {})
        
        # Escalate critical issues with low confidence
        if signals.get("severity") == "critical" and confidence < 0.6:
            return True
        
        # Escalate if multiple recent failures
        if signals.get("recent_execution_success_rate") is not None:
            if signals["recent_execution_success_rate"] < 0.3:
                return True
        
        return False
    
    def _build_reasoning(
        self,
        pattern: ExecutionPattern,
        match_score: float,
        confidence: float,
        context_data: Dict[str, Any]
    ) -> str:
        """Build human-readable reasoning for the recommendation"""
        parts = []
        
        if pattern:
            parts.append(f"Found matching pattern (match score: {match_score:.2f})")
            if pattern.success_rate:
                parts.append(f"Pattern success rate: {pattern.success_rate:.1f}%")
            if pattern.usage_count:
                parts.append(f"Pattern used {pattern.usage_count} times")
        
        parts.append(f"Overall confidence: {confidence:.2%}")
        
        signals = context_data.get("signals", {})
        if signals.get("alert_count", 0) > 0:
            parts.append(f"Correlated with {signals['alert_count']} alerts")
        
        if signals.get("execution_count", 0) > 0:
            parts.append(f"Found {signals['execution_count']} related executions")
        
        return ". ".join(parts) + "."








