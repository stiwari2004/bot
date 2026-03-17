"""
Mixin: LLM-based command validation helpers for RunbookCommandValidator
"""
import json
import re
from typing import Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class CommandValidatorLLMMixin:
    """LLM-based validation helpers for RunbookCommandValidator."""

    async def _validate_command_existence(
        self,
        command: str,
        os_type: str
    ) -> Dict[str, Any]:
        """Validate that a command exists and has correct syntax via web search."""
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
                return {"exists": True, "issue": None, "suggested_command": None}
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
            return {"exists": True, "issue": None, "suggested_command": None}

    async def _validate_remediation_command(
        self,
        command: str,
        issue_type: str,
        os_type: str
    ) -> Dict[str, Any]:
        """Validate that a command marked as remediation actually fixes issues."""
        if not self.llm_service:
            return {
                "is_remediation": True,
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
        """Detect issue type from description using phrase-level matching."""
        from app.services.runbook.generation.service_classifier import ServiceClassifier
        classifier = ServiceClassifier()
        service = classifier.classify_service_type(issue_description)
        issue_type = classifier.detect_issue_type(issue_description, service)
        _labels = {
            "high_cpu": "high CPU usage",
            "high_memory": "high memory usage",
            "low_disk": "low disk space",
            "service_down": "service down",
            "host_unreachable": "host unreachable",
            "db_slow_query": "slow database query",
            "db_connection_failure": "database connection failure",
            "db_disk_full": "database disk full",
            "db_deadlock": "database deadlock",
            "db_replication_lag": "database replication lag",
            "web_5xx": "web 5xx error",
            "web_high_latency": "web high latency",
            "web_cert_expired": "web certificate expired",
            "web_service_down": "web service down",
            "dns_failure": "DNS failure",
            "firewall_block": "firewall blocking traffic",
            "interface_down": "network interface down",
            "high_network_latency": "high network latency",
            "network_unreachable": "network unreachable",
            "stale_mount": "stale NFS mount",
            "nfs_mount_failure": "NFS mount failure",
            "storage_full": "storage full",
            "storage_access_denied": "storage access denied",
        }
        return _labels.get(issue_type, "general issue")

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM service with prompt."""
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
        """Parse JSON from LLM response (handles markdown code blocks)."""
        if not response:
            return None
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
            return json.loads(response_clean)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_clean)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        logger.warning(f"Could not parse JSON from response: {response_clean[:200]}")
        return None
