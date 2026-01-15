"""
Unit tests for ticket analysis service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.ticket_analysis_service import TicketAnalysisService
from app.services.llm_budget_manager import LLMBudgetExceeded, LLMRateLimitExceeded


@pytest.fixture
def ticket_analysis_service():
    """Create a TicketAnalysisService instance"""
    return TicketAnalysisService()


@pytest.fixture
def sample_ticket_data():
    """Sample ticket data for testing"""
    return {
        "title": "High CPU Usage Alert",
        "description": "CPU usage is above 90% on server-01",
        "severity": "high",
        "source": "prometheus",
        "tenant_id": 1
    }


@pytest.fixture
def false_positive_ticket_data():
    """Sample false positive ticket data"""
    return {
        "title": "Scheduled Maintenance Window",
        "description": "Server will be under maintenance from 2-4 AM",
        "severity": "low",
        "source": "custom",
        "tenant_id": 1
    }


class TestAnalyzeTicket:
    """Test analyze_ticket method"""
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_with_true_positive(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test analyzing a true positive ticket"""
        mock_response = json.dumps({
            "classification": "true_positive",
            "confidence": 0.9,
            "reasoning": "High CPU usage indicates a real issue",
            "suggested_action": "proceed"
        })
        
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            assert result["classification"] == "true_positive"
            assert result["confidence"] == 0.9
            assert result["suggested_action"] == "proceed"
            assert "reasoning" in result
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_with_false_positive(
        self, ticket_analysis_service, false_positive_ticket_data
    ):
        """Test analyzing a false positive ticket"""
        mock_response = json.dumps({
            "classification": "false_positive",
            "confidence": 0.85,
            "reasoning": "This is scheduled maintenance",
            "suggested_action": "close"
        })
        
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await ticket_analysis_service.analyze_ticket(false_positive_ticket_data)
            
            assert result["classification"] == "false_positive"
            assert result["confidence"] == 0.85
            assert result["suggested_action"] == "close"
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_with_uncertain_classification(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test analyzing a ticket with uncertain classification"""
        mock_response = json.dumps({
            "classification": "uncertain",
            "confidence": 0.5,
            "reasoning": "Need more information",
            "suggested_action": "review"
        })
        
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            assert result["classification"] == "uncertain"
            assert result["confidence"] == 0.5
            assert result["suggested_action"] == "review"
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_handles_rate_limit_exception(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that rate limit exception is handled gracefully"""
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = LLMRateLimitExceeded("Rate limit exceeded")
            
            result = await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            assert result["classification"] == "uncertain"
            assert result["confidence"] == 0.0
            assert result["suggested_action"] == "review"
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_handles_budget_exceeded_exception(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that budget exceeded exception is handled gracefully"""
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = LLMBudgetExceeded("Budget exceeded")
            
            result = await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            assert result["classification"] == "uncertain"
            assert result["confidence"] == 0.0
            assert result["suggested_action"] == "review"
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_handles_generic_exception(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that generic exceptions are handled gracefully"""
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = Exception("Unexpected error")
            
            result = await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            assert result["classification"] == "uncertain"
            assert result["confidence"] == 0.0
            assert result["suggested_action"] == "review"
            assert "Analysis failed" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_uses_tenant_id_from_parameter(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that tenant_id parameter is used when provided"""
        mock_response = json.dumps({
            "classification": "true_positive",
            "confidence": 0.9,
            "reasoning": "Test",
            "suggested_action": "proceed"
        })
        
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = mock_response
            
            await ticket_analysis_service.analyze_ticket(
                sample_ticket_data,
                tenant_id=999
            )
            
            # Verify tenant_id was passed to LLM service
            call_args = mock_chat.call_args
            assert call_args[1]["tenant_id"] == 999
    
    @pytest.mark.asyncio
    async def test_analyze_ticket_uses_tenant_id_from_ticket_data(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that tenant_id from ticket_data is used when parameter not provided"""
        mock_response = json.dumps({
            "classification": "true_positive",
            "confidence": 0.9,
            "reasoning": "Test",
            "suggested_action": "proceed"
        })
        
        with patch.object(
            ticket_analysis_service.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = mock_response
            
            await ticket_analysis_service.analyze_ticket(sample_ticket_data)
            
            # Verify tenant_id from ticket_data was used
            call_args = mock_chat.call_args
            assert call_args[1]["tenant_id"] == 1


class TestParseResponse:
    """Test _parse_response method"""
    
    def test_parse_response_with_valid_json(
        self, ticket_analysis_service
    ):
        """Test parsing valid JSON response"""
        response = json.dumps({
            "classification": "true_positive",
            "confidence": 0.9,
            "reasoning": "Test reasoning",
            "suggested_action": "proceed"
        })
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["classification"] == "true_positive"
        assert result["confidence"] == 0.9
        assert result["reasoning"] == "Test reasoning"
        assert result["suggested_action"] == "proceed"
    
    def test_parse_response_with_markdown_code_block(
        self, ticket_analysis_service
    ):
        """Test parsing JSON wrapped in markdown code block"""
        json_data = json.dumps({
            'classification': 'false_positive',
            'confidence': 0.8,
            'reasoning': 'Test',
            'suggested_action': 'close'
        })
        response = f"```json\n{json_data}\n```"
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["classification"] == "false_positive"
        assert result["confidence"] == 0.8
    
    def test_parse_response_with_invalid_classification(
        self, ticket_analysis_service
    ):
        """Test that invalid classification defaults to uncertain"""
        response = json.dumps({
            "classification": "invalid_value",
            "confidence": 0.9,
            "reasoning": "Test",
            "suggested_action": "proceed"
        })
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["classification"] == "uncertain"
    
    def test_parse_response_with_invalid_confidence(
        self, ticket_analysis_service
    ):
        """Test that invalid confidence is clamped to valid range"""
        response = json.dumps({
            "classification": "true_positive",
            "confidence": 1.5,  # Invalid: > 1.0
            "reasoning": "Test",
            "suggested_action": "proceed"
        })
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["confidence"] == 0.5  # Defaulted to 0.5
    
    def test_parse_response_with_missing_fields(
        self, ticket_analysis_service
    ):
        """Test that missing required fields return default response"""
        response = json.dumps({
            "classification": "true_positive"
            # Missing other fields
        })
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["classification"] == "uncertain"
        assert result["confidence"] == 0.5
        assert "Failed to parse" in result["reasoning"]
    
    def test_parse_response_with_invalid_json(
        self, ticket_analysis_service
    ):
        """Test that invalid JSON returns default response"""
        response = "This is not JSON"
        
        result = ticket_analysis_service._parse_response(response)
        
        assert result["classification"] == "uncertain"
        assert result["confidence"] == 0.5
        assert "Failed to parse" in result["reasoning"]


class TestBuildAnalysisPrompt:
    """Test _build_analysis_prompt method"""
    
    def test_build_analysis_prompt_includes_all_fields(
        self, ticket_analysis_service, sample_ticket_data
    ):
        """Test that prompt includes all ticket fields"""
        prompt = ticket_analysis_service._build_analysis_prompt(sample_ticket_data)
        
        assert "High CPU Usage Alert" in prompt
        assert "CPU usage is above 90%" in prompt
        assert "high" in prompt
        assert "prometheus" in prompt
    
    def test_build_analysis_prompt_handles_missing_fields(
        self, ticket_analysis_service
    ):
        """Test that prompt handles missing optional fields"""
        ticket_data = {
            "title": "Test Ticket"
            # Missing description, severity, source
        }
        
        prompt = ticket_analysis_service._build_analysis_prompt(ticket_data)
        
        assert "Test Ticket" in prompt
        assert "N/A" in prompt  # Default for missing fields

