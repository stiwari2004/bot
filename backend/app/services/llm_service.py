"""
LLM Service for AI-powered runbook generation using Hugging Face models.
Supports both Hugging Face Inference API and local transformers models.
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from app.services.prompt_store import render_prompt
import torch

class HuggingFaceLLMService:
    """Service for LLM operations using Hugging Face models."""
    
    def __init__(self, use_inference_api: bool = True, model_name: str = "microsoft/DialoGPT-medium"):
        """
        Initialize the LLM service.
        
        Args:
            use_inference_api: If True, use HF Inference API. If False, use local transformers.
            model_name: Model name for local inference (ignored if use_inference_api=True)
        """
        self.use_inference_api = use_inference_api
        self.model_name = model_name
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        
        if use_inference_api:
            if not self.api_token:
                raise ValueError("HUGGINGFACE_API_TOKEN environment variable is required for Inference API")
            self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
            self.headers = {"Authorization": f"Bearer {self.api_token}"}
        else:
            # Initialize local model
            self._load_local_model()
    
    def _load_local_model(self):
        """Load the local transformers model."""
        try:
            print(f"Loading local model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            print("Local model loaded successfully")
        except Exception as e:
            print(f"Error loading local model: {e}")
            raise
    
    async def classify_service_type(self, issue_description: str) -> str:
        """
        Classify the service type from issue description using LLM.
        
        Args:
            issue_description: The issue description to classify
            
        Returns:
            One of: 'server', 'network', 'database', 'web', 'storage'
        """
        prompt = f"""
        Classify this IT issue into one of these service types:
        - server: General server performance, CPU, memory, local disk issues
        - network: Network connectivity, DNS, routing, firewall issues  
        - database: Database performance, queries, connections, DB-specific issues
        - web: Web applications, HTTP errors, API issues, web server problems
        - storage: External storage systems (NAS, SAN, network storage)
        
        Issue: "{issue_description}"
        
        Respond with only the service type (one word):
        """
        
        if self.use_inference_api:
            response = await self._call_inference_api(prompt)
        else:
            response = await self._call_local_model(prompt)
        
        # Extract service type from response
        response_lower = response.lower().strip()
        service_types = ['server', 'network', 'database', 'web', 'storage']
        
        for service_type in service_types:
            if service_type in response_lower:
                return service_type
        
        # Default fallback
        return 'server'
    
    async def generate_runbook_content(self, issue_description: str, service_type: str, env: str = "prod", risk: str = "low") -> Dict[str, Any]:
        """
        Generate runbook content using LLM.
        
        Args:
            issue_description: The issue description
            service_type: Detected service type
            env: Environment (prod, staging, dev)
            risk: Risk level (low, medium, high)
            
        Returns:
            Dictionary with generated runbook content
        """
        prompt = f"""
        Generate a detailed troubleshooting runbook for this IT issue:
        
        Issue: "{issue_description}"
        Service Type: {service_type}
        Environment: {env}
        Risk Level: {risk}
        
        Provide a structured response with:
        1. Root cause analysis
        2. Step-by-step troubleshooting steps
        3. Commands to run
        4. Expected outputs
        5. Verification steps
        6. Prevention recommendations
        
        Format as JSON with these keys:
        - root_cause: string
        - steps: array of objects with name, command, expected_output
        - verification: array of verification steps
        - recommendations: array of prevention tips
        """
        
        if self.use_inference_api:
            response = await self._call_inference_api(prompt)
        else:
            response = await self._call_local_model(prompt)
        
        # Try to parse JSON response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to structured text parsing
            return self._parse_text_response(response)
    
    async def _call_inference_api(self, prompt: str) -> str:
        """Call Hugging Face Inference API."""
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 500,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
                return str(result)
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return "Error: API call failed"
                
        except Exception as e:
            print(f"Error calling Inference API: {e}")
            return "Error: API call failed"
    
    async def _call_local_model(self, prompt: str) -> str:
        """Call local transformers model."""
        try:
            # Tokenize input
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=500,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the input prompt from response
            if prompt in response:
                response = response.replace(prompt, "").strip()
            
            return response
            
        except Exception as e:
            print(f"Error calling local model: {e}")
            return "Error: Local model call failed"
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse text response into structured format."""
        return {
            "root_cause": "AI-generated analysis",
            "steps": [
                {
                    "name": "Step 1",
                    "command": "Check system status",
                    "expected_output": "System operational"
                }
            ],
            "verification": ["Verify issue is resolved"],
            "recommendations": ["Monitor system performance"]
        }


