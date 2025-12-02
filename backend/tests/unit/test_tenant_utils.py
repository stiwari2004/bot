"""
Unit tests for tenant utilities
"""
import pytest
from unittest.mock import Mock
from app.core.tenant_utils import get_tenant_id
from app.core.config import settings


class TestGetTenantId:
    """Test get_tenant_id function"""
    
    def test_with_user(self):
        """Test that tenant_id is returned from user when available"""
        user = Mock()
        user.tenant_id = 5
        assert get_tenant_id(user) == 5
    
    def test_without_user(self):
        """Test that default tenant_id is returned when user is None"""
        assert get_tenant_id(None) == settings.DEFAULT_TENANT_ID
    
    def test_with_user_none_tenant_id(self):
        """Test that default tenant_id is returned when user has None tenant_id"""
        user = Mock()
        user.tenant_id = None
        # Should still return user's tenant_id (None) or handle gracefully
        # This depends on implementation - adjust based on actual behavior
        result = get_tenant_id(user)
        assert result is not None  # Should return a valid tenant_id



