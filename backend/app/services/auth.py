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
    from sqlalchemy import func
    # Case-insensitive email lookup
    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    if not user:
        return None
    if not user.is_active:
        return None  # Inactive users cannot authenticate
    if not verify_password(password, user.password_hash):
        return None
    return user


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
        session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.token_hash == token_hash
        ).first()
        
        if session:
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
            # Session not found - this might be an old token or token from before session tracking
            # For backward compatibility, we'll allow it but log a warning
            logger.debug(f"Session not found for token hash, but allowing authentication for {email} (backward compatibility)")
    
    except HTTPException:
        raise
    except Exception as e:
        # Log the error but don't fail authentication for backward compatibility
        # This allows old tokens (from before session tracking) to still work
        logger.warning(f"Error validating session for user {email}: {e}", exc_info=True)
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