# Global LLM service instance (initialized after class definitions)
llm_service: Optional[Any] = None

class LlamaCppLLMService:
    """Service for LLM operations using a local llama.cpp server (OpenAI-compatible API)."""

    def __init__(self, base_url: Optional[str] = None, model_id: Optional[str] = None):
        # If backend runs inside Docker on macOS, host is reachable via host.docker.internal
        self.base_url = base_url or os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080")
        self.model_id = model_id or os.getenv("LLAMACPP_MODEL_ID")

    def _ensure_model_id(self) -> str:
        if self.model_id:
            return self.model_id
        try:
            resp = requests.get(f"{self.base_url}/v1/models", timeout=10)
            data = resp.json()
            # Prefer OpenAI style: data[].id; fallback to models[].model
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list) and data["data"]:
                    self.model_id = data["data"][0].get("id")
                if not self.model_id and "models" in data and isinstance(data["models"], list) and data["models"]:
                    self.model_id = data["models"][0].get("model") or data["models"][0].get("name")
            if not self.model_id:
                print(f"LLM: unable to detect model id from {self.base_url}/v1/models, response keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        except Exception as e:
            print(f"LLM: error fetching models from {self.base_url} - {e}")
            # Fallback to a sensible default filename if detection fails
            self.model_id = "model.gguf"
        return self.model_id

    async def classify_service_type(self, issue_description: str) -> str:
        prompt = (
            f"Classify this IT issue into one of: server, network, database, web, storage.\n"
            f"server=CPU/memory/disk, network=connectivity/DNS, database=DB queries, web=HTTP/APIs, storage=NAS/SAN\n"
            f"Issue: \"{issue_description}\"\nRespond with ONE WORD only."
        )
        text = await self._chat_once(prompt)
        response_lower = (text or "").lower().strip()
        # Check each type in order of specificity
        for t in ["network", "database", "web", "storage", "server"]:
            if t in response_lower:
                return t
        return "server"

    async def generate_runbook_content(self, issue_description: str, service_type: str, env: str = "prod", risk: str = "low") -> Dict[str, Any]:
        prompt = f"""
        Generate a detailed troubleshooting runbook for this IT issue:

        Issue: "{issue_description}"
        Service Type: {service_type}
        Environment: {env}
        Risk Level: {risk}

        Provide JSON with keys: root_cause, steps (name, command, expected_output),
        verification (array), recommendations (array). Keep it concise and valid JSON.
        """
        text = await self._chat_once(prompt)
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

    async def _chat_once(self, prompt: str) -> str:
        try:
            model_id = self._ensure_model_id()
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
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                print(f"LLM: empty choices from {url}")
            else:
                print(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        except Exception as e:
            print(f"LLM: exception calling chat completions at {self.base_url} - {e}")
            return ""

    async def generate_yaml_runbook(self, *, issue_description: str, service_type: str, env: str, risk: str, context: str = "") -> str:
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
        text = await self._chat_once_with_system(system_msg, user_msg)
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

    async def _chat_once_with_system(self, system: str, user: str) -> str:
        try:
            model_id = self._ensure_model_id()
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 768,
            }
            url = f"{self.base_url}/v1/chat/completions"
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                print(f"LLM: empty choices from {url}")
            else:
                print(f"LLM: non-200 from {url} status={resp.status_code} body={resp.text[:200]}")
            return ""
        except Exception as e:
            print(f"LLM: exception calling chat completions at {self.base_url} - {e}")
            return ""


def get_llm_service() -> LlamaCppLLMService:
    """Get or create the global LLM service instance."""
    global llm_service
    
    if llm_service is None:
        # Always use llama.cpp provider for this POC
        llm_service = LlamaCppLLMService()
    
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

