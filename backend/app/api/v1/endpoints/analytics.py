"""
Analytics and observability endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.controllers.analytics_controller import AnalyticsController

router = APIRouter()
controller = AnalyticsController()


@router.get("/demo/usage-stats")
async def get_usage_stats_demo(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get usage statistics for demo tenant"""
    return await controller.get_usage_statistics(
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )


@router.get("/demo/quality-metrics")
async def get_quality_metrics_demo(
    db: Session = Depends(get_db)
):
    """Get quality metrics for demo tenant"""
    return await controller.get_quality_metrics(
        tenant_id=1,  # Demo tenant
        db=db
    )


@router.get("/demo/coverage")
async def get_coverage_analysis_demo(
    db: Session = Depends(get_db)
):
    """Get runbook coverage analysis for demo tenant"""
    return await controller.get_coverage_analysis(
        tenant_id=1,  # Demo tenant
        db=db
    )


@router.get("/demo/search-quality")
async def get_search_quality_demo(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get search quality metrics for demo tenant"""
    return await controller.get_search_quality_metrics(
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )


@router.post("/demo/record-usage")
async def record_runbook_usage_demo(
    runbook_id: int,
    issue_description: str,
    confidence_score: float = Query(..., ge=0.0, le=1.0),
    was_helpful: bool = Query(None),
    feedback_text: str = Query(None),
    execution_time_minutes: int = Query(None),
    db: Session = Depends(get_db)
):
    """Record runbook usage for demo tenant"""
    return await controller.record_runbook_usage(
        runbook_id=runbook_id,
        tenant_id=1,  # Demo tenant
        db=db,
        issue_description=issue_description,
        confidence_score=confidence_score,
        was_helpful=was_helpful,
        feedback_text=feedback_text,
        execution_time_minutes=execution_time_minutes
    )


@router.get("/demo/runbook-quality")
async def get_runbook_quality_metrics_demo(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get comprehensive quality metrics for all runbooks"""
    return await controller.get_runbook_quality_metrics(
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )


@router.get("/demo/runbooks/{runbook_id}/metrics")
async def get_runbook_metrics_demo(
    runbook_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get detailed metrics for a specific runbook"""
    return await controller.get_runbook_metrics(
        runbook_id=runbook_id,
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )


