"""
Unit tests for TicketController
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from app.controllers.ticket_controller import TicketController
from app.models.ticket import Ticket
from app.models.runbook import Runbook


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def ticket_controller(mock_db):
    """Create a TicketController instance"""
    return TicketController(db=mock_db, tenant_id=1)


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload for testing"""
    return {
        "alert_id": "alert-123",
        "title": "High CPU Usage",
        "description": "CPU usage is above 90%",
        "severity": "high",
        "source": "prometheus"
    }


@pytest.fixture
def sample_ticket():
    """Sample ticket object"""
    ticket = Mock(spec=Ticket)
    ticket.id = 1
    ticket.tenant_id = 1
    ticket.title = "High CPU Usage"
    ticket.description = "CPU usage is above 90%"
    ticket.status = "open"
    ticket.classification = None
    ticket.meta_data = {}
    return ticket


class TestReceiveWebhook:
    """Test receive_webhook method"""
    
    @pytest.mark.asyncio
    async def test_receive_webhook_creates_ticket(
        self, ticket_controller, mock_db, sample_webhook_payload
    ):
        """Test that webhook creates a ticket"""
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 1
        mock_ticket.status = "open"
        mock_ticket.classification = "true_positive"
        
        with patch.object(
            ticket_controller.ticket_repo,
            'create_ticket',
            return_value=mock_ticket
        ):
            with patch.object(
                ticket_controller,
                '_analyze_ticket',
                new_callable=AsyncMock,
                return_value={"classification": "true_positive", "confidence": 0.9}
            ):
                with patch.object(
                    ticket_controller.recommendation_engine,
                    'recommend_runbook',
                    new_callable=AsyncMock,
                    return_value=Mock(to_dict=lambda: {"runbook_id": 1})
                ):
                    with patch.object(
                        ticket_controller.ticket_repo,
                        'update_ticket_metadata'
                    ):
                        with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                            mock_change.return_value.check_and_suppress_ticket.return_value = False
                            
                            result = await ticket_controller.receive_webhook(
                                source="prometheus",
                                payload=sample_webhook_payload
                            )
                            
                            assert result["ticket_id"] == 1
                            assert result["status"] == "open"
    
    @pytest.mark.asyncio
    async def test_receive_webhook_suppresses_ticket_during_change_window(
        self, ticket_controller, mock_db, sample_webhook_payload
    ):
        """Test that ticket is suppressed during change window"""
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 1
        
        with patch.object(
            ticket_controller.ticket_repo,
            'create_ticket',
            return_value=mock_ticket
        ):
            with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                mock_change.return_value.check_and_suppress_ticket.return_value = True
                
                result = await ticket_controller.receive_webhook(
                    source="prometheus",
                    payload=sample_webhook_payload
                )
                
                assert result["status"] == "suppressed"
                assert "change window" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_receive_webhook_analyzes_ticket(
        self, ticket_controller, mock_db, sample_webhook_payload
    ):
        """Test that ticket is analyzed after creation"""
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 1
        mock_ticket.status = "open"
        mock_ticket.classification = None  # Initially None, will be set by _analyze_ticket
        
        with patch.object(
            ticket_controller.ticket_repo,
            'create_ticket',
            return_value=mock_ticket
        ):
            with patch.object(
                ticket_controller,
                '_analyze_ticket',
                new_callable=AsyncMock
            ) as mock_analyze:
                # Update ticket classification when _analyze_ticket is called
                def analyze_side_effect(ticket):
                    ticket.classification = "false_positive"
                    return {
                        "classification": "false_positive",
                        "confidence": 0.85
                    }
                
                mock_analyze.side_effect = analyze_side_effect
                
                with patch.object(
                    ticket_controller.recommendation_engine,
                    'recommend_runbook',
                    new_callable=AsyncMock,
                    return_value=Mock(to_dict=lambda: {})
                ):
                    with patch.object(
                        ticket_controller.ticket_repo,
                        'update_ticket_metadata'
                    ):
                        with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                            mock_change.return_value.check_and_suppress_ticket.return_value = False
                            
                            result = await ticket_controller.receive_webhook(
                                source="prometheus",
                                payload=sample_webhook_payload
                            )
                            
                            mock_analyze.assert_called_once()
                            assert result["classification"] == "false_positive"
                            assert result["confidence"] == 0.85


