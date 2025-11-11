# Database models
# Import new Phase 2 models
from app.models.ticket import Ticket
from app.models.credential import Credential, InfrastructureConnection
from app.models.execution_session import (
    ExecutionSession,
    ExecutionStep,
    ExecutionFeedback,
    ExecutionEvent,
    AgentWorkerAssignment,
)
try:
    from app.models.ticketing_tool_connection import TicketingToolConnection
except ImportError:
    TicketingToolConnection = None

# Export for backward compatibility
__all__ = [
    "Ticket",
    "Credential",
    "InfrastructureConnection",
    "ExecutionSession",
    "ExecutionStep",
    "ExecutionFeedback",
    "ExecutionEvent",
    "AgentWorkerAssignment",
]
if TicketingToolConnection:
    __all__.append("TicketingToolConnection")

