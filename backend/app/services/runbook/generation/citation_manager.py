"""
Manages citation storage for runbooks
"""
from typing import List
from sqlalchemy.orm import Session
from app.schemas.search import SearchResult
from app.models.runbook import Runbook
from app.models.runbook_citation import RunbookCitation
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitationManager:
    """Manages citation storage for runbooks"""
    
    def store_citations(
        self,
        db: Session,
        runbook: Runbook,
        search_results: List[SearchResult]
    ) -> None:
        """
        Store citations for a runbook from search results.
        
        Args:
            db: Database session
            runbook: Runbook model instance
            search_results: List of search results to cite
        """
        if not search_results:
            return
        
        for result in search_results:
            citation = RunbookCitation(
                runbook_id=runbook.id,
                tenant_id=runbook.tenant_id,
                document_id=result.document_id,
                chunk_id=getattr(result, 'chunk_id', None),
                relevance_score=result.score
            )
            db.add(citation)
        
        try:
            db.commit()
            logger.info(f"Stored {len(search_results)} citations for runbook {runbook.id}")
        except Exception as e:
            logger.warning(f"Failed to store citations: {e}")
            db.rollback()

