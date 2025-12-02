"""
Database models convenience imports.

This module exposes the most commonly used models and ensures they are
imported early so SQLAlchemy can register their metadata.
"""

from app.models.ticket import Ticket
from app.models.alert import Alert
from app.models.credential import Credential, InfrastructureConnection
from app.models.execution_session import (
    ExecutionSession,
    ExecutionStep,
    ExecutionFeedback,
    ExecutionEvent,
    AgentWorkerAssignment,
)
from app.models.execution_pattern import ExecutionPattern
from app.models.pattern_feedback import PatternFeedback
from app.models.runbook_metrics import RunbookMetrics
from app.models.confidence_breakdown import ConfidenceBreakdown
from app.models.runbook_version import RunbookVersion
from app.models.citation_verification import CitationVerification
from app.models.resolution_flow import ResolutionFlow
from app.models.decision_analytics import DecisionAnalytics

try:
    from app.models.ticketing_tool_connection import TicketingToolConnection
except ImportError:  # pragma: no cover - optional dependency
    TicketingToolConnection = None

try:
    from app.models.monitoring_tool_connection import MonitoringToolConnection
except ImportError:  # pragma: no cover - optional dependency
    MonitoringToolConnection = None


# Export for backward compatibility
__all__ = [
    "Ticket",
    "Alert",
    "Credential",
    "InfrastructureConnection",
    "ExecutionSession",
    "ExecutionStep",
    "ExecutionFeedback",
    "ExecutionEvent",
    "AgentWorkerAssignment",
    "ExecutionPattern",
    "PatternFeedback",
    "RunbookMetrics",
    "ConfidenceBreakdown",
    "RunbookVersion",
    "CitationVerification",
    "ResolutionFlow",
    "DecisionAnalytics",
]

if TicketingToolConnection:
    __all__.append("TicketingToolConnection")

if MonitoringToolConnection:
    __all__.append("MonitoringToolConnection")

