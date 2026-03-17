"""
Decision API — thin router composing ticket, pattern, and confidence sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.decision_tickets import router as tickets_router
from app.api.v1.endpoints.decision_patterns import router as patterns_router

router = APIRouter()
router.include_router(tickets_router)
router.include_router(patterns_router)
