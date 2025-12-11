"""
MSP Tenant Admin authentication and authorization service
For MSP tenants to manage their own customers (sub-tenants)
"""
from typing import List, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_allowed_tenant_ids_for_msp(msp_tenant_id: int, db: Session) -> Set[int]:
    """
    Get all tenant IDs that an MSP can access:
    - MSP's own tenant (for viewing/managing MSP settings)
    - All sub-tenants (customers) of the MSP
    
    Returns set of allowed tenant IDs
    
    NOTE: For user creation, use explicit check to prevent creating users under MSP tenant
    """
    allowed_ids = {msp_tenant_id}  # Include MSP's own tenant for other operations
    
    # Get all sub-tenants (customers)
    customers = db.query(Tenant).filter(
        Tenant.parent_tenant_id == msp_tenant_id,
        Tenant.is_msp == False  # Only customers, not other MSPs
    ).all()
    
    allowed_ids.update([c.id for c in customers])
    
    return allowed_ids


def verify_tenant_access(msp_tenant_id: int, target_tenant_id: int, db: Session) -> bool:
    """
    Verify that MSP can access a target tenant.
    MSP can only access:
    - Its own tenant
    - Its sub-tenants (customers)
    """
    allowed_ids = get_allowed_tenant_ids_for_msp(msp_tenant_id, db)
    return target_tenant_id in allowed_ids


def require_tenant_access(
    msp_tenant_id: int,
    target_tenant_id: int,
    db: Session
):
    """
    Verify that MSP can access a target tenant.
    Raises HTTPException if access is denied.
    """
    if not verify_tenant_access(msp_tenant_id, target_tenant_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only manage your own MSP tenant and its customers."
        )


async def get_current_msp_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated MSP tenant admin.
    Validates:
    1. User is authenticated
    2. User's tenant is an MSP (is_msp = True)
    3. User has admin role
    """
    # Refresh tenant relationship
    db.refresh(current_user, ['tenant'])
    tenant = current_user.tenant
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no associated tenant"
        )
    
    if not tenant.is_msp:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your tenant is not an MSP. This endpoint is only for MSP tenant admins."
        )
    
    # Check for MSP admin role: either 'msp_admin' or legacy 'admin' with MSP tenant
    is_msp_admin = (
        current_user.role == "msp_admin" or 
        (current_user.role == "admin" and tenant.is_msp)
    )
    
    if not is_msp_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MSP admin access required. Only users with 'msp_admin' role (or 'admin' role in MSP tenant) can access MSP admin features."
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MSP tenant is inactive"
        )
    
    logger.debug(f"MSP admin authenticated: {current_user.email}, tenant_id: {tenant.id}")
    return current_user

