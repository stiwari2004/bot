"""
Safety Policy API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.services.safety_policy_service import SafetyPolicyService
from app.api.v1.endpoints.super_admin_auth import get_current_super_admin
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class SafetyEvaluationRequest(BaseModel):
    runbook_id: int
    environment: str
    severity: str
    risk_score: Optional[float] = None
    target_host: Optional[str] = None


@router.post("/safety-policy/evaluate")
async def evaluate_execution_safety(
    request: SafetyEvaluationRequest,
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Evaluate safety of an execution before proceeding"""
    try:
        service = SafetyPolicyService(db, tenant_id=tenant_id)
        evaluation = service.evaluate_execution_safety(
            runbook_id=request.runbook_id,
            environment=request.environment,
            severity=request.severity,
            risk_score=request.risk_score,
            target_host=request.target_host
        )
        return evaluation
    except Exception as e:
        logger.error(f"Error evaluating execution safety: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate safety: {str(e)}")


@router.get("/safety-policy/check-rate-limit")
async def check_rate_limit(
    runbook_id: int = Query(...),
    target_host: Optional[str] = Query(None),
    window_minutes: int = Query(60, ge=1, le=1440),
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Check if rate limit would be exceeded"""
    try:
        service = SafetyPolicyService(db, tenant_id=tenant_id)
        is_allowed = service.check_rate_limit(
            runbook_id=runbook_id,
            target_host=target_host,
            window_minutes=window_minutes
        )
        return {
            "allowed": is_allowed,
            "runbook_id": runbook_id,
            "window_minutes": window_minutes
        }
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check rate limit: {str(e)}")
