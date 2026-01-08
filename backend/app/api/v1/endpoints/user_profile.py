"""
User Profile API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    phone_number: Optional[str]
    department: Optional[str]
    job_title: Optional[str]
    timezone: str
    locale: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    try:
        # Update fields
        if profile_data.full_name is not None:
            current_user.full_name = profile_data.full_name
        if profile_data.avatar_url is not None:
            current_user.avatar_url = profile_data.avatar_url
        if profile_data.phone_number is not None:
            current_user.phone_number = profile_data.phone_number
        if profile_data.department is not None:
            current_user.department = profile_data.department
        if profile_data.job_title is not None:
            current_user.job_title = profile_data.job_title
        if profile_data.timezone is not None:
            current_user.timezone = profile_data.timezone
        if profile_data.locale is not None:
            current_user.locale = profile_data.locale
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.email} updated profile")
        
        return current_user
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")

