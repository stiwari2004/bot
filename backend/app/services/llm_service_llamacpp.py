"""
LLM Service using local llama.cpp / Ollama server (OpenAI-compatible API).
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


class LlamaCppLLMService:
    """Service for LLM operations using a local llama.cpp server (OpenAI-compatible API)."""

    def __init__(self, base_url: Optional[str] = None, model_id: Optional[str] = None):
        self.base_url = base_url or os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080")
        self.model_id = model_id or os.getenv("LLAMACPP_MODEL_ID")
        self.client = httpx.AsyncClient(timeout=600.0)

    @staticmethod
    def _normalise_tenant(tenant_id: Optional[int]) -> int:
        return _normalise_tenant(tenant_id)

    async def _ensure_model_id(self) -> str:
        if self.model_id:
            return self.model_id
        try:
            resp = await self.client.get(f"{self.base_url}/v1/models", timeout=10.0)
            if resp.status_code != 200:
                logger.error(f"LLM: failed to fetch models, status={resp.status_code}, body={resp.text[:200]}")
                try:
                    resp = await self.client.get(f"{self.base_url}/api/tags", timeout=10.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        models = data.get("models", [])
                        if models:
                            model_name = models[0].get("name", "llama3.2:latest")
                            if ":" not in model_name:
                                model_name = f"{model_name}:latest"
                            self.model_id = model_name
                            logger.info(f"LLM: detected model '{self.model_id}' from Ollama API")
                            return self.model_id
                except Exception as e2:
                    logger.warning(f"LLM: Ollama API fallback also failed: {e2}")
                raise Exception(f"Failed to fetch models: HTTP {resp.status_code}")

            data = resp.json()
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list) and data["data"]:
                    self.model_id = data["data"][0].get("id")
                if not self.model_id and "models" in data and isinstance(data["models"], list) and data["models"]:
                    self.model_id = data["models"][0].get("model") or data["models"][0].get("name")
            if not self.model_id:
                logger.warning(f"LLM: unable to detect model id from {self.base_url}/v1/models, response keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
                try:
                    resp = await self.client.get(f"{self.base_url}/api/tags", timeout=10.0)
                    if resp.status_code == 200:
                        ollama_data = resp.json()
                        models = ollama_data.get("models", [])
                        if models:
                            model_name = models[0].get("name", "llama3.2:latest")
                            if ":" not in model_name:
                                model_name = f"{model_name}:latest"
                            self.model_id = model_name
                            logger.info(f"LLM: detected model '{self.model_id}' from Ollama API")
                            return self.model_id
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"LLM: error fetching models from {self.base_url} - {e}")

        if not self.model_id:
            self.model_id = "llama3.2:latest"
            logger.warning(f"LLM: using default model '{self.model_id}'")

        return self.model_id

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

    async def _chat_once(self, prompt: str, *, tenant_id: Optional[int] = None) -> str:
        try:
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
                    return choices[0].get("message", {}).get("content", "")
                logger.warning(f"LLM: empty choices from {url}")
            else:
                logger.warning(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"LLM: exception calling chat completions at {self.base_url} - {error_type}: {error_msg}")
            if "ReadTimeout" in error_type or "timeout" in error_msg.lower():
                logger.error("LLM timeout: Request took longer than 600 seconds. Check Ollama status.")
            elif "Connection" in error_type or "connection" in error_msg.lower():
                logger.error(f"LLM connection error: Cannot reach Ollama at {self.base_url}. Ensure Ollama is running.")
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
        os_type: Optional[str] = None,
        issue_type: Optional[str] = None,
        entities: Optional[str] = None,
    ) -> str:
        """Generate agent-executable YAML runbook using POML templates."""
        from app.services.prompt_store import PromptNotFound
        from app.services.poml_parser import POMLParseError

        ctx = context[:4000] if context else ""
        prompt_id = f"runbook_yaml_{service_type}"
        logger.info(f"[PROMPT_LOAD] Loading prompt template: {prompt_id} for service_type={service_type}, os_type={os_type}")

        if not os_type:
            issue_lower = issue_description.lower()
            if any(kw in issue_lower for kw in ["windows", "powershell", "get-process", "get-counter"]):
                os_type = "Windows"
            elif any(kw in issue_lower for kw in ["linux", "ubuntu", "centos", "systemctl", "journalctl"]):
                os_type = "Linux"
            else:
                os_type = env if env in ["Windows", "Linux"] else "Windows"

        prompt_context = {
            "issue_description": issue_description,
            "service": service_type,
            "env": env,
            "risk": risk,
            "context": ctx,
            "issue_type": issue_type or "general_issue",
            "entities": entities or "",
        }
        if service_type == "server":
            prompt_context["os_type"] = os_type or "Windows"

        try:
            rendered = render_prompt(prompt_id, prompt_context)
            logger.info(f"[PROMPT_LOAD] Loaded POML prompt: {prompt_id}")
        except (PromptNotFound, POMLParseError):
            logger.error(f"Service-specific prompt '{prompt_id}' not found or invalid for service_type '{service_type}'.")
            raise ValueError(f"No prompt template found for service type '{service_type}'. Please ensure the prompt file 'runbook_yaml_{service_type}.poml' exists.")

        system_msg = rendered.get("system", "You are a precise YAML generator.")
        user_msg = rendered.get("user", "")
        text = await self._chat_once_with_system(system_msg, user_msg, tenant_id=tenant_id)
        if not text or not text.strip():
            logger.error("LLM returned empty response for YAML generation")
            return ""

        raw = text
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

    async def _chat_once_with_system(
        self,
        system: str,
        user: str,
        *,
        tenant_id: Optional[int] = None,
    ) -> str:
        try:
            model_id = await self._ensure_model_id()
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 2048,
            }
            url = f"{self.base_url}/v1/chat/completions"
            resp = await self.client.post(url, json=payload, timeout=600.0)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    if not text or not text.strip():
                        logger.warning(f"LLM: empty content in response from {url}")
                        return ""
                    return text
                logger.warning(f"LLM: empty choices from {url}")
            else:
                logger.warning(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"LLM: exception calling chat completions at {self.base_url} - {error_type}: {error_msg}")
            if "ReadTimeout" in error_type or "timeout" in error_msg.lower():
                logger.error("LLM timeout: Request took longer than 600 seconds. Check Ollama status.")
            elif "Connection" in error_type or "connection" in error_msg.lower():
                logger.error(f"LLM connection error: Cannot reach Ollama at {self.base_url}. Ensure Ollama is running.")
            return ""
