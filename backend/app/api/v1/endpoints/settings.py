"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.config_service import ConfigService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ExecutionModeRequest(BaseModel):
    mode: Literal['hil', 'auto']


class ExecutionModeResponse(BaseModel):
    mode: str
    description: str


@router.get("/execution-mode", response_model=ExecutionModeResponse)
async def get_execution_mode(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current execution mode"""
    try:
        mode = ConfigService.get_execution_mode(db, current_user.tenant_id)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=mode, description=description)
    except Exception as e:
        logger.error(f"Error getting execution mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution mode: {str(e)}")


@router.post("/execution-mode", response_model=ExecutionModeResponse)
async def set_execution_mode(
    request: ExecutionModeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set execution mode"""
    try:
        ConfigService.set_execution_mode(db, current_user.tenant_id, request.mode)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if request.mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=request.mode, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting execution mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set execution mode: {str(e)}")


@router.get("/execution-mode/demo", response_model=ExecutionModeResponse)
async def get_execution_mode_demo(db: Session = Depends(get_db)):
    """Get execution mode (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        mode = ConfigService.get_execution_mode(db, tenant_id)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=mode, description=description)
    except Exception as e:
        logger.error(f"Error getting execution mode (demo): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution mode: {str(e)}")


@router.post("/execution-mode/demo", response_model=ExecutionModeResponse)
async def set_execution_mode_demo(
    request: ExecutionModeRequest,
    db: Session = Depends(get_db)
):
    """Set execution mode (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        ConfigService.set_execution_mode(db, tenant_id, request.mode)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if request.mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=request.mode, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting execution mode (demo): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set execution mode: {str(e)}")



