"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class TenantInfo(BaseModel):
    id: int
    name: str
    is_msp: bool
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    must_change_password: Optional[bool] = False
    tenant_id: int
    tenant: Optional[TenantInfo] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    must_change_password: Optional[bool] = False  # Indicates if user must change password


class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[int] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

