"""
Utility functions for tenant management
"""
from typing import Optional
from app.core.config import settings
from app.models.user import User


def get_tenant_id(user: Optional[User] = None) -> int:
    """
    Get tenant ID from user or default to configured default tenant.
    
    Args:
        user: Optional User object (from get_current_user dependency)
        
    Returns:
        Tenant ID (from user if available, otherwise from config)
    """
    if user and hasattr(user, 'tenant_id') and user.tenant_id:
        return user.tenant_id
    return settings.DEFAULT_TENANT_ID




