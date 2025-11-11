"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal, Optional

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.config_service import ConfigService
from app.core.logging import get_logger
from app.services.llm_budget_manager import budget_manager

router = APIRouter()
logger = get_logger(__name__)


class ExecutionModeRequest(BaseModel):
    mode: Literal['hil', 'auto']


class ExecutionModeResponse(BaseModel):
    mode: str
    description: str


class LLMBudgetPolicyRequest(BaseModel):
    budget_tokens: Optional[int] = Field(default=None, ge=0)
    window_seconds: Optional[int] = Field(default=None, ge=60)
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=0)
    alert_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class LLMBudgetPolicyResponse(BaseModel):
    tenant_id: int
    budget_tokens: int
    window_seconds: int
    rate_limit_per_minute: int
    alert_threshold: float
    usage_tokens: int
    window_start: int


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


async def _ensure_authorised(tenant_id: int, current_user: User) -> None:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied for requested tenant.")


@router.get("/llm-budgets/{tenant_id}", response_model=LLMBudgetPolicyResponse)
async def get_llm_budget_policy(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
):
    await _ensure_authorised(tenant_id, current_user)
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.post("/llm-budgets/{tenant_id}", response_model=LLMBudgetPolicyResponse)
async def set_llm_budget_policy(
    tenant_id: int,
    request: LLMBudgetPolicyRequest,
    current_user: User = Depends(get_current_user),
):
    await _ensure_authorised(tenant_id, current_user)
    await budget_manager.set_policy(
        tenant_id=tenant_id,
        budget_tokens=request.budget_tokens,
        window_seconds=request.window_seconds,
        rate_limit_per_minute=request.rate_limit_per_minute,
        alert_threshold=request.alert_threshold,
    )
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.get("/llm-budgets/demo", response_model=LLMBudgetPolicyResponse)
async def get_llm_budget_policy_demo():
    tenant_id = 1
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.post("/llm-budgets/demo", response_model=LLMBudgetPolicyResponse)
async def set_llm_budget_policy_demo(request: LLMBudgetPolicyRequest):
    tenant_id = 1
    await budget_manager.set_policy(
        tenant_id=tenant_id,
        budget_tokens=request.budget_tokens,
        window_seconds=request.window_seconds,
        rate_limit_per_minute=request.rate_limit_per_minute,
        alert_threshold=request.alert_threshold,
    )
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )



