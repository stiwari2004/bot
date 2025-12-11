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
from app.models.super_admin import SuperAdmin
from app.services.auth import verify_password, get_password_hash, create_access_token

# OAuth2 scheme for super admin (separate from regular auth)
super_admin_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/super-admin/auth/login",
    scheme_name="SuperAdminBearer"
)


def authenticate_super_admin(db: Session, email: str, password: str) -> Optional[SuperAdmin]:
    """Authenticate a super admin"""
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
    if not super_admin:
        return None
    if not super_admin.is_active:
        return None
    if not verify_password(password, super_admin.password_hash):
        return None
    return super_admin


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







