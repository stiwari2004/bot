"""
Unit tests for ExecutionController
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session
from app.controllers.execution_controller import ExecutionController
from app.models.runbook import Runbook
from app.models.execution_session import ExecutionSession
from app.models.ticket import Ticket


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def controller(mock_db):
    """Create an ExecutionController instance"""
    return ExecutionController(mock_db, tenant_id=1)


class TestCreateExecutionSession:
    """Test create_execution_session method"""
    
    @pytest.mark.asyncio
    async def test_create_session_with_valid_runbook(self, controller, mock_db):
        """Test creating a session with a valid runbook"""
        # Mock runbook with all required attributes
        runbook = Mock(spec=Runbook)
        runbook.id = 1
        runbook.tenant_id = 1
        runbook.status = "approved"
        runbook.is_active = "active"
        runbook.title = "Test Runbook"
        runbook.body_md = "```yaml\nrunbook_id: test\nsteps: []\n```"  # Required: string, not Mock
        
        # Mock repository methods
        controller.runbook_repo.get_approved_by_id_and_tenant = Mock(return_value=runbook)
        
        # Mock session creation
        mock_session = Mock(spec=ExecutionSession)
        mock_session.id = 1
        mock_session.status = "pending"
        mock_session.runbook_id = 1
        
        # Mock execution orchestrator
        with patch('app.controllers.execution_controller.execution_orchestrator') as mock_orch:
            mock_orch.enqueue_session = AsyncMock(return_value=mock_session)
            mock_orch.serialize_session = Mock(return_value={"id": 1, "status": "pending"})
            
            result = await controller.create_execution_session(
                runbook_id=1,
                issue_description="Test issue",
                user_id=1
            )
            
            assert result is not None
            assert "id" in result
            mock_orch.enqueue_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_with_nonexistent_runbook(self, controller, mock_db):
        """Test creating a session with a nonexistent runbook"""
        # Mock database query to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(Exception):  # Should raise HTTPException or similar
            await controller.create_execution_session(
                runbook_id=999,
                issue_description="Test issue",
                user_id=1
            )
    
    @pytest.mark.asyncio
    async def test_create_session_with_unapproved_runbook(self, controller, mock_db):
        """Test creating a session with an unapproved runbook"""
        # Mock runbook that is not approved
        runbook = Mock(spec=Runbook)
        runbook.id = 1
        runbook.tenant_id = 1
        runbook.status = "draft"
        runbook.is_active = "active"
        runbook.body_md = "```yaml\nrunbook_id: test\nsteps: []\n```"  # Required: string, not Mock
        
        mock_db.query.return_value.filter.return_value.first.return_value = runbook
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await controller.create_execution_session(
                runbook_id=1,
                issue_description="Test issue",
                user_id=1
            )


class TestApproveStep:
    """Test approve_step method"""
    
    @pytest.mark.asyncio
    async def test_approve_step_with_valid_session(self, controller, mock_db):
        """Test approving a step with a valid session"""
        # Mock execution session
        session = Mock(spec=ExecutionSession)
        session.id = 1
        session.tenant_id = 1
        session.status = "running"
        session.steps = []
        
        # Mock step
        step = Mock()
        step.step_number = 1
        step.requires_approval = True
        step.approved = None
        step.completed = False
        
        # Mock repository methods
        controller.execution_repo.get_by_id = Mock(return_value=session)
        controller.execution_repo.get_step = Mock(return_value=step)
        
        # Mock execution engine approve_step
        with patch.object(controller.execution_engine, 'approve_step', new_callable=AsyncMock) as mock_approve:
            mock_approve.return_value = session
            
            result = await controller.update_execution_step(
                session_id=1,
                step_number=1,
                step_type="remediation",
                completed=False,
                approved=True
            )
            
            assert result is not None
            assert "message" in result


class TestGetPendingApprovals:
    """Test get_pending_approvals method"""
    
    def test_get_pending_approvals(self, controller, mock_db):
        """Test getting pending approvals"""
        # Mock pending sessions
        session1 = Mock(spec=ExecutionSession)
        session1.id = 1
        session1.waiting_for_approval = True
        session1.approval_step_number = 1
        session1.runbook_id = 1
        
        session2 = Mock(spec=ExecutionSession)
        session2.id = 2
        session2.waiting_for_approval = True
        session2.approval_step_number = 2
        session2.runbook_id = 2
        
        # Mock repository methods
        controller.execution_repo.get_pending_approvals = Mock(return_value=[session1, session2])
        
        # Mock step retrieval
        mock_step1 = Mock()
        mock_step1.step_type = "remediation"
        mock_step2 = Mock()
        mock_step2.step_type = "verification"
        controller.execution_repo.get_step = Mock(side_effect=[mock_step1, mock_step2])
        
        # Mock runbook retrieval
        mock_runbook1 = Mock()
        mock_runbook1.title = "Runbook 1"
        mock_runbook2 = Mock()
        mock_runbook2.title = "Runbook 2"
        controller.runbook_repo.get_by_id_and_tenant = Mock(side_effect=[mock_runbook1, mock_runbook2])
        
        result = controller.get_pending_approvals()
        
        assert result is not None
        # get_pending_approvals returns {"pending_approvals": [...]}
        assert isinstance(result, dict)
        assert "pending_approvals" in result
        pending_list = result["pending_approvals"]
        assert isinstance(pending_list, list)
        assert len(pending_list) == 2
        assert pending_list[0]["session_id"] == 1
        assert pending_list[1]["session_id"] == 2



