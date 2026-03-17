"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import (
    Token, UserCreate, UserResponse, PasswordChangeRequest,
    ForgotPasswordRequest, ResetPasswordRequest, EmailVerificationRequest
)
from app.services.auth import get_current_user
from app.models.user import User
from app.core.rate_limiting import rate_limit
from app.controllers.auth_controller import get_auth_controller

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


@router.post("/login", response_model=Token)
@rate_limit("10/minute")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    try:
        controller = get_auth_controller(db)
        return await controller.login(username=form_data.username, password=form_data.password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again or contact support."
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information including tenant details"""
    from app.schemas.auth import TenantInfo
    controller = get_auth_controller(db)
    data = controller.get_current_user_info(current_user)
    if data.get("tenant"):
        data["tenant"] = TenantInfo(**data["tenant"])
    return UserResponse(**data)


@router.post("/register", response_model=UserResponse)
@rate_limit("5/minute")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user"""
    controller = get_auth_controller(db)
    return controller.register(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )


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
        controller = get_auth_controller(db)
        return controller.change_password(
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for {current_user.email}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")


@router.post("/forgot-password")
@rate_limit("5/hour")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request password reset via email"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    try:
        controller = get_auth_controller(db)
        return controller.forgot_password(email=request.email)
    except Exception as e:
        logger.error(f"Error processing password reset request: {e}", exc_info=True)
        return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
@rate_limit("10/hour")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using token from email"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    try:
        controller = get_auth_controller(db)
        return controller.reset_password(token=request.token, new_password=request.new_password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset password")


@router.get("/verify-email")
async def verify_email_get(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email address using token (GET endpoint for email links)"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    try:
        controller = get_auth_controller(db)
        return controller.verify_email(token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify email")


@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address using token (POST endpoint)"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    try:
        controller = get_auth_controller(db)
        return controller.verify_email(token=request.token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify email")
