"""
Ticket analysis service - False positive detection
POC version - uses LLM to analyze tickets
"""
import json
from typing import Dict, Optional

from app.core.logging import get_logger
from app.services.llm_budget_manager import LLMBudgetExceeded, LLMRateLimitExceeded

logger = get_logger(__name__)


class TicketAnalysisService:
    """Analyze tickets to determine if they're false positives"""
    
    def __init__(self):
        # Import LLM service dynamically to avoid circular imports
        from app.services.llm_service import get_llm_service
        self.llm_service = get_llm_service()
    
    async def analyze_ticket(self, ticket_data: Dict, tenant_id: Optional[int] = None) -> Dict:
        """
        Analyze ticket to determine if it's a false positive
        
        Returns:
        {
            "classification": "false_positive" | "true_positive" | "uncertain",
            "confidence": 0.0-1.0,
            "reasoning": "explanation",
            "suggested_action": "close" | "proceed" | "review"
        }
        """
        prompt = self._build_analysis_prompt(ticket_data)
        tenant = tenant_id or ticket_data.get("tenant_id") or 1
        
        try:
            # Use _chat_once method which is available on all LLM services
            if hasattr(self.llm_service, '_chat_once'):
                response = await self.llm_service._chat_once(prompt, tenant_id=tenant)
            elif hasattr(self.llm_service, '_chat_once_with_system'):
                response = await self.llm_service._chat_once_with_system(
                    "You are a ticket analysis assistant.",
                    prompt,
                    tenant_id=tenant,
                )
            else:
                # Fallback: try generate_response or use mock
                response = await getattr(self.llm_service, 'generate_response', lambda p: "")(prompt)
            
            # Parse JSON response
            result = self._parse_response(response)
            
            logger.info(f"Ticket analysis result: {result.get('classification')} (confidence: {result.get('confidence')})")
            
            return result
            
        except (LLMRateLimitExceeded, LLMBudgetExceeded) as budget_exc:
            logger.warning("Ticket analysis skipped due to budget/rate limit: %s", budget_exc)
            return {
                "classification": "uncertain",
                "confidence": 0.0,
                "reasoning": str(budget_exc),
                "suggested_action": "review",
            }
        except Exception as e:
            logger.error(f"Error analyzing ticket: {e}")
            # Default to uncertain on error
            return {
                "classification": "uncertain",
                "confidence": 0.0,
                "reasoning": f"Analysis failed: {str(e)}",
                "suggested_action": "review"
            }
    
    def _build_analysis_prompt(self, ticket_data: Dict) -> str:
        """Build prompt for LLM analysis"""
        title = ticket_data.get('title', 'N/A')
        description = ticket_data.get('description', 'N/A')
        severity = ticket_data.get('severity', 'unknown')
        source = ticket_data.get('source', 'unknown')
        
        prompt = f"""Analyze the following monitoring alert/ticket and determine if it's a false positive or a true positive.

Ticket Details:
- Title: {title}
- Description: {description}
- Severity: {severity}
- Source: {source}

False Positive Indicators:
- Expected behavior (scheduled maintenance, backups, etc.)
- Known issues already acknowledged
- Configuration changes that are intentional
- Test/development environments
- Transient network issues that resolve quickly
- Metrics that are expected to fluctuate

True Positive Indicators:
- Unexpected errors or failures
- Service degradation or downtime
- Resource exhaustion (CPU, memory, disk)
- Authentication/authorization failures
- Data corruption or loss
- Security alerts

Respond with a JSON object with the following structure:
{{
    "classification": "false_positive" | "true_positive" | "uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of your analysis",
    "suggested_action": "close" | "proceed" | "review"
}}

Only respond with the JSON object, no additional text."""
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response JSON"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate structure
            required_fields = ["classification", "confidence", "reasoning", "suggested_action"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate classification
            if result["classification"] not in ["false_positive", "true_positive", "uncertain"]:
                result["classification"] = "uncertain"
            
            # Validate confidence
            confidence = float(result["confidence"])
            if confidence < 0.0 or confidence > 1.0:
                confidence = 0.5
            result["confidence"] = confidence
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}, response: {response}")
            # Return default uncertain response
            return {
                "classification": "uncertain",
                "confidence": 0.5,
                "reasoning": f"Failed to parse response: {str(e)}",
                "suggested_action": "review"
            }

