"""
Integration tests for ticket endpoints
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, TicketFactory, RunbookFactory
)


@pytest.mark.integration
class TestListTicketsEndpoint:
    """Test GET /api/v1/ticket-ingestion/demo/tickets endpoint"""
    
    def test_list_tickets_returns_tickets(
        self, authenticated_client, db
    ):
        """Test listing tickets returns tickets for tenant"""
        client, user = authenticated_client
        
        # Create test tickets
        ticket1 = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Ticket 1",
            status="open"
        )
        ticket2 = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Ticket 2",
            status="resolved"
        )
        
        response = client.get("/api/v1/ticket-ingestion/demo/tickets")
        
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert len(data["tickets"]) >= 2
    
    def test_list_tickets_filters_by_status(
        self, authenticated_client, db
    ):
        """Test that status filter works"""
        client, user = authenticated_client
        
        TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Open Ticket",
            status="open"
        )
        TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Resolved Ticket",
            status="resolved"
        )
        
        response = client.get(
            "/api/v1/ticket-ingestion/demo/tickets?status=open"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "open" for t in data["tickets"])
    
    def test_list_tickets_respects_limit(
        self, authenticated_client, db
    ):
        """Test that limit parameter works"""
        client, user = authenticated_client
        
        # Create multiple tickets
        for i in range(10):
            TicketFactory.create(
                db,
                tenant_id=user.tenant_id,
                title=f"Ticket {i}",
                status="open"
            )
        
        response = client.get(
            "/api/v1/ticket-ingestion/demo/tickets?limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) <= 5


@pytest.mark.integration
class TestGetTicketEndpoint:
    """Test GET /api/v1/ticket-ingestion/demo/tickets/{ticket_id} endpoint"""
    
    def test_get_ticket_returns_ticket_details(
        self, authenticated_client, db
    ):
        """Test getting a specific ticket"""
        client, user = authenticated_client
        
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Test Ticket",
            description="Test description",
            status="open"
        )
        
        response = client.get(
            f"/api/v1/ticket-ingestion/demo/tickets/{ticket.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ticket.id
        assert data["title"] == "Test Ticket"
        assert "matched_runbooks" in data
    
    def test_get_ticket_with_nonexistent_id_returns_404(
        self, authenticated_client, db
    ):
        """Test getting nonexistent ticket returns 404"""
        client, user = authenticated_client
        
        response = client.get("/api/v1/ticket-ingestion/demo/tickets/99999")
        
        assert response.status_code == 404
    
    def test_get_ticket_includes_matched_runbooks(
        self, authenticated_client, db
    ):
        """Test that ticket details include matched runbooks"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Test Ticket"
        )
        
        # Manually add matched runbook to ticket metadata
        import json
        ticket.meta_data = json.dumps({
            "matched_runbooks": [{
                "id": runbook.id,
                "title": runbook.title,
                "confidence_score": 0.9
            }]
        })
        db.commit()
        
        response = client.get(
            f"/api/v1/ticket-ingestion/demo/tickets/{ticket.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "matched_runbooks" in data
        assert len(data["matched_runbooks"]) >= 1


@pytest.mark.integration
class TestCreateDemoTicketEndpoint:
    """Test POST /api/v1/ticket-ingestion/demo/ticket endpoint"""
    
    def test_create_demo_ticket_creates_ticket(
        self, client, db
    ):
        """Test creating a demo ticket"""
        tenant = TenantFactory.create(db, name="demo")
        
        ticket_data = {
            "title": "Demo Ticket",
            "description": "Test ticket description",
            "severity": "high",
            "source": "custom",
            "environment": "prod",
            "service": "server"
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
                    return_value=Mock(to_dict=lambda: {})
                )
                
                with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
                    mock_change.return_value.check_and_suppress_ticket.return_value = False
                    
                    response = client.post(
                        "/api/v1/ticket-ingestion/demo/ticket",
                        json=ticket_data
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "ticket_id" in data
                    assert data["status"] in ["open", "analyzing"]
    
    def test_create_demo_ticket_suppresses_during_change_window(
        self, client, db
    ):
        """Test that ticket is suppressed during change window"""
        tenant = TenantFactory.create(db, name="demo")
        
        ticket_data = {
            "title": "Demo Ticket",
            "description": "Test description",
            "severity": "high",
            "source": "custom"
        }
        
        with patch('app.controllers.ticket_controller.get_change_window_service') as mock_change:
            mock_change.return_value.check_and_suppress_ticket.return_value = True
            
            response = client.post(
                "/api/v1/ticket-ingestion/demo/ticket",
                json=ticket_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "suppressed"
            assert "change window" in data["message"].lower()


@pytest.mark.integration
class TestAnalyzeTicketEndpoint:
    """Test POST /api/v1/tickets/analyze endpoint"""
    
    def test_analyze_ticket_returns_recommendation(
        self, authenticated_client, db
    ):
        """Test analyzing a ticket returns recommendation"""
        client, user = authenticated_client
        
        # Create a runbook for matching
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="High CPU Runbook",
            status="approved"
        )
        
        with patch('app.api.v1.endpoints.tickets.RunbookSearchService') as mock_search:
            mock_search.return_value.search_similar_runbooks = AsyncMock(
                return_value=[{
                    "id": runbook.id,
                    "title": runbook.title,
                    "confidence_score": 0.9,
                    "reasoning": "High similarity"
                }]
            )
            
            response = client.post(
                "/api/v1/tickets/analyze",
                json={
                    "issue_description": "CPU usage is high on Windows server"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "recommendation" in data
            assert "confidence" in data
            assert "matched_runbooks" in data
    
    def test_analyze_ticket_with_no_matches_suggests_generate_new(
        self, authenticated_client, db
    ):
        """Test that no matches suggests generating new runbook"""
        client, user = authenticated_client
        
        with patch('app.api.v1.endpoints.tickets.RunbookSearchService') as mock_search:
            mock_search.return_value.search_similar_runbooks = AsyncMock(
                return_value=[]  # No matches
            )
            
            response = client.post(
                "/api/v1/tickets/analyze",
                json={
                    "issue_description": "Unique issue that has no matches"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["recommendation"] == "generate_new"
            assert data["confidence"] >= 0.7
    
    def test_analyze_ticket_validates_input(
        self, authenticated_client, db
    ):
        """Test that invalid input is rejected"""
        client, user = authenticated_client
        
        response = client.post(
            "/api/v1/tickets/analyze",
            json={
                "issue_description": ""  # Empty description
            }
        )
        
        # Should return validation error or handle gracefully
        assert response.status_code in [400, 422]

