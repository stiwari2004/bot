"""
ConfidenceController
Handles HTTP requests for confidence scoring operations
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.decision.confidence_scoring_service import ConfidenceScoringService
from app.repositories.confidence_breakdown_repository import ConfidenceBreakdownRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConfidenceController(BaseController):
    """Controller for confidence scoring operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.confidence_service = ConfidenceScoringService()
        self.breakdown_repo = ConfidenceBreakdownRepository(db)
    
    async def get_confidence_breakdown(
        self,
        runbook_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        recommendation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get confidence breakdown for a runbook, ticket, or recommendation
        
        Args:
            runbook_id: Runbook ID
            ticket_id: Ticket ID
            recommendation_id: Recommendation ID
            
        Returns:
            Confidence breakdown dictionary
        """
        try:
            breakdown = await self.confidence_service.get_confidence_breakdown(
                db=self.db,
                runbook_id=runbook_id,
                ticket_id=ticket_id,
                recommendation_id=recommendation_id,
                tenant_id=self.tenant_id
            )
            
            if not breakdown:
                raise self.not_found("Confidence breakdown", runbook_id or ticket_id or recommendation_id)
            
            return {
                "id": breakdown.id,
                "overall_confidence": float(breakdown.overall_confidence),
                "components": {
                    "search_quality": {
                        "score": float(breakdown.search_quality_score),
                        "weight": 0.40,
                        "details": breakdown.search_quality_details,
                    },
                    "llm_consistency": {
                        "score": float(breakdown.llm_consistency_score) if breakdown.llm_consistency_score else None,
                        "weight": 0.30,
                        "details": breakdown.llm_consistency_details,
                    },
                    "yaml_quality": {
                        "score": float(breakdown.yaml_quality_score) if breakdown.yaml_quality_score else None,
                        "weight": 0.20,
                        "details": breakdown.yaml_quality_details,
                    },
                    "citation_coverage": {
                        "score": float(breakdown.citation_coverage_score) if breakdown.citation_coverage_score else None,
                        "weight": 0.10,
                        "details": breakdown.citation_coverage_details,
                    },
                },
                "warnings": breakdown.warnings or [],
                "flags": breakdown.flags or [],
                "created_at": breakdown.created_at.isoformat() if breakdown.created_at else None,
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting confidence breakdown: {e}")
            raise self.handle_error(e, "Failed to get confidence breakdown")
    
    async def calculate_confidence_breakdown(
        self,
        runbook_id: Optional[int] = None,
        recommendation_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        search_results: Optional[list] = None,
        runbook_yaml: Optional[str] = None,
        llm_output: Optional[str] = None,
        context_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate and store confidence breakdown
        
        Args:
            runbook_id: Runbook ID
            recommendation_id: Recommendation ID
            ticket_id: Ticket ID
            search_results: List of search results
            runbook_yaml: Runbook YAML content
            llm_output: LLM output text
            context_text: Context text for consistency checking
            
        Returns:
            Calculated confidence breakdown
        """
        try:
            from app.schemas.search import SearchResult
            
            # Convert search_results if provided
            search_result_objects = None
            if search_results:
                search_result_objects = [
                    SearchResult(**r) if isinstance(r, dict) else r
                    for r in search_results
                ]
            
            breakdown = await self.confidence_service.calculate_confidence_breakdown(
                db=self.db,
                tenant_id=self.tenant_id,
                runbook_id=runbook_id,
                recommendation_id=recommendation_id,
                ticket_id=ticket_id,
                search_results=search_result_objects,
                runbook_yaml=runbook_yaml,
                llm_output=llm_output,
                context_text=context_text,
            )
            
            return {
                "id": breakdown.id,
                "overall_confidence": float(breakdown.overall_confidence),
                "components": {
                    "search_quality": {
                        "score": float(breakdown.search_quality_score),
                        "weight": 0.40,
                    },
                    "llm_consistency": {
                        "score": float(breakdown.llm_consistency_score) if breakdown.llm_consistency_score else None,
                        "weight": 0.30,
                    },
                    "yaml_quality": {
                        "score": float(breakdown.yaml_quality_score) if breakdown.yaml_quality_score else None,
                        "weight": 0.20,
                    },
                    "citation_coverage": {
                        "score": float(breakdown.citation_coverage_score) if breakdown.citation_coverage_score else None,
                        "weight": 0.10,
                    },
                },
                "warnings": breakdown.warnings or [],
                "flags": breakdown.flags or [],
            }
        
        except Exception as e:
            logger.error(f"Error calculating confidence breakdown: {e}")
            raise self.handle_error(e, "Failed to calculate confidence breakdown")

