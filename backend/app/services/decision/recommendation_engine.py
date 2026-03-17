"""
Recommendation Engine
Generates actionable recommendations based on patterns and context
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.models.execution_pattern import ExecutionPattern
from app.services.decision.context_correlation_service import ContextCorrelationService
from app.services.decision.pattern_matching_service import PatternMatchingService
from app.services.decision.confidence_scoring_service import ConfidenceScoringService
from app.services.decision.recommendation_scoring_mixin import RecommendationScoringMixin
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
        context_signals: Optional[Dict[str, Any]] = None,
        confidence_breakdown_id: Optional[int] = None,
        detailed_explanation: Optional[Dict[str, Any]] = None,
    ):
        self.runbook_id = runbook_id
        self.runbook = runbook
        self.confidence = confidence
        self.pattern = pattern
        self.reasoning = reasoning
        self.should_auto_execute = should_auto_execute
        self.should_escalate = should_escalate
        self.context_signals = context_signals or {}
        self.confidence_breakdown_id = confidence_breakdown_id
        self.detailed_explanation = detailed_explanation or {}

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


class RecommendationEngine(RecommendationScoringMixin):
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
        """Generate runbook recommendation for a ticket."""
        context_data = self.context_correlation_service.correlate_ticket_context(ticket.id, db)

        context = {
            "tenant_id": ticket.tenant_id,
            "environment": ticket.environment,
            "service": ticket.service,
            "severity": ticket.severity,
        }

        from app.services.ticket.runbook_matching_service import (
            _runbook_search_query,
            _extract_cag_issue_and_phrases,
        )
        cag_summary, _ = _extract_cag_issue_and_phrases(ticket.description)
        issue_description = _runbook_search_query(
            ticket.description, ticket.title, cag_summary=cag_summary or None
        )
        matching_patterns = self.pattern_matching_service.find_matching_patterns(
            issue_description, context, db, pattern_type="execution", limit=5
        )

        best_pattern_tuple = self.pattern_matching_service.get_best_pattern(
            matching_patterns, min_score=min_confidence
        )

        if best_pattern_tuple:
            pattern, match_score = best_pattern_tuple

            runbook = None
            if pattern.runbook_id:
                runbook = db.query(Runbook).filter(Runbook.id == pattern.runbook_id).first()

            confidence = self.calculate_confidence(pattern, match_score, context_data["signals"])

            confidence_breakdown_id = None
            detailed_explanation = {}
            if store_breakdown and runbook:
                try:
                    detailed_explanation = self._build_detailed_explanation(
                        pattern, match_score, confidence, context_data, runbook
                    )
                except Exception as e:
                    logger.warning(f"Failed to store confidence breakdown: {e}")

            should_auto_exec = self.should_auto_execute(confidence, pattern, context_data)
            should_esc = self.should_escalate(confidence, pattern, context_data)
            reasoning = self._build_reasoning(pattern, match_score, confidence, context_data)

            return Recommendation(
                runbook_id=pattern.runbook_id,
                runbook=runbook,
                confidence=confidence,
                pattern=pattern,
                reasoning=reasoning,
                should_auto_execute=should_auto_exec,
                should_escalate=should_esc,
                context_signals=context_data["signals"],
                confidence_breakdown_id=confidence_breakdown_id,
                detailed_explanation=detailed_explanation
            )
        else:
            return Recommendation(
                confidence=0.0,
                reasoning=(
                    "No matching runbook found for this ticket. "
                    "Consider generating a new runbook or reviewing similar runbooks manually."
                ),
                should_escalate=True,
                context_signals=context_data["signals"]
            )

    async def generate_explanation(
        self,
        ticket_id: int,
        recommendation_id: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """Generate detailed explanation for a recommendation."""
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

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
