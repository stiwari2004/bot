"""
Database models convenience imports.

This module exposes the most commonly used models and ensures they are
imported early so SQLAlchemy can register their metadata.

IMPORTANT: Import order matters for SQLAlchemy relationships.
Import Tenant and User before Ticket to ensure relationships resolve correctly.
"""

# Import core models first (Tenant, User) before models that reference them
from app.models.tenant import Tenant
from app.models.user import User

# Now import models that have relationships to Tenant/User
from app.models.ticket import Ticket
from app.models.alert import Alert

# Change management models
try:
    from app.models.change_ticket import ChangeTicket
except ImportError:
    ChangeTicket = None
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

# RBAC models
try:
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.models.user_permission import UserPermission
except ImportError:  # pragma: no cover - optional dependency
    Permission = None
    Role = None
    RolePermission = None
    UserPermission = None

# License plan models
try:
    from app.models.license_plan import LicensePlan
except ImportError:  # pragma: no cover - optional dependency
    LicensePlan = None

try:
    from app.models.runbook import Runbook
except ImportError:  # pragma: no cover - optional dependency
    Runbook = None

try:
    from app.models.deployment_approval import DeploymentApproval
except ImportError:  # pragma: no cover - optional dependency
    DeploymentApproval = None

# Provisioning models
try:
    from app.models.provisioning_project import ProvisioningProject
    from app.models.provisioned_resource import ProvisionedResource
    from app.models.infrastructure_template import InfrastructureTemplate
except ImportError:  # pragma: no cover - optional dependency
    ProvisioningProject = None
    ProvisionedResource = None
    InfrastructureTemplate = None


# Export for backward compatibility
__all__ = [
    "Tenant",
    "User",
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

if Permission:
    __all__.extend(["Permission", "Role", "RolePermission", "UserPermission"])

if LicensePlan:
    __all__.append("LicensePlan")

if Runbook:
    __all__.append("Runbook")

if DeploymentApproval:
    __all__.append("DeploymentApproval")

if ProvisioningProject:
    __all__.extend(["ProvisioningProject", "ProvisionedResource", "InfrastructureTemplate"])

# Prediction models
try:
    from app.models.log_entry import LogEntry
    from app.models.log_pattern import LogPattern
    from app.models.prediction import Prediction, PredictionPattern, PredictionModel
except ImportError:  # pragma: no cover - optional dependency
    LogEntry = None
    LogPattern = None
    Prediction = None
    PredictionPattern = None
    PredictionModel = None

if LogEntry:
    __all__.extend(["LogEntry", "LogPattern", "Prediction", "PredictionPattern", "PredictionModel"])

