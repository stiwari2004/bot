"""
Service for matching runbooks to tickets
"""
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.runbook import Runbook
from app.core.logging import get_logger

logger = get_logger(__name__)


def _extract_cag_issue_and_phrases(description: Optional[str]) -> Tuple[str, List[str]]:
    """
    Extract a CAG-style issue summary and meaningful phrases from alarm/ticket description.
    For pipe-delimited text (e.g. OpManager), parses EventType and Message so matching
    uses the actual issue ("Device Down", "Device not responding") instead of envelope words.
    Returns (summary_string, list of phrases for string matching).
    """
    desc = (description or "").strip()
    if not desc:
        return "", []
    event_type = ""
    message = ""
    # Parse "Key: Value" pairs from pipe- or newline-delimited description
    for part in re.split(r"\s*\|\s*|\n", desc):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, _, val = part.partition(":")
            key, val = key.strip().lower(), val.strip()
            if key == "eventtype":
                event_type = val
            elif key == "message":
                message = val
    # Build CAG-style summary for semantic search (focus on issue, not AlarmID/Category/Server)
    parts = []
    if event_type:
        parts.append(f"EventType: {event_type}")
    if message:
        parts.append(f"Message: {message}")
    summary = ". ".join(parts) if parts else desc
    # Phrases for string matching: EventType value, Message value, and 2–3 word chunks from Message
    phrases = []
    if event_type and len(event_type) >= 2:
        phrases.append(event_type.lower())
    if message:
        msg_lower = message.lower()
        phrases.append(msg_lower)
        # First segment before colon (e.g. "device not responding")
        if ":" in msg_lower:
            phrases.append(msg_lower.split(":")[0].strip())
        # 2–3 word n-grams from message (min length 5 to avoid "or", "on")
        words = [w for w in re.split(r"\W+", msg_lower) if len(w) >= 2]
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                ng = " ".join(words[i : i + n])
                if len(ng) >= 5 and ng not in phrases:
                    phrases.append(ng)
    return summary, phrases


def _runbook_search_query(
    description: Optional[str],
    title: Optional[str],
    cag_summary: Optional[str] = None,
) -> str:
    """
    Build search query for runbook matching: description-first (or CAG summary when available), then title.
    When cag_summary is provided (from _extract_cag_issue_and_phrases), use it so semantic search
    matches on the actual issue (e.g. "Device Down. Message: Device not responding") instead of envelope text.
    """
    if cag_summary and (cag_summary or "").strip():
        summary = (cag_summary or "").strip()
        tit = (title or "").strip()
        if tit:
            return f"{summary} Title: {tit}"
        return summary
    desc = (description or "").strip()
    tit = (title or "").strip()
    if desc and tit:
        return f"{desc} Title: {tit}"
    if desc:
        return desc
    if tit:
        return tit
    return " "


# Words from alarm/ticket envelope or too generic to match runbook titles alone.
# Prevents e.g. "Category: Server" from matching "Fix low memory on Windows server".
_KEYWORD_STOPLIST = frozenset({
    "server", "windows", "linux", "memory", "attention", "severity", "category",
    "entity", "eventtype", "message", "probably", "polling", "alarmid",
    "error", "failed", "warning", "critical", "status", "time",
})


