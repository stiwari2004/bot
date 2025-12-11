"""
CitationController
Handles HTTP requests for citation verification operations
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.runbook.citation_verification_service import CitationVerificationService
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitationController(BaseController):
    """Controller for citation verification operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.verification_service = CitationVerificationService()
    
    async def verify_runbook_citations(
        self,
        runbook_id: int
    ) -> Dict[str, Any]:
        """
        Verify all citations for a runbook
        
        Args:
            runbook_id: Runbook ID
            
        Returns:
            Verification summary
        """
        try:
            summary = await self.verification_service.verify_runbook_citations(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id
            )
            return summary
        
        except Exception as e:
            logger.error(f"Error verifying citations for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to verify citations")
    
    async def get_citation_health(
        self,
        runbook_id: int
    ) -> Dict[str, Any]:
        """
        Get citation health summary for a runbook
        
        Args:
            runbook_id: Runbook ID
            
        Returns:
            Citation health summary
        """
        try:
            health = await self.verification_service.get_citation_health(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id
            )
            return health
        
        except Exception as e:
            logger.error(f"Error getting citation health for runbook {runbook_id}: {e}")
            raise self.handle_error(e, "Failed to get citation health")
    
    async def verify_single_citation(
        self,
        citation_id: int
    ) -> Dict[str, Any]:
        """
        Verify a single citation
        
        Args:
            citation_id: Citation ID
            
        Returns:
            Verification result
        """
        try:
            verification = await self.verification_service.verify_citation(
                db=self.db,
                citation_id=citation_id,
                tenant_id=self.tenant_id
            )
            
            return {
                "id": verification.id,
                "citation_id": verification.citation_id,
                "verification_status": verification.verification_status,
                "document_exists": verification.document_exists,
                "document_accessible": verification.document_accessible,
                "chunk_valid": verification.chunk_valid,
                "overall_quality_score": float(verification.overall_quality_score) if verification.overall_quality_score else None,
                "relevance_score": float(verification.relevance_score) if verification.relevance_score else None,
                "recency_score": float(verification.recency_score) if verification.recency_score else None,
                "source_type_score": float(verification.source_type_score) if verification.source_type_score else None,
                "last_verified_at": verification.last_verified_at.isoformat() if verification.last_verified_at else None,
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error verifying citation {citation_id}: {e}")
            raise self.handle_error(e, "Failed to verify citation")








