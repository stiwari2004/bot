"""
Command corrector service for post-execution command correction.
Uses rule-based corrections first, then Perplexity web search as fallback.
"""
import json
import re
from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.services.execution.command_rules import correct_command_with_rules
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)


class CommandCorrector:
    """Corrects failed commands using hybrid approach (rules + LLM)"""
    
    def __init__(self, llm_service_instance=None):
        """Initialize corrector with optional LLM service (Perplexity for web search)"""
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
    
    async def correct_command(
        self,
        command: str,
        error_text: str,
        step_type: str = "main",
        connector_type: str = "local",
        connection_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Correct command using hybrid approach (rules first, Perplexity web search fallback).
        
        Args:
            command: Original command that failed
            error_text: Error message from execution
            step_type: Type of step (precheck, main, postcheck)
            connector_type: Connector type to detect OS (azure_bastion=Windows, ssh=Linux)
            
        Returns:
            {
                "corrected_command": str,
                "correction_method": "rule"|"perplexity",
                "confidence": float,
                "explanation": str
            }
        """
        if not command or not error_text:
            return {
                "corrected_command": None,
                "correction_method": "none",
                "confidence": 0.0,
                "explanation": "Missing command or error text",
            }
        
        # Detect OS from connector type
        os_type = "Windows PowerShell" if connector_type in ("azure_bastion", "local") else "Linux/bash"
        
        # Strategy 1: Rule-based correction (fast, deterministic, OS-aware)
        logger.debug(f"Attempting rule-based correction for {os_type}: {command[:100]}...")
        rule_result = correct_command_with_rules(command, error_text, connector_type, connection_config)
        
        if rule_result:
            corrected_command, rule_name = rule_result
            logger.info(f"Rule-based correction applied: {rule_name}")
            return {
                "corrected_command": corrected_command,
                "correction_method": "rule",
                "confidence": 0.9,
                "explanation": f"Applied rule: {rule_name}",
            }
        
        # Strategy 2: Perplexity web search correction (fallback for unknown patterns)
        if self.llm_service:
            try:
                logger.debug(f"Attempting Perplexity-based correction for {os_type}: {command[:100]}...")
                perplexity_result = await self._apply_perplexity_correction(command, error_text, step_type, os_type)
                
                if perplexity_result.get("corrected_command"):
                    logger.info("Perplexity-based correction applied")
                    return perplexity_result
            except Exception as e:
                logger.warning(f"Perplexity correction failed: {e}")
        
        # No correction found
        logger.warning(f"Could not correct command: {command[:100]}...")
        return {
            "corrected_command": None,
            "correction_method": "none",
            "confidence": 0.0,
            "explanation": "No correction rules matched and Perplexity correction failed",
        }
    
    async def _apply_perplexity_correction(
        self,
        command: str,
        error_text: str,
        step_type: str,
        os_type: str
    ) -> Dict[str, Any]:
        """
        Correct command using Perplexity web search (grounded in official documentation).
        
        Args:
            command: Original command that failed
            error_text: Error message from execution
            step_type: Type of step
            os_type: OS type (Windows PowerShell or Linux/bash)
            
        Returns:
            Correction result dictionary
        """
        if not self.llm_service:
            return {
                "corrected_command": None,
                "correction_method": "perplexity",
                "confidence": 0.0,
                "explanation": "Perplexity service not available",
            }
        
        prompt = f"""Search Microsoft documentation for this {os_type} command that failed and provide the corrected command.

Original Command: {command}
Error Message: {error_text}

Search official Microsoft PowerShell documentation (docs.microsoft.com) and provide the corrected command.
Common issues to check:
- Missing required parameters (e.g., Get-EventLog needs -LogName System on Windows)
- Invalid property names
- OS-specific syntax (e.g., ping -n on Windows vs ping -c on Linux)
- Syntax errors
- Parameter typos

Respond with JSON only:
{{
    "corrected_command": "corrected command based on official documentation",
    "explanation": "brief explanation of what was fixed"
}}

If you cannot determine a correction, set corrected_command to null."""

        try:
            # Use LLM service's chat method (Perplexity with online model)
            if hasattr(self.llm_service, '_chat_once'):
                response = await self.llm_service._chat_once(prompt, tenant_id=1)
            elif hasattr(self.llm_service, '_chat_once_with_system'):
                response = await self.llm_service._chat_once_with_system(
                    "You are a PowerShell command correction assistant. Search official Microsoft documentation to provide accurate corrections.",
                    prompt,
                    tenant_id=1,
                )
            else:
                logger.warning("LLM service does not have expected chat methods")
                return {
                    "corrected_command": None,
                    "correction_method": "perplexity",
                    "confidence": 0.0,
                    "explanation": "Perplexity service method not available",
                }
            
            # Parse JSON response
            if not response:
                logger.warning("Perplexity returned empty response")
                return {
                    "corrected_command": None,
                    "correction_method": "perplexity",
                    "confidence": 0.0,
                    "explanation": "Perplexity returned empty response",
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
                        "corrected_command": None,
                        "correction_method": "perplexity",
                        "confidence": 0.0,
                        "explanation": "Could not parse Perplexity response",
                    }
            
            # Extract correction result
            corrected_command = result.get("corrected_command")
            explanation = result.get("explanation", "Perplexity suggested correction based on official documentation")
            
            if corrected_command:
                return {
                    "corrected_command": corrected_command,
                    "correction_method": "perplexity",
                    "confidence": 0.8,  # Perplexity web search is more reliable than pure LLM
                    "explanation": explanation,
                }
            else:
                return {
                    "corrected_command": None,
                    "correction_method": "perplexity",
                    "confidence": 0.0,
                    "explanation": "Perplexity could not determine correction",
                }
            
        except Exception as e:
            logger.error(f"Error in Perplexity correction: {e}", exc_info=True)
            return {
                "corrected_command": None,
                "correction_method": "perplexity",
                "confidence": 0.0,
                "explanation": f"Perplexity correction error: {str(e)}",
            }

