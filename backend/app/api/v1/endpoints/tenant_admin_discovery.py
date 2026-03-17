"""
Tenant Admin Discovery — thin router composing management and agent sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.tenant_admin_discovery_management import router as management_router
from app.api.v1.endpoints.tenant_admin_discovery_agent import router as agent_router

router = APIRouter()
router.include_router(management_router)
router.include_router(agent_router)
