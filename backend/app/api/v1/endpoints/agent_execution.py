"""
Agent execution API — thin router composing control and session sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.agent_execution_control import router as control_router
from app.api.v1.endpoints.agent_execution_sessions import router as sessions_router

router = APIRouter()
router.include_router(control_router)
router.include_router(sessions_router)
