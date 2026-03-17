"""
Predictions API — thin router composing ingest and analysis sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.predictions_ingest import router as ingest_router
from app.api.v1.endpoints.predictions_analysis import router as analysis_router

router = APIRouter()
router.include_router(ingest_router)
router.include_router(analysis_router)
