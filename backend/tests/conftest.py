"""
Pytest configuration and shared fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.config import settings
from fastapi.testclient import TestClient
from app.main import app

# Test database URL (use separate test database)
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_troubleshooting_ai"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Create a test database session"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up: drop all tables
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close, let fixture handle it
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    from unittest.mock import Mock
    from app.models.user import User
    
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.tenant_id = 1
    user.full_name = "Test User"
    user.role = "user"
    return user


@pytest.fixture
def mock_tenant():
    """Create a mock tenant for testing"""
    from unittest.mock import Mock
    from app.models.tenant import Tenant
    
    tenant = Mock(spec=Tenant)
    tenant.id = 1
    tenant.name = "demo"
    tenant.description = "Demo tenant"
    tenant.is_active = True
    return tenant



