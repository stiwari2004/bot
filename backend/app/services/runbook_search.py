"""
Enhanced runbook search service with multi-factor confidence scoring
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta

from app.services.vector_store import VectorStoreService
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.models.runbook_citation import RunbookCitation
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookSearchService:
    """Advanced runbook search with multi-factor scoring"""
    
    def __init__(self):
        self.vector_service = VectorStoreService()
    
    async def search_similar_runbooks(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        top_k: int = 5,
        min_confidence: float = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar runbooks with multi-factor confidence.
        
        Factors:
        1. Semantic similarity (vector search)
        2. Keyword match (text search)
        3. Historical success rate
        4. Recency of last successful use
        5. Number of times used
        
        Returns list of dictionaries with:
        - id, title, similarity_score, confidence_score, success_rate, times_used, last_used, reasoning
        """
        try:
            # First, get semantic matches from vector store (only approved runbooks)
            search_results = await self.vector_service.hybrid_search(
                query=issue_description,
                tenant_id=tenant_id,
                db=db,
                top_k=top_k * 2,  # Get more candidates for re-ranking
                use_reranking=True,
                source_types=['runbook']  # Only search runbooks
            )
            
            if not search_results:
                logger.info(f"No runbooks found for query: {issue_description[:50]}")
                return []
            
            # Extract runbook IDs from search results
            runbook_ids = []
            semantic_scores = {}
            for result in search_results:
                # Extract runbook ID from metadata or title
                rb_id = self._extract_runbook_id(result)
                if rb_id:
                    runbook_ids.append(rb_id)
                    semantic_scores[rb_id] = result.score
            
            if not runbook_ids:
                logger.warning("Could not extract runbook IDs from search results")
                return []
            
            # Get runbooks with usage statistics
            runbooks_with_stats = self._get_runbooks_with_stats(runbook_ids, tenant_id, db)
            
            # Calculate multi-factor confidence for each
            enriched_results = []
            for runbook_data in runbooks_with_stats:
                runbook_id = runbook_data['id']
                semantic_score = semantic_scores.get(runbook_id, 0.0)
                
                # Calculate composite confidence
                confidence = await self.calculate_confidence(
                    semantic_score=semantic_score,
                    keyword_score=runbook_data.get('keyword_score', semantic_score),  # Use semantic as proxy
                    success_rate=runbook_data['success_rate'],
                    usage_count=runbook_data['times_used'],
                    days_since_last_use=runbook_data['days_since_last_use']
                )
                
                # Create reasoning string
                reasoning = self._generate_reasoning(runbook_data, semantic_score, confidence)
                
                enriched_results.append({
                    'id': runbook_id,
                    'title': runbook_data['title'],
                    'similarity_score': semantic_score,
                    'confidence_score': confidence,
                    'success_rate': runbook_data['success_rate'],
                    'times_used': runbook_data['times_used'],
                    'last_used': runbook_data['last_used'],
                    'reasoning': reasoning
                })
            
            # Sort by confidence score descending
            enriched_results.sort(key=lambda x: x['confidence_score'], reverse=True)
            
            # Apply min_confidence filter if provided
            if min_confidence is not None:
                enriched_results = [r for r in enriched_results if r['confidence_score'] >= min_confidence]
            
            # Return top_k
            return enriched_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching similar runbooks: {e}")
            return []
    
    def _extract_runbook_id(self, search_result) -> int:
        """Extract runbook ID from search result"""
        # Try to get from metadata first
        if hasattr(search_result, 'meta_data') and search_result.meta_data:
            import json
            try:
                meta = json.loads(search_result.meta_data) if isinstance(search_result.meta_data, str) else search_result.meta_data
                if 'runbook_id' in meta:
                    return int(meta['runbook_id'])
            except:
                pass
        
        # Fall back to parsing from title or source
        if hasattr(search_result, 'title') and search_result.title:
            # Title format might be like "Runbook: Fix Server Issue #42"
            import re
            match = re.search(r'#(\d+)', search_result.title)
            if match:
                return int(match.group(1))
        
        return None
    
    def _get_runbooks_with_stats(self, runbook_ids: List[int], tenant_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get runbooks with usage statistics"""
        if not runbook_ids:
            return []
        
        # Get runbook details (only active, approved runbooks)
        runbooks = db.query(Runbook).filter(
            Runbook.id.in_(runbook_ids),
            Runbook.tenant_id == tenant_id,
            Runbook.status == 'approved',
            Runbook.is_active == 'active'  # Exclude archived runbooks
        ).all()
        
        results = []
        for runbook in runbooks:
            # Calculate usage statistics
            usage_stats = db.query(
                func.count(RunbookUsage.id).label('count'),
                func.avg(
                    case((RunbookUsage.was_helpful == True, 1), else_=0)
                ).label('success_rate')
            ).filter(RunbookUsage.runbook_id == runbook.id).first()
            
            times_used = usage_stats.count or 0
            success_rate = float(usage_stats.success_rate) if usage_stats.success_rate else None
            
            # Get last used date
            last_usage = db.query(RunbookUsage).filter(
                RunbookUsage.runbook_id == runbook.id
            ).order_by(RunbookUsage.created_at.desc()).first()
            
            days_since_last_use = None
            last_used = None
            if last_usage:
                last_used = last_usage.created_at.isoformat() if last_usage.created_at else None
                if last_used:
                    try:
                        last_date = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                        days_since_last_use = (datetime.now(last_date.tzinfo) - last_date).days
                    except:
                        pass
            
            results.append({
                'id': runbook.id,
                'title': runbook.title,
                'success_rate': success_rate,
                'times_used': times_used,
                'last_used': last_used,
                'days_since_last_use': days_since_last_use or 999  # Large number if never used
            })
        
        return results
    
    async def calculate_confidence(
        self,
        semantic_score: float,
        keyword_score: float,
        success_rate: float,
        usage_count: int,
        days_since_last_use: int
    ) -> float:
        """
        Calculate multi-factor confidence score
        
        Weights:
        - Semantic similarity: 50%
        - Historical success: 30%
        - Recency: 10%
        - Usage count: 10%
        """
        # Normalize semantic and keyword scores (already 0-1)
        semantic_weight = 0.5
        keyword_weight = 0.0  # Already part of semantic via hybrid search
        
        # Success rate contribution (0.3 weight)
        success_weight = 0.3
        success_contribution = (success_rate if success_rate is not None else 0.5) * success_weight
        
        # Recency contribution (0.1 weight) - newer is better
        recency_weight = 0.1
        if days_since_last_use < 30:
            recency_contribution = recency_weight
        elif days_since_last_use < 90:
            recency_contribution = recency_weight * 0.7
        elif days_since_last_use < 180:
            recency_contribution = recency_weight * 0.5
        else:
            recency_contribution = recency_weight * 0.2
        
        # Usage count contribution (0.1 weight) - more usage is better (up to a point)
        usage_weight = 0.1
        if usage_count == 0:
            usage_contribution = 0  # Never used = no trust
        elif usage_count < 3:
            usage_contribution = usage_weight * 0.5
        elif usage_count < 10:
            usage_contribution = usage_weight
        else:
            usage_contribution = usage_weight * 1.2  # Bonus for proven track record
        
        # Calculate final confidence
        base_score = (semantic_score * semantic_weight) + (keyword_score * keyword_weight)
        confidence = base_score + success_contribution + recency_contribution + min(usage_contribution, usage_weight * 1.2)
        
        # Ensure confidence is bounded between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def _generate_reasoning(self, runbook_data: Dict, semantic_score: float, confidence: float) -> str:
        """Generate human-readable reasoning for match"""
        reasons = []
        
        if semantic_score >= 0.9:
            reasons.append("Very high semantic match")
        elif semantic_score >= 0.8:
            reasons.append("High semantic match")
        elif semantic_score >= 0.7:
            reasons.append("Good semantic match")
        
        if runbook_data['times_used'] > 0:
            if runbook_data['success_rate'] is not None:
                if runbook_data['success_rate'] >= 0.9:
                    reasons.append(f"Excellent success rate ({runbook_data['success_rate']:.0%})")
                elif runbook_data['success_rate'] >= 0.7:
                    reasons.append(f"Good success rate ({runbook_data['success_rate']:.0%})")
            
            if runbook_data['days_since_last_use'] < 30:
                reasons.append("Recently used")
            elif runbook_data['times_used'] > 5:
                reasons.append(f"Proven track record ({runbook_data['times_used']} times)")
        else:
            reasons.append("New runbook, not yet used")
        
        if not reasons:
            return "Potential match based on content analysis"
        
        return ", ".join(reasons)

