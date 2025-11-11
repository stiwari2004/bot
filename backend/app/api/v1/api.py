"""
API v1 router configuration
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, search, runbooks, upload, test, demo, test_auth, tickets, analytics, executions, agent_workers

# Import new Phase 2 endpoints
try:
    from app.api.v1.endpoints import ticket_ingestion, agent_execution, ticket_csv_upload, settings, ticketing_connections
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

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(runbooks.router, prefix="/runbooks", tags=["runbooks"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
api_router.include_router(agent_workers.router, prefix="/agent/workers", tags=["agent-workers"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(test_auth.router, prefix="/test-auth", tags=["test-auth"])

# Include Phase 2 endpoints if available
if ticket_ingestion:
    api_router.include_router(ticket_ingestion.router, prefix="/tickets", tags=["ticket-ingestion"])
if agent_execution:
    api_router.include_router(agent_execution.router, prefix="/agent", tags=["agent-execution"])
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


