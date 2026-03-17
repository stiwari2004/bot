"""
Mixin: private helper methods for RunbookGeneratorService
"""
from typing import List, Dict, Any, Optional

from app.schemas.search import SearchResult
from app.core.logging import get_logger

logger = get_logger(__name__)

# Keyword lists for diagnostic detection (mirrors constants in runbook_generator_core)
_REMEDIATION_KEYWORDS = [
    "stop-process", "restart-service", "kill", "systemctl restart",
    "clear", "delete", "remove", "fix", "repair", "resolve", "restart", "stop"
]
_DIAGNOSTIC_KEYWORDS = [
    "get-process", "get-counter", "get-service", "get-eventlog",
    "top", "ps", "free", "df", "select-object", "where-object", "sort-object"
]


class RunbookGeneratorHelpersMixin:
    """Private helper methods for RunbookGeneratorService."""

    def _detect_and_flag_diagnostic_only(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Post-processing: detect diagnostic-only step sequences and flag if remediation is missing."""
        steps = spec.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 3:
            return spec

        remediation_count = 0
        diagnostic_only_count = 0

        for step in steps:
            if not isinstance(step, dict):
                continue
            cmd = str(step.get("command", "")).lower()
            name = str(step.get("name", "")).lower()
            has_remediation = any(kw in cmd or kw in name for kw in _REMEDIATION_KEYWORDS)
            is_diagnostic = any(kw in cmd or kw in name for kw in _DIAGNOSTIC_KEYWORDS)
            if has_remediation:
                remediation_count += 1
            elif is_diagnostic:
                diagnostic_only_count += 1

        if remediation_count < 2:
            logger.warning(
                f"Post-processing detected diagnostic-heavy runbook: "
                f"{remediation_count} remediation steps, {diagnostic_only_count} diagnostic-only steps. "
                f"Runbook may need manual review."
            )
            if "meta_data" not in spec:
                spec["meta_data"] = {}
            if isinstance(spec["meta_data"], dict):
                spec["meta_data"]["diagnostic_heavy"] = True
                spec["meta_data"]["remediation_count"] = remediation_count
                spec["meta_data"]["diagnostic_count"] = diagnostic_only_count

        return spec

    def _format_runbook_context(self, search_results: List[SearchResult], issue_type: str) -> str:
        """Format retrieved runbooks and documents into structured context for the generation prompt."""
        if not search_results:
            return "No similar runbooks or documents found."

        def _is_document(result: SearchResult) -> bool:
            src = getattr(result, "document_source", "") or ""
            return str(src).lower() == "document"

        runbook_results = [r for r in search_results if not _is_document(r)]
        document_results = [r for r in search_results if _is_document(r)]
        issue_token = issue_type.replace("_", " ").lower()

        def _is_issue_match(result: SearchResult) -> bool:
            text = (result.text or "").lower()
            title = (result.document_title or "").lower()
            return issue_token in text or issue_token in title

        def _golden_tag(result: SearchResult) -> str:
            try:
                import json as _json
                meta = result.meta_data if hasattr(result, "meta_data") else {}
                if isinstance(meta, str):
                    meta = _json.loads(meta)
                if isinstance(meta, dict) and meta.get("golden_example"):
                    tag = f" ✓ PROVEN ({meta.get('success_count', 1)}x"
                    avg = meta.get("avg_resolution_minutes")
                    if avg:
                        tag += f", avg {avg:.0f}min"
                    return tag + ")"
            except Exception:
                pass
            return ""

        def _rank_key(result: SearchResult):
            is_golden = bool(_golden_tag(result))
            return (not is_golden, not _is_issue_match(result), -result.score)

        context_parts = []
        ranked = sorted(runbook_results[:6], key=_rank_key)
        for i, result in enumerate(ranked[:3], 1):
            title = result.document_title or "Untitled Runbook"
            match_tag = " [issue match]" if _is_issue_match(result) else ""
            header = f"[Runbook] {i}: {title} (similarity: {result.score:.2f}{_golden_tag(result)}{match_tag})"
            context_parts.append(header)
            snippet = (result.text or "").strip()[:600]
            if snippet:
                context_parts.append(f"  {snippet}")
            context_parts.append("")

        if document_results:
            context_parts.append("Document knowledge (reference only):")
            for i, result in enumerate(document_results[:4], 1):
                title = result.document_title or "Untitled Document"
                snippet = (result.text or "").strip()[:400]
                if snippet:
                    context_parts.append(f"  [Document] {i}: {title} (similarity: {result.score:.2f})")
                    context_parts.append(f"    {snippet}")
                    context_parts.append("")

        return "\n".join(context_parts).strip() if context_parts else "No similar runbooks or documents found."

    def _build_learned_command_context(
        self,
        db,
        tenant_id: int,
        issue_description: str,
        os_type: Optional[str] = None,
    ) -> str:
        """Build KAG context from the execution learning store."""
        if db is None:
            return ""

        learning = self.learning_service
        parts = []

        try:
            good_cmds = learning.get_known_good_commands(
                db=db, tenant_id=tenant_id, issue_description=issue_description, os_type=os_type, limit=6
            )
            if good_cmds:
                parts.append("Commands proven to work in past executions for similar issues (prefer these):")
                for entry in good_cmds:
                    parts.append(f"  [PROVEN] {entry['command']}")
                    if entry.get("issue_description"):
                        parts.append(f"    (context: {entry['issue_description'][:80]})")
                parts.append("")
        except Exception as e:
            logger.debug(f"Could not fetch known-good commands: {e}")

        try:
            bad_cmds = learning.get_known_bad_commands(
                db=db, tenant_id=tenant_id, issue_description=issue_description, os_type=os_type, limit=4
            )
            if bad_cmds:
                parts.append("Commands known to FAIL for similar issues (avoid these):")
                for entry in bad_cmds:
                    parts.append(f"  [AVOID] {entry['command']}")
                    if entry.get("error_text"):
                        parts.append(f"    (error: {entry['error_text'][:80]})")
                parts.append("")
        except Exception as e:
            logger.debug(f"Could not fetch known-bad commands: {e}")

        return "\n".join(parts).strip()

    def _validate_generated_runbook(
        self, spec: Dict[str, Any], issue_description: str
    ) -> tuple:
        return self.quality_validator.validate(spec, issue_description)
