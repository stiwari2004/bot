"""
Shared Pydantic schemas for decision endpoints
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    runbook_id: Optional[int] = None
    runbook_title: Optional[str] = None
    confidence: float
    pattern_id: Optional[int] = None
    pattern_success_rate: Optional[float] = None
    reasoning: str
    should_auto_execute: bool
    should_escalate: bool
    context_signals: Dict[str, Any]


class PatternMatchResponse(BaseModel):
    pattern_id: int
    pattern_type: str
    runbook_id: Optional[int] = None
    issue_signature: Optional[str] = None
    match_score: float
    success_rate: Optional[float] = None
    usage_count: int


class ContextCorrelationResponse(BaseModel):
    ticket_id: int
    alert_count: int
    execution_count: int
    signals: Dict[str, Any]
    correlated_at: str


class MarkProblemCandidateRequest(BaseModel):
    note: Optional[str] = None


class MarkProblemCandidateResponse(BaseModel):
    ticket_id: int
    problem_candidate: Dict[str, Any]


class RunbookFeedbackRequest(BaseModel):
    runbook_id: int
    matches: bool


class RunbookFeedbackResponse(BaseModel):
    ticket_id: int
    runbook_id: int
    matches: bool
    message: str


class PatternFeedbackRequest(BaseModel):
    pattern_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    ticket_id: Optional[int] = None
    feedback_type: str
    reason: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class PatternFeedbackResponse(BaseModel):
    feedback_id: int
    message: str
    pattern_id: Optional[int] = None


class ExplanationRequest(BaseModel):
    recommendation_id: Optional[int] = None


class ExplanationResponse(BaseModel):
    ticket_id: int
    recommendation_id: Optional[int] = None
    has_breakdown: bool
    confidence_breakdown: Optional[Dict[str, Any]] = None
    detailed_explanation: Optional[Dict[str, Any]] = None