class RunbookMatchingService:
    """Service for finding and matching runbooks to tickets"""
    
    async def find_matching_runbooks(
        self,
        db: Session,
        ticket_description: str,
        ticket_title: str,
        tenant_id: int,
        classification: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find matching runbooks for a ticket using semantic and keyword search.
        Uses description-first query so matching is driven by full alarm/issue text, not just title.
        """
        matched_runbooks = []
        
        # Skip if explicitly false positive
        if classification == "false_positive":
            return matched_runbooks
        
        # CAG-style: use EventType + Message for semantic search when description is pipe-delimited alarm
        cag_summary, issue_phrases = _extract_cag_issue_and_phrases(ticket_description)
        search_query = _runbook_search_query(
            ticket_description, ticket_title, cag_summary=cag_summary or None
        )
        
        try:
            # Import lazily to avoid loading embedding model unless needed
            from app.services.runbook_search import RunbookSearchService
            runbook_search_service = RunbookSearchService()
            matching_runbooks = await runbook_search_service.search_similar_runbooks(
                issue_description=search_query,
                tenant_id=tenant_id,
                db=db,
                top_k=5,
                min_confidence=0.65  # Require stronger match to avoid e.g. Device Down → low memory
            )
            
            # Store all matching runbooks
            if matching_runbooks and len(matching_runbooks) > 0:
                for match in matching_runbooks:
                    runbook_id = match.get("id") or match.get("runbook_id")
                    if runbook_id:
                        # Verify runbook is active
                        runbook = db.query(Runbook).filter(
                            Runbook.id == runbook_id,
                            Runbook.tenant_id == tenant_id,
                            Runbook.is_active == "active"
                        ).first()
                        if runbook:
                            matched_runbooks.append({
                                "id": runbook_id,
                                "title": match.get("title") or runbook.title,
                                "confidence_score": match.get("confidence_score", 0.0),
                                "reasoning": match.get("reasoning", "Semantic match found")
                            })
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
        
        # Fallback: phrase-based string match first, then keyword matching
        if len(matched_runbooks) == 0:
            matched_runbooks = self._phrase_match_runbooks(
                db, tenant_id, issue_phrases
            )
        if len(matched_runbooks) == 0:
            matched_runbooks = self._keyword_match_runbooks(
                db, search_query, tenant_id
            )
        
        return matched_runbooks
    
    def _phrase_match_runbooks(
        self,
        db: Session,
        tenant_id: int,
        phrases: List[str],
    ) -> List[Dict[str, Any]]:
        """Match runbooks by requiring ticket issue phrases (e.g. 'device down', 'not responding') to appear in runbook title or issue_description. Uses strings, not single keywords."""
        if not phrases:
            return []
        # Only consider phrases that are at least 5 chars or multi-word so we don't match on 'down' alone
        meaningful = [p for p in phrases if len(p) >= 5 and (" " in p or len(p) > 6)]
        if not meaningful:
            return []
        matched_runbooks = []
        try:
            runbooks = db.query(Runbook).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.is_active == "active",
                Runbook.status == "approved",
            ).all()
            for runbook in runbooks:
                title_lower = (runbook.title or "").lower()
                issue_desc = ""
                if runbook.meta_data:
                    try:
                        meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                        if isinstance(meta, dict):
                            issue_desc = (meta.get("issue_description") or "").lower()
                    except (json.JSONDecodeError, TypeError):
                        pass
                searchable = f"{title_lower} {issue_desc}"
                if any(phrase in searchable for phrase in meaningful):
                    matched_runbooks.append({
                        "id": runbook.id,
                        "title": runbook.title,
                        "confidence_score": 0.65,
                        "reasoning": "Phrase match: runbook title or issue description contains ticket issue phrase",
                    })
                    if len(matched_runbooks) >= 3:
                        break
        except Exception as e:
            logger.warning(f"Phrase matching failed: {e}")
        return matched_runbooks
    
    def _keyword_match_runbooks(
        self,
        db: Session,
        ticket_text: str,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword matching for runbooks. Uses stoplist and requires 2+ matches to avoid false positives (e.g. 'Server' matching 'Windows server')."""
        matched_runbooks = []
        
        try:
            ticket_text_lower = (ticket_text or "").lower()
            raw_words = [w for w in ticket_text_lower.split() if len(w) > 4]
            keywords = [w for w in raw_words if w not in _KEYWORD_STOPLIST]
            
            if len(keywords) < 2:
                return matched_runbooks  # Need at least 2 meaningful keywords to consider
            
            all_active_runbooks = db.query(Runbook).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.is_active == "active",
                Runbook.status == "approved"
            ).all()
            
            for runbook in all_active_runbooks:
                runbook_title_lower = runbook.title.lower()
                matches = [kw for kw in keywords if kw in runbook_title_lower]
                if len(matches) >= 2:  # Require at least 2 keyword matches to reduce false positives
                    matched_runbooks.append({
                        "id": runbook.id,
                        "title": runbook.title,
                        "confidence_score": 0.6,
                        "reasoning": "Keyword match: runbook title contains relevant terms"
                    })
                    if len(matched_runbooks) >= 3:
                        break
        except Exception as e:
            logger.warning(f"Keyword matching failed: {e}")
        
        return matched_runbooks
    
    def get_matched_runbooks_from_meta(
        self,
        db: Session,
        ticket_meta_data: Dict[str, Any],
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """Get matched runbooks from ticket meta_data, verifying they exist (include archived if they were matched)"""
        matched_runbooks = []
        
        # Handle both dict and JSON string cases (SQLAlchemy JSON columns can sometimes return strings)
        if not ticket_meta_data:
            return matched_runbooks
        
        # If it's a string, try to parse it as JSON
        if isinstance(ticket_meta_data, str):
            try:
                import json
                ticket_meta_data = json.loads(ticket_meta_data)
            except (json.JSONDecodeError, TypeError):
                return matched_runbooks
        
        if not isinstance(ticket_meta_data, dict):
            return matched_runbooks
        
        stored_runbooks = ticket_meta_data.get("matched_runbooks", [])
        if not stored_runbooks or not isinstance(stored_runbooks, list):
            return matched_runbooks
        
        runbook_feedback = ticket_meta_data.get("runbook_feedback") or {}
        if not isinstance(runbook_feedback, dict):
            runbook_feedback = {}
        for stored_rb in stored_runbooks:
            if isinstance(stored_rb, dict):
                rb_id = stored_rb.get("id") or stored_rb.get("runbook_id")
                if rb_id:
                    # Exclude runbooks user marked as "does not match"
                    if runbook_feedback.get(str(rb_id), {}).get("matches") is False:
                        continue
                    # Include archived runbooks if they were previously matched (they're still valid)
                    # Only filter by status="approved" to ensure they're valid runbooks
                    runbook = db.query(Runbook).filter(
                        Runbook.id == int(rb_id),
                        Runbook.tenant_id == tenant_id,
                        Runbook.status == "approved"  # Only require approved, not active (archived is OK)
                    ).first()
                    if runbook:
                        matched_runbooks.append({
                            "id": int(rb_id),
                            "title": stored_rb.get("title") or runbook.title,
                            "confidence_score": stored_rb.get("confidence_score", 1.0),
                            "reasoning": stored_rb.get("reasoning", "Previously matched runbook"),
                            "is_active": runbook.is_active  # Include status so frontend can show it
                        })
                    else:
                        logger.warning(f"Runbook {rb_id} from ticket meta_data not found or not approved")
        
        return matched_runbooks




