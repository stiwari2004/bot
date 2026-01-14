"""
Unit tests for authentication service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from jose import jwt
from sqlalchemy.orm import Session

from app.services.auth import (
    authenticate_user,
    get_password_hash,
    verify_password,
    get_current_user,
    create_access_token
)
from app.models.user import User
from app.core.config import settings
from app.core.database import get_db


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def sample_user():
    """Create a sample user for testing"""
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.password_hash = get_password_hash("testpassword123")
    user.tenant_id = 1
    user.is_active = True
    user.locked_until = None
    user.failed_login_attempts = 0
    user.role = "user"
    user.full_name = "Test User"
    return user


@pytest.fixture
def locked_user(sample_user):
    """Create a locked user"""
    locked = Mock(spec=User)
    locked.id = 2
    locked.email = "locked@example.com"
    locked.password_hash = get_password_hash("testpassword123")
    locked.tenant_id = 1
    locked.is_active = True
    locked.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    locked.failed_login_attempts = 5
    locked.role = "user"
    return locked


class TestPasswordHashing:
    """Test password hashing functions"""
    
    def test_get_password_hash_creates_hash(self):
        """Test that password hash is created"""
        password = "testpassword123"
        hash_value = get_password_hash(password)
        
        assert hash_value is not None
        assert hash_value != password
        assert len(hash_value) > 20
    
    def test_verify_password_with_correct_password_returns_true(self):
        """Test password verification with correct password"""
        password = "testpassword123"
        hash_value = get_password_hash(password)
        
        result = verify_password(password, hash_value)
        assert result is True
    
    def test_verify_password_with_incorrect_password_returns_false(self):
        """Test password verification with incorrect password"""
        password = "testpassword123"
        hash_value = get_password_hash(password)
        
        result = verify_password("wrongpassword", hash_value)
        assert result is False


class TestAuthenticateUser:
    """Test user authentication"""
    
    def test_authenticate_user_with_valid_credentials(
        self, mock_db, sample_user
    ):
        """Test authentication with valid credentials"""
        from sqlalchemy import func
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        result = authenticate_user(mock_db, "test@example.com", "testpassword123")
        
        assert result is not None
        assert result.email == "test@example.com"
        assert result.id == 1
    
    def test_authenticate_user_with_invalid_email(self, mock_db):
        """Test authentication with invalid email"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = authenticate_user(mock_db, "nonexistent@example.com", "password")
        
        assert result is None
    
    def test_authenticate_user_with_invalid_password(
        self, mock_db, sample_user
    ):
        """Test authentication with invalid password"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        result = authenticate_user(mock_db, "test@example.com", "wrongpassword")
        
        assert result is None
    
    def test_authenticate_user_with_inactive_account(
        self, mock_db, sample_user
    ):
        """Test authentication with inactive account"""
        sample_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        result = authenticate_user(mock_db, "test@example.com", "testpassword123")
        
        assert result is None
    
    def test_authenticate_user_with_locked_account(
        self, mock_db, locked_user
    ):
        """Test authentication with locked account"""
        from datetime import datetime, timezone
        # Check if account is locked (locked_until is in the future)
        if locked_user.locked_until and locked_user.locked_until > datetime.now(timezone.utc):
            mock_db.query.return_value.filter.return_value.first.return_value = locked_user
            
            result = authenticate_user(mock_db, "locked@example.com", "testpassword123")
            
            # Should return None for locked account (implementation may vary)
            assert result is None


class TestCreateAccessToken:
    """Test access token creation"""
    
    def test_create_access_token_creates_valid_token(self):
        """Test that access token is created and valid"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data=data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify token
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == "test@example.com"
    
    def test_create_access_token_includes_expiration(self):
        """Test that token includes expiration"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data=data)
        
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in decoded
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp()


class TestGetCurrentUser:
    """Test get_current_user function"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(
        self, mock_db, sample_user
    ):
        """Test getting current user with valid token"""
        from sqlalchemy import func
        token = create_access_token(data={"sub": "test@example.com"})
        
        # Mock database query chain
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value = mock_query
        
        # Mock UserSession query to return None (no sessions - backward compatibility)
        with patch('app.services.auth.UserSession') as mock_session_model:
            mock_session_query = Mock()
            mock_session_query.filter.return_value.first.return_value = None
            mock_db.query.return_value = mock_session_query
            
            # Also mock the user query
            with patch.object(mock_db, 'query') as mock_query_func:
                # First call for UserSession, second for User
                mock_query_func.side_effect = [
                    mock_session_query,  # UserSession query
                    mock_query  # User query
                ]
                
                result = await get_current_user(token=token, db=mock_db)
                
                assert result is not None
                assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, mock_db):
        """Test getting current user with invalid token"""
        invalid_token = "invalid.token.here"
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=invalid_token, db=mock_db)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_nonexistent_user(self, mock_db):
        """Test getting current user when user doesn't exist"""
        from sqlalchemy import func
        token = create_access_token(data={"sub": "nonexistent@example.com"})
        
        # Mock UserSession query (no sessions)
        mock_session_query = Mock()
        mock_session_query.filter.return_value.first.return_value = None
        
        # Mock User query (user not found)
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = None
        
        with patch.object(mock_db, 'query') as mock_query_func:
            mock_query_func.side_effect = [
                mock_session_query,  # UserSession query
                mock_user_query  # User query
            ]
            
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, db=mock_db)
            
            assert exc_info.value.status_code == 401

