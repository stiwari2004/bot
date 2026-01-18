"""
Super Admin authentication service
Separate from regular user authentication for security
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# CRITICAL: Import ALL model modules in dependency order, exactly like init_db() does
# This ensures all classes are registered with SQLAlchemy Base before any query runs
# SQLAlchemy configures ALL mappers when ANY query is made, so ALL models must be imported first
from app.models import (
    tenant,
    user,
    document,
    chunk,
    embedding,
    runbook,
    execution,
    audit,
)
from app.models import super_admin  # Super Admin model
from app.models import (
    system_config,
    runbook_usage,
    runbook_similarity,
)
# Import RunbookCitation CLASS (not module) to ensure it's registered in SQLAlchemy registry
try:
    from app.models.runbook_citation import RunbookCitation
except ImportError:
    RunbookCitation = None
from app.models import ticket, alert, credential
from app.models import change_ticket  # Must be imported before ticket relationships are resolved
from app.models import execution_session
from app.models import execution_pattern
from app.models import pattern_feedback
from app.models import runbook_metrics
from app.models import confidence_breakdown
from app.models import runbook_version
from app.models import citation_verification  # Depends on runbook_citation
from app.models import resolution_flow
from app.models import decision_analytics
from app.models import metadata_mapping
from app.models import tenant_billing_config  # Must be imported before tenant
from app.models import tenant_subscription  # Must be imported before tenant

# Now import the SuperAdmin class for use
from app.models.super_admin import SuperAdmin
from app.services.auth import verify_password, get_password_hash, create_access_token
from app.core.logging import get_logger

# OAuth2 scheme for super admin (separate from regular auth)
super_admin_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/super-admin/auth/login",
    scheme_name="SuperAdminBearer"
)


def authenticate_super_admin(db: Session, email: str, password: str) -> Optional[SuperAdmin]:
    """Authenticate a super admin"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    
    # #region agent log
    import json
    try:
        with open('/app/.cursor/debug.log', 'a') as f:
            from app.core.database import Base
            registry_classes = list(Base.registry._class_registry.keys())
            f.write(json.dumps({
                "location": "super_admin_auth.py:66",
                "message": "SQLAlchemy registry classes before query",
                "data": {
                    "registry_size": len(registry_classes),
                    "has_runbook_citation": "RunbookCitation" in registry_classes,
                    "has_citation_verification": "CitationVerification" in registry_classes,
                    "sample_classes": registry_classes[:10]
                },
                "timestamp": __import__("time").time() * 1000,
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }) + "\n")
    except Exception:
        pass
    # #endregion
    
    try:
        # Case-insensitive email lookup
        from sqlalchemy import func
        super_admin = db.query(SuperAdmin).filter(func.lower(SuperAdmin.email) == func.lower(email)).first()
        if not super_admin:
            logger.warning(f"Super admin not found for email: {email}")
            return None
        if not super_admin.is_active:
            logger.warning(f"Super admin {email} is inactive")
            return None
        
        password_valid = verify_password(password, super_admin.password_hash)
        if not password_valid:
            logger.warning(f"Password verification failed for super admin: {email}")
            logger.debug(f"Hash in DB: {super_admin.password_hash[:50]}...")
            # Test if hash is valid format
            try:
                test_hash = get_password_hash(password)
                logger.debug(f"New hash would be: {test_hash[:50]}...")
            except Exception as e:
                logger.error(f"Error generating test hash: {e}")
            return None
        
        logger.info(f"Super admin {email} authenticated successfully")
        return super_admin
    except Exception as e:
        logger.error(f"Error authenticating super admin {email}: {e}", exc_info=True)
        return None


async def get_current_super_admin(
    token: str = Depends(super_admin_oauth2_scheme),
    db: Session = Depends(get_db)
) -> SuperAdmin:
    """Get current authenticated super admin"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate super admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        admin_type: str = payload.get("admin_type", "")
        
        if email is None or admin_type != "super_admin":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
    if super_admin is None or not super_admin.is_active:
        raise credentials_exception
    
    # Update last login
    super_admin.last_login = datetime.utcnow()
    db.commit()
    db.refresh(super_admin)  # Refresh to ensure object is still attached to session
    
    return super_admin


def create_super_admin_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token for super admin (includes admin_type claim)"""
    to_encode = {
        "sub": email,
        "admin_type": "super_admin"
    }
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=8)  # Longer session for super admin
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt







