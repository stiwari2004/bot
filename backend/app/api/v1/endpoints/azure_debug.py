"""
Azure-specific debug endpoints for execution sessions
"""
from fastapi import APIRouter

from app.api.v1.endpoints.azure_debug_vm import router as vm_router
from app.api.v1.endpoints.azure_debug_diagnostics import router as diagnostics_router

router = APIRouter()
router.include_router(vm_router)
router.include_router(diagnostics_router)
