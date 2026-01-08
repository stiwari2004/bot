"""
User Session Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class UserSessionResponse(BaseModel):
    id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_info: Optional[dict]
    last_activity_at: datetime
    expires_at: datetime
    revoked: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/sessions", response_model=List[UserSessionResponse])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all active sessions for current user"""
    try:
        # Get all non-revoked, non-expired sessions
        now = datetime.now(timezone.utc)
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False,
            UserSession.expires_at > now
        ).order_by(UserSession.last_activity_at.desc()).all()
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a specific session"""
    try:
        session = db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.revoked = True
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"User {current_user.email} revoked session {session_id}")
        
        return {"message": "Session revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke session")


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke all sessions except current one"""
    try:
        # Get current session token hash (would need to extract from request)
        # For now, revoke all sessions
        now = datetime.now(timezone.utc)
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked == False,
            UserSession.expires_at > now
        ).all()
        
        revoked_count = 0
        for session in sessions:
            session.revoked = True
            session.revoked_at = now
            revoked_count += 1
        
        db.commit()
        
        logger.info(f"User {current_user.email} revoked {revoked_count} sessions")
        
        return {"message": f"Revoked {revoked_count} sessions", "revoked_count": revoked_count}
        
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke sessions")

