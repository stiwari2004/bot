"""
Runbook API — thin router that composes generation, demo, and management sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.runbooks_generation import router as generation_router
from app.api.v1.endpoints.runbooks_demo import router as demo_router
from app.api.v1.endpoints.runbooks_management import router as management_router

router = APIRouter()

# NOTE: order matters — more-specific demo/* routes must be included before /{runbook_id}
router.include_router(generation_router)
router.include_router(demo_router)
router.include_router(management_router)
