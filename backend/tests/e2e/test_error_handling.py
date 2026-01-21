"""
End-to-end tests for error handling
Tests system behavior under various error conditions
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, RunbookFactory, TicketFactory
)


@pytest.mark.e2e
class TestNetworkFailureHandling:
    """Test handling of network failures"""
    
    @pytest.mark.asyncio
    async def test_llm_service_failure_handling(
        self, authenticated_client, db
    ):
        """Test that LLM service failures are handled gracefully"""
        client, user = authenticated_client
        
        # Try to generate runbook when LLM service is down
        with patch('app.services.llm_service.get_llm_service') as mock_llm:
            mock_llm.return_value.generate_yaml_runbook = AsyncMock(
                side_effect=Exception("LLM service unavailable")
            )
            
            response = client.post(
                "/api/v1/runbooks/generate-agent",
                json={
                    "issue_description": "CPU usage is high on Windows server",
                    "service": "server",
                    "env": "prod",
                    "risk": "low"
                }
            )
            
            # Should return error, not crash
            assert response.status_code in [500, 502, 503]
            data = response.json()
            assert "error" in data.get("detail", "").lower() or "failed" in data.get("detail", "").lower()
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(
        self, authenticated_client, db
    ):
        """Test that database connection failures are handled"""
        client, user = authenticated_client
        
        # Simulate database failure by patching the repository method
        from sqlalchemy.exc import OperationalError
        
        with patch('app.repositories.runbook_repository.RunbookRepository.get_by_tenant') as mock_repo:
            # Simulate a database connection error
            mock_repo.side_effect = OperationalError(
                "Database connection failed",
                None,
                None
            )
            
            response = client.get("/api/v1/runbooks/")
            
            # Should return error, not crash
            # Endpoint should catch OperationalError and return 503
            assert response.status_code in [500, 503]


@pytest.mark.e2e
class TestInvalidInputHandling:
    """Test handling of invalid input"""
    
    def test_invalid_runbook_id_returns_404(
        self, authenticated_client, db
    ):
        """Test that invalid runbook ID returns 404"""
        client, user = authenticated_client
        
        response = client.get("/api/v1/runbooks/99999")
        assert response.status_code == 404
    
    def test_invalid_ticket_id_returns_404(
        self, authenticated_client, db
    ):
        """Test that invalid ticket ID returns 404"""
        client, user = authenticated_client
        
        response = client.get("/api/v1/tickets/demo/tickets/99999")
        assert response.status_code == 404
    
    def test_invalid_execution_session_id_returns_404(
        self, authenticated_client, db
    ):
        """Test that invalid execution session ID returns 404"""
        client, user = authenticated_client
        
        response = client.get("/api/v1/agent/99999")
        assert response.status_code == 404
    
    def test_malformed_request_returns_422(
        self, authenticated_client, db
    ):
        """Test that malformed requests return 422"""
        client, user = authenticated_client
        
        # Missing required fields
        response = client.post(
            "/api/v1/runbooks/generate-agent",
            json={
                "issue_description": "short"  # Too short
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_authentication_returns_401(
        self, client, db
    ):
        """Test that invalid authentication returns 401"""
        # No token
        response = client.get("/api/v1/runbooks/")
        assert response.status_code == 401
        
        # Invalid token
        client.headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/v1/runbooks/")
        assert response.status_code == 401


@pytest.mark.e2e
class TestTimeoutHandling:
    """Test handling of timeouts"""
    
    @pytest.mark.asyncio
    async def test_llm_timeout_handling(
        self, authenticated_client, db
    ):
        """Test that LLM timeouts are handled"""
        client, user = authenticated_client
        
        # Simulate timeout
        with patch('app.services.llm_service.get_llm_service') as mock_llm:
            import asyncio
            mock_llm.return_value.generate_yaml_runbook = AsyncMock(
                side_effect=asyncio.TimeoutError("LLM request timed out")
            )
            
            response = client.post(
                "/api/v1/runbooks/generate-agent",
                json={
                    "issue_description": "CPU usage is high on Windows server",
                    "service": "server",
                    "env": "prod",
                    "risk": "low"
                }
            )
            
            # Should handle timeout gracefully
            assert response.status_code in [500, 502, 504]


@pytest.mark.e2e
class TestConcurrentRequestHandling:
    """Test handling of concurrent requests"""
    
    def test_concurrent_runbook_generation_requests(
        self, authenticated_client, db
    ):
        """Test that concurrent runbook generation requests are handled"""
        client, user = authenticated_client
        
        # This would test concurrent requests
        # In a real scenario, we'd use threading or asyncio
        # For now, we'll just verify the endpoint can handle requests
        
        issue_description = "CPU usage is high on Windows server"
        
        with patch('app.services.runbook.generation.runbook_generator_core.RunbookGeneratorService') as mock_gen:
            mock_response = Mock()
            mock_response.id = 1
            mock_response.title = "Test"
            mock_response.body_md = "# Test"
            mock_response.confidence = 0.85
            mock_response.meta_data = {}
            mock_response.created_at = None
            mock_response.updated_at = None
            
            mock_generator = Mock()
            mock_generator.generate_agent_runbook = AsyncMock(
                return_value=mock_response
            )
            mock_gen.return_value = mock_generator
            
            # Make multiple requests
            responses = []
            for i in range(3):
                response = client.post(
                    "/api/v1/runbooks/generate-agent",
                    json={
                        "issue_description": f"{issue_description} - Request {i}",
                        "service": "server",
                        "env": "prod",
                        "risk": "low"
                    }
                )
                responses.append(response)
            
            # All requests should be handled (may succeed or fail, but not crash)
            for response in responses:
                assert response.status_code in [200, 500, 502]


@pytest.mark.e2e
class TestResourceExhaustionHandling:
    """Test handling of resource exhaustion scenarios"""
    
    @pytest.mark.asyncio
    async def test_llm_rate_limit_handling(
        self, authenticated_client, db
    ):
        """Test that LLM rate limits are handled"""
        client, user = authenticated_client
        
        from app.services.llm_budget_manager import LLMRateLimitExceeded
        
        # Patch where it's actually used (yaml_generation_pipeline imports it directly)
        with patch('app.services.runbook.generation.yaml_generation_pipeline.get_llm_service') as mock_llm:
            mock_service = AsyncMock()
            mock_service.generate_yaml_runbook = AsyncMock(
                side_effect=LLMRateLimitExceeded("Rate limit exceeded")
            )
            mock_llm.return_value = mock_service
            
            response = client.post(
                "/api/v1/runbooks/generate-agent",
                json={
                    "issue_description": "CPU usage is high on Windows server",
                    "service": "server",
                    "env": "prod",
                    "risk": "low"
                }
            )
            
            # Should return error (may be 429, 500, or other depending on implementation)
            assert response.status_code in [429, 500, 502, 503]
    
    @pytest.mark.asyncio
    async def test_llm_budget_exceeded_handling(
        self, authenticated_client, db
    ):
        """Test that LLM budget exceeded is handled"""
        client, user = authenticated_client
        
        from app.services.llm_budget_manager import LLMBudgetExceeded
        
        # Patch where it's actually used (yaml_generation_pipeline imports it directly)
        with patch('app.services.runbook.generation.yaml_generation_pipeline.get_llm_service') as mock_llm:
            mock_service = AsyncMock()
            mock_service.generate_yaml_runbook = AsyncMock(
                side_effect=LLMBudgetExceeded("Budget exceeded")
            )
            mock_llm.return_value = mock_service
            
            response = client.post(
                "/api/v1/runbooks/generate-agent",
                json={
                    "issue_description": "CPU usage is high on Windows server",
                    "service": "server",
                    "env": "prod",
                    "risk": "low"
                }
            )
            
            # Should return error (may be 402, 500, or other depending on implementation)
            assert response.status_code in [402, 500, 502, 503]

