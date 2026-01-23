"""
Super Admin authentication endpoints
Separate login system for platform administrators
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.services.super_admin_auth import (
    authenticate_super_admin,
    create_super_admin_token,
    get_current_super_admin
)
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class SuperAdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class SuperAdminMeResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    last_login: str | None


@router.post("/login", response_model=SuperAdminLoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Super Admin login endpoint"""
    logger.info(f"Super admin login attempt for: {form_data.username}")
    super_admin = authenticate_super_admin(db, form_data.username, form_data.password)
    if not super_admin:
        logger.warning(f"Super admin login failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_super_admin_token(email=super_admin.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": super_admin.id,
            "email": super_admin.email,
            "full_name": super_admin.full_name,
            "is_active": super_admin.is_active,
        }
    }


@router.get("/me", response_model=SuperAdminMeResponse)
async def get_me(
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get current super admin information"""
    return {
        "id": current_admin.id,
        "email": current_admin.email,
        "full_name": current_admin.full_name,
        "is_active": current_admin.is_active,
        "last_login": current_admin.last_login.isoformat() if current_admin.last_login else None,
    }


@router.get("/check-account")
async def check_super_admin_account(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if a super admin account exists (for debugging)
    Returns account status without revealing sensitive information
    """
    from sqlalchemy import func
    
    super_admin = db.query(SuperAdmin).filter(func.lower(SuperAdmin.email) == func.lower(email)).first()
    
    if not super_admin:
        return {
            "exists": False,
            "message": f"No super admin account found with email: {email}",
            "suggestion": "Create a super admin account using the create_super_admin.py script"
        }
    
    return {
        "exists": True,
        "email": super_admin.email,
        "is_active": super_admin.is_active,
        "has_password": bool(super_admin.password_hash),
        "full_name": super_admin.full_name,
        "created_at": super_admin.created_at.isoformat() if super_admin.created_at else None,
        "last_login": super_admin.last_login.isoformat() if super_admin.last_login else None,
        "message": "Account exists" + (" but is inactive" if not super_admin.is_active else "")
    }







