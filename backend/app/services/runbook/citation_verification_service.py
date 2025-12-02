"""
CitationVerificationService
Business logic for verifying and scoring citation quality
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.core.logging import get_logger
from app.models.runbook_citation import RunbookCitation
from app.models.citation_verification import CitationVerification
from app.models.document import Document
from app.models.chunk import Chunk
from app.repositories.citation_verification_repository import CitationVerificationRepository

logger = get_logger(__name__)


class CitationVerificationService:
    """Service for verifying citations and calculating quality scores"""
    
    def __init__(self):
        pass
    
    async def verify_citation(
        self,
        db: Session,
        citation_id: int,
        tenant_id: int
    ) -> CitationVerification:
        """
        Verify a single citation
        
        Checks:
        - Document exists
        - Document is accessible
        - Chunk is valid
        - Calculates quality scores
        
        Args:
            db: Database session
            citation_id: Citation ID
            tenant_id: Tenant ID
            
        Returns:
            CitationVerification object
        """
        citation = db.query(RunbookCitation).filter(
            RunbookCitation.id == citation_id
        ).first()
        
        if not citation:
            raise ValueError(f"Citation {citation_id} not found")
        
        # Check document existence
        document = db.query(Document).filter(
            Document.id == citation.document_id
        ).first()
        document_exists = 'true' if document else 'false'
        
        # Check document accessibility (simplified - in production would check actual access)
        document_accessible = 'true' if document and document_exists == 'true' else 'false'
        
        # Check chunk validity
        chunk_valid = 'unknown'
        if citation.chunk_id:
            chunk = db.query(Chunk).filter(
                Chunk.id == citation.chunk_id
            ).first()
            chunk_valid = 'true' if chunk else 'false'
        else:
            chunk_valid = 'true'  # No chunk specified is valid
        
        # Determine verification status
        if document_exists == 'false' or document_accessible == 'false':
            verification_status = 'broken'
        elif chunk_valid == 'false':
            verification_status = 'broken'
        else:
            verification_status = 'verified'
        
        # Calculate quality scores
        relevance_score = float(citation.relevance_score or 0.0) * 100.0 if citation.relevance_score else None
        
        # Recency score (newer documents are better)
        recency_score = None
        if document and document.created_at:
            days_old = (datetime.now(timezone.utc) - document.created_at).days
            if days_old < 30:
                recency_score = 100.0
            elif days_old < 90:
                recency_score = 80.0
            elif days_old < 180:
                recency_score = 60.0
            elif days_old < 365:
                recency_score = 40.0
            else:
                recency_score = 20.0
        
        # Source type score (runbook > doc > ticket)
        source_type_score = None
        if document:
            source_type = document.source_type or ''
            if 'runbook' in source_type.lower():
                source_type_score = 100.0
            elif 'doc' in source_type.lower() or 'document' in source_type.lower():
                source_type_score = 70.0
            elif 'ticket' in source_type.lower():
                source_type_score = 50.0
            else:
                source_type_score = 60.0  # Default
        
        # Overall quality score (weighted average)
        overall_quality_score = None
        if relevance_score is not None and recency_score is not None and source_type_score is not None:
            overall_quality_score = (
                relevance_score * 0.5 +
                recency_score * 0.3 +
                source_type_score * 0.2
            )
        
        # Get or create verification record
        repo = CitationVerificationRepository(db)
        verification = repo.get_by_citation(citation_id, tenant_id)
        
        if verification:
            # Update existing
            verification.verification_status = verification_status
            verification.document_exists = document_exists
            verification.document_accessible = document_accessible
            verification.chunk_valid = chunk_valid
            verification.relevance_score = relevance_score
            verification.recency_score = recency_score
            verification.source_type_score = source_type_score
            verification.overall_quality_score = overall_quality_score
            verification.last_verified_at = datetime.now(timezone.utc)
            db.add(verification)
            db.commit()
            db.refresh(verification)
        else:
            # Create new
            verification = CitationVerification(
                tenant_id=tenant_id,
                citation_id=citation_id,
                runbook_id=citation.runbook_id,
                verification_status=verification_status,
                document_exists=document_exists,
                document_accessible=document_accessible,
                chunk_valid=chunk_valid,
                relevance_score=relevance_score,
                recency_score=recency_score,
                source_type_score=source_type_score,
                overall_quality_score=overall_quality_score,
                last_verified_at=datetime.now(timezone.utc),
            )
            db.add(verification)
            db.commit()
            db.refresh(verification)
        
        logger.info(
            f"Verified citation {citation_id}: status={verification_status}, "
            f"quality={overall_quality_score:.2f if overall_quality_score else 'N/A'}"
        )
        
        return verification
    
    async def verify_runbook_citations(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Verify all citations for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            
        Returns:
            Summary of verification results
        """
        citations = db.query(RunbookCitation).filter(
            RunbookCitation.runbook_id == runbook_id
        ).all()
        
        if not citations:
            return {
                "runbook_id": runbook_id,
                "total_citations": 0,
                "verified": 0,
                "broken": 0,
                "pending": 0,
                "avg_quality_score": None,
                "message": "No citations found for this runbook"
            }
        
        verified_count = 0
        broken_count = 0
        pending_count = 0
        quality_scores = []
        
        for citation in citations:
            try:
                verification = await self.verify_citation(db, citation.id, tenant_id)
                
                if verification.verification_status == 'verified':
                    verified_count += 1
                elif verification.verification_status == 'broken':
                    broken_count += 1
                else:
                    pending_count += 1
                
                if verification.overall_quality_score:
                    quality_scores.append(float(verification.overall_quality_score))
            except Exception as e:
                logger.error(f"Error verifying citation {citation.id}: {e}")
                pending_count += 1
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        return {
            "runbook_id": runbook_id,
            "total_citations": len(citations),
            "verified": verified_count,
            "broken": broken_count,
            "pending": pending_count,
            "avg_quality_score": float(avg_quality_score) if avg_quality_score else None,
            "verification_completed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def get_citation_health(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Get citation health summary for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            tenant_id: Tenant ID
            
        Returns:
            Citation health summary
        """
        repo = CitationVerificationRepository(db)
        verifications = repo.get_by_runbook(runbook_id, tenant_id)
        
        if not verifications:
            return {
                "runbook_id": runbook_id,
                "total_citations": 0,
                "health_status": "unknown",
                "message": "No citation verifications found"
            }
        
        verified = sum(1 for v in verifications if v.verification_status == 'verified')
        broken = sum(1 for v in verifications if v.verification_status == 'broken')
        pending = sum(1 for v in verifications if v.verification_status == 'pending')
        
        quality_scores = [
            float(v.overall_quality_score) for v in verifications
            if v.overall_quality_score
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Determine health status
        if broken > 0:
            health_status = "unhealthy"
        elif pending > len(verifications) * 0.5:
            health_status = "needs_verification"
        elif avg_quality and avg_quality < 50.0:
            health_status = "low_quality"
        else:
            health_status = "healthy"
        
        return {
            "runbook_id": runbook_id,
            "total_citations": len(verifications),
            "verified": verified,
            "broken": broken,
            "pending": pending,
            "avg_quality_score": float(avg_quality) if avg_quality else None,
            "health_status": health_status,
            "broken_citations": [
                {
                    "citation_id": v.citation_id,
                    "verification_status": v.verification_status,
                    "overall_quality_score": float(v.overall_quality_score) if v.overall_quality_score else None,
                }
                for v in verifications if v.verification_status == 'broken'
            ],
        }

