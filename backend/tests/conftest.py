"""
Pytest configuration and shared fixtures
"""
import sys
import os

# Add /app to Python path so we can import app modules
# This must be done BEFORE any app imports
_app_path = '/app'
if _app_path not in sys.path:
    sys.path.insert(0, _app_path)

# Verify path was added
if _app_path not in sys.path:
    raise ImportError(f"Failed to add {_app_path} to Python path. Current path: {sys.path}")

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


@pytest.fixture
def mock_runbook():
    """Create a mock runbook for testing"""
    from unittest.mock import Mock
    from app.models.runbook import Runbook
    
    runbook = Mock(spec=Runbook)
    runbook.id = 1
    runbook.tenant_id = 1
    runbook.title = "Test Runbook"
    runbook.status = "approved"
    runbook.is_active = "active"
    runbook.body_md = "# Test Runbook\nTest content"
    runbook.meta_data = '{"service": "server", "env": "prod", "risk": "low"}'
    runbook.confidence = 0.85
    return runbook


@pytest.fixture
def mock_execution_session():
    """Create a mock execution session for testing"""
    from unittest.mock import Mock
    from app.models.execution_session import ExecutionSession
    
    session = Mock(spec=ExecutionSession)
    session.id = 1
    session.runbook_id = 1
    session.tenant_id = 1
    session.status = "pending"
    session.current_step = 0
    session.waiting_for_approval = False
    session.approval_step_number = None
    session.ticket_id = None
    session.started_at = None
    session.completed_at = None
    return session


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service for testing"""
    from unittest.mock import AsyncMock, Mock
    
    llm = Mock()
    llm.generate_yaml_runbook = AsyncMock(return_value="runbook_id: test\nsteps: []")
    llm.generate_content = AsyncMock(return_value="Generated content")
    llm._chat_once = AsyncMock(return_value="LLM response")
    return llm


@pytest.fixture
def mock_vector_service():
    """Create a mock vector store service for testing"""
    from unittest.mock import AsyncMock, Mock
    
    vector_service = Mock()
    vector_service.hybrid_search = AsyncMock(return_value=[])
    vector_service.search = AsyncMock(return_value=[])
    return vector_service


@pytest.fixture
def authenticated_client(client, db):
    """Create an authenticated test client"""
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.services.auth import get_password_hash, create_access_token
    
    # Create test tenant
    tenant = Tenant(
        id=1,
        name="test_tenant",
        description="Test tenant",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    
    # Create test user
    user = User(
        id=1,
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        tenant_id=1,
        full_name="Test User",
        role="user",
        is_active=True
    )
    db.add(user)
    db.commit()
    
    # Create access token
    token = create_access_token(data={"sub": user.email})
    
    # Set authorization header
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client, user



