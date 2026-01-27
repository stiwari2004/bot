"""
Remediation Analytics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.remediation_analytics_controller import RemediationAnalyticsController
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/demo/remediation/effectiveness")
async def get_remediation_effectiveness(
    period_start: Optional[str] = Query(None, description="Period start (ISO format)"),
    period_end: Optional[str] = Query(None, description="Period end (ISO format)"),
    period_type: str = Query("monthly", description="Period type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get MTTR, automation coverage, and ROI metrics"""
    try:
        controller = RemediationAnalyticsController(db, current_user.tenant_id)
        
        period_start_dt = datetime.fromisoformat(period_start) if period_start else None
        period_end_dt = datetime.fromisoformat(period_end) if period_end else None
        
        result = controller.get_effectiveness(
            period_start=period_start_dt,
            period_end=period_end_dt,
            period_type=period_type
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting remediation effectiveness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/remediation/trends")
async def get_improvement_trends(
    period_type: str = Query("monthly", description="Period type"),
    periods: int = Query(12, ge=1, le=24, description="Number of periods"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get improvement trends over time"""
    try:
        controller = RemediationAnalyticsController(db, current_user.tenant_id)
        trends = controller.get_trends(period_type=period_type, periods=periods)
        return trends
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/remediation/failing-steps")
async def get_failing_steps(
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top failing steps"""
    try:
        controller = RemediationAnalyticsController(db, current_user.tenant_id)
        
        period_start_dt = datetime.fromisoformat(period_start) if period_start else None
        period_end_dt = datetime.fromisoformat(period_end) if period_end else None
        
        steps = controller.get_failing_steps(
            period_start=period_start_dt,
            period_end=period_end_dt,
            limit=limit
        )
        return steps
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting failing steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))
