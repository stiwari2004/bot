"""
Recommendation Engine
Generates actionable recommendations based on patterns and context
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import math

from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.execution_pattern import ExecutionPattern
from app.services.decision.context_correlation_service import ContextCorrelationService
from app.services.decision.pattern_matching_service import PatternMatchingService
from app.services.decision.confidence_scoring_service import ConfidenceScoringService
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
        self.confidence_scoring_service = ConfidenceScoringService()
    
    def recommend_runbook(
        self,
        ticket: Ticket,
        db: Session,
        min_confidence: float = 0.5,
        store_breakdown: bool = True
    ) -> Recommendation:
        """
        Generate runbook recommendation for a ticket
        
        Args:
            ticket: Ticket object
            db: Database session
            min_confidence: Minimum confidence threshold
            store_breakdown: Whether to store detailed confidence breakdown
            
        Returns:
            Recommendation object
        """
        # Correlate context
        context_data = self.context_correlation_service.correlate_ticket_context(
            ticket.id, db
        )
        
        # Extract context for pattern matching
        context = {
            "tenant_id": ticket.tenant_id,
            "environment": ticket.environment,
            "service": ticket.service,
            "severity": ticket.severity,
        }
        
        # Find matching patterns: use description-first so matching is driven by full alarm/issue text
        from app.services.ticket.runbook_matching_service import _runbook_search_query
        issue_description = _runbook_search_query(ticket.description, ticket.title)
        matching_patterns = self.pattern_matching_service.find_matching_patterns(
            issue_description,
            context,
            db,
            pattern_type="execution",
            limit=5
        )
        
        # Get best pattern
        best_pattern_tuple = self.pattern_matching_service.get_best_pattern(
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
            confidence = self.calculate_confidence(
                pattern, match_score, context_data["signals"]
            )
            
            # Store detailed confidence breakdown if requested
            confidence_breakdown_id = None
            detailed_explanation = {}
            if store_breakdown and runbook:
                try:
                    # Build detailed explanation
                    detailed_explanation = self._build_detailed_explanation(
                        pattern, match_score, confidence, context_data, runbook
                    )
                    
                    # Store confidence breakdown (if we have runbook YAML/metadata)
                    # Note: This requires runbook body_md or meta_data to be available
                    # Note: This is async but called from sync context - will be stored in background
                    # For now, we'll skip async storage to avoid blocking
                    pass  # Confidence breakdown can be calculated on-demand via API
                except Exception as e:
                    logger.warning(f"Failed to store confidence breakdown: {e}")
            
            # Determine actions
            should_auto_execute = self.should_auto_execute(confidence, pattern, context_data)
            should_escalate = self.should_escalate(confidence, pattern, context_data)
            
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
                context_signals=context_data["signals"],
                confidence_breakdown_id=confidence_breakdown_id,
                detailed_explanation=detailed_explanation
            )
        else:
            # No good pattern found: explicit fallback so UI can offer "Generate runbook"
            return Recommendation(
                confidence=0.0,
                reasoning=(
                    "No matching runbook found for this ticket. "
                    "Consider generating a new runbook or reviewing similar runbooks manually."
                ),
                should_escalate=True,
                context_signals=context_data["signals"]
            )
    
    def calculate_confidence(
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
            # Log normalization using log1p for better numerical stability
            # Using max_expected_usage = 100 for reasonable scaling
            # This gives: 1 use = 0.15, 10 uses = 0.50, 50 uses = 0.85, 100+ uses = 1.0
            max_expected_usage = 100
            usage_score = min(1.0, math.log1p(pattern.usage_count) / math.log1p(max_expected_usage))
            confidence += usage_score * 0.1
        
        # 4. Context match (10% weight)
        context_match = 1.0  # Assume good context match if we got here
        if context_signals.get("recent_execution_success_rate") is not None:
            context_match = context_signals["recent_execution_success_rate"]
        confidence += context_match * 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def should_auto_execute(
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
    
    def should_escalate(
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
            if pattern.issue_signature:
                parts.append(f"Issue signature: {pattern.issue_signature[:50]}...")
        
        parts.append(f"Overall confidence: {confidence:.2%}")
        
        signals = context_data.get("signals", {})
        if signals.get("alert_count", 0) > 0:
            parts.append(f"Correlated with {signals['alert_count']} alerts")
        
        if signals.get("execution_count", 0) > 0:
            parts.append(f"Found {signals['execution_count']} related executions")
        
        if signals.get("recent_execution_success_rate") is not None:
            success_rate = signals["recent_execution_success_rate"]
            parts.append(f"Recent execution success rate: {success_rate:.1%}")
        
        return ". ".join(parts) + "."
    
    def _build_detailed_explanation(
        self,
        pattern: ExecutionPattern,
        match_score: float,
        confidence: float,
        context_data: Dict[str, Any],
        runbook: Runbook
    ) -> Dict[str, Any]:
        """Build detailed explanation with citations, pattern details, and reasoning steps"""
        explanation = {
            "pattern_match": {
                "pattern_id": pattern.id,
                "match_score": match_score,
                "success_rate": pattern.success_rate,
                "usage_count": pattern.usage_count,
                "issue_signature": pattern.issue_signature,
            },
            "confidence_components": {
                "pattern_match_weight": 0.5,
                "pattern_success_weight": 0.3,
                "pattern_usage_weight": 0.1,
                "context_match_weight": 0.1,
            },
            "context_signals": context_data.get("signals", {}),
            "runbook_info": {
                "runbook_id": runbook.id,
                "title": runbook.title,
                "confidence": float(runbook.confidence) if runbook.confidence else None,
            },
            "reasoning_steps": []
        }
        
        # Add reasoning steps
        if pattern:
            explanation["reasoning_steps"].append({
                "step": 1,
                "description": f"Pattern match found with score {match_score:.2f}",
                "evidence": f"Pattern ID {pattern.id} matches the issue description"
            })
            
            if pattern.success_rate:
                explanation["reasoning_steps"].append({
                    "step": 2,
                    "description": f"Pattern has {pattern.success_rate:.1f}% success rate",
                    "evidence": f"Based on {pattern.usage_count} previous uses"
                })
        
        # Add citation information if available
        if runbook.meta_data:
            try:
                import json
                meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                if "citations" in meta:
                    explanation["citations"] = {
                        "count": len(meta["citations"]),
                        "sources": meta["citations"][:5]  # Top 5 citations
                    }
            except Exception:
                pass
        
        return explanation
    
    async def _store_confidence_breakdown(
        self,
        db: Session,
        tenant_id: int,
        runbook_id: int,
        ticket_id: int,
        pattern: ExecutionPattern,
        match_score: float,
        context_data: Dict[str, Any]
    ) -> Optional[Any]:
        """Store detailed confidence breakdown using ConfidenceScoringService"""
        try:
            # Get runbook to extract YAML/metadata
            runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if not runbook:
                return None
            
            # Extract YAML from body_md if available
            runbook_yaml = None
            if runbook.body_md:
                # Try to extract YAML block from markdown
                import re
                yaml_match = re.search(r'```yaml\n(.*?)\n```', runbook.body_md, re.DOTALL)
                if yaml_match:
                    runbook_yaml = yaml_match.group(1)
            
            # Build context text from signals
            context_text = f"Pattern match: {match_score:.2f}, Success rate: {pattern.success_rate}%"
            
            # Create search results simulation (since we don't have actual search results here)
            # In a real scenario, this would come from the search service
            from app.schemas.search import SearchResult
            search_results = [
                SearchResult(
                    id=pattern.id,
                    score=match_score,
                    content=f"Pattern: {pattern.issue_signature}",
                    metadata={"pattern_id": pattern.id}
                )
            ]
            
            # Calculate and store breakdown
            breakdown = await self.confidence_scoring_service.calculate_confidence_breakdown(
                db=db,
                tenant_id=tenant_id,
                runbook_id=runbook_id,
                ticket_id=ticket_id,
                search_results=search_results,
                runbook_yaml=runbook_yaml,
                llm_output=runbook.body_md[:1000] if runbook.body_md else None,
                context_text=context_text
            )
            
            return breakdown
        except Exception as e:
            logger.error(f"Error storing confidence breakdown: {e}")
            return None
    
    async def generate_explanation(
        self,
        ticket_id: int,
        recommendation_id: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """
        Generate detailed explanation for a recommendation
        
        Args:
            ticket_id: Ticket ID
            recommendation_id: Optional recommendation ID
            db: Database session
            
        Returns:
            Detailed explanation dictionary
        """
        # Get ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Get confidence breakdown if available
        breakdown = await self.confidence_scoring_service.get_confidence_breakdown(
            db=db,
            ticket_id=ticket_id,
            recommendation_id=recommendation_id,
            tenant_id=ticket.tenant_id
        )
        
        explanation = {
            "ticket_id": ticket_id,
            "recommendation_id": recommendation_id,
            "has_breakdown": breakdown is not None,
        }
        
        if breakdown:
            explanation["confidence_breakdown"] = {
                "overall_confidence": float(breakdown.overall_confidence),
                "components": {
                    "search_quality": {
                        "score": float(breakdown.search_quality_score),
                        "weight": 0.40,
                        "details": breakdown.search_quality_details,
                    },
                    "llm_consistency": {
                        "score": float(breakdown.llm_consistency_score) if breakdown.llm_consistency_score else None,
                        "weight": 0.30,
                        "details": breakdown.llm_consistency_details,
                    },
                    "yaml_quality": {
                        "score": float(breakdown.yaml_quality_score) if breakdown.yaml_quality_score else None,
                        "weight": 0.20,
                        "details": breakdown.yaml_quality_details,
                    },
                    "citation_coverage": {
                        "score": float(breakdown.citation_coverage_score) if breakdown.citation_coverage_score else None,
                        "weight": 0.10,
                        "details": breakdown.citation_coverage_details,
                    },
                },
                "warnings": breakdown.warnings or [],
                "flags": breakdown.flags or [],
            }
        
        return explanation
