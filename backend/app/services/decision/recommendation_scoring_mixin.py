"""
Mixin: confidence scoring and action-decision methods for RecommendationEngine
"""
import math
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.runbook import Runbook
from app.models.execution_pattern import ExecutionPattern
from app.core.logging import get_logger

logger = get_logger(__name__)


class RecommendationScoringMixin:
    """Confidence scoring and action-decision helpers for RecommendationEngine."""

    def calculate_confidence(
        self,
        pattern: ExecutionPattern,
        match_score: float,
        context_signals: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score for a recommendation."""
        confidence = 0.0

        # 1. Pattern match score (50% weight)
        confidence += match_score * 0.5

        # 2. Pattern success rate (30% weight)
        if pattern.success_rate:
            success_rate_normalized = pattern.success_rate / 100.0
            confidence += success_rate_normalized * 0.3

        # 3. Pattern usage count (10% weight) - log normalization
        if pattern.usage_count:
            max_expected_usage = 100
            usage_score = min(1.0, math.log1p(pattern.usage_count) / math.log1p(max_expected_usage))
            confidence += usage_score * 0.1

        # 4. Context match (10% weight)
        context_match = 1.0
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
        """Determine if runbook should be auto-executed."""
        if confidence < 0.85:
            return False
        if pattern and pattern.success_rate < 90:
            return False
        signals = context_data.get("signals", {})
        if signals.get("has_active_alerts"):
            return False
        if signals.get("severity") == "critical":
            return False
        return True

    def should_escalate(
        self,
        confidence: float,
        pattern: Optional[ExecutionPattern],
        context_data: Dict[str, Any]
    ) -> bool:
        """Determine if issue should be escalated."""
        if confidence < 0.3:
            return True
        if not pattern:
            return True
        signals = context_data.get("signals", {})
        if signals.get("severity") == "critical" and confidence < 0.6:
            return True
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
        """Build human-readable reasoning for the recommendation."""
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
        """Build detailed explanation with citations, pattern details, and reasoning steps."""
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
        if runbook.meta_data:
            try:
                import json
                meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                if "citations" in meta:
                    explanation["citations"] = {
                        "count": len(meta["citations"]),
                        "sources": meta["citations"][:5]
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
        """Store detailed confidence breakdown using ConfidenceScoringService."""
        try:
            runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if not runbook:
                return None
            runbook_yaml = None
            if runbook.body_md:
                import re
                yaml_match = re.search(r'```yaml\n(.*?)\n```', runbook.body_md, re.DOTALL)
                if yaml_match:
                    runbook_yaml = yaml_match.group(1)
            context_text = f"Pattern match: {match_score:.2f}, Success rate: {pattern.success_rate}%"
            from app.schemas.search import SearchResult
            search_results = [
                SearchResult(
                    id=pattern.id,
                    score=match_score,
                    content=f"Pattern: {pattern.issue_signature}",
                    metadata={"pattern_id": pattern.id}
                )
            ]
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
