"""
Integration tests for execution endpoints
"""
import pytest
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, RunbookFactory, ExecutionSessionFactory
)


@pytest.mark.integration
class TestStartExecutionEndpoint:
    """Test /api/v1/agent/execute endpoint"""
    
    def test_start_execution_with_valid_runbook_creates_session(
        self, authenticated_client, db
    ):
        """Test starting execution with valid runbook"""
        client, user = authenticated_client
        
        # Create runbook
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": runbook.id,
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["runbook_id"] == runbook.id
    
    def test_start_execution_with_invalid_runbook_returns_404(
        self, authenticated_client, db
    ):
        """Test starting execution with invalid runbook"""
        client, user = authenticated_client
        
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": 99999,
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code in [404, 400]
    
    def test_start_execution_with_unapproved_runbook_returns_error(
        self, authenticated_client, db
    ):
        """Test starting execution with unapproved runbook"""
        client, user = authenticated_client
        
        # Create draft runbook
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="draft"
        )
        
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": runbook.id,
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code in [400, 403]


@pytest.mark.integration
class TestApproveStepEndpoint:
    """Test /api/v1/agent/{session_id}/approve-step endpoint"""
    
    def test_approve_step_with_valid_session_approves_step(
        self, authenticated_client, db
    ):
        """Test approving a step with valid session"""
        client, user = authenticated_client
        
        # Create runbook and session
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="waiting_approval",
            waiting_for_approval=True,
            approval_step_number=1
        )
        
        response = client.post(
            f"/api/v1/agent/{session.id}/approve-step",
            json={
                "approve": True,
                "step_number": 1
            }
        )
        
        # Note: May return 200 or 202 depending on async processing
        assert response.status_code in [200, 202]
    
    def test_reject_step_stops_execution(
        self, authenticated_client, db
    ):
        """Test rejecting a step stops execution"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="waiting_approval",
            waiting_for_approval=True,
            approval_step_number=1
        )
        
        response = client.post(
            f"/api/v1/agent/{session.id}/approve-step",
            json={
                "approve": False,
                "step_number": 1
            }
        )
        
        assert response.status_code in [200, 202]


@pytest.mark.integration
class TestGetExecutionStatusEndpoint:
    """Test /api/v1/agent/{session_id} endpoint"""
    
    def test_get_execution_status_returns_session_status(
        self, authenticated_client, db
    ):
        """Test getting execution status"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="in_progress"
        )
        
        response = client.get(f"/api/v1/agent/{session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.id
        assert data["status"] == "in_progress"
    
    def test_get_execution_status_with_nonexistent_session_returns_404(
        self, authenticated_client, db
    ):
        """Test getting status for nonexistent session"""
        client, user = authenticated_client
        
        response = client.get("/api/v1/agent/99999")
        
        assert response.status_code == 404


@pytest.mark.integration
class TestListExecutionSessionsEndpoint:
    """Test /api/v1/agent/sessions endpoint"""
    
    def test_list_execution_sessions_returns_sessions(
        self, authenticated_client, db
    ):
        """Test listing execution sessions"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session1 = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="completed"
        )
        session2 = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="in_progress"
        )
        
        response = client.get("/api/v1/agent/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) >= 2
    
    def test_list_execution_sessions_filters_by_status(
        self, authenticated_client, db
    ):
        """Test filtering sessions by status"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="completed"
        )
        ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="in_progress"
        )
        
        response = client.get("/api/v1/agent/sessions?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "completed" for s in data["sessions"])


@pytest.mark.integration
class TestCancelExecutionEndpoint:
    """Test /api/v1/agent/{session_id}/cancel endpoint"""
    
    def test_cancel_execution_cancels_session(
        self, authenticated_client, db
    ):
        """Test canceling an execution session"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="in_progress"
        )
        
        response = client.post(f"/api/v1/agent/{session.id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "abandoned"
    
    def test_cancel_execution_with_completed_session_returns_error(
        self, authenticated_client, db
    ):
        """Test canceling a completed session returns error"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(db, tenant_id=user.tenant_id)
        session = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook.id,
            tenant_id=user.tenant_id,
            status="completed"
        )
        
        response = client.post(f"/api/v1/agent/{session.id}/cancel")
        
        assert response.status_code == 400

