"""
Settings API — thin router composing execution and config sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.settings_execution import router as execution_router
from app.api.v1.endpoints.settings_config import router as config_router

router = APIRouter()
router.include_router(execution_router)
router.include_router(config_router)
