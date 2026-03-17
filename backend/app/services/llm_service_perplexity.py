"""
LLM Service using Perplexity API.
"""
import json
import os
from typing import Any, Dict, Optional

import httpx

from app.core.logging import get_logger
from app.services.prompt_store import render_prompt

logger = get_logger(__name__)


def _normalise_tenant(tenant_id: Optional[int]) -> int:
    try:
        return int(tenant_id or 1)
    except Exception:
        return 1


class PerplexityLLMService:
    """Service for LLM operations using Perplexity API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-sonar-large-128k-online"):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        self.base_url = "https://api.perplexity.ai"
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout_sec = float(os.getenv("PERPLEXITY_TIMEOUT", "120").strip() or "120")
        timeout_sec = max(30.0, min(300.0, timeout_sec))
        self._timeout = timeout_sec
        self.client = httpx.AsyncClient(timeout=timeout_sec, headers=self.headers)

    async def classify_service_type(self, issue_description: str, *, tenant_id: Optional[int] = None) -> str:
        prompt = (
            f"Classify this IT issue into one of: server, network, database, web, storage.\n"
            f"server=CPU/memory/disk, network=connectivity/DNS, database=DB queries, web=HTTP/APIs, storage=NAS/SAN\n"
            f"Issue: \"{issue_description}\"\nRespond with ONE WORD only."
        )
        text = await self._chat_once(prompt, tenant_id=_normalise_tenant(tenant_id))
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
        text = await self._chat_once(prompt, tenant_id=_normalise_tenant(tenant_id))
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
        os_type: Optional[str] = None,
        issue_type: Optional[str] = None,
        entities: Optional[str] = None,
    ) -> str:
        """Generate YAML runbook using Perplexity with POML templates."""
        from app.services.prompt_store import PromptNotFound
        from app.services.poml_parser import POMLParseError

        ctx = context[:4000] if context else ""
        prompt_id = f"runbook_yaml_{service_type}"

        prompt_context = {
            "issue_description": issue_description,
            "service": service_type,
            "env": env,
            "risk": risk,
            "context": ctx,
            "issue_type": issue_type or "general_issue",
            "entities": entities or "",
        }
        if service_type == "server" and os_type:
            prompt_context["os_type"] = os_type

        try:
            rendered = render_prompt(prompt_id, prompt_context)
        except (PromptNotFound, POMLParseError):
            logger.error(f"Service-specific prompt '{prompt_id}' not found or invalid for service_type '{service_type}'.")
            raise ValueError(f"No prompt template found for service type '{service_type}'. Please ensure the prompt file 'runbook_yaml_{service_type}.poml' exists.")

        system_msg = rendered.get("system", "You are a precise YAML generator.")
        user_msg = rendered.get("user", "")
        raw = await self._chat_once_with_system(system_msg, user_msg, tenant_id=tenant_id)

        if raw and "```" in raw:
            lines = raw.strip().split("\n")
            start_idx, end_idx = 0, len(lines)
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
        return await self._chat_once_with_system("You are a helpful assistant.", prompt, tenant_id=tenant_id)

    async def _chat_once_with_system(
        self,
        system: str,
        user: str,
        *,
        tenant_id: Optional[int] = None,
    ) -> str:
        """Make a chat completion request to Perplexity API. One retry on timeout."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        for attempt in range(2):
            try:
                resp = await self.client.post(url, json=payload, timeout=self._timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices") or []
                    if choices:
                        return (choices[0].get("message", {}) or {}).get("content", "") or ""
                    logger.warning(f"Perplexity: empty choices from {url}")
                else:
                    logger.error(f"Perplexity: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
                return ""
            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                logger.warning(f"Perplexity: timeout on attempt {attempt + 1}/2 (timeout={self._timeout}s) - {e}")
                if attempt == 0:
                    continue
                return ""
            except Exception as e:
                logger.error(f"Perplexity: exception calling API - {e}")
                return ""
        return ""
