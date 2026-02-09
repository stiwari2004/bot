"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.schemas.auth import (
    Token, UserCreate, UserResponse, PasswordChangeRequest,
    ForgotPasswordRequest, ResetPasswordRequest, EmailVerificationRequest
)
from app.services.auth import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, verify_password, generate_reset_token
)
from app.models.user import User
from app.core.rate_limiting import rate_limit
from app.services.email_service import get_email_service
from app.services.password_validator import get_password_validator
from app.core.password_policy import PasswordPolicy
import json

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
    
    # #region agent log - Login start
    import json
    import time
    import os
    try:
        # Try workspace log path first, fallback to /tmp
        log_path = '/app/.cursor/debug.log' if os.path.exists('/app/.cursor') else '/tmp/debug.log'
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(json.dumps({
                "location": "auth.py:login_start",
                "message": "Login attempt started",
                "data": {
                    "email": form_data.username,
                    "has_password": bool(form_data.password)
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "login-check",
                "hypothesisId": "A"
            }) + "\n")
    except Exception:
        pass
    # #endregion
    
    try:
        # Check if user exists first (case-insensitive email lookup)
        from sqlalchemy import func
        # #region agent log - Check for duplicate users
        try:
            all_users_same_email = db.query(User).filter(func.lower(User.email) == func.lower(form_data.username)).all()
            log_path = '/app/.cursor/debug.log' if os.path.exists('/app/.cursor') else '/tmp/debug.log'
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(json.dumps({
                    "location": "auth.py:duplicate_check",
                    "message": "Found users with same email",
                    "data": {
                        "email": form_data.username,
                        "user_count": len(all_users_same_email),
                        "users": [{"id": u.id, "email": u.email, "tenant_id": u.tenant_id, "role": u.role, "is_active": u.is_active} for u in all_users_same_email]
                    },
                    "timestamp": int(time.time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "login-check",
                    "hypothesisId": "A"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        user = db.query(User).filter(func.lower(User.email) == func.lower(form_data.username)).first()
        
        # #region agent log - Selected user
        try:
            log_path = '/app/.cursor/debug.log' if os.path.exists('/app/.cursor') else '/tmp/debug.log'
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(json.dumps({
                    "location": "auth.py:user_selected",
                    "message": "User selected for authentication",
                    "data": {
                        "user_id": user.id if user else None,
                        "email": user.email if user else None,
                        "tenant_id": user.tenant_id if user else None,
                        "role": user.role if user else None,
                        "is_active": user.is_active if user else None
                    },
                    "timestamp": int(time.time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "login-check",
                    "hypothesisId": "A"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
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
        
        # Use timezone-aware timestamps for all account lock checks
        now = datetime.now(timezone.utc)

        # Check if account is locked
        if user.locked_until and user.locked_until > now:
            remaining_minutes = int((user.locked_until - now).total_seconds() / 60)
            logger.warning(f"Login attempt for locked account: {form_data.username} (locked for {remaining_minutes} more minutes)")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked due to too many failed login attempts. Please try again in {remaining_minutes} minutes or contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Auto-unlock if lockout period has expired
        if user.locked_until and user.locked_until <= now:
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()
            logger.info(f"Auto-unlocked account for {form_data.username}")
        
        # Check if password is expired
        from app.services.password_validator import get_password_validator
        password_validator = get_password_validator()
        if user.password_expires_at and password_validator.is_password_expired(user.password_expires_at):
            logger.warning(f"Login attempt with expired password for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your password has expired. Please reset your password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Now authenticate (keep original user reference for failed login tracking)
        logger.info(f"Attempting to authenticate user: {form_data.username}")
        authenticated_user = authenticate_user(db, form_data.username, form_data.password)
        if not authenticated_user:
            # Increment failed login attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login_at = datetime.now(timezone.utc)
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                logger.warning(f"Account locked for {form_data.username} after {user.failed_login_attempts} failed attempts")
            
            db.commit()
            logger.warning(
                f"Login attempt with incorrect password for: {form_data.username} "
                f"(attempt {user.failed_login_attempts}, user_id: {user.id}, active: {user.is_active}, "
                f"locked_until: {user.locked_until})"
            )
            
            # Track failed login in history
            try:
                from app.models.user_login_history import UserLoginHistory
                login_history = UserLoginHistory(
                    user_id=user.id,
                    login_at=datetime.now(timezone.utc),
                    success=False,
                    failure_reason="Incorrect password"
                )
                db.add(login_history)
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to track failed login: {e}")
                db.rollback()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Successful login - reset failed attempts and unlock
        user = authenticated_user
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        # Track login history
        try:
            from app.models.user_login_history import UserLoginHistory
            from starlette.requests import Request
            
            # Get client IP and user agent (if available)
            ip_address = None
            user_agent = None
            # Note: In FastAPI, we'd need to pass Request to get these
            # For now, we'll track without them
            
            login_history = UserLoginHistory(
                user_id=user.id,
                login_at=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            db.add(login_history)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to track login history: {e}")
            db.rollback()
        
        # #region agent log - Before token creation
        try:
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            log_path = '/app/.cursor/debug.log' if os.path.exists('/app/.cursor') else '/tmp/debug.log'
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(json.dumps({
                    "location": "auth.py:before_token",
                    "message": "Creating token with tenant info",
                    "data": {
                        "user_id": user.id,
                        "user_email": user.email,
                        "user_tenant_id": user.tenant_id,
                        "tenant_id": tenant.id if tenant else None,
                        "tenant_name": tenant.name if tenant else None,
                        "tenant_slug": tenant.subdomain_slug if tenant else None
                    },
                    "timestamp": int(time.time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "login-check",
                    "hypothesisId": "B"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Create access token first
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "tenant_id": user.tenant_id},
            expires_delta=access_token_expires
        )
        
        # #region agent log - Token created
        try:
            log_path = '/app/.cursor/debug.log' if os.path.exists('/app/.cursor') else '/tmp/debug.log'
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(json.dumps({
                    "location": "auth.py:token_created",
                    "message": "Access token created",
                    "data": {
                        "user_id": user.id,
                        "user_email": user.email,
                        "tenant_id_in_token": user.tenant_id,
                        "token_length": len(access_token)
                    },
                    "timestamp": int(time.time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "login-check",
                    "hypothesisId": "B"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Track session using the actual token that will be returned.
        # If this fails we must not return the token, or the next request will get 401 "Session not found".
        try:
            from app.models.user_session import UserSession
            import hashlib

            token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            session = UserSession(
                user_id=user.id,
                token_hash=token_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.now(timezone.utc) + access_token_expires
            )
            db.add(session)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist session for user {user.email}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session could not be created. Please try logging in again.",
            ) from e

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
    # Check if user already exists (case-insensitive email lookup)
    from sqlalchemy import func
    existing_user = db.query(User).filter(func.lower(User.email) == func.lower(user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password using PasswordPolicy
    is_valid, errors = PasswordPolicy.validate_password(user_data.password, user_data.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Create new user
    new_user = User(
        tenant_id=1,  # Default tenant for now
        email=user_data.email,
        password_hash=password_hash,
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
        
        # Enhanced password validation using PasswordPolicy
        is_valid, errors = PasswordPolicy.validate_password(password_data.new_password, current_user.email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors)
            )
        
        # Also use existing password validator for additional checks
        password_validator = get_password_validator()
        validator_valid, validator_errors = password_validator.validate_password_strength(password_data.new_password)
        if not validator_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(validator_errors)
            )
        
        # Check password history
        password_history = current_user.password_history
        if password_history is None:
            password_history = []
        elif isinstance(password_history, str):
            try:
                password_history = json.loads(password_history)
            except:
                password_history = []
        
        is_reused, reuse_error = password_validator.check_password_history(
            password_data.new_password,
            current_user.password_hash,
            password_history
        )
        
        if is_reused:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reuse_error
            )
        
        # Store current password in history before updating
        old_password_hash = current_user.password_hash
        new_password_hash = get_password_hash(password_data.new_password)
        
        # Update password history
        updated_history = password_validator.add_to_history(
            new_password_hash,
            password_history,
            old_password_hash
        )
        
        # Update password
        current_user.password_hash = new_password_hash
        current_user.password_history = json.dumps(updated_history) if updated_history else json.dumps([])
        current_user.password_changed_at = datetime.now(timezone.utc)
        current_user.password_expires_at = password_validator.calculate_expiration_date(days=90)
        current_user.must_change_password = False  # Clear the flag after password change
        current_user.updated_at = datetime.now(timezone.utc)
        
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


@router.post("/forgot-password")
@rate_limit("5/hour")  # Rate limit: 5 requests per hour per email
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request password reset via email"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Find user by email (case-insensitive)
        from sqlalchemy import func
        user = db.query(User).filter(func.lower(User.email) == func.lower(request.email)).first()
        
        # Always return success (don't reveal if email exists)
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {request.email}")
            return {"message": "If the email exists, a password reset link has been sent."}
        
        if not user.is_active:
            logger.warning(f"Password reset requested for inactive user: {request.email}")
            return {"message": "If the email exists, a password reset link has been sent."}
        
        # Generate reset token
        reset_token = generate_reset_token()
        reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour
        
        # Store token in user record
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        db.commit()
        
        # Send reset email
        email_service = get_email_service()
        email_sent = email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.full_name
        )
        
        if not email_sent:
            logger.warning(f"Failed to send password reset email to {user.email}")
            # Don't fail the request - token is still valid
        
        logger.info(f"Password reset token generated for {user.email}")
        return {"message": "If the email exists, a password reset link has been sent."}
        
    except Exception as e:
        logger.error(f"Error processing password reset request: {e}", exc_info=True)
        # Return generic message even on error (security best practice)
        return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
@rate_limit("10/hour")  # Rate limit for reset attempts
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using token from email"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Find user by reset token
        user = db.query(User).filter(
            User.password_reset_token == request.token,
            User.password_reset_expires > datetime.now(timezone.utc)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Enhanced password validation using PasswordPolicy
        is_valid, errors = PasswordPolicy.validate_password(request.new_password, user.email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(errors)
            )
        
        # Also use existing password validator for additional checks
        password_validator = get_password_validator()
        validator_valid, validator_errors = password_validator.validate_password_strength(request.new_password)
        if not validator_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(validator_errors)
            )
        
        # Check password history (if exists)
        password_history = user.password_history
        if password_history is None:
            password_history = []
        elif isinstance(password_history, str):
            try:
                password_history = json.loads(password_history)
            except:
                password_history = []
        
        # Only check history if user has a current password
        if user.password_hash:
            is_reused, reuse_error = password_validator.check_password_history(
                request.new_password,
                user.password_hash,
                password_history
            )
            
            if is_reused:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=reuse_error
                )
        
        # Store current password in history before updating
        old_password_hash = user.password_hash
        new_password_hash = get_password_hash(request.new_password)
        
        # Update password history
        updated_history = password_validator.add_to_history(
            new_password_hash,
            password_history,
            old_password_hash
        )
        
        # Update password
        user.password_hash = new_password_hash
        user.password_history = json.dumps(updated_history) if updated_history else json.dumps([])
        user.password_changed_at = datetime.now(timezone.utc)
        user.password_expires_at = password_validator.calculate_expiration_date(days=90)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.must_change_password = False  # Clear force change flag
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Password reset successful for {user.email}")
        return {"message": "Password has been reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.get("/verify-email")
async def verify_email_get(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email address using token (GET endpoint for email links)"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Find user by verification token
        user = db.query(User).filter(
            User.email_verification_token == token
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Mark email as verified
        user.email_verified = True
        user.email_verification_token = None
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Email verified for {user.email}")
        return {"message": "Email has been verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )


@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address using token (POST endpoint)"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    try:
        # Find user by verification token
        user = db.query(User).filter(
            User.email_verification_token == request.token
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Mark email as verified
        user.email_verified = True
        user.email_verification_token = None
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Email verified for {user.email}")
        return {"message": "Email has been verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )

