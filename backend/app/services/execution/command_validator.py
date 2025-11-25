"""
Command validator service for pre-execution validation.
Uses rule-based validation first, then Perplexity web search (grounded in documentation).
"""
import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from app.core.logging import get_logger
from app.services.execution.command_rules import validate_command_with_rules
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)


class CommandValidator:
    """Validates PowerShell commands before execution"""
    
    def __init__(self, llm_service_instance=None):
        """Initialize validator with optional LLM service (Perplexity for web search)"""
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                llm_service = get_llm_service()
                # Check if it's Perplexity (has online model capability)
                if hasattr(llm_service, 'model') and 'online' in getattr(llm_service, 'model', '').lower():
                    self.llm_service = llm_service
                else:
                    # Try to get Perplexity service specifically
                    from app.services.llm_service import PerplexityLLMService
                    import os
                    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
                    if perplexity_key:
                        self.llm_service = PerplexityLLMService(api_key=perplexity_key)
                    else:
                        self.llm_service = llm_service  # Fallback to whatever is available
            except Exception as e:
                logger.warning(f"Could not initialize LLM service: {e}")
                self.llm_service = None
    
    async def validate_command(
        self,
        command: str,
        step_type: str = "main",
        connector_type: str = "local",
        connection_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate command before execution using multiple strategies.
        
        Strategy order:
        1. Rule-based validation (fastest, deterministic, OS-aware)
        2. Perplexity web search validation (grounded in official documentation)
        
        Args:
            command: PowerShell command to validate
            step_type: Type of step (precheck, main, postcheck)
            connector_type: Connector type to detect OS (azure_bastion=Windows, ssh=Linux)
            
        Returns:
            {
                "is_valid": bool,
                "corrected_command": Optional[str],
                "validation_method": str,
                "confidence": float,
                "issues": List[str],
                "suggested_timeout": Optional[int]
            }
        """
        if not command or not command.strip():
            return {
                "is_valid": False,
                "corrected_command": None,
                "validation_method": "rule",
                "confidence": 1.0,
                "issues": ["Command is empty"],
                "suggested_timeout": None,
            }
        
        # Detect OS from connector type
        os_type = "Windows PowerShell" if connector_type in ("azure_bastion", "local") else "Linux/bash"
        
        # Strategy 1: Rule-based validation (fastest, OS-aware)
        logger.debug(f"Validating command with rules (OS: {os_type}): {command[:100]}...")
        rule_result = validate_command_with_rules(command, connector_type, connection_config)
        
        if not rule_result["is_valid"]:
            logger.info(
                f"Rule-based validation found issues: {rule_result.get('issues', [])}, "
                f"suggested correction: {rule_result.get('corrected_command', 'N/A')[:100]}"
            )
            return rule_result
        
        # Strategy 2: Perplexity web search validation (grounded in documentation)
        # Only use if rule-based validation passed (to avoid unnecessary API calls)
        if self.llm_service:
            try:
                logger.debug(f"Validating command with Perplexity web search: {command[:100]}...")
                perplexity_result = await self._validate_via_perplexity(command, step_type, os_type)
                
                # If Perplexity found issues, use its result
                if not perplexity_result.get("is_valid", True):
                    logger.info(
                        f"Perplexity validation found issues: {perplexity_result.get('issues', [])}, "
                        f"suggested correction: {perplexity_result.get('corrected_command', 'N/A')[:100]}"
                    )
                    return perplexity_result
                
                # If Perplexity suggests a timeout, merge it with rule result
                if perplexity_result.get("suggested_timeout"):
                    rule_result["suggested_timeout"] = perplexity_result["suggested_timeout"]
            except Exception as e:
                logger.warning(f"Perplexity validation failed, using rule-based result: {e}")
                # Continue with rule-based result on Perplexity failure
        
        # Rule-based validation passed, command appears valid
        logger.debug(f"Command validation passed: {command[:100]}...")
        return rule_result
    
    async def _validate_via_perplexity(
        self,
        command: str,
        step_type: str,
        os_type: str
    ) -> Dict[str, Any]:
        """
        Validate command using Perplexity web search (grounded in official documentation).
        
        Args:
            command: PowerShell command to validate
            step_type: Type of step
            os_type: OS type (Windows PowerShell or Linux/bash)
            
        Returns:
            Validation result dictionary
        """
        if not self.llm_service:
            return {
                "is_valid": True,
                "corrected_command": None,
                "validation_method": "perplexity",
                "confidence": 0.0,
                "issues": [],
                "suggested_timeout": None,
            }
        
        prompt = f"""Search Microsoft documentation for this {os_type} command and validate its syntax:

Command: {command}

Search official Microsoft PowerShell documentation (docs.microsoft.com) and validate:
1. Missing required parameters (e.g., Get-EventLog needs -LogName on Windows)
2. Invalid parameter names
3. Invalid property names
4. Syntax errors
5. OS-specific issues (e.g., ping -n on Windows vs ping -c on Linux)

Respond with JSON only:
{{
    "is_valid": true/false,
    "issues": ["issue1", "issue2"],
    "corrected_command": "corrected command if invalid, otherwise null",
    "suggested_timeout": null or number in seconds
}}

If the command is valid, set is_valid to true and corrected_command to null.
If invalid, provide the corrected command based on official documentation and list the issues found."""

        try:
            # Use LLM service's chat method (Perplexity with online model)
            if hasattr(self.llm_service, '_chat_once'):
                response = await self.llm_service._chat_once(prompt, tenant_id=1)
            elif hasattr(self.llm_service, '_chat_once_with_system'):
                response = await self.llm_service._chat_once_with_system(
                    "You are a PowerShell command validation assistant. Search official Microsoft documentation to validate commands.",
                    prompt,
                    tenant_id=1,
                )
            else:
                logger.warning("LLM service does not have expected chat methods")
                return {
                    "is_valid": True,
                    "corrected_command": None,
                    "validation_method": "perplexity",
                    "confidence": 0.0,
                    "issues": [],
                    "suggested_timeout": None,
                }
            
            # Parse JSON response
            if not response:
                logger.warning("Perplexity returned empty response")
                return {
                    "is_valid": True,
                    "corrected_command": None,
                    "validation_method": "perplexity",
                    "confidence": 0.0,
                    "issues": [],
                    "suggested_timeout": None,
                }
            
            # Extract JSON from response (might be wrapped in markdown code blocks)
            response_clean = response.strip()
            if "```json" in response_clean:
                json_start = response_clean.find("```json") + 7
                json_end = response_clean.find("```", json_start)
                if json_end > json_start:
                    response_clean = response_clean[json_start:json_end].strip()
            elif "```" in response_clean:
                json_start = response_clean.find("```") + 3
                json_end = response_clean.find("```", json_start)
                if json_end > json_start:
                    response_clean = response_clean[json_start:json_end].strip()
            
            try:
                result = json.loads(response_clean)
            except json.JSONDecodeError:
                # Try to extract JSON object from text
                json_match = re.search(r'\{[^{}]*\}', response_clean)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    logger.warning(f"Could not parse Perplexity response as JSON: {response_clean[:200]}")
                    return {
                        "is_valid": True,
                        "corrected_command": None,
                        "validation_method": "perplexity",
                        "confidence": 0.0,
                        "issues": [],
                        "suggested_timeout": None,
                    }
            
            # Extract validation result
            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            corrected_command = result.get("corrected_command")
            suggested_timeout = result.get("suggested_timeout")
            
            return {
                "is_valid": is_valid,
                "corrected_command": corrected_command if not is_valid else None,
                "validation_method": "perplexity",
                "confidence": 0.8,  # Perplexity web search is more reliable than pure LLM
                "issues": issues if isinstance(issues, list) else [],
                "suggested_timeout": suggested_timeout if isinstance(suggested_timeout, int) else None,
            }
            
        except Exception as e:
            logger.error(f"Error in Perplexity validation: {e}", exc_info=True)
            # Fail-safe: return valid result on error
            return {
                "is_valid": True,
                "corrected_command": None,
                "validation_method": "perplexity",
                "confidence": 0.0,
                "issues": [],
                "suggested_timeout": None,
            }
    

