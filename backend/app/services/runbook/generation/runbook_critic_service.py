"""
Runbook Critic Service - LLM-based critique of generated runbooks for semantic/logical validation.
Validates that runbook steps logically flow and actually solve the issue.
"""
import json
import re
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)


class RunbookCriticService:
    """LLM-based critique of generated runbooks for semantic/logical validation"""
    
    def __init__(self, llm_service_instance=None):
        """Initialize critic with optional LLM service"""
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning(f"Could not initialize LLM service for critique: {e}")
                self.llm_service = None
    
    async def critique_runbook(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        tenant_id: int = 1
    ) -> Dict[str, Any]:
        """
        Ask LLM to critique the runbook as a troubleshooting expert.
        
        Args:
            spec: Parsed YAML runbook specification
            issue_description: Original issue description
            tenant_id: Tenant ID for LLM service
            
        Returns:
            {
                "is_valid": bool,
                "confidence": float,
                "issues": List[str],  # Critical issues found
                "warnings": List[str],  # Minor issues
                "suggestions": List[str],  # Improvement suggestions
                "regeneration_needed": bool  # Should we regenerate?
            }
        """
        if not self.llm_service:
            logger.warning("LLM service not available for critique - skipping")
            return {
                "is_valid": True,  # Fail open
                "confidence": 0.0,
                "issues": [],
                "warnings": ["LLM critique unavailable"],
                "suggestions": [],
                "regeneration_needed": False
            }
        
        # Format runbook for critique
        runbook_summary = self._format_runbook_for_critique(spec)
        
        prompt = f"""You are an expert troubleshooting engineer reviewing a runbook. Analyze this runbook and determine if it will actually solve the issue.

ISSUE: {issue_description}

RUNBOOK:
{runbook_summary}

Analyze the runbook and respond with JSON:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["critical issue 1", "critical issue 2"],
    "warnings": ["minor issue 1", "minor issue 2"],
    "suggestions": ["improvement 1", "improvement 2"],
    "regeneration_needed": true/false
}}

Check for:
1. **Logical Flow**: Do steps flow logically? (e.g., can't kill a process before identifying it)
2. **Variable Dependencies**: If step 3 uses {{variable_name}}, was it captured in step 1 or 2?
3. **Remediation Relevance**: Do remediation steps actually fix the issue type? (e.g., Clear-EventLog won't fix high CPU)
4. **Step Ordering**: Are steps in correct order? (diagnose → remediate → verify)
5. **Missing Steps**: Are critical steps missing? (e.g., no step to identify the problem before fixing it)
6. **Command Appropriateness**: Are commands appropriate for the OS and issue type?
7. **Resolution Path**: Will this runbook actually resolve the issue or just gather data?

CRITICAL ISSUES (set is_valid=false, regeneration_needed=true):
- Steps reference variables that aren't captured
- Remediation steps won't fix the issue type
- Steps are in wrong order (e.g., verify before remediate)
- Missing critical steps (e.g., no step to identify problem before fixing)

WARNINGS (set is_valid=true, regeneration_needed=false):
- Minor ordering issues
- Could use better commands
- Missing optional steps

If the runbook is valid and will solve the issue, set is_valid=true, confidence>=0.8, regeneration_needed=false."""

        try:
            response = await self._call_llm(prompt, tenant_id)
            if not response:
                return {
                    "is_valid": True,
                    "confidence": 0.0,
                    "issues": [],
                    "warnings": ["Could not get critique response"],
                    "suggestions": [],
                    "regeneration_needed": False
                }
            
            result = self._parse_json_response(response)
            if not result:
                return {
                    "is_valid": True,
                    "confidence": 0.0,
                    "issues": [],
                    "warnings": ["Could not parse critique response"],
                    "suggestions": [],
                    "regeneration_needed": False
                }
            
            return {
                "is_valid": result.get("is_valid", True),
                "confidence": float(result.get("confidence", 0.5)),
                "issues": result.get("issues", []) if isinstance(result.get("issues"), list) else [],
                "warnings": result.get("warnings", []) if isinstance(result.get("warnings"), list) else [],
                "suggestions": result.get("suggestions", []) if isinstance(result.get("suggestions"), list) else [],
                "regeneration_needed": result.get("regeneration_needed", False)
            }
            
        except Exception as e:
            logger.error(f"Error in runbook critique: {e}", exc_info=True)
            return {
                "is_valid": True,
                "confidence": 0.0,
                "issues": [],
                "warnings": [f"Critique error: {str(e)}"],
                "suggestions": [],
                "regeneration_needed": False
            }
    
    def _format_runbook_for_critique(self, spec: Dict[str, Any]) -> str:
        """Format runbook spec for critique prompt"""
        lines = []
        lines.append(f"Title: {spec.get('title', 'N/A')}")
        lines.append(f"Service: {spec.get('service', 'N/A')}")
        lines.append(f"Environment: {spec.get('env', 'N/A')}")
        lines.append("")
        
        # Prechecks
        prechecks = spec.get("prechecks", [])
        lines.append("PRECHECKS:")
        for idx, precheck in enumerate(prechecks, 1):
            if isinstance(precheck, dict):
                lines.append(f"  {idx}. {precheck.get('description', 'N/A')}")
                lines.append(f"     Command: {precheck.get('command', 'N/A')}")
        lines.append("")
        
        # Steps
        steps = spec.get("steps", [])
        lines.append("STEPS:")
        for idx, step in enumerate(steps, 1):
            if isinstance(step, dict):
                name = step.get("name", f"Step {idx}")
                purpose = step.get("purpose", "")
                command = step.get("command", "N/A")
                captures = step.get("captures_variable", "")
                depends = step.get("depends_on", [])
                
                lines.append(f"  {idx}. {name}")
                if purpose:
                    lines.append(f"     Purpose: {purpose}")
                lines.append(f"     Command: {command}")
                if captures:
                    lines.append(f"     Captures: {captures}")
                if depends:
                    lines.append(f"     Depends on: {', '.join(depends)}")
        lines.append("")
        
        # Postchecks
        postchecks = spec.get("postchecks", [])
        lines.append("POSTCHECKS:")
        for idx, postcheck in enumerate(postchecks, 1):
            if isinstance(postcheck, dict):
                lines.append(f"  {idx}. {postcheck.get('description', 'N/A')}")
                lines.append(f"     Command: {postcheck.get('command', 'N/A')}")
        
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str, tenant_id: int) -> Optional[str]:
        """Call LLM service with prompt"""
        try:
            if hasattr(self.llm_service, '_chat_once'):
                return await self.llm_service._chat_once(prompt, tenant_id=tenant_id)
            elif hasattr(self.llm_service, '_chat_once_with_system'):
                return await self.llm_service._chat_once_with_system(
                    "You are an expert troubleshooting engineer. Review runbooks for logical flow and effectiveness.",
                    prompt,
                    tenant_id=tenant_id,
                )
            else:
                logger.warning("LLM service does not have expected chat methods")
                return None
        except Exception as e:
            logger.error(f"Error calling LLM for critique: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response (handles markdown code blocks)"""
        if not response:
            return None
        
        response_clean = response.strip()
        
        # Extract JSON from markdown code blocks
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
        
        # Try to extract JSON object
        try:
            return json.loads(response_clean)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_clean)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        logger.warning(f"Could not parse JSON from critique response: {response_clean[:200]}")
        return None







