"""
Auth Controller — login, register, password management, email verification
"""
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.services.auth import (
    authenticate_user, create_access_token,
    get_password_hash, verify_password, generate_reset_token,
)
from app.services.email_service import get_email_service
from app.services.password_validator import get_password_validator
from app.core.password_policy import PasswordPolicy

logger = get_logger(__name__)


class AuthController:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    async def login(self, username: str, password: str) -> dict:
        db = self.db

        # --- PaaS branch ---
        if (
            (getattr(settings, "DEPLOYMENT_MODE", "") or "").lower() == "paas"
            and getattr(settings, "CENTRAL_SERVER_URL", None)
        ):
            from app.services.central_client import validate_paas_login

            central_result = validate_paas_login(username, password)
            if central_result is not None:
                local_user = db.query(User).filter(
                    func.lower(User.email) == func.lower(username)
                ).first()
                default_tenant_id = getattr(settings, "DEFAULT_TENANT_ID", 1)
                if not local_user:
                    local_user = User(
                        tenant_id=default_tenant_id,
                        email=username,
                        password_hash=get_password_hash(secrets.token_urlsafe(32)),
                        full_name=central_result.get("full_name"),
                        role=central_result.get("role", "tenant_admin"),
                        is_active=True,
                    )
                    db.add(local_user)
                    db.commit()
                    db.refresh(local_user)
                else:
                    local_user.full_name = central_result.get("full_name") or local_user.full_name
                    local_user.role = central_result.get("role", local_user.role)
                    local_user.is_active = True
                    db.commit()
                    db.refresh(local_user)

                user = local_user
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.now(timezone.utc)
                db.commit()

                self._track_login_history(user.id, success=True)

                access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user.email, "tenant_id": user.tenant_id},
                    expires_delta=access_token_expires,
                )
                self._create_session(user, access_token, access_token_expires)
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "must_change_password": getattr(user, "must_change_password", False) or False,
                }

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate with central",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # --- Local auth branch ---
        user = db.query(User).filter(func.lower(User.email) == func.lower(username)).first()

        if not user:
            logger.warning(f"Login attempt with non-existent email: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive. Please contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        now = datetime.now(timezone.utc)

        if user.locked_until and user.locked_until > now:
            remaining = int((user.locked_until - now).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked due to too many failed login attempts. Please try again in {remaining} minutes or contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.locked_until and user.locked_until <= now:
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

        password_validator = get_password_validator()
        if user.password_expires_at and password_validator.is_password_expired(user.password_expires_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your password has expired. Please reset your password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        authenticated_user = authenticate_user(db, username, password)
        if not authenticated_user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login_at = datetime.now(timezone.utc)
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            db.commit()
            self._track_login_history(user.id, success=False, failure_reason="Incorrect password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = authenticated_user
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        self._track_login_history(user.id, success=True)

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "tenant_id": user.tenant_id},
            expires_delta=access_token_expires,
        )
        self._create_session(user, access_token, access_token_expires)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "must_change_password": user.must_change_password or False,
        }

    # ------------------------------------------------------------------
    # Current user info
    # ------------------------------------------------------------------
    def get_current_user_info(self, current_user: User) -> dict:
        tenant_info = None
        if current_user.tenant:
            tenant_info = {
                "id": current_user.tenant.id,
                "name": current_user.tenant.name,
                "is_msp": current_user.tenant.is_msp,
            }
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "must_change_password": current_user.must_change_password or False,
            "tenant_id": current_user.tenant_id,
            "tenant": tenant_info,
            "created_at": current_user.created_at,
        }

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------
    def register(self, email: str, password: str, full_name: str = None) -> User:
        db = self.db
        existing = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        is_valid, errors = PasswordPolicy.validate_password(password, email)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

        new_user = User(
            tenant_id=1,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role="user",
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    # ------------------------------------------------------------------
    # Change password
    # ------------------------------------------------------------------
    def change_password(self, current_password: str, new_password: str, current_user: User) -> dict:
        db = self.db
        if not verify_password(current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        is_valid, errors = PasswordPolicy.validate_password(new_password, current_user.email)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

        password_validator = get_password_validator()
        validator_valid, validator_errors = password_validator.validate_password_strength(new_password)
        if not validator_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(validator_errors))

        password_history = self._load_password_history(current_user.password_history)
        is_reused, reuse_error = password_validator.check_password_history(
            new_password, current_user.password_hash, password_history
        )
        if is_reused:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reuse_error)

        old_hash = current_user.password_hash
        new_hash = get_password_hash(new_password)
        updated_history = password_validator.add_to_history(new_hash, password_history, old_hash)

        current_user.password_hash = new_hash
        current_user.password_history = json.dumps(updated_history) if updated_history else json.dumps([])
        current_user.password_changed_at = datetime.now(timezone.utc)
        current_user.password_expires_at = password_validator.calculate_expiration_date(days=90)
        current_user.must_change_password = False
        current_user.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(current_user)
        logger.info(f"User {current_user.email} changed password")
        return {"message": "Password changed successfully"}

    # ------------------------------------------------------------------
    # Forgot password
    # ------------------------------------------------------------------
    def forgot_password(self, email: str) -> dict:
        db = self.db
        user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
        generic = {"message": "If the email exists, a password reset link has been sent."}

        if not user or not user.is_active:
            return generic

        reset_token = generate_reset_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()

        email_service = get_email_service()
        email_service.send_password_reset_email(
            to_email=user.email, reset_token=reset_token, user_name=user.full_name
        )
        return generic

    # ------------------------------------------------------------------
    # Reset password
    # ------------------------------------------------------------------
    def reset_password(self, token: str, new_password: str) -> dict:
        db = self.db
        user = db.query(User).filter(
            User.password_reset_token == token,
            User.password_reset_expires > datetime.now(timezone.utc),
        ).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        is_valid, errors = PasswordPolicy.validate_password(new_password, user.email)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

        password_validator = get_password_validator()
        validator_valid, validator_errors = password_validator.validate_password_strength(new_password)
        if not validator_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(validator_errors))

        password_history = self._load_password_history(user.password_history)
        if user.password_hash:
            is_reused, reuse_error = password_validator.check_password_history(
                new_password, user.password_hash, password_history
            )
            if is_reused:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reuse_error)

        old_hash = user.password_hash
        new_hash = get_password_hash(new_password)
        updated_history = password_validator.add_to_history(new_hash, password_history, old_hash)

        user.password_hash = new_hash
        user.password_history = json.dumps(updated_history) if updated_history else json.dumps([])
        user.password_changed_at = datetime.now(timezone.utc)
        user.password_expires_at = password_validator.calculate_expiration_date(days=90)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.must_change_password = False
        user.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)
        logger.info(f"Password reset successful for {user.email}")
        return {"message": "Password has been reset successfully"}

    # ------------------------------------------------------------------
    # Verify email
    # ------------------------------------------------------------------
    def verify_email(self, token: str) -> dict:
        db = self.db
        user = db.query(User).filter(User.email_verification_token == token).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

        user.email_verified = True
        user.email_verification_token = None
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        logger.info(f"Email verified for {user.email}")
        return {"message": "Email has been verified successfully"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _load_password_history(self, raw) -> list:
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return []
        return raw if isinstance(raw, list) else []

    def _track_login_history(self, user_id: int, success: bool, failure_reason: str = None):
        try:
            from app.models.user_login_history import UserLoginHistory
            record = UserLoginHistory(
                user_id=user_id,
                login_at=datetime.now(timezone.utc),
                success=success,
                failure_reason=failure_reason,
            )
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to track login history: {e}")
            self.db.rollback()

    def _create_session(self, user: User, access_token: str, expires_delta: timedelta):
        try:
            from app.models.user_session import UserSession
            token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            session = UserSession(
                user_id=user.id,
                token_hash=token_hash,
                ip_address=None,
                user_agent=None,
                expires_at=datetime.now(timezone.utc) + expires_delta,
            )
            self.db.add(session)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to persist session for user {user.email}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session could not be created. Please try logging in again.",
            ) from e


def get_auth_controller(db: Session) -> AuthController:
    return AuthController(db)
