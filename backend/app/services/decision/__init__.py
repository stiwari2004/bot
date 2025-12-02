"""
Decision-making services package.

This module exposes high-level services used for lightweight decision-making
in Phase 1 (L1–L1.5 issues): pattern storage, context correlation, pattern
matching, recommendations, and simple conditional logic.
"""

from .pattern_storage_service import PatternStorageService
from .context_correlation_service import ContextCorrelationService
from .pattern_matching_service import PatternMatchingService
from .recommendation_engine import RecommendationEngine
from .conditional_logic_service import ConditionalLogicService
from .pattern_feedback_service import PatternFeedbackService

__all__ = [
    "PatternStorageService",
    "ContextCorrelationService",
    "PatternMatchingService",
    "RecommendationEngine",
    "ConditionalLogicService",
    "PatternFeedbackService",
]


