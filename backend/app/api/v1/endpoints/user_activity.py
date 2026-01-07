"""
User Activity and Login History API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.user_login_history import UserLoginHistory
from app.models.user_activity_log import UserActivityLog
from app.services.auth import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class LoginHistoryResponse(BaseModel):
    id: int
    login_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    failure_reason: Optional[str]
    
    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/login-history", response_model=List[LoginHistoryResponse])
async def get_login_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's login history"""
    try:
        history = db.query(UserLoginHistory).filter(
            UserLoginHistory.user_id == current_user.id
        ).order_by(UserLoginHistory.login_at.desc()).limit(limit).all()
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting login history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get login history")


@router.get("/activity-log", response_model=List[ActivityLogResponse])
async def get_activity_log(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's activity log"""
    try:
        query = db.query(UserActivityLog).filter(
            UserActivityLog.user_id == current_user.id
        )
        
        if action:
            query = query.filter(UserActivityLog.action == action)
        if resource_type:
            query = query.filter(UserActivityLog.resource_type == resource_type)
        
        activities = query.order_by(UserActivityLog.created_at.desc()).limit(limit).all()
        
        return activities
        
    except Exception as e:
        logger.error(f"Error getting activity log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get activity log")

