"""
LLM Service for AI-powered runbook generation using llama.cpp or Perplexity.
Supports both local llama.cpp server and Perplexity API.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx

from app.core.logging import get_logger
from app.services.prompt_store import render_prompt
from app.services.llm_budget_manager import (
    LLMBudgetExceeded,
    LLMRateLimitExceeded,
    budget_manager,
    estimate_tokens,
)

logger = get_logger(__name__)


# Global LLM service instance (initialized after class definitions)
llm_service: Optional[Any] = None

class LlamaCppLLMService:
    """Service for LLM operations using a local llama.cpp server (OpenAI-compatible API)."""

    def __init__(self, base_url: Optional[str] = None, model_id: Optional[str] = None):
        # If backend runs inside Docker on macOS, host is reachable via host.docker.internal
        self.base_url = base_url or os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080")
        self.model_id = model_id or os.getenv("LLAMACPP_MODEL_ID")
        # Create async HTTP client with longer timeout for generation tasks
        self.client = httpx.AsyncClient(timeout=120.0)

    @staticmethod
    def _normalise_tenant(tenant_id: Optional[int]) -> int:
        try:
            return int(tenant_id or 1)
        except Exception:
            return 1

    async def _ensure_model_id(self) -> str:
        if self.model_id:
            return self.model_id
        try:
            resp = await self.client.get(f"{self.base_url}/v1/models", timeout=10.0)
            data = resp.json()
            # Prefer OpenAI style: data[].id; fallback to models[].model
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list) and data["data"]:
                    self.model_id = data["data"][0].get("id")
                if not self.model_id and "models" in data and isinstance(data["models"], list) and data["models"]:
                    self.model_id = data["models"][0].get("model") or data["models"][0].get("name")
            if not self.model_id:
                logger.warning(f"LLM: unable to detect model id from {self.base_url}/v1/models, response keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        except Exception as e:
            logger.warning(f"LLM: error fetching models from {self.base_url} - {e}")
            # Fallback to a sensible default filename if detection fails
            self.model_id = "model.gguf"
        return self.model_id

    async def classify_service_type(self, issue_description: str, *, tenant_id: Optional[int] = None) -> str:
        prompt = (
            f"Classify this IT issue into one of: server, network, database, web, storage.\n"
            f"server=CPU/memory/disk, network=connectivity/DNS, database=DB queries, web=HTTP/APIs, storage=NAS/SAN\n"
            f"Issue: \"{issue_description}\"\nRespond with ONE WORD only."
        )
        text = await self._chat_once(prompt, tenant_id=self._normalise_tenant(tenant_id))
        response_lower = (text or "").lower().strip()
        # Check each type in order of specificity
        for t in ["network", "database", "web", "storage", "server"]:
            if t in response_lower:
                return t
        return "server"

    async def generate_runbook_content(
        self,
        issue_description: str,
        service_type: str,
        env: str = "prod",
        risk: str = "low",
        *,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        prompt = f"""
        Generate a detailed troubleshooting runbook for this IT issue:

        Issue: "{issue_description}"
        Service Type: {service_type}
        Environment: {env}
        Risk Level: {risk}

        Provide JSON with keys: root_cause, steps (name, command, expected_output),
        verification (array), recommendations (array). Keep it concise and valid JSON.
        """
        text = await self._chat_once(prompt, tenant_id=self._normalise_tenant(tenant_id))
        try:
            return json.loads(text)
        except Exception:
            return {
                "root_cause": "AI-generated analysis",
                "steps": [
                    {"name": "Initial Assessment", "command": "Check system status", "expected_output": "System operational"}
                ],
                "verification": ["Verify issue is resolved"],
                "recommendations": ["Monitor system performance"],
            }

    async def _chat_once(self, prompt: str, *, tenant_id: Optional[int] = None) -> str:
        tenant = self._normalise_tenant(tenant_id)
        try:
            # Token counting disabled for now
            # prompt_tokens = estimate_tokens(prompt)
            # await budget_manager.charge_tokens(
            #     tenant_id=tenant,
            #     tokens=prompt_tokens,
            #     direction="prompt",
            # )
            model_id = await self._ensure_model_id()
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a concise troubleshooting assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 512,
            }
            url = f"{self.base_url}/v1/chat/completions"
            resp = await self.client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    # Token counting disabled for now
                    # completion_tokens = estimate_tokens(text)
                    # if completion_tokens:
                    #     await budget_manager.charge_tokens(
                    #         tenant_id=tenant,
                    #         tokens=completion_tokens,
                    #         direction="completion",
                    #     )
                    return text
                logger.warning(f"LLM: empty choices from {url}")
            else:
                logger.warning(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        # Budget exceptions disabled - token counting is disabled
        # except (LLMRateLimitExceeded, LLMBudgetExceeded):
        #     raise
        except Exception as e:
            logger.error(f"LLM: exception calling chat completions at {self.base_url} - {type(e).__name__}: {e}")
            return ""
    
    async def generate_yaml_runbook(
        self,
        *,
        tenant_id: int,
        issue_description: str,
        service_type: str,
        env: str,
        risk: str,
        context: str = "",
    ) -> str:
        """Ask the model to return an agent-executable YAML runbook following our schema.
        Uses centralized prompt templates (TOML) via prompt_store.
        """
        ctx = context[:800] if context else ""
        rendered = render_prompt(
            "runbook_yaml_v1",
            {
                "issue_description": issue_description,
                "service": service_type,
                "env": env,
                "risk": risk,
                "context": ctx,
            },
        )
        system_msg = rendered.get("system", "You are a precise YAML generator.")
        user_msg = rendered.get("user", "")

        # Call chat with explicit system + user messages
        text = await self._chat_once_with_system(system_msg, user_msg, tenant_id=tenant_id)
        raw = text
        # Post-process: strip any remaining code fences
        if raw and "```" in raw:
            # Remove markdown code fences if present
            lines = raw.strip().split("\n")
            start_idx = 0
            end_idx = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    if i == 0 or "yaml" in line.lower():
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            raw = "\n".join(lines[start_idx:end_idx]).strip()
        return raw

    async def _chat_once_with_system(
        self,
        system: str,
        user: str,
        *,
        tenant_id: Optional[int] = None,
    ) -> str:
        tenant = self._normalise_tenant(tenant_id)
        try:
            # Token counting disabled for now
            # prompt_tokens = estimate_tokens(system) + estimate_tokens(user)
            # await budget_manager.charge_tokens(
            #     tenant_id=tenant,
            #     tokens=prompt_tokens,
            #     direction="prompt",
            # )
            model_id = await self._ensure_model_id()
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 2048,  # Increased to allow for 10-12 steps with full details
            }
            url = f"{self.base_url}/v1/chat/completions"
            resp = await self.client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    # Token counting disabled for now
                    # completion_tokens = estimate_tokens(text)
                    # if completion_tokens:
                    #     await budget_manager.charge_tokens(
                    #         tenant_id=tenant,
                    #         tokens=completion_tokens,
                    #         direction="completion",
                    #     )
                    return text
                logger.warning(f"LLM: empty choices from {url}")
            else:
                logger.warning(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        # Budget exceptions disabled - token counting is disabled
        # except (LLMRateLimitExceeded, LLMBudgetExceeded):
        #     raise
        except Exception as e:
            logger.error(f"LLM: exception calling chat completions at {self.base_url} - {type(e).__name__}: {e}")
            return ""


class PerplexityLLMService:
    """Service for LLM operations using Perplexity API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-sonar-large-128k-online"):
        """
        Initialize Perplexity LLM service.
        
        Args:
            api_key: Perplexity API key (from PERPLEXITY_API_KEY env var)
            model: Model to use - options:
                - llama-3.1-sonar-large-128k-online (recommended, $0.50/M input, $2.25/M output)
                - llama-3.1-sonar-small-128k-online (cheaper, $0.20/M input, $1.00/M output)
                - llama-3.1-sonar-huge-128k-online (premium, $1.00/M input, $7.00/M output)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        self.base_url = "https://api.perplexity.ai"
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Create async HTTP client
        self.client = httpx.AsyncClient(timeout=120.0, headers=self.headers)
    
    async def classify_service_type(self, issue_description: str, *, tenant_id: Optional[int] = None) -> str:
        """Classify service type using Perplexity."""
        prompt = (
            f"Classify this IT issue into one of: server, network, database, web, storage.\n"
            f"server=CPU/memory/disk, network=connectivity/DNS, database=DB queries, web=HTTP/APIs, storage=NAS/SAN\n"
            f"Issue: \"{issue_description}\"\nRespond with ONE WORD only."
        )
        text = await self._chat_once(
            prompt,
            tenant_id=LlamaCppLLMService._normalise_tenant(tenant_id),
        )
        response_lower = (text or "").lower().strip()
        for t in ["network", "database", "web", "storage", "server"]:
            if t in response_lower:
                return t
        return "server"
    
    async def generate_runbook_content(
        self,
        issue_description: str,
        service_type: str,
        env: str = "prod",
        risk: str = "low",
        *,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate runbook using Perplexity (deprecated, use generate_yaml_runbook)."""
        prompt = f"""
        Generate a detailed troubleshooting runbook for this IT issue:

        Issue: "{issue_description}"
        Service Type: {service_type}
        Environment: {env}
        Risk Level: {risk}

        Provide JSON with keys: root_cause, steps (name, command, expected_output),
        verification (array), recommendations (array). Keep it concise and valid JSON.
        """
        text = await self._chat_once(
            prompt,
            tenant_id=LlamaCppLLMService._normalise_tenant(tenant_id),
        )
        try:
            return json.loads(text)
        except Exception:
            return {
                "root_cause": "AI-generated analysis",
                "steps": [{"name": "Initial Assessment", "command": "Check system status", "expected_output": "System operational"}],
                "verification": ["Verify issue is resolved"],
                "recommendations": ["Monitor system performance"],
            }
    
    async def generate_yaml_runbook(
        self,
        *,
        tenant_id: int,
        issue_description: str,
        service_type: str,
        env: str,
        risk: str,
        context: str = "",
    ) -> str:
        """Generate YAML runbook using Perplexity with centralized prompts."""
        ctx = context[:800] if context else ""
        rendered = render_prompt(
            "runbook_yaml_v1",
            {
                "issue_description": issue_description,
                "service": service_type,
                "env": env,
                "risk": risk,
                "context": ctx,
            },
        )
        system_msg = rendered.get("system", "You are a precise YAML generator.")
        user_msg = rendered.get("user", "")
        
        text = await self._chat_once_with_system(
            system_msg,
            user_msg,
            tenant_id=tenant_id,
        )
        raw = text
        
        # Post-process: strip any remaining code fences
        if raw and "```" in raw:
            lines = raw.strip().split("\n")
            start_idx = 0
            end_idx = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    if i == 0 or "yaml" in line.lower():
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            raw = "\n".join(lines[start_idx:end_idx]).strip()
        return raw
    
    async def _chat_once(self, prompt: str, *, tenant_id: Optional[int] = None) -> str:
        """Single chat call without system message."""
        return await self._chat_once_with_system(
            "You are a helpful assistant.",
            prompt,
            tenant_id=tenant_id,
        )
    
    async def _chat_once_with_system(
        self,
        system: str,
        user: str,
        *,
        tenant_id: Optional[int] = None,
    ) -> str:
        """Make a chat completion request to Perplexity API."""
        try:
            tenant = LlamaCppLLMService._normalise_tenant(tenant_id)
            # Token counting disabled for now
            # prompt_tokens = estimate_tokens(system) + estimate_tokens(user)
            # await budget_manager.charge_tokens(
            #     tenant_id=tenant,
            #     tokens=prompt_tokens,
            #     direction="prompt",
            # )
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 4096,  # Perplexity supports up to 4096 tokens for sonar models
            }
            url = f"{self.base_url}/chat/completions"
            resp = await self.client.post(url, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    # Token counting disabled for now
                    # completion_tokens = estimate_tokens(text)
                    # if completion_tokens:
                    #     await budget_manager.charge_tokens(
                    #         tenant_id=tenant,
                    #         tokens=completion_tokens,
                    #         direction="completion",
                    #     )
                    return text
                logger.warning(f"Perplexity: empty choices from {url}")
            else:
                logger.error(f"Perplexity: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        # Budget exceptions disabled - token counting is disabled
        # except (LLMRateLimitExceeded, LLMBudgetExceeded):
        #     raise
        except Exception as e:
            logger.error(f"Perplexity: exception calling API - {e}")
            return ""


def get_llm_service() -> LlamaCppLLMService:
    """Get or create the global LLM service instance."""
    global llm_service
    
    if llm_service is None:
        # Check if Perplexity API key is set
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if perplexity_api_key:
            try:
                llm_service = PerplexityLLMService(api_key=perplexity_api_key)
                logger.info("Using Perplexity LLM service")
            except Exception as e:
                logger.warning(f"Failed to initialize Perplexity: {e}, falling back to llama.cpp")
                llm_service = LlamaCppLLMService()
        else:
            # Use llama.cpp as default for this POC
            llm_service = LlamaCppLLMService()
            logger.info("Using llama.cpp LLM service")
    
    return llm_service


class MockLLMService:
    """Mock LLM service for when Hugging Face is not available."""
    
    async def classify_service_type(self, issue_description: str) -> str:
        """Fallback classification using keyword matching."""
        issue_lower = issue_description.lower()
        
        if any(word in issue_lower for word in ['database', 'db', 'mysql', 'postgres']):
            return 'database'
        elif any(word in issue_lower for word in ['web', 'http', 'website', 'api']):
            return 'web'
        elif any(word in issue_lower for word in ['network', 'connectivity', 'dns', 'ping']):
            return 'network'
        elif any(word in issue_lower for word in ['storage', 'nas', 'san', 'disk']):
            return 'storage'
        else:
            return 'server'
    
    async def generate_runbook_content(self, issue_description: str, service_type: str, env: str = "prod", risk: str = "low") -> Dict[str, Any]:
        """Fallback runbook generation."""
        return {
            "root_cause": f"Analysis needed for {service_type} issue",
            "steps": [
                {
                    "name": "Initial Assessment",
                    "command": "Check system status",
                    "expected_output": "System operational"
                }
            ],
            "verification": ["Verify issue is resolved"],
            "recommendations": ["Monitor system performance"]
        }

