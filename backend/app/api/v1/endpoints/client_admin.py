"""
Client Admin API — thin router composing user and node sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.client_admin_users import router as users_router
from app.api.v1.endpoints.client_admin_nodes import router as nodes_router

router = APIRouter()
router.include_router(users_router)
router.include_router(nodes_router)
