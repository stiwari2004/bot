"""
API v1 router configuration
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, search, runbooks, upload, test, demo, test_auth, tickets, analytics

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(runbooks.router, prefix="/runbooks", tags=["runbooks"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(test_auth.router, prefix="/test-auth", tags=["test-auth"])

