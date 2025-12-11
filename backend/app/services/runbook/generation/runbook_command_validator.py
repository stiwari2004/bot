"""
Runbook Command Validator - Validates all commands in generated runbooks using web search.
Ensures commands are grounded in documentation and properly classified as remediation vs diagnostic.
"""
import json
import re
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)


class RunbookCommandValidator:
    """Validates all commands in a generated runbook using Perplexity web search for grounding"""
    
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
                logger.warning(f"Could not initialize LLM service for command validation: {e}")
                self.llm_service = None
    
    async def validate_runbook_commands(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        os_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate all commands in runbook using web search grounding.
        
        Args:
            spec: Parsed YAML runbook specification
            issue_description: Original issue description
            os_type: OS type (Windows/Linux) - auto-detected if not provided
            
        Returns:
            {
                "is_valid": bool,
                "invalid_commands": List[Dict],  # Commands that don't exist or have syntax errors
                "diagnostic_mislabeled": List[Dict],  # Commands marked as remediation but are diagnostic
                "missing_remediation": bool,  # True if no actual remediation commands found
                "suggestions": List[str],
                "validation_summary": str
            }
        """
        if not self.llm_service:
            logger.warning("LLM service not available for command validation - skipping web search validation")
            return {
                "is_valid": True,  # Fail open if service unavailable
                "invalid_commands": [],
                "diagnostic_mislabeled": [],
                "missing_remediation": False,
                "suggestions": ["Web search validation unavailable - commands not verified"],
                "validation_summary": "Skipped (service unavailable)"
            }
        
        # Auto-detect OS type if not provided
        if not os_type:
            issue_lower = issue_description.lower()
            if any(kw in issue_lower for kw in ['windows', 'powershell', 'get-process', 'get-counter']):
                os_type = "Windows"
            elif any(kw in issue_lower for kw in ['linux', 'ubuntu', 'centos', 'systemctl', 'journalctl']):
                os_type = "Linux"
            else:
                # Check spec for env field
                env = spec.get("env", "").lower()
                if "windows" in env:
                    os_type = "Windows"
                elif "linux" in env:
                    os_type = "Linux"
                else:
                    os_type = "Windows"  # Default
        
        # Detect issue type from description
        issue_type = self._detect_issue_type(issue_description)
        
        invalid_commands = []
        diagnostic_mislabeled = []
        remediation_commands_found = []
        
        # Validate prechecks
        prechecks = spec.get("prechecks", [])
        for idx, precheck in enumerate(prechecks):
            if isinstance(precheck, dict):
                command = precheck.get("command", "").strip()
                if command:
                    validation = await self._validate_command_existence(command, os_type)
                    if not validation["exists"]:
                        invalid_commands.append({
                            "section": "precheck",
                            "index": idx + 1,
                            "command": command,
                            "issue": validation.get("issue", "Command not found in documentation"),
                            "suggested_fix": validation.get("suggested_command")
                        })
        
        # Validate main steps (critical - these must be remediation)
        steps = spec.get("steps", [])
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            
            command = step.get("command", "").strip()
            if not command:
                continue
            
            step_name = step.get("name", f"Step {idx + 1}")
            purpose = step.get("purpose", "").lower()
            
            # Check 1: Command exists and syntax is valid
            existence_validation = await self._validate_command_existence(command, os_type)
            if not existence_validation["exists"]:
                invalid_commands.append({
                    "section": "steps",
                    "index": idx + 1,
                    "name": step_name,
                    "command": command,
                    "issue": existence_validation.get("issue", "Command not found in documentation"),
                    "suggested_fix": existence_validation.get("suggested_command")
                })
                continue
            
            # Check 2: If marked as remediation, verify it's actually remediation
            is_marked_remediation = (
                purpose == "remediate" or
                "remediate" in step_name.lower() or
                "fix" in step_name.lower() or
                "kill" in step_name.lower() or
                "restart" in step_name.lower()
            )
            
            if is_marked_remediation:
                remediation_validation = await self._validate_remediation_command(
                    command, issue_type, os_type
                )
                
                if not remediation_validation["is_remediation"]:
                    diagnostic_mislabeled.append({
                        "section": "steps",
                        "index": idx + 1,
                        "name": step_name,
                        "command": command,
                        "issue": f"Command marked as remediation but is actually diagnostic: {remediation_validation.get('explanation', '')}",
                        "suggested_fix": remediation_validation.get("suggested_remediation")
                    })
                elif not remediation_validation.get("can_fix_issue", False):
                    diagnostic_mislabeled.append({
                        "section": "steps",
                        "index": idx + 1,
                        "name": step_name,
                        "command": command,
                        "issue": f"Remediation command exists but cannot fix {issue_type}: {remediation_validation.get('explanation', '')}",
                        "suggested_fix": remediation_validation.get("suggested_remediation")
                    })
                else:
                    remediation_commands_found.append({
                        "index": idx + 1,
                        "name": step_name,
                        "command": command
                    })
        
        # Validate postchecks
        postchecks = spec.get("postchecks", [])
        for idx, postcheck in enumerate(postchecks):
            if isinstance(postcheck, dict):
                command = postcheck.get("command", "").strip()
                if command:
                    validation = await self._validate_command_existence(command, os_type)
                    if not validation["exists"]:
                        invalid_commands.append({
                            "section": "postcheck",
                            "index": idx + 1,
                            "command": command,
                            "issue": validation.get("issue", "Command not found in documentation"),
                            "suggested_fix": validation.get("suggested_command")
                        })
        
        # Determine if runbook is valid
        # Require at least MIN_REMEDIATION_STEPS and REMEDIATION_RATIO
        from app.config.runbook_config import runbook_structure
        min_remediation = runbook_structure.MIN_REMEDIATION_STEPS
        remediation_ratio = runbook_structure.REMEDIATION_RATIO
        total_steps = len(steps)
        
        # Check both minimum count and ratio
        remediation_count_ok = len(remediation_commands_found) >= min_remediation
        remediation_ratio_ok = (len(remediation_commands_found) / total_steps) >= remediation_ratio if total_steps > 0 else False
        
        missing_remediation = not (remediation_count_ok and remediation_ratio_ok)
        has_invalid_commands = len(invalid_commands) > 0
        has_mislabeled = len(diagnostic_mislabeled) > 0
        
        is_valid = not (has_invalid_commands or has_mislabeled or missing_remediation)
        
        # Build suggestions
        suggestions = []
        if missing_remediation:
            from app.config.runbook_config import runbook_structure
            min_remediation = runbook_structure.MIN_REMEDIATION_STEPS
            remediation_ratio = runbook_structure.REMEDIATION_RATIO * 100
            current_ratio = (len(remediation_commands_found) / total_steps * 100) if total_steps > 0 else 0.0
            suggestions.append(
                f"CRITICAL: Only {len(remediation_commands_found)} remediation command(s) found. "
                f"Need at least {min_remediation} remediation steps AND at least {remediation_ratio:.0f}% of steps must be remediation. "
                f"Runbook must include actual fix actions (kill, restart, stop, clear, etc.), not just diagnostics. "
                f"Current: {len(remediation_commands_found)}/{total_steps} steps are remediation ({current_ratio:.0f}%)."
            )
        if has_invalid_commands:
            suggestions.append(
                f"Found {len(invalid_commands)} invalid command(s) that don't exist or have syntax errors. "
                f"These commands will fail during execution."
            )
        if has_mislabeled:
            suggestions.append(
                f"Found {len(diagnostic_mislabeled)} command(s) marked as remediation but are actually diagnostic. "
                f"These won't fix the issue."
            )
        
        validation_summary = (
            f"Validated {len(steps)} steps: "
            f"{len(remediation_commands_found)} remediation, "
            f"{len(invalid_commands)} invalid, "
            f"{len(diagnostic_mislabeled)} mislabeled"
        )
        
        return {
            "is_valid": is_valid,
            "invalid_commands": invalid_commands,
            "diagnostic_mislabeled": diagnostic_mislabeled,
            "missing_remediation": missing_remediation,
            "remediation_commands_found": remediation_commands_found,
            "suggestions": suggestions,
            "validation_summary": validation_summary
        }
    
    async def _validate_command_existence(
        self,
        command: str,
        os_type: str
    ) -> Dict[str, Any]:
        """
        Validate that a command exists and has correct syntax via web search.
        
        Returns:
            {
                "exists": bool,
                "issue": str (if not exists),
                "suggested_command": Optional[str]
            }
        """
        if not self.llm_service:
            return {"exists": True, "issue": None, "suggested_command": None}
        
        shell_type = "PowerShell" if os_type == "Windows" else "bash/Linux shell"
        
        prompt = f"""Search official documentation to validate this {shell_type} command exists and has correct syntax:

Command: {command}

Search official Microsoft documentation (docs.microsoft.com for Windows) or Linux man pages and respond with JSON:
{{
    "exists": true/false,
    "is_valid_syntax": true/false,
    "issue": "description of problem if invalid, null if valid",
    "suggested_command": "corrected command if invalid, null if valid"
}}

Check for:
1. Command/commandlet exists (e.g., Get-Process exists, Get-Proces does not)
2. Required parameters are present
3. Parameter names are correct
4. Syntax is valid for the OS

If the command is valid, set exists=true, is_valid_syntax=true, issue=null, suggested_command=null."""

        try:
            response = await self._call_llm(prompt)
            if not response:
                return {"exists": True, "issue": None, "suggested_command": None}  # Fail open
            
            result = self._parse_json_response(response)
            if not result:
                return {"exists": True, "issue": None, "suggested_command": None}
            
            exists = result.get("exists", True)
            is_valid = result.get("is_valid_syntax", True)
            
            if not exists or not is_valid:
                return {
                    "exists": False,
                    "issue": result.get("issue", "Command not found or invalid syntax"),
                    "suggested_command": result.get("suggested_command")
                }
            
            return {"exists": True, "issue": None, "suggested_command": None}
            
        except Exception as e:
            logger.warning(f"Error validating command existence: {e}")
            return {"exists": True, "issue": None, "suggested_command": None}  # Fail open
    
    async def _validate_remediation_command(
        self,
        command: str,
        issue_type: str,
        os_type: str
    ) -> Dict[str, Any]:
        """
        Validate that a command marked as remediation actually fixes issues.
        
        Returns:
            {
                "is_remediation": bool,
                "is_diagnostic": bool,
                "can_fix_issue": bool,
                "explanation": str,
                "suggested_remediation": Optional[str]
            }
        """
        if not self.llm_service:
            return {
                "is_remediation": True,  # Fail open
                "is_diagnostic": False,
                "can_fix_issue": True,
                "explanation": "Validation unavailable",
                "suggested_remediation": None
            }
        
        shell_type = "PowerShell" if os_type == "Windows" else "bash/Linux shell"
        
        prompt = f"""Search documentation to determine if this {shell_type} command is a REMEDIATION command (fixes issues) or DIAGNOSTIC command (only gathers information):

Command: {command}
Issue Type: {issue_type}

Search official documentation and respond with JSON:
{{
    "is_remediation": true/false,
    "is_diagnostic": true/false,
    "can_fix_issue": true/false,
    "explanation": "brief explanation",
    "suggested_remediation": "actual remediation command if this is diagnostic, null if this is remediation"
}}

REMEDIATION commands: kill, stop, restart, clear, delete, remove, fix, repair, terminate, shutdown
DIAGNOSTIC commands: get, list, show, display, check, monitor, select, where-object, sort-object

Examples:
- "Get-Process" = diagnostic (gathers info)
- "Stop-Process -Id 1234 -Force" = remediation (kills process)
- "Get-Counter" = diagnostic (monitors metrics)
- "Restart-Service w3svc" = remediation (fixes service)

If the command can fix {issue_type}, set can_fix_issue=true."""

        try:
            response = await self._call_llm(prompt)
            if not response:
                return {
                    "is_remediation": True,
                    "is_diagnostic": False,
                    "can_fix_issue": True,
                    "explanation": "Validation unavailable",
                    "suggested_remediation": None
                }
            
            result = self._parse_json_response(response)
            if not result:
                return {
                    "is_remediation": True,
                    "is_diagnostic": False,
                    "can_fix_issue": True,
                    "explanation": "Could not parse validation result",
                    "suggested_remediation": None
                }
            
            return {
                "is_remediation": result.get("is_remediation", True),
                "is_diagnostic": result.get("is_diagnostic", False),
                "can_fix_issue": result.get("can_fix_issue", True),
                "explanation": result.get("explanation", ""),
                "suggested_remediation": result.get("suggested_remediation")
            }
            
        except Exception as e:
            logger.warning(f"Error validating remediation command: {e}")
            return {
                "is_remediation": True,
                "is_diagnostic": False,
                "can_fix_issue": True,
                "explanation": "Validation error",
                "suggested_remediation": None
            }
    
    def _detect_issue_type(self, issue_description: str) -> str:
        """Detect issue type from description"""
        issue_lower = issue_description.lower()
        
        if any(kw in issue_lower for kw in ["cpu", "processor", "processor time"]):
            return "high CPU usage"
        elif any(kw in issue_lower for kw in ["memory", "ram", "available mbytes"]):
            return "high memory usage"
        elif any(kw in issue_lower for kw in ["disk", "disk space", "free space"]):
            return "low disk space"
        elif any(kw in issue_lower for kw in ["network", "latency", "throughput"]):
            return "network issue"
        elif any(kw in issue_lower for kw in ["service", "daemon", "down", "not running"]):
            return "service down"
        else:
            return "general issue"
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM service with prompt"""
        try:
            if hasattr(self.llm_service, '_chat_once'):
                return await self.llm_service._chat_once(prompt, tenant_id=1)
            elif hasattr(self.llm_service, '_chat_once_with_system'):
                return await self.llm_service._chat_once_with_system(
                    "You are a command validation assistant. Search official documentation to validate commands.",
                    prompt,
                    tenant_id=1,
                )
            else:
                logger.warning("LLM service does not have expected chat methods")
                return None
        except Exception as e:
            logger.error(f"Error calling LLM for validation: {e}")
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
        
        logger.warning(f"Could not parse JSON from response: {response_clean[:200]}")
        return None

