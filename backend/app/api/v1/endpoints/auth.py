"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.schemas.auth import Token, UserCreate, UserResponse, PasswordChangeRequest
from app.services.auth import authenticate_user, create_access_token, get_current_user, get_password_hash, verify_password
from app.models.user import User
from app.core.rate_limiting import rate_limit

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


@router.post("/login", response_model=Token)
@rate_limit("10/minute")  # Stricter limit for login
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Check if user exists first
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user:
            logger.warning(f"Login attempt with non-existent email: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive. Please contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Now authenticate
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Login attempt with incorrect password for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last_login
        user.last_login = datetime.utcnow()
        db.commit()
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "tenant_id": user.tenant_id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "must_change_password": user.must_change_password or False
        }
    except HTTPException:
        # Re-raise HTTP exceptions (401, etc.)
        raise
    except Exception as e:
        # Log any unexpected errors
        logger.error(f"Unexpected error during login for {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login. Please try again or contact support."
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information including tenant details"""
    # Load tenant relationship
    from app.schemas.auth import TenantInfo
    tenant_info = None
    if current_user.tenant:
        tenant_info = TenantInfo(
            id=current_user.tenant.id,
            name=current_user.tenant.name,
            is_msp=current_user.tenant.is_msp
        )
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        must_change_password=current_user.must_change_password or False,
        tenant_id=current_user.tenant_id,
        tenant=tenant_info,
        created_at=current_user.created_at
    )


@router.post("/register", response_model=UserResponse)
@rate_limit("5/minute")  # Stricter limit for registration
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user (simplified for now)
    # In production, you'd hash the password and create tenant
    new_user = User(
        tenant_id=1,  # Default tenant for now
        email=user_data.email,
        password_hash="hashed_password",  # Hash this properly
        full_name=user_data.full_name,
        role="user"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password (basic validation)
        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(password_data.new_password)
        current_user.must_change_password = False  # Clear the flag after password change
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.email} changed password")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for {current_user.email}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

