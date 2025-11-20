"""
Service for matching runbooks to tickets
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.runbook import Runbook
from app.core.logging import get_logger

logger = get_logger(__name__)


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
        """Find matching runbooks for a ticket using semantic and keyword search"""
        matched_runbooks = []
        
        # Skip if explicitly false positive
        if classification == "false_positive":
            return matched_runbooks
        
        try:
            # Import lazily to avoid loading embedding model unless needed
            from app.services.runbook_search import RunbookSearchService
            runbook_search_service = RunbookSearchService()
            matching_runbooks = await runbook_search_service.search_similar_runbooks(
                issue_description=ticket_description or ticket_title,
                tenant_id=tenant_id,
                db=db,
                top_k=5,
                min_confidence=0.5
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
        
        # Fallback: Keyword matching if no semantic matches
        if len(matched_runbooks) == 0:
            matched_runbooks = self._keyword_match_runbooks(
                db, ticket_description or ticket_title, tenant_id
            )
        
        return matched_runbooks
    
    def _keyword_match_runbooks(
        self,
        db: Session,
        ticket_text: str,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword matching for runbooks"""
        matched_runbooks = []
        
        try:
            ticket_text_lower = (ticket_text or "").lower()
            keywords = [word for word in ticket_text_lower.split() if len(word) > 4]
            
            if keywords:
                all_active_runbooks = db.query(Runbook).filter(
                    Runbook.tenant_id == tenant_id,
                    Runbook.is_active == "active",
                    Runbook.status == "approved"
                ).all()
                
                for runbook in all_active_runbooks:
                    runbook_title_lower = runbook.title.lower()
                    if any(keyword in runbook_title_lower for keyword in keywords):
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
        """Get matched runbooks from ticket meta_data, verifying they're still active"""
        matched_runbooks = []
        
        if not ticket_meta_data or not isinstance(ticket_meta_data, dict):
            return matched_runbooks
        
        stored_runbooks = ticket_meta_data.get("matched_runbooks", [])
        if not stored_runbooks or not isinstance(stored_runbooks, list):
            return matched_runbooks
        
        for stored_rb in stored_runbooks:
            if isinstance(stored_rb, dict):
                rb_id = stored_rb.get("id") or stored_rb.get("runbook_id")
                if rb_id:
                    runbook = db.query(Runbook).filter(
                        Runbook.id == int(rb_id),
                        Runbook.tenant_id == tenant_id,
                        Runbook.is_active == "active"
                    ).first()
                    if runbook:
                        matched_runbooks.append({
                            "id": int(rb_id),
                            "title": stored_rb.get("title") or runbook.title,
                            "confidence_score": stored_rb.get("confidence_score", 1.0),
                            "reasoning": stored_rb.get("reasoning", "Previously matched runbook")
                        })
        
        return matched_runbooks


