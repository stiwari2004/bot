"""
Unit tests for execution engine
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.execution.execution_engine import ExecutionEngine
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    
    # Create a chainable query mock
    query_mock = Mock()
    filter_mock = Mock()
    first_mock = Mock()
    
    # Chain: db.query(Model).filter(...).first()
    query_mock.filter.return_value = filter_mock
    filter_mock.first = Mock()
    db.query = Mock(return_value=query_mock)
    
    return db


@pytest.fixture
def execution_engine():
    """Create an ExecutionEngine instance"""
    return ExecutionEngine()


@pytest.fixture
def mock_runbook():
    """Create a mock runbook"""
    runbook = Mock(spec=Runbook)
    runbook.id = 1
    runbook.tenant_id = 1
    runbook.status = "approved"
    runbook.is_active = "active"
    runbook.body_md = "test runbook content"
    return runbook


@pytest.fixture
def mock_execution_session():
    """Create a mock execution session"""
    session = Mock(spec=ExecutionSession)
    session.id = 1
    session.runbook_id = 1
    session.tenant_id = 1
    session.status = "pending"
    session.current_step = 0
    session.waiting_for_approval = False
    session.ticket_id = None
    return session


class TestCreateExecutionSession:
    """Test create_execution_session method"""
    
    @pytest.mark.asyncio
    async def test_create_execution_session_with_valid_runbook(
        self, execution_engine, mock_db, mock_runbook
    ):
        """Test creating a session with a valid runbook"""
        # Mock session service
        with patch.object(
            execution_engine.session_service,
            'create_execution_session',
            new_callable=AsyncMock
        ) as mock_create:
            mock_session = Mock(spec=ExecutionSession)
            mock_session.id = 1
            mock_create.return_value = mock_session
            
            result = await execution_engine.create_execution_session(
                db=mock_db,
                runbook_id=1,
                tenant_id=1,
                issue_description="Test issue",
                user_id=1
            )
            
            assert result is not None
            assert result.id == 1
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_execution_session_with_ticket(
        self, execution_engine, mock_db
    ):
        """Test creating a session with a ticket"""
        with patch.object(
            execution_engine.session_service,
            'create_execution_session',
            new_callable=AsyncMock
        ) as mock_create:
            mock_session = Mock(spec=ExecutionSession)
            mock_session.id = 1
            mock_create.return_value = mock_session
            
            result = await execution_engine.create_execution_session(
                db=mock_db,
                runbook_id=1,
                tenant_id=1,
                ticket_id=100,
                issue_description="Test issue",
                user_id=1
            )
            
            assert result is not None
            # Verify ticket_id was passed
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get('ticket_id') == 100


class TestApproveStep:
    """Test approve_step method"""
    
    @pytest.mark.asyncio
    async def test_approve_step_with_valid_session(
        self, execution_engine, mock_db, mock_execution_session
    ):
        """Test approving a step with a valid session"""
        # Mock the approval service's approve_step method
        with patch.object(
            execution_engine.approval_service,
            'approve_step',
            new_callable=AsyncMock
        ) as mock_approve:
            mock_approve.return_value = mock_execution_session
            
            result = await execution_engine.approve_step(
                db=mock_db,
                session_id=1,
                step_number=1,
                user_id=1,
                approve=True
            )
            
            assert result is not None
            assert result == mock_execution_session
            # Verify the approval service was called with correct parameters
            mock_approve.assert_called_once()
            call_args = mock_approve.call_args
            assert call_args[0][0] == mock_db  # db
            assert call_args[0][1] == 1  # session_id
            assert call_args[0][2] == 1  # step_number
            assert call_args[0][3] == 1  # user_id
            assert call_args[0][4] is True  # approve
    
    @pytest.mark.asyncio
    async def test_approve_step_rejects_step(
        self, execution_engine, mock_db, mock_execution_session
    ):
        """Test rejecting a step"""
        mock_execution_session.status = "failed"  # Changed from "abandoned" to match actual behavior
        
        with patch.object(
            execution_engine.approval_service,
            'approve_step',
            new_callable=AsyncMock
        ) as mock_approve:
            mock_approve.return_value = mock_execution_session
            
            result = await execution_engine.approve_step(
                db=mock_db,
                session_id=1,
                step_number=1,
                user_id=1,
                approve=False
            )
            
            assert result is not None
            assert result.status == "failed"
            mock_approve.assert_called_once()
            call_args = mock_approve.call_args
            assert call_args[0][4] is False  # approve=False


class TestStartExecution:
    """Test start_execution method"""
    
    @pytest.mark.asyncio
    async def test_start_execution_creates_steps(
        self, execution_engine, mock_db, mock_execution_session
    ):
        """Test that starting execution creates steps"""
        mock_execution_session.status = "pending"
        
        # Mock database query for ExecutionSession
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution_session
        
        # Mock ExecutionStep query (for first step)
        mock_step = Mock()
        mock_step.step_number = 1
        mock_step.requires_approval = False
        mock_step.completed = False
        
        # Create separate query chain for ExecutionStep
        step_query_mock = Mock()
        step_filter_mock = Mock()
        step_filter_mock.first.return_value = mock_step
        step_query_mock.filter.return_value = step_filter_mock
        
        # Make db.query return different mocks based on what's queried
        def query_side_effect(model):
            if model.__name__ == "ExecutionSession":
                return mock_db.query.return_value
            elif model.__name__ == "ExecutionStep":
                return step_query_mock
            return mock_db.query.return_value
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock step_execution_service.execute_step
        with patch.object(
            execution_engine.step_execution_service,
            'execute_step',
            new_callable=AsyncMock
        ) as mock_execute:
            result = await execution_engine.start_execution(
                mock_db, mock_execution_session.id
            )
            
            assert result is not None
            # Verify step execution was called if step doesn't require approval
            if not mock_step.requires_approval:
                mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_execution_with_already_running_session(
        self, execution_engine, mock_db, mock_execution_session
    ):
        """Test starting execution when session is already running"""
        mock_execution_session.status = "in_progress"
        
        # Mock database query to return session with in_progress status
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution_session
        
        # Should raise ValueError because status is not "pending" or "queued"
        with pytest.raises(ValueError, match="expected 'pending' or 'queued'"):
            result = await execution_engine.start_execution(
                mock_db, mock_execution_session.id
            )

