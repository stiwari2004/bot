"""
Google Gemini 2.5 Flash LLM Service using official google-genai SDK.
Uses POML templates for runbook prompts. Optimized for accurate runbook generation with shorter, contextual prompts.
Supports model priority selection based on complexity.
"""
import os
import json
import yaml
from typing import Optional, Any
from google import genai
from google.genai import types
from app.core.logging import get_logger
from app.services.prompt_store import render_prompt, PromptNotFound
from app.services.poml_parser import POMLParseError
from app.services.model_selector import ModelSelector

logger = get_logger(__name__)


class GeminiLLMService:
    """Service for LLM operations using Google Gemini API with model priority selection."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini LLM service.
        
        Args:
            api_key: Google AI API key (from GEMINI_API_KEY env var)
            model: Optional fixed model to use. If None, will use dynamic selection based on complexity.
                Available models:
                - gemini-2.0-flash-exp (free tier, fast - default for simple cases)
                - gemini-2.5-flash (free tier, stable - for moderate complexity)
                - gemini-2.5-pro (paid tier, highest quality - for complex cases)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Get it from https://aistudio.google.com/apikey"
            )
        
        self.client = genai.Client(api_key=self.api_key)
        # If model is explicitly provided, use it; otherwise will be selected dynamically
        # Default uses n-1 strategy: stable gemini-2.5-flash (not experimental)
        self.default_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_selector = ModelSelector()
        
        # Check if using free tier for default model
        is_free_tier = "flash" in self.default_model.lower() and "pro" not in self.default_model.lower()
        logger.info(f"Initialized Gemini LLM service with default model: {self.default_model} (free_tier: {is_free_tier})")
    
    @staticmethod
    def _normalise_tenant(tenant_id: Optional[int]) -> int:
        try:
            return int(tenant_id or 1)
        except Exception:
            return 1
    
    @staticmethod
    def _convert_json_to_yaml_if_needed(text: str) -> str:
        """
        Convert JSON response to YAML if the response is JSON format.
        If the response is already YAML or plain text, return as-is.
        """
        text = text.strip()
        
        # Check if text looks like JSON (starts with { or [)
        if text.startswith('{') or text.startswith('['):
            try:
                # Try to parse as JSON
                json_data = json.loads(text)
                # Convert JSON to YAML
                yaml_output = yaml.dump(json_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
                logger.info("Gemini: Converted JSON response to YAML")
                return yaml_output.strip()
            except json.JSONDecodeError:
                # Not valid JSON, return as-is
                logger.debug("Gemini: Response looks like JSON but failed to parse, returning as-is")
                return text
        else:
            # Not JSON, return as-is (likely already YAML or plain text)
            return text
    
    async def _chat_once_with_system(
        self,
        system: str,
        user: str,
        *,
        tenant_id: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Chat with system and user prompts using Gemini API."""
        tenant = self._normalise_tenant(tenant_id)
        
        # Use provided model or default
        model_to_use = model_name or self.default_model
        
        try:
            # Combine system and user into a single prompt (Gemini works well with this)
            # For better results, we can use system instruction separately if needed
            combined_prompt = f"{system}\n\n{user}"
            
            # Create content with user message
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=combined_prompt),
                    ],
                ),
            ]
            
            # Configure generation with optimal settings for YAML generation
            # Note: ThinkingConfig may not be available in all SDK versions
            generate_content_config = types.GenerateContentConfig(
                temperature=0.2,  # Lower for more consistent YAML
                max_output_tokens=8192,  # Increased for longer YAML
                top_p=0.95,
                top_k=40,
            )
            
            # Stream response and collect all chunks
            # Note: generate_content_stream is synchronous, so we run it in a thread
            import asyncio
            
            def _stream_response():
                """Synchronous function to stream response"""
                full_response = ""
                try:
                    for chunk in self.client.models.generate_content_stream(
                        model=model_to_use,
                        contents=contents,
                        config=generate_content_config,
                    ):
                        if chunk.text:
                            full_response += chunk.text
                except Exception as e:
                    logger.error(f"Gemini streaming error: {e}")
                    raise
                return full_response
            
            # Run synchronous streaming in thread pool with timeout (5 minutes max)
            try:
                full_response = await asyncio.wait_for(
                    asyncio.to_thread(_stream_response),
                    timeout=300.0  # 5 minute timeout for Gemini API calls
                )
            except asyncio.TimeoutError:
                logger.error(f"Gemini API call timed out after 5 minutes for model {model_to_use}")
                raise TimeoutError("Gemini API call timed out. The request took longer than 5 minutes.")
            
            if not full_response or not full_response.strip():
                logger.warning("Gemini: empty content in response")
                return ""
            
            # Check if response is JSON and convert to YAML if needed
            response_text = full_response.strip()
            yaml_response = self._convert_json_to_yaml_if_needed(response_text)
            
            return yaml_response
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                logger.error("Gemini: Rate limit or quota exceeded. Consider upgrading to paid tier.")
            elif "api_key" in str(e).lower() or "authentication" in str(e).lower():
                logger.error("Gemini: Invalid API key. Check GEMINI_API_KEY environment variable.")
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
        model_name: Optional[str] = None,
    ) -> str:
        """
        Generate YAML runbook using Gemini with optimized prompts.
        
        Args:
            model_name: Optional model name. If None, will be selected based on complexity.
        """
        # Limit context to keep prompts shorter (Gemini handles context well but shorter = faster)
        ctx = context[:500] if context else ""  # Reduced from 800 to 500
        
        prompt_id = f"runbook_yaml_{service_type}"
        logger.info(f"[GEMINI] Loading prompt: {prompt_id} for service_type={service_type}, os_type={os_type}")
        
        # Determine OS type if not provided
        if not os_type:
            issue_lower = issue_description.lower()
            if any(kw in issue_lower for kw in ['windows', 'powershell', 'get-process', 'get-counter']):
                os_type = "Windows"
            elif any(kw in issue_lower for kw in ['linux', 'ubuntu', 'centos', 'systemctl', 'journalctl']):
                os_type = "Linux"
            else:
                os_type = env if env in ["Windows", "Linux"] else "Windows"
        
        # Select model based on complexity if not explicitly provided
        if model_name is None:
            model_name = self.model_selector.select_model(
                issue_description=issue_description,
                risk=risk,
                service_type=service_type,
                issue_length=len(issue_description)
            )
            logger.info(f"[GEMINI] Selected model: {model_name} for issue complexity")
        else:
            logger.info(f"[GEMINI] Using explicitly provided model: {model_name}")
        
        # Build prompt context
        prompt_context = {
            "issue_description": issue_description,
            "service": service_type,
            "env": env,
            "risk": risk,
            "context": ctx,
        }
        
        # Only add os_type for server CI types
        if service_type == "server":
            prompt_context["os_type"] = os_type or "Windows"
        
        try:
            rendered = render_prompt(prompt_id, prompt_context)
        except (PromptNotFound, POMLParseError):
            logger.error(f"Prompt '{prompt_id}' not found or invalid for service type '{service_type}'")
            raise ValueError(f"No prompt template found for service type '{service_type}'. Please ensure the prompt file 'runbook_yaml_{service_type}.poml' exists in the prompts directory.")
        
        system_msg = rendered.get("system", "You are a precise YAML generator.")
        user_msg = rendered.get("user", "")
        
        # For Gemini, we can combine system and user more efficiently
        # Gemini handles longer prompts well, but we'll keep it contextual
        return await self._chat_once_with_system(
            system=system_msg,
            user=user_msg,
            tenant_id=tenant_id,
            model_name=model_name,
        )
    
    async def classify_service_type(
        self,
        issue_description: str,
        *,
        tenant_id: Optional[int] = None,
    ) -> str:
        """Classify service type using Gemini."""
        system = "You are a service classifier. Classify the issue into one of: server, network, database, web, storage, or auto. Respond with only the category name."
        user = f"Classify this issue: {issue_description}"
        
        result = await self._chat_once_with_system(system, user, tenant_id=tenant_id)
        result = result.strip().lower()
        
        valid_types = ["server", "network", "database", "web", "storage", "auto"]
        if result in valid_types:
            return result
        return "auto"

