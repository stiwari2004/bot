"""
Lightweight LLM-based ticket classification service.

Only invoked for Tier 2 runbook generation (no existing runbook match).
Runs concurrently with RAG hybrid search via asyncio.gather() so the
classification latency is hidden behind the search round-trip.

Returns a TicketClassification with:
  - service / issue_type / os_type  (routing signals)
  - hosts / ips / service_names / ports  (concrete entities from the ticket)

Falls back to ServiceClassifier (regex phrase-matching) on any LLM error so
the pipeline never blocks.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TicketClassification:
    service: str                                     # server | database | web | network | storage
    issue_type: str                                  # high_cpu | host_unreachable | db_deadlock | …
    os_type: Optional[str] = None                   # Windows | Linux | None
    hosts: List[str] = field(default_factory=list)  # hostnames / server names
    ips: List[str] = field(default_factory=list)    # IP addresses
    service_names: List[str] = field(default_factory=list)  # nginx, mysql, …
    ports: List[str] = field(default_factory=list)  # port numbers
    confidence: float = 0.0
    fallback_used: bool = False                      # True when regex fallback was used

    def format_entities(self) -> str:
        """
        Return a compact human-readable entity string for POML injection.
        Returns empty string when nothing was extracted (so POML output stays clean).
        """
        parts: List[str] = []
        if self.hosts:
            parts.append(f"Hosts: {', '.join(self.hosts[:4])}")
        if self.ips:
            parts.append(f"IPs: {', '.join(self.ips[:4])}")
        if self.service_names:
            parts.append(f"Services: {', '.join(self.service_names[:4])}")
        if self.ports:
            parts.append(f"Ports: {', '.join(self.ports[:4])}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Inline fallback prompt (used when ticket_classify.poml is not found)
# ---------------------------------------------------------------------------

_INLINE_SYSTEM = (
    "You are an IT ticket classifier. Extract structured information from incident descriptions. "
    "Return ONLY a JSON object — no markdown fences, no explanation."
)

_INLINE_USER_TMPL = """TICKET:
{description}

Classify this ticket and extract all mentioned entities. Return JSON exactly:
{{
  "service": "server|database|web|network|storage",
  "issue_type": "high_cpu|high_memory|low_disk|service_down|host_unreachable|db_slow_query|db_connection_failure|db_disk_full|db_deadlock|db_replication_lag|web_5xx|web_high_latency|web_cert_expired|web_service_down|dns_failure|firewall_block|interface_down|high_network_latency|network_unreachable|stale_mount|nfs_mount_failure|storage_full|storage_access_denied|general_issue",
  "os_type": "Windows|Linux|null",
  "hosts": ["all hostnames and server names mentioned"],
  "ips": ["all IP addresses mentioned"],
  "service_names": ["application/service names e.g. nginx, mysql, apache"],
  "ports": ["port numbers mentioned"],
  "confidence": 0.0
}}"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TicketClassifierService:
    """
    Lightweight LLM classification for Tier 2 runbook generation.

    Usage in runbook_generator_core.py (Tier 2 branch):
        classification, search_results = await asyncio.gather(
            self.ticket_classifier.classify(issue_description, tenant_id),
            self.vector_service.hybrid_search(...),
        )
    """

    async def classify(
        self,
        description: str,
        tenant_id: int,
    ) -> TicketClassification:
        """
        Classify a ticket. Always returns a result — falls back to regex on error.
        """
        try:
            result = await self._llm_classify(description, tenant_id)
            if result is not None:
                logger.info(
                    "LLM ticket classification: service=%s issue_type=%s os=%s "
                    "hosts=%s confidence=%.2f",
                    result.service, result.issue_type, result.os_type,
                    result.hosts, result.confidence,
                )
                return result
        except Exception as exc:
            logger.warning("LLM ticket classification failed, using regex fallback: %s", exc)

        return await self._regex_fallback(description)

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    async def _llm_classify(
        self,
        description: str,
        tenant_id: int,
    ) -> Optional[TicketClassification]:
        from app.services.llm_service import get_llm_service
        from app.services.prompt_store import render_prompt, PromptNotFound

        llm = get_llm_service()

        try:
            rendered = render_prompt("ticket_classify", {"description": description})
            system_msg = rendered["system"]
            user_msg = rendered["user"]
        except (PromptNotFound, Exception):
            system_msg = _INLINE_SYSTEM
            user_msg = _INLINE_USER_TMPL.format(description=description[:2000])

        raw = await llm._chat_once_with_system(system_msg, user_msg, tenant_id=tenant_id)
        if not raw:
            return None

        data = _parse_json(raw)
        if not data:
            logger.warning("Could not parse JSON from classification response")
            return None

        return TicketClassification(
            service=_validated_service(data.get("service")),
            issue_type=data.get("issue_type") or "general_issue",
            os_type=_validated_os(data.get("os_type")),
            hosts=_str_list(data.get("hosts")),
            ips=_str_list(data.get("ips")),
            service_names=_str_list(data.get("service_names")),
            ports=_str_list(data.get("ports")),
            confidence=float(data.get("confidence", 0.8)),
            fallback_used=False,
        )

    # ------------------------------------------------------------------
    # Regex fallback
    # ------------------------------------------------------------------

    async def _regex_fallback(self, description: str) -> TicketClassification:
        from app.services.runbook.generation.service_classifier import ServiceClassifier
        classifier = ServiceClassifier()
        service = classifier.classify_service_type(description)
        issue_type = classifier.detect_issue_type(description, service)
        os_type = await classifier.detect_os_type(description)
        return TicketClassification(
            service=service,
            issue_type=issue_type,
            os_type=os_type,
            confidence=0.5,
            fallback_used=True,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SERVICES = {"server", "database", "web", "network", "storage"}
_VALID_OS = {"Windows", "Linux"}


def _validated_service(value: object) -> str:
    if isinstance(value, str) and value in _VALID_SERVICES:
        return value
    return "server"


def _validated_os(value: object) -> Optional[str]:
    if isinstance(value, str) and value in _VALID_OS:
        return value
    return None


def _str_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if v and str(v).strip()]
    return []


def _parse_json(text: str) -> Optional[dict]:
    """Extract and parse the first JSON object from LLM response."""
    text = text.strip()
    # Strip markdown fences if present
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first {...} block
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None
