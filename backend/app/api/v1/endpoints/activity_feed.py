"""
Activity Feed API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.activity_feed_service import ActivityFeedService
from app.api.v1.endpoints.super_admin_auth import get_current_super_admin
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    tenant_id: Optional[int] = Query(None),
    ticket_id: Optional[int] = Query(None),
    execution_session_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get activity feed showing agentic operations"""
    try:
        service = ActivityFeedService(db, tenant_id=tenant_id)
        feed = service.get_activity_feed(
            limit=limit,
            ticket_id=ticket_id,
            execution_session_id=execution_session_id
        )
        return {
            "activities": feed,
            "count": len(feed)
        }
    except Exception as e:
        logger.error(f"Error fetching activity feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity feed: {str(e)}")


@router.get("/activity-feed/timeline/{ticket_id}")
async def get_incident_timeline(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get detailed timeline for a specific incident/ticket"""
    try:
        service = ActivityFeedService(db)
        timeline = service.get_incident_timeline(ticket_id)
        return timeline
    except Exception as e:
        logger.error(f"Error fetching incident timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch incident timeline: {str(e)}")
