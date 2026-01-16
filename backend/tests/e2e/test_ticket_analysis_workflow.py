"""
End-to-end tests for ticket analysis workflow
Tests complete flow from ticket creation to analysis and runbook matching
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, TicketFactory, RunbookFactory
)


@pytest.mark.e2e
class TestTicketAnalysisWorkflow:
    """Test complete ticket analysis workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_ticket_analysis_workflow(
        self, authenticated_client, db
    ):
        """Test complete workflow from ticket creation to analysis"""
        client, user = authenticated_client
        
        # Step 1: Create a ticket
        ticket_data = {
            "title": "High CPU Usage Alert",
            "description": "CPU usage is above 90% on server-01",
            "severity": "high",
            "source": "prometheus",
            "environment": "prod",
            "service": "server"
        }
        
        with patch('app.controllers.ticket_controller.TicketAnalysisService') as mock_analysis:
            mock_analysis.return_value.analyze_ticket = AsyncMock(
                return_value={
                    "classification": "true_positive",
                    "confidence": 0.9,
                    "reasoning": "High CPU indicates real issue",
                    "suggested_action": "proceed"
                }
            )
            
            with patch('app.controllers.ticket_controller.RecommendationEngine') as mock_rec:
                mock_rec.return_value.recommend_runbook = AsyncMock(
                    return_value=Mock(to_dict=lambda: {"runbook_id": 1})
                )
                
                with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                    mock_change.return_value.check_and_suppress_ticket.return_value = False
                    
                    create_response = client.post(
                        "/api/v1/tickets/demo/ticket",
                        json=ticket_data
                    )
                    
                    assert create_response.status_code == 200
                    ticket_id = create_response.json()["ticket_id"]
                    
                    # Step 2: Analyze ticket
                    analyze_response = client.post(
                        "/api/v1/tickets/analyze",
                        json={
                            "issue_description": ticket_data["description"]
                        }
                    )
                    
                    assert analyze_response.status_code == 200
                    analyze_data = analyze_response.json()
                    assert "recommendation" in analyze_data
                    assert "matched_runbooks" in analyze_data
                    
                    # Step 3: Get ticket details
                    get_response = client.get(
                        f"/api/v1/tickets/demo/tickets/{ticket_id}"
                    )
                    
                    assert get_response.status_code == 200
                    ticket_details = get_response.json()
                    assert ticket_details["id"] == ticket_id
                    assert ticket_details["classification"] == "true_positive"
    
    @pytest.mark.asyncio
    async def test_ticket_analysis_with_false_positive_detection(
        self, authenticated_client, db
    ):
        """Test ticket analysis workflow with false positive detection"""
        client, user = authenticated_client
        
        ticket_data = {
            "title": "Scheduled Maintenance Window",
            "description": "Server will be under maintenance from 2-4 AM",
            "severity": "low",
            "source": "custom"
        }
        
        with patch('app.controllers.ticket_controller.TicketAnalysisService') as mock_analysis:
            mock_analysis.return_value.analyze_ticket = AsyncMock(
                return_value={
                    "classification": "false_positive",
                    "confidence": 0.85,
                    "reasoning": "This is scheduled maintenance",
                    "suggested_action": "close"
                }
            )
            
            with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                mock_change.return_value.check_and_suppress_ticket.return_value = False
                
                create_response = client.post(
                    "/api/v1/tickets/demo/ticket",
                    json=ticket_data
                )
                
                assert create_response.status_code == 200
                ticket_id = create_response.json()["ticket_id"]
                
                # Verify ticket is classified as false positive
                get_response = client.get(
                    f"/api/v1/tickets/demo/tickets/{ticket_id}"
                )
                
                assert get_response.status_code == 200
                ticket_details = get_response.json()
                # Ticket should be closed if false positive with high confidence
                assert ticket_details["classification"] == "false_positive"
    
    @pytest.mark.asyncio
    async def test_ticket_analysis_with_runbook_matching(
        self, authenticated_client, db
    ):
        """Test ticket analysis workflow with runbook matching"""
        client, user = authenticated_client
        
        # Create a runbook for matching
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Fix High CPU",
            status="approved"
        )
        
        ticket_data = {
            "title": "High CPU Usage",
            "description": "CPU usage is high on Windows server",
            "severity": "high",
            "source": "prometheus"
        }
        
        with patch('app.api.v1.endpoints.tickets.RunbookSearchService') as mock_search:
            mock_search.return_value.search_similar_runbooks = AsyncMock(
                return_value=[{
                    "id": runbook.id,
                    "title": runbook.title,
                    "confidence_score": 0.9,
                    "reasoning": "High similarity to existing runbook"
                }]
            )
            
            # Analyze ticket
            analyze_response = client.post(
                "/api/v1/tickets/analyze",
                json={
                    "issue_description": ticket_data["description"]
                }
            )
            
            assert analyze_response.status_code == 200
            analyze_data = analyze_response.json()
            assert analyze_data["recommendation"] == "existing_runbook"
            assert len(analyze_data["matched_runbooks"]) >= 1
            assert analyze_data["matched_runbooks"][0]["id"] == runbook.id


@pytest.mark.e2e
class TestTicketToExecutionWorkflow:
    """Test workflow from ticket to execution"""
    
    @pytest.mark.asyncio
    async def test_ticket_to_execution_workflow(
        self, authenticated_client, db
    ):
        """Test complete workflow from ticket to execution"""
        client, user = authenticated_client
        
        # Step 1: Create runbook
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Fix High CPU",
            status="approved"
        )
        
        # Step 2: Create ticket
        ticket_data = {
            "title": "High CPU Alert",
            "description": "CPU usage is above 90%",
            "severity": "high",
            "source": "prometheus"
        }
        
        with patch('app.controllers.ticket_controller.TicketAnalysisService') as mock_analysis:
            mock_analysis.return_value.analyze_ticket = AsyncMock(
                return_value={
                    "classification": "true_positive",
                    "confidence": 0.9,
                    "reasoning": "Test",
                    "suggested_action": "proceed"
                }
            )
            
            with patch('app.controllers.ticket_controller.RecommendationEngine') as mock_rec:
                mock_rec.return_value.recommend_runbook = AsyncMock(
                    return_value=Mock(to_dict=lambda: {"runbook_id": runbook.id})
                )
                
                with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                    mock_change.return_value.check_and_suppress_ticket.return_value = False
                    
                    create_response = client.post(
                        "/api/v1/tickets/demo/ticket",
                        json=ticket_data
                    )
                    
                    assert create_response.status_code == 200
                    ticket_id = create_response.json()["ticket_id"]
                    
                    # Step 3: Execute runbook for ticket
                    with patch('app.services.execution.execution_engine.StepExecutionService') as mock_step:
                        mock_step.return_value.execute_next_step = AsyncMock()
                        
                        execute_response = client.post(
                            f"/api/v1/tickets/demo/tickets/{ticket_id}/execute",
                            json={
                                "runbook_id": runbook.id
                            }
                        )
                        
                        assert execute_response.status_code in [200, 202]
                        if execute_response.status_code == 200:
                            data = execute_response.json()
                            assert "session_id" in data

