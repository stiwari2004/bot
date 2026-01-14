"""
Authentication service
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# Password hashing
# NOTE: Use pbkdf2_sha256 only to avoid bcrypt backend issues in some environments.
# This is sufficient for dev/test and sandbox usage.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
# HTTP Bearer for optional auth (doesn't raise error if no token)
http_bearer = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def generate_reset_token() -> str:
    """Generate a secure random token for password reset"""
    import secrets
    return secrets.token_urlsafe(32)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user (email is case-insensitive)"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    from sqlalchemy import func
    
    try:
        # Case-insensitive email lookup
        user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
        if not user:
            logger.debug(f"User not found for email: {email}")
            return None
        
        if not user.is_active:
            logger.debug(f"User {email} is inactive")
            return None  # Inactive users cannot authenticate
        
        # Verify password
        password_valid = verify_password(password, user.password_hash)
        if not password_valid:
            logger.debug(f"Password verification failed for user: {email}")
            return None
        
        logger.debug(f"Password verification successful for user: {email}")
        return user
    except Exception as e:
        logger.error(f"Error during authentication for {email}: {e}", exc_info=True)
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Log token presence (but not the actual token value for security)
    if not token:
        logger.warning("No token provided in request")
        raise credentials_exception
    
    logger.info(f"Token received (length: {len(token) if token else 0})")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if email is None:
            logger.warning(f"JWT token missing 'sub' claim. Payload keys: {list(payload.keys())}")
            raise credentials_exception
        logger.info(f"JWT decoded successfully for email: {email}, tenant_id: {tenant_id}")
    except JWTError as e:
        logger.error(f"JWT decode error: {type(e).__name__}: {e}")
        raise credentials_exception
    
    # Case-insensitive email lookup
    from sqlalchemy import func
    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    if user is None:
        logger.warning(f"User not found for email: {email}")
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"User {email} is inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate session - check if token corresponds to a valid, non-revoked session
    try:
        from app.models.user_session import UserSession
        import hashlib
        from datetime import timezone
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if any session exists for this user (to determine if session tracking is enabled)
        any_session_exists = db.query(UserSession).filter(UserSession.user_id == user.id).first() is not None
        
        if any_session_exists:
            # Session tracking is enabled for this user - must validate
            logger.debug(f"Session tracking enabled for user {email}, validating token hash")
            session = db.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.token_hash == token_hash
            ).first()
            
            if not session:
                # Check all sessions for this user to see what's in the database
                all_sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()
                logger.warning(
                    f"Session not found for token hash (session tracking enabled for user {email}). "
                    f"User has {len(all_sessions)} total sessions. "
                    f"Active sessions: {sum(1 for s in all_sessions if not s.revoked and s.expires_at > datetime.now(timezone.utc))}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session not found. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.debug(f"Session found for user {email}, session_id: {session.id}, revoked: {session.revoked}")
            
            # Check if session is revoked
            if session.revoked:
                logger.warning(f"Session revoked for user {email}, session_id: {session.id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has been revoked. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if session is expired
            now = datetime.now(timezone.utc)
            if session.expires_at < now:
                logger.warning(f"Session expired for user {email}, session_id: {session.id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has expired. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update last activity
            try:
                session.last_activity_at = now
                db.commit()
            except Exception as commit_error:
                # If commit fails, rollback but don't fail authentication
                db.rollback()
                logger.warning(f"Failed to update session last_activity_at: {commit_error}")
        else:
            # No sessions exist for this user - backward compatibility mode
            # Allow authentication but log for tracking
            logger.debug(f"No sessions found for user {email} - allowing authentication (backward compatibility)")
    
    except HTTPException:
        raise
    except Exception as e:
        # Log the error but don't fail authentication for backward compatibility
        # This allows old tokens (from before session tracking) to still work
        logger.error(f"Error validating session for user {email}: {e}", exc_info=True)
        # Continue with authentication for backward compatibility
    
    logger.debug(f"Authenticated user: {email}, tenant_id: {user.tenant_id}, active: {user.is_active}")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user, or None if not authenticated (for demo/optional auth endpoints)"""
    if not credentials or not credentials.credentials:
        return None
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except (JWTError, Exception):
        return None
    
    # Case-insensitive email lookup
    from sqlalchemy import func
    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they have admin role (tenant admin)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_super_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they have super_admin role (platform admin)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user
