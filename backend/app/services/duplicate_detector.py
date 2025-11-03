"""
Duplicate detection service for runbooks
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.runbook import Runbook
from app.models.runbook_similarity import RunbookSimilarity
from app.services.vector_store import VectorStoreService
from app.services.config_service import ConfigService
from app.core.logging import get_logger

logger = get_logger(__name__)


class DuplicateDetectorService:
    """Detect and manage duplicate runbooks"""
    
    def __init__(self):
        self.vector_service = VectorStoreService()
    
    async def check_for_duplicates(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Check if runbook is duplicate of existing approved runbooks.
        Returns list of similar runbooks with scores.
        
        This compares the new runbook against all approved runbooks in the system
        to detect potential duplicates before approval.
        """
        try:
            # Get the runbook being checked
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            ).first()
            
            if not runbook:
                logger.error(f"Runbook {runbook_id} not found for tenant {tenant_id}")
                return []
            
            # Extract searchable text from the runbook
            searchable_text = self._extract_searchable_text(runbook)
            
            if not searchable_text:
                logger.warning(f"Cannot extract searchable text from runbook {runbook_id}")
                return []
            
            # Search for similar approved runbooks
            # Note: We search documents, so we need to find documents created from runbooks
            search_results = await self.vector_service.hybrid_search(
                query=searchable_text,
                tenant_id=tenant_id,
                db=db,
                top_k=20,  # Get more candidates for duplicate checking
                use_reranking=True,
                source_types=None  # Search all sources for now
            )
            
            if not search_results:
                logger.info(f"No similar content found for runbook {runbook_id}")
                return []
            
            # Filter for only runbook sources and extract runbook IDs
            similar_runbooks = []
            seen_ids = set()
            
            for result in search_results:
                # Check if this result is from a runbook document
                if result.document_source == 'runbook':
                    # Try to extract runbook ID from search result
                    rb_id = self._extract_runbook_id_from_result(result, db)
                    
                    if rb_id and rb_id != runbook_id and rb_id not in seen_ids:
                        similar_runbooks.append({
                            'id': rb_id,
                            'title': result.document_title,
                            'similarity_score': result.score,
                            'source': 'vector_search'
                        })
                        seen_ids.add(rb_id)
            
            # Store similarity records
            if similar_runbooks:
                await self._store_similarities(runbook_id, similar_runbooks, tenant_id, db)
            
            return similar_runbooks
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return []
    
    def _extract_searchable_text(self, runbook: Runbook) -> str:
        """
        Extract searchable text from runbook for similarity comparison.
        Includes title, description, issue description, and key steps.
        """
        try:
            import json
            
            # Parse metadata
            metadata = json.loads(runbook.meta_data) if runbook.meta_data else {}
            runbook_spec = metadata.get('runbook_spec', {})
            
            # Build searchable text
            parts = []
            
            # Title
            if runbook.title:
                parts.append(runbook.title)
            
            # Issue description
            issue_desc = metadata.get('issue_description', '')
            if issue_desc:
                parts.append(issue_desc)
            
            # Runbook spec fields
            if runbook_spec:
                if runbook_spec.get('description'):
                    parts.append(runbook_spec['description'])
                if runbook_spec.get('service'):
                    parts.append(f"service: {runbook_spec['service']}")
                
                # Add key step names
                steps = runbook_spec.get('steps', [])
                for step in steps[:5]:  # First 5 steps only
                    if isinstance(step, dict):
                        parts.append(step.get('name', ''))
                        parts.append(step.get('description', ''))
            
            return "\n".join(filter(None, parts))
            
        except Exception as e:
            logger.error(f"Error extracting searchable text from runbook {runbook.id}: {e}")
            return ""
    
    def _extract_runbook_id_from_result(self, result, db: Session) -> int:
        """Extract runbook ID from search result"""
        # Try to get from metadata
        if hasattr(result, 'meta_data') and result.meta_data:
            import json
            try:
                meta = json.loads(result.meta_data) if isinstance(result.meta_data, str) else result.meta_data
                if 'runbook_id' in meta:
                    return int(meta['runbook_id'])
            except:
                pass
        
        # Try parsing from title (e.g., "Runbook: Fix Server Issue #42")
        if hasattr(result, 'title') and result.title:
            import re
            match = re.search(r'#(\d+)', result.title)
            if match:
                return int(match.group(1))
        
        # Try getting document_id and looking up in database
        if hasattr(result, 'document_id'):
            try:
                from app.models.document import Document
                doc = db.query(Document).filter(Document.id == result.document_id).first()
                if doc and doc.metadata:
                    meta = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
                    if 'runbook_id' in meta:
                        return int(meta['runbook_id'])
            except:
                pass
        
        return None
    
    async def _store_similarities(
        self,
        runbook_id: int,
        similar_runbooks: List[Dict],
        tenant_id: int,
        db: Session
    ) -> None:
        """Store similarity records in database"""
        try:
            for similar in similar_runbooks:
                # Check if similarity already exists
                existing = db.query(RunbookSimilarity).filter(
                    and_(
                        ((RunbookSimilarity.runbook_id_1 == runbook_id) & 
                         (RunbookSimilarity.runbook_id_2 == similar['id'])) |
                        ((RunbookSimilarity.runbook_id_1 == similar['id']) & 
                         (RunbookSimilarity.runbook_id_2 == runbook_id))
                    )
                ).first()
                
                if not existing:
                    similarity = RunbookSimilarity(
                        runbook_id_1=min(runbook_id, similar['id']),
                        runbook_id_2=max(runbook_id, similar['id']),
                        similarity_score=similar['similarity_score'],
                        status='detected'
                    )
                    db.add(similarity)
            
            db.commit()
            logger.info(f"Stored {len(similar_runbooks)} similarity records for runbook {runbook_id}")
            
        except Exception as e:
            logger.error(f"Error storing similarities: {e}")
            db.rollback()
    
    async def should_block_approval(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Check if runbook approval should be blocked due to duplicates.
        
        Returns:
            (should_block, similar_runbooks)
        """
        # Get duplicate threshold
        threshold = ConfigService.get_duplicate_threshold(db, tenant_id)
        
        # Check for duplicates
        similar = await self.check_for_duplicates(runbook_id, tenant_id, db)
        
        if not similar:
            return False, []
        
        # Filter by threshold
        above_threshold = [
            s for s in similar 
            if s['similarity_score'] >= threshold
        ]
        
        if above_threshold:
            logger.warning(
                f"Runbook {runbook_id} blocked: {len(above_threshold)} duplicates above threshold {threshold}"
            )
            return True, above_threshold
        
        return False, above_threshold
    
    async def get_similar_runbooks(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all similar runbooks from stored similarities"""
        try:
            similarities = db.query(RunbookSimilarity).filter(
                and_(
                    ((RunbookSimilarity.runbook_id_1 == runbook_id) |
                     (RunbookSimilarity.runbook_id_2 == runbook_id)),
                    RunbookSimilarity.status == 'detected'
                )
            ).all()
            
            results = []
            for sim in similarities:
                other_id = sim.runbook_id_2 if sim.runbook_id_1 == runbook_id else sim.runbook_id_1
                
                # Get runbook details
                other_rb = db.query(Runbook).filter(Runbook.id == other_id).first()
                if other_rb:
                    results.append({
                        'id': other_id,
                        'title': other_rb.title,
                        'similarity_score': float(sim.similarity_score),
                        'created_at': other_rb.created_at.isoformat() if other_rb.created_at else None
                    })
            
            return sorted(results, key=lambda x: x['similarity_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting similar runbooks: {e}")
            return []

