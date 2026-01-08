"""
User Preferences API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class UserPreferencesResponse(BaseModel):
    preferences: Dict[str, Any]
    
    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    preferences: Dict[str, Any]


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user preferences"""
    prefs = current_user.preferences
    if prefs is None:
        prefs = {}
    elif isinstance(prefs, str):
        try:
            prefs = json.loads(prefs)
        except:
            prefs = {}
    
    return {"preferences": prefs}


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    preferences_data: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user preferences"""
    try:
        # Merge with existing preferences
        current_prefs = current_user.preferences
        if current_prefs is None:
            current_prefs = {}
        elif isinstance(current_prefs, str):
            try:
                current_prefs = json.loads(current_prefs)
            except:
                current_prefs = {}
        
        # Merge new preferences
        current_prefs.update(preferences_data.preferences)
        
        # Store as JSON string
        current_user.preferences = json.dumps(current_prefs) if current_prefs else json.dumps({})
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.email} updated preferences")
        
        return {"preferences": current_prefs}
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update preferences")

