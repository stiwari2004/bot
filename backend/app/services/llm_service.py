"""
LLM Service for AI-powered runbook generation using llama.cpp or Perplexity.
Uses POML templates for runbook prompts. Supports both local llama.cpp server and Perplexity API.
"""
import os
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.llm_service_llamacpp import LlamaCppLLMService
from app.services.llm_service_perplexity import PerplexityLLMService

logger = get_logger(__name__)

# Global LLM service instance
llm_service: Optional[Any] = None


class MockLLMService:
    """Mock LLM service for when a real LLM backend is not available."""

    async def classify_service_type(self, issue_description: str) -> str:
        issue_lower = issue_description.lower()
        if any(word in issue_lower for word in ["database", "db", "mysql", "postgres"]):
            return "database"
        elif any(word in issue_lower for word in ["web", "http", "website", "api"]):
            return "web"
        elif any(word in issue_lower for word in ["network", "connectivity", "dns", "ping"]):
            return "network"
        elif any(word in issue_lower for word in ["storage", "nas", "san", "disk"]):
            return "storage"
        return "server"

    async def generate_runbook_content(
        self, issue_description: str, service_type: str, env: str = "prod", risk: str = "low"
    ) -> Dict[str, Any]:
        return {
            "root_cause": f"Analysis needed for {service_type} issue",
            "steps": [{"name": "Initial Assessment", "command": "Check system status", "expected_output": "System operational"}],
            "verification": ["Verify issue is resolved"],
            "recommendations": ["Monitor system performance"],
        }


def get_llm_service():
    """Get or create the global LLM service instance.

    Priority:
    1. Gemini 2.0 Flash (if GEMINI_API_KEY is set) — recommended for accuracy
    2. Ollama/Llama (fallback if LLAMACPP_BASE_URL is set)

    Perplexity is only used for command validation/verification (via RunbookCommandValidator).
    """
    global llm_service

    if llm_service is None:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key.strip():
            try:
                from app.services.llm_service_gemini import GeminiLLMService
                model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                llm_service = GeminiLLMService(api_key=gemini_api_key, model=model)
                logger.info(f"Using Google Gemini LLM service (model: {model})")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}. Falling back to Ollama.")
                logger.exception("Gemini initialization error details:", exc_info=True)
                llm_service = LlamaCppLLMService()
                logger.info("Using llama.cpp LLM service (fallback)")
        else:
            llm_service = LlamaCppLLMService()
            logger.info("Using llama.cpp LLM service (no GEMINI_API_KEY set or empty)")

    return llm_service
