"""
Analytics and observability endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/demo/usage-stats")
async def get_usage_stats_demo(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get usage statistics for demo tenant"""
    service = AnalyticsService()
    stats = await service.get_usage_statistics(
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )
    return stats


@router.get("/demo/quality-metrics")
async def get_quality_metrics_demo(
    db: Session = Depends(get_db)
):
    """Get quality metrics for demo tenant"""
    service = AnalyticsService()
    metrics = await service.get_quality_metrics(
        tenant_id=1,  # Demo tenant
        db=db
    )
    return metrics


@router.get("/demo/coverage")
async def get_coverage_analysis_demo(
    db: Session = Depends(get_db)
):
    """Get runbook coverage analysis for demo tenant"""
    service = AnalyticsService()
    coverage = await service.get_coverage_analysis(
        tenant_id=1,  # Demo tenant
        db=db
    )
    return coverage


@router.get("/demo/search-quality")
async def get_search_quality_demo(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get search quality metrics for demo tenant"""
    service = AnalyticsService()
    metrics = await service.get_search_quality_metrics(
        tenant_id=1,  # Demo tenant
        db=db,
        days=days
    )
    return metrics


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
    service = AnalyticsService()
    result = await service.record_runbook_usage(
        runbook_id=runbook_id,
        tenant_id=1,  # Demo tenant
        db=db,
        issue_description=issue_description,
        confidence_score=confidence_score,
        was_helpful=was_helpful,
        feedback_text=feedback_text,
        execution_time_minutes=execution_time_minutes
    )
    return result


