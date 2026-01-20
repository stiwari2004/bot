"""
Unit tests for RunbookController
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.runbook_controller import RunbookController
from app.models.runbook import Runbook
from app.models.ticket import Ticket


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def runbook_controller(mock_db):
    """Create a RunbookController instance"""
    return RunbookController(db=mock_db, tenant_id=1)


@pytest.fixture
def sample_runbook():
    """Sample runbook object"""
    runbook = Mock(spec=Runbook)
    runbook.id = 1
    runbook.tenant_id = 1
    runbook.title = "Test Runbook"
    runbook.status = "draft"
    runbook.meta_data = '{"service": "server", "env": "prod"}'
    return runbook


class TestGenerateAgentRunbook:
    """Test generate_agent_runbook method"""
    
    @pytest.mark.asyncio
    async def test_generate_agent_runbook_creates_runbook(
        self, runbook_controller, mock_db
    ):
        """Test that agent runbook is generated"""
        issue_description = "CPU usage is high on Windows server"
        
        mock_runbook_response = Mock()
        mock_runbook_response.id = 1
        mock_runbook_response.title = "Test Runbook"
        mock_runbook_response.body_md = "# Test Runbook"
        mock_runbook_response.confidence = 0.85
        mock_runbook_response.meta_data = {}
        mock_runbook_response.created_at = None
        mock_runbook_response.updated_at = None
        
        with patch.object(
            runbook_controller.duplicate_service,
            'check_duplicate',
            return_value=(False, None)
        ):
            with patch.object(
                runbook_controller.generator,
                'generate_agent_runbook',
                new_callable=AsyncMock,
                return_value=mock_runbook_response
            ):
                result = await runbook_controller.generate_agent_runbook(
                    issue_description=issue_description,
                    service="server",
                    env="prod",
                    risk="low"
                )
                
                # generate_agent_runbook returns RunbookResponse (or mock with same attributes)
                assert result is not None
                assert result.id == 1
                assert result.title == "Test Runbook"
    
    @pytest.mark.asyncio
    async def test_generate_agent_runbook_detects_duplicate(
        self, runbook_controller, mock_db, sample_runbook
    ):
        """Test that duplicate runbook is detected"""
        issue_description = "CPU usage is high"
        
        with patch.object(
            runbook_controller.duplicate_service,
            'check_duplicate',
            return_value=(True, sample_runbook)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await runbook_controller.generate_agent_runbook(
                    issue_description=issue_description,
                    service="server",
                    env="prod",
                    risk="low"
                )
            
            assert exc_info.value.status_code == 409
            assert "duplicate" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_generate_agent_runbook_associates_with_ticket(
        self, runbook_controller, mock_db
    ):
        """Test that runbook is associated with ticket"""
        issue_description = "CPU usage is high"
        ticket_id = 100
        
        mock_runbook_response = Mock()
        mock_runbook_response.id = 1
        mock_runbook_response.title = "Test Runbook"
        mock_runbook_response.body_md = "# Test"
        mock_runbook_response.confidence = 0.85
        mock_runbook_response.meta_data = {}
        mock_runbook_response.created_at = None
        mock_runbook_response.updated_at = None
        
        mock_runbook_obj = Mock(spec=Runbook)
        mock_runbook_obj.id = 1
        mock_runbook_obj.meta_data = '{}'
        
        with patch.object(
            runbook_controller.duplicate_service,
            'check_duplicate',
            return_value=(False, None)
        ):
            with patch.object(
                runbook_controller.generator,
                'generate_agent_runbook',
                new_callable=AsyncMock,
                return_value=mock_runbook_response
            ):
                with patch.object(
                    runbook_controller.runbook_repo,
                    'get_by_id_and_tenant',
                    return_value=mock_runbook_obj
                ):
                    with patch.object(
                        runbook_controller.runbook_repo,
                        'update'
                    ) as mock_update:
                        with patch.object(
                            runbook_controller,
                            '_associate_with_ticket'
                        ) as mock_associate:
                            await runbook_controller.generate_agent_runbook(
                                issue_description=issue_description,
                                service="server",
                                env="prod",
                                risk="low",
                                ticket_id=ticket_id
                            )
                            
                            mock_update.assert_called_once()
                            mock_associate.assert_called_once_with(1, ticket_id)
    
    @pytest.mark.asyncio
    async def test_generate_agent_runbook_handles_generation_error(
        self, runbook_controller, mock_db
    ):
        """Test that generation errors are handled"""
        issue_description = "CPU usage is high"
        
        with patch.object(
            runbook_controller.duplicate_service,
            'check_duplicate',
            return_value=(False, None)
        ):
            with patch.object(
                runbook_controller.generator,
                'generate_agent_runbook',
                new_callable=AsyncMock,
                side_effect=Exception("Generation failed")
            ):
                with pytest.raises(HTTPException):
                    await runbook_controller.generate_agent_runbook(
                        issue_description=issue_description,
                        service="server",
                        env="prod",
                        risk="low"
                    )


class TestAssociateWithTicket:
    """Test _associate_with_ticket method"""
    
    def test_associate_with_ticket_adds_runbook_to_ticket(
        self, runbook_controller, mock_db
    ):
        """Test that runbook is added to ticket metadata"""
        runbook_id = 1
        ticket_id = 100
        
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = ticket_id
        mock_ticket.tenant_id = 1
        mock_ticket.meta_data = {}
        
        mock_runbook = Mock(spec=Runbook)
        mock_runbook.id = runbook_id
        mock_runbook.title = "Test Runbook"
        
        with patch.object(
            runbook_controller.ticket_repo,
            'get_by_id_and_tenant',
            return_value=mock_ticket
        ):
            with patch.object(
                runbook_controller.runbook_repo,
                'get',
                return_value=mock_runbook
            ):
                with patch.object(
                    runbook_controller.ticket_repo,
                    'update_ticket_metadata'
                ) as mock_update:
                    result = runbook_controller._associate_with_ticket(
                        runbook_id, ticket_id
                    )
                    
                    assert result is True
                    mock_update.assert_called_once()
                    
                    # Verify runbook was added to metadata
                    call_args = mock_update.call_args
                    meta_data = call_args[1]["meta_data"]
                    assert "matched_runbooks" in meta_data
                    assert len(meta_data["matched_runbooks"]) == 1
                    assert meta_data["matched_runbooks"][0]["id"] == runbook_id
    
    def test_associate_with_ticket_handles_nonexistent_ticket(
        self, runbook_controller, mock_db
    ):
        """Test that nonexistent ticket is handled"""
        with patch.object(
            runbook_controller.ticket_repo,
            'get_by_id_and_tenant',
            return_value=None
        ):
            result = runbook_controller._associate_with_ticket(1, 999)
            
            assert result is False
    
    def test_associate_with_ticket_prevents_duplicate_association(
        self, runbook_controller, mock_db
    ):
        """Test that duplicate association is prevented"""
        runbook_id = 1
        ticket_id = 100
        
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = ticket_id
        mock_ticket.tenant_id = 1
        mock_ticket.meta_data = {
            "matched_runbooks": [{"id": runbook_id, "title": "Existing"}]
        }
        
        with patch.object(
            runbook_controller.ticket_repo,
            'get_by_id_and_tenant',
            return_value=mock_ticket
        ):
            with patch.object(
                runbook_controller.ticket_repo,
                'update_ticket_metadata'
            ) as mock_update:
                result = runbook_controller._associate_with_ticket(
                    runbook_id, ticket_id
                )
                
                # Should still return True but not add duplicate
                assert result is True
                # Verify update_ticket_metadata was NOT called (duplicate detected, early return)
                mock_update.assert_not_called()
                # Verify the original meta_data is unchanged
                assert len(mock_ticket.meta_data["matched_runbooks"]) == 1