class TestCreateDemoTicket:
    """Test create_demo_ticket method"""
    
    @pytest.mark.asyncio
    async def test_create_demo_ticket_creates_ticket(
        self, ticket_controller, mock_db
    ):
        """Test that demo ticket is created"""
        ticket_data = {
            "title": "Demo Ticket",
            "description": "Test description",
            "severity": "medium"
        }
        
        mock_ticket = Mock(spec=Ticket)
        mock_ticket.id = 1
        mock_ticket.status = "open"
        mock_ticket.classification = "true_positive"
        
        with patch.object(
            ticket_controller.ticket_repo,
            'create_ticket',
            return_value=mock_ticket
        ):
            with patch.object(
                ticket_controller,
                '_analyze_ticket',
                new_callable=AsyncMock,
                return_value={"classification": "true_positive", "confidence": 0.9, "reasoning": "Test"}
            ):
                with patch.object(
                    ticket_controller.recommendation_engine,
                    'recommend_runbook',
                    new_callable=AsyncMock,
                    return_value=Mock(to_dict=lambda: {})
                ):
                    with patch.object(
                        ticket_controller,
                        '_find_and_store_matched_runbooks',
                        new_callable=AsyncMock
                    ):
                        with patch.object(
                            ticket_controller,
                            '_auto_execute_if_eligible',
                            new_callable=AsyncMock
                        ):
                            with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                                mock_change.return_value.check_and_suppress_ticket.return_value = False
                                
                                result = await ticket_controller.create_demo_ticket(ticket_data)
                                
                                assert result["ticket_id"] == 1
                                assert result["classification"] == "true_positive"
                                assert result["confidence"] == 0.9
                                assert "reasoning" in result  # create_demo_ticket returns reasoning, not message


class TestAnalyzeTicket:
    """Test _analyze_ticket method"""
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_calls_analysis_service(
        self, ticket_controller, sample_ticket
    ):
        """Test that analysis service is called"""
        with patch.object(
            ticket_controller.analysis_service,
            'analyze_ticket',
            new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = {
                "classification": "true_positive",
                "confidence": 0.9,
                "reasoning": "Test reasoning",
                "suggested_action": "proceed"
            }
            
            result = await ticket_controller._analyze_ticket(sample_ticket)
            
            mock_analyze.assert_called_once()
            assert result["classification"] == "true_positive"
            assert result["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_updates_ticket_classification(
        self, ticket_controller, sample_ticket, mock_db
    ):
        """Test that ticket classification is updated"""
        # Create updated ticket mock
        updated_ticket = Mock(spec=Ticket)
        updated_ticket.id = 1
        updated_ticket.classification = "false_positive"
        updated_ticket.classification_confidence = "high"
        
        with patch.object(
            ticket_controller.analysis_service,
            'analyze_ticket',
            new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = {
                "classification": "false_positive",
                "confidence": 0.85
            }
            
            with patch.object(
                ticket_controller.ticket_repo,
                'update_ticket'  # The actual method is update_ticket, not update_ticket_metadata
            ) as mock_update:
                with patch.object(
                    ticket_controller.ticket_repo,
                    'get_by_id_and_tenant',
                    return_value=updated_ticket
                ):
                    with patch.object(
                        ticket_controller.ticket_status_service,
                        'update_ticket_on_false_positive'
                    ) as mock_status:
                        result = await ticket_controller._analyze_ticket(sample_ticket)
                        
                        # Verify update_ticket was called
                        mock_update.assert_called_once()
                        # Verify result contains classification
                        assert result["classification"] == "false_positive"
                        # Verify ticket status service was called (confidence >= 0.8)
                        mock_status.assert_called_once()

