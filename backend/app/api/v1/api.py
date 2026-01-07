"""
API v1 router configuration
"""
from fastapi import APIRouter
from app.core.logging import get_logger

logger = get_logger(__name__)
from app.api.v1.endpoints import (
    auth,
    documents,
    search,
    runbooks,
    upload,
    test,
    demo,
    test_auth,
    tickets,
    analytics,
    executions,
    agent_workers,
    network,
    setup,
)

# Import new Phase 2 endpoints
try:
    from app.api.v1.endpoints import (
        ticket_ingestion,
        agent_execution,
        ticket_csv_upload,
        settings,
        ticketing_connections,
        alerts,
        monitoring_connections,
        decision,
        resolution,
        change_tickets,
    )
    connectors = None  # Will be imported separately if available
    try:
        from app.api.v1.endpoints import connectors
    except ImportError:
        connectors = None
except ImportError:
    # If modules don't exist yet, create placeholders
    ticket_ingestion = None
    agent_execution = None
    ticket_csv_upload = None
    connectors = None
    settings = None
    ticketing_connections = None
    alerts = None
    monitoring_connections = None
    decision = None
    resolution = None

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(runbooks.router, prefix="/runbooks", tags=["runbooks"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
if alerts:
    api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
api_router.include_router(agent_workers.router, prefix="/agent/workers", tags=["agent-workers"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(test_auth.router, prefix="/test-auth", tags=["test-auth"])

# Setup endpoints (for first-run configuration)
try:
    from app.api.v1.endpoints import setup
    api_router.include_router(setup.router, prefix="/setup", tags=["setup"])
except ImportError:
    pass  # setup module not available

# Include Phase 2 endpoints if available
if ticket_ingestion:
    api_router.include_router(ticket_ingestion.router, prefix="/tickets", tags=["ticket-ingestion"])
if agent_execution:
    api_router.include_router(agent_execution.router, prefix="/agent", tags=["agent-execution"])
api_router.include_router(network.router, prefix="/network", tags=["network"])
if ticket_csv_upload:
    api_router.include_router(ticket_csv_upload.router, prefix="/tickets", tags=["ticket-csv-upload"])
try:
    if connectors:
        api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
except NameError:
    pass  # connectors not imported
if settings:
    api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
if ticketing_connections:
    api_router.include_router(ticketing_connections.router, prefix="/settings", tags=["ticketing-connections"])
if monitoring_connections:
    api_router.include_router(monitoring_connections.router, prefix="/connectors", tags=["monitoring-connections"])
if decision:
    api_router.include_router(decision.router, prefix="/decision", tags=["decision"])
if resolution:
    api_router.include_router(resolution.router, prefix="/resolution", tags=["resolution"])
if change_tickets:
    api_router.include_router(change_tickets.router, prefix="", tags=["change-tickets"])

# User profile and preferences endpoints
try:
    from app.api.v1.endpoints import user_profile, user_preferences, user_activity, user_sessions
    api_router.include_router(user_profile.router, prefix="/auth", tags=["user-profile"])
    api_router.include_router(user_preferences.router, prefix="/auth", tags=["user-preferences"])
    api_router.include_router(user_activity.router, prefix="/auth", tags=["user-activity"])
    api_router.include_router(user_sessions.router, prefix="/auth", tags=["user-sessions"])
except ImportError:
    pass

# Super Admin endpoints (platform-level management)
# Import super_admin_auth separately so it loads even if super_admin doesn't exist
try:
    from app.api.v1.endpoints import super_admin_auth
    api_router.include_router(super_admin_auth.router, prefix="/super-admin/auth", tags=["super-admin-auth"])
except ImportError:
    pass  # Super admin auth module not available

# Import super_admin endpoints separately (if they exist)
try:
    from app.api.v1.endpoints import super_admin
    api_router.include_router(super_admin.router, prefix="/super-admin", tags=["super-admin"])
    logger.info("Super admin endpoints loaded successfully")
except ImportError as e:
    logger.warning(f"Super admin management endpoints not available (ImportError): {e}")
except Exception as e:
    logger.error(f"Error loading super admin endpoints: {e}", exc_info=True)
    # Don't fail the entire app if super admin endpoints fail to load

# RBAC endpoints (Super Admin only)
try:
    from app.api.v1.endpoints import permissions, roles
    api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
    api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
except ImportError:
    pass

# License Plan endpoints (Super Admin only)
try:
    from app.api.v1.endpoints import license_plans
    api_router.include_router(license_plans.router, prefix="/license-plans", tags=["license-plans"])
except ImportError:
    pass

# Billing endpoints (Super Admin only)
try:
    from app.api.v1.endpoints import billing
    api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
except ImportError:
    pass  # Billing module not available

# Tenant Admin endpoints (for MSPs to manage their customers)
try:
    from app.api.v1.endpoints import tenant_admin
    api_router.include_router(tenant_admin.router, prefix="/tenant-admin", tags=["tenant-admin"])
except ImportError:
    pass  # Tenant admin module not available

# Subscription endpoints (Super Admin only)
try:
    from app.api.v1.endpoints import subscriptions
    api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
except ImportError:
    pass  # Subscriptions module not available

# License Activation endpoints (PaaS only)
try:
    from app.api.v1.endpoints import license_activation
    api_router.include_router(license_activation.router, prefix="/license", tags=["license-activation"])
except ImportError:
    pass  # License activation module not available

# Client Admin endpoints (for tenant admins to manage their own tenant)
try:
    from app.api.v1.endpoints import client_admin
    api_router.include_router(client_admin.router, prefix="/client-admin", tags=["client-admin"])
except ImportError:
    pass  # Client admin module not available

# Dev Runbook Management endpoints
try:
    from app.api.v1.endpoints import dev_runbooks
    api_router.include_router(dev_runbooks.router, tags=["dev-runbooks"])
except ImportError:
    pass  # Dev runbooks module not available

# Deployment Approval endpoints
try:
    from app.api.v1.endpoints import deployment_approvals
    api_router.include_router(deployment_approvals.router, prefix="/deployment-approvals", tags=["deployment-approvals"])
except ImportError:
    pass  # Deployment approvals module not available


