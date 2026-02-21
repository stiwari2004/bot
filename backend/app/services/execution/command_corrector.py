"""
Command corrector service for post-execution command correction.
Uses DB learnings first (no hardcoded rules), then Perplexity web search with OS-aware prompts.
"""
import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.execution.command_learning_service import CommandLearningService
from app.services.execution.ssh_command_utils import strip_ssh_wrapper
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)


def _detect_os_from_connector(connector_type: str) -> str:
    """Detect os_type from connector."""
    if connector_type in ("azure_bastion", "local", "winrm"):
        return "windows"
    elif connector_type in ("ssh", "gcp_iap"):
        return "linux"
    return "windows"


class CommandCorrector:
    """Corrects failed commands using DB learnings + Perplexity (no hardcoded rules)."""

    def __init__(self, llm_service_instance=None):
        """Initialize corrector with optional LLM service (Perplexity for web search)."""
        self.learning_service = CommandLearningService()
        if llm_service_instance:
            self.llm_service = llm_service_instance
        else:
            try:
                llm_service = get_llm_service()
                if hasattr(llm_service, "model") and "online" in getattr(llm_service, "model", "").lower():
                    self.llm_service = llm_service
                else:
                    from app.services.llm_service import PerplexityLLMService
                    import os
                    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
                    if perplexity_key:
                        self.llm_service = PerplexityLLMService(api_key=perplexity_key)
                    else:
                        self.llm_service = llm_service
            except Exception as e:
                logger.warning(f"Could not initialize LLM service: {e}")
                self.llm_service = None

    async def correct_command(
        self,
        command: str,
        error_text: str,
        step_type: str = "main",
        connector_type: str = "local",
        connection_config: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Correct command using DB learnings first, then Perplexity (OS-aware, no hardcoded rules).

        Returns:
            {
                "corrected_command": str | None,
                "correction_method": "db_learning" | "perplexity" | "none",
                "confidence": float,
                "explanation": str,
                "learning_id": int | None  # For updating on success
            }
        """
        if not command or not error_text:
            return {
                "corrected_command": None,
                "correction_method": "none",
                "confidence": 0.0,
                "explanation": "Missing command or error text",
                "learning_id": None,
            }

        # Strip ssh host "cmd" wrapper - we correct the raw command
        command_raw = strip_ssh_wrapper(command)
        os_type_str = "Windows PowerShell" if _detect_os_from_connector(connector_type) == "windows" else "Linux/bash"

        # Strategy 1: DB lookup (similar past fixes, no hardcoded rules)
        if db is not None and tenant_id is not None:
            similar = self.learning_service.find_similar_fix(
                db, tenant_id, command_raw, error_text, connector_type
            )
            if similar and similar.get("fix_applied"):
                logger.info(f"DB learning correction applied for {os_type_str}")
                return {
                    "corrected_command": similar["fix_applied"],
                    "correction_method": "db_learning",
                    "confidence": 0.9 if similar.get("success_after_fix") else 0.75,
                    "explanation": f"Applied similar past fix (source={similar.get('fix_source', 'db_learning')})",
                    "learning_id": similar.get("learning_id"),
                }

        # Strategy 2: Perplexity web search (OS-aware: Linux man pages, Windows Microsoft docs)
        if self.llm_service:
            try:
                perplexity_result = await self._apply_perplexity_correction(
                    command_raw, error_text, step_type, connector_type
                )
                if perplexity_result.get("corrected_command"):
                    perplexity_result["learning_id"] = perplexity_result.get("learning_id")
                    return perplexity_result
            except Exception as e:
                logger.warning(f"Perplexity correction failed: {e}")

        return {
            "corrected_command": None,
            "correction_method": "none",
            "confidence": 0.0,
            "explanation": "No DB learning matched and Perplexity correction failed",
            "learning_id": None,
        }

    async def _apply_perplexity_correction(
        self,
        command: str,
        error_text: str,
        step_type: str,
        connector_type: str,
    ) -> Dict[str, Any]:
        """Correct command using Perplexity with OS-aware documentation sources."""
        if not self.llm_service:
            return {
                "corrected_command": None,
                "correction_method": "perplexity",
                "confidence": 0.0,
                "explanation": "Perplexity service not available",
                "learning_id": None,
            }

        is_linux = connector_type in ("ssh", "gcp_iap")
        if is_linux:
            doc_instructions = """Search Linux/bash documentation:
- man pages (man7.org, linux.die.net)
- systemctl, journalctl, systemd documentation
- bash syntax (gnu.org)
- Common Linux commands: top, ps, free, df, systemctl status, journalctl
- Strip any ssh host "..." wrapper - return the raw command only (connector handles connection)"""
            system_msg = (
                "You are a Linux/bash command correction assistant. Search official Linux man pages "
                "and documentation to provide accurate corrections. Return raw commands without ssh prefixes."
            )
        else:
            doc_instructions = """Search Microsoft documentation (docs.microsoft.com):
- PowerShell cmdlets: Get-Process, Get-Counter, Get-EventLog, etc.
- Missing required parameters (e.g., Get-EventLog -LogName System)
- Invalid property names, syntax errors
- OS-specific syntax (e.g., ping -n on Windows vs ping -c on Linux)"""
            system_msg = (
                "You are a PowerShell command correction assistant. Search official Microsoft documentation "
                "to provide accurate corrections."
            )

        prompt = f"""Search official documentation for this command that failed and provide the corrected command.

Original Command: {command}
Error Message: {error_text}

{doc_instructions}

Respond with JSON only:
{{
    "corrected_command": "corrected command based on official documentation (raw command, no ssh wrapper)",
    "explanation": "brief explanation of what was fixed"
}}

If you cannot determine a correction, set corrected_command to null."""

        try:
            if hasattr(self.llm_service, "_chat_once"):
                response = await self.llm_service._chat_once(prompt, tenant_id=1)
            elif hasattr(self.llm_service, "_chat_once_with_system"):
                response = await self.llm_service._chat_once_with_system(
                    system_msg, prompt, tenant_id=1
                )
            else:
                return {
                    "corrected_command": None,
                    "correction_method": "perplexity",
                    "confidence": 0.0,
                    "explanation": "Perplexity service method not available",
                    "learning_id": None,
                }

            if not response:
                return {
                    "corrected_command": None,
                    "correction_method": "perplexity",
                    "confidence": 0.0,
                    "explanation": "Perplexity returned empty response",
                    "learning_id": None,
                }

            response_clean = response.strip()
            if "```json" in response_clean:
                js = response_clean.find("```json") + 7
                je = response_clean.find("```", js)
                if je > js:
                    response_clean = response_clean[js:je].strip()
            elif "```" in response_clean:
                js = response_clean.find("```") + 3
                je = response_clean.find("```", js)
                if je > js:
                    response_clean = response_clean[js:je].strip()

            try:
                result = json.loads(response_clean)
            except json.JSONDecodeError:
                m = re.search(r"\{[^{}]*\}", response_clean)
                result = json.loads(m.group(0)) if m else {}
            corrected_command = result.get("corrected_command")
            explanation = result.get("explanation", "Perplexity suggested correction")

            if corrected_command:
                # Ensure no ssh wrapper in correction
                corrected_command = strip_ssh_wrapper(corrected_command)
                return {
                    "corrected_command": corrected_command,
                    "correction_method": "perplexity",
                    "confidence": 0.8,
                    "explanation": explanation,
                    "learning_id": None,
                }
            return {
                "corrected_command": None,
                "correction_method": "perplexity",
                "confidence": 0.0,
                "explanation": "Perplexity could not determine correction",
                "learning_id": None,
            }
        except Exception as e:
            logger.error(f"Error in Perplexity correction: {e}", exc_info=True)
            return {
                "corrected_command": None,
                "correction_method": "perplexity",
                "confidence": 0.0,
                "explanation": str(e),
                "learning_id": None,
            }
