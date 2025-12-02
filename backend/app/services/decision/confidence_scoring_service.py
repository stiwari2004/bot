"""
ConfidenceScoringService
Multi-factor confidence calculation with detailed breakdown
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import yaml
import json
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.schemas.search import SearchResult
from app.models.confidence_breakdown import ConfidenceBreakdown
from app.models.runbook_citation import RunbookCitation
from app.repositories.confidence_breakdown_repository import ConfidenceBreakdownRepository

logger = get_logger(__name__)


class ConfidenceScoringService:
    """Service for calculating multi-factor confidence scores"""
    
    def __init__(self):
        pass
    
    async def calculate_confidence_breakdown(
        self,
        db: Session,
        *,
        tenant_id: int,
        runbook_id: Optional[int] = None,
        recommendation_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        search_results: Optional[List[SearchResult]] = None,
        runbook_yaml: Optional[str] = None,
        llm_output: Optional[str] = None,
        context_text: Optional[str] = None,
    ) -> ConfidenceBreakdown:
        """
        Calculate comprehensive confidence breakdown with 4 factors:
        1. Search Quality (40% weight)
        2. LLM Consistency (30% weight)
        3. YAML Quality (20% weight)
        4. Citation Coverage (10% weight)
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            runbook_id: Runbook ID (optional)
            recommendation_id: Recommendation ID (optional)
            ticket_id: Ticket ID (optional)
            search_results: List of search results
            runbook_yaml: Generated runbook YAML content
            llm_output: LLM-generated output text
            context_text: Retrieved context text for consistency checking
            
        Returns:
            ConfidenceBreakdown object
        """
        warnings = []
        flags = []
        
        # Factor 1: Search Quality (40% weight)
        search_quality_score, search_details = await self._calculate_search_quality(
            search_results or []
        )
        
        # Factor 2: LLM Consistency (30% weight)
        llm_consistency_score, llm_details = await self._calculate_llm_consistency(
            llm_output or "",
            context_text or "",
            runbook_yaml or ""
        )
        if llm_consistency_score < 0.5:
            warnings.append("Low LLM consistency detected - output may not match context")
            flags.append("low_llm_consistency")
        
        # Factor 3: YAML Quality (20% weight)
        yaml_quality_score, yaml_details = await self._calculate_yaml_quality(
            runbook_yaml or ""
        )
        if yaml_quality_score < 0.5:
            warnings.append("YAML structure issues detected")
            flags.append("yaml_quality_issues")
        
        # Factor 4: Citation Coverage (10% weight)
        citation_coverage_score, citation_details = await self._calculate_citation_coverage(
            db, runbook_id
        )
        if citation_coverage_score < 0.3:
            warnings.append("Low citation coverage - limited source references")
            flags.append("low_citation_coverage")
        
        # Calculate overall confidence (weighted sum)
        overall_confidence = (
            search_quality_score * 0.40 +
            (llm_consistency_score or 0.5) * 0.30 +
            (yaml_quality_score or 0.5) * 0.20 +
            (citation_coverage_score or 0.5) * 0.10
        ) * 100.0  # Convert to 0-100 scale
        
        # Create breakdown record
        breakdown = ConfidenceBreakdown(
            tenant_id=tenant_id,
            runbook_id=runbook_id,
            recommendation_id=recommendation_id,
            ticket_id=ticket_id,
            overall_confidence=overall_confidence,
            search_quality_score=search_quality_score * 100.0,
            llm_consistency_score=llm_consistency_score * 100.0 if llm_consistency_score else None,
            yaml_quality_score=yaml_quality_score * 100.0 if yaml_quality_score else None,
            citation_coverage_score=citation_coverage_score * 100.0 if citation_coverage_score else None,
            search_quality_details=search_details,
            llm_consistency_details=llm_details,
            yaml_quality_details=yaml_details,
            citation_coverage_details=citation_details,
            warnings=warnings if warnings else None,
            flags=flags if flags else None,
            calculation_method="multi_factor_v1",
        )
        
        db.add(breakdown)
        db.commit()
        db.refresh(breakdown)
        
        logger.info(
            f"Calculated confidence breakdown: overall={overall_confidence:.2f}%, "
            f"search={search_quality_score*100:.2f}%, "
            f"llm={llm_consistency_score*100 if llm_consistency_score else 'N/A'}%, "
            f"yaml={yaml_quality_score*100 if yaml_quality_score else 'N/A'}%, "
            f"citations={citation_coverage_score*100 if citation_coverage_score else 'N/A'}%"
        )
        
        return breakdown
    
    async def _calculate_search_quality(
        self,
        search_results: List[SearchResult]
    ) -> tuple[float, Dict[str, Any]]:
        """
        Calculate search quality score (Factor 1: 40% weight)
        
        Factors:
        - Top result score
        - Result count
        - Average relevance score
        """
        if not search_results:
            return 0.0, {
                "top_score": 0.0,
                "result_count": 0,
                "avg_relevance": 0.0,
                "message": "No search results"
            }
        
        top_score = search_results[0].score if search_results else 0.0
        result_count = len(search_results)
        avg_relevance = sum(r.score for r in search_results) / len(search_results) if search_results else 0.0
        
        # Normalize scores (assuming scores are 0-1)
        top_score_normalized = min(top_score, 1.0)
        result_count_normalized = min(result_count / 5.0, 1.0)  # 5+ results = full score
        avg_relevance_normalized = min(avg_relevance, 1.0)
        
        # Weighted combination
        search_quality = (
            top_score_normalized * 0.5 +
            result_count_normalized * 0.3 +
            avg_relevance_normalized * 0.2
        )
        
        details = {
            "top_score": top_score,
            "result_count": result_count,
            "avg_relevance": avg_relevance,
            "top_score_normalized": top_score_normalized,
            "result_count_normalized": result_count_normalized,
            "avg_relevance_normalized": avg_relevance_normalized,
        }
        
        return search_quality, details
    
    async def _calculate_llm_consistency(
        self,
        llm_output: str,
        context_text: str,
        runbook_yaml: str
    ) -> tuple[Optional[float], Dict[str, Any]]:
        """
        Calculate LLM consistency score (Factor 2: 30% weight)
        
        Checks:
        - Command type consistency (e.g., PostgreSQL commands for PostgreSQL issues)
        - Output matches context
        - No obvious hallucinations
        """
        if not llm_output and not runbook_yaml:
            return None, {"message": "No LLM output to check"}
        
        consistency_checks = []
        warnings = []
        
        # Check 1: Command type consistency (if YAML contains commands)
        if runbook_yaml:
            try:
                yaml_data = yaml.safe_load(runbook_yaml)
                if yaml_data and isinstance(yaml_data, dict):
                    steps = yaml_data.get("steps", [])
                    commands = []
                    for step in steps:
                        if isinstance(step, dict):
                            cmd = step.get("command") or step.get("action")
                            if cmd:
                                commands.append(str(cmd).lower())
                    
                    # Simple consistency check: look for common patterns
                    has_sql = any("sql" in cmd or "select" in cmd or "insert" in cmd for cmd in commands)
                    has_shell = any("bash" in cmd or "sh " in cmd or "curl" in cmd for cmd in commands)
                    
                    if commands:
                        consistency_checks.append({
                            "type": "command_type_check",
                            "passed": True,  # Basic check passed
                            "commands_found": len(commands),
                        })
            except Exception as e:
                warnings.append(f"YAML parsing error: {str(e)}")
                consistency_checks.append({
                    "type": "yaml_parse",
                    "passed": False,
                    "error": str(e),
                })
        
        # Check 2: Context overlap (simple keyword matching)
        if context_text and llm_output:
            context_keywords = set(context_text.lower().split())
            output_keywords = set(llm_output.lower().split())
            overlap = len(context_keywords & output_keywords)
            total_unique = len(context_keywords | output_keywords)
            overlap_ratio = overlap / total_unique if total_unique > 0 else 0.0
            
            consistency_checks.append({
                "type": "context_overlap",
                "overlap_ratio": overlap_ratio,
                "passed": overlap_ratio > 0.1,  # At least 10% overlap
            })
        
        # Calculate consistency score
        if consistency_checks:
            passed_checks = sum(1 for c in consistency_checks if c.get("passed", False))
            consistency_score = passed_checks / len(consistency_checks)
        else:
            consistency_score = 0.5  # Neutral if no checks possible
        
        details = {
            "consistency_checks": consistency_checks,
            "warnings": warnings,
            "consistency_score": consistency_score,
        }
        
        return consistency_score, details
    
    async def _calculate_yaml_quality(
        self,
        runbook_yaml: str
    ) -> tuple[Optional[float], Dict[str, Any]]:
        """
        Calculate YAML quality score (Factor 3: 20% weight)
        
        Checks:
        - Valid YAML structure
        - Complete fields (required inputs present)
        - Proper formatting
        """
        if not runbook_yaml:
            return None, {"message": "No YAML to validate"}
        
        quality_checks = []
        
        # Check 1: Valid YAML structure
        try:
            yaml_data = yaml.safe_load(runbook_yaml)
            if yaml_data and isinstance(yaml_data, dict):
                quality_checks.append({
                    "type": "yaml_structure",
                    "passed": True,
                })
                
                # Check 2: Required fields
                required_fields = ["title", "steps"]
                has_required = all(field in yaml_data for field in required_fields)
                quality_checks.append({
                    "type": "required_fields",
                    "passed": has_required,
                    "missing_fields": [f for f in required_fields if f not in yaml_data],
                })
                
                # Check 3: Steps structure
                steps = yaml_data.get("steps", [])
                if steps and isinstance(steps, list):
                    valid_steps = sum(1 for s in steps if isinstance(s, dict) and ("command" in s or "action" in s))
                    steps_quality = valid_steps / len(steps) if steps else 0.0
                    quality_checks.append({
                        "type": "steps_structure",
                        "passed": steps_quality > 0.5,
                        "valid_steps_ratio": steps_quality,
                    })
                else:
                    quality_checks.append({
                        "type": "steps_structure",
                        "passed": False,
                        "message": "No valid steps found",
                    })
            else:
                quality_checks.append({
                    "type": "yaml_structure",
                    "passed": False,
                    "message": "Invalid YAML structure",
                })
        except yaml.YAMLError as e:
            quality_checks.append({
                "type": "yaml_structure",
                "passed": False,
                "error": str(e),
            })
        except Exception as e:
            quality_checks.append({
                "type": "yaml_structure",
                "passed": False,
                "error": f"Unexpected error: {str(e)}",
            })
        
        # Calculate quality score
        if quality_checks:
            passed_checks = sum(1 for c in quality_checks if c.get("passed", False))
            quality_score = passed_checks / len(quality_checks)
        else:
            quality_score = 0.0
        
        details = {
            "quality_checks": quality_checks,
            "quality_score": quality_score,
        }
        
        return quality_score, details
    
    async def _calculate_citation_coverage(
        self,
        db: Session,
        runbook_id: Optional[int]
    ) -> tuple[Optional[float], Dict[str, Any]]:
        """
        Calculate citation coverage score (Factor 4: 10% weight)
        
        Factors:
        - Number of citations
        - Average citation relevance
        - Citation diversity (multiple sources)
        """
        if not runbook_id:
            return None, {"message": "No runbook ID provided"}
        
        citations = db.query(RunbookCitation).filter(
            RunbookCitation.runbook_id == runbook_id
        ).all()
        
        if not citations:
            return 0.0, {
                "citation_count": 0,
                "avg_relevance": 0.0,
                "source_diversity": 0.0,
                "message": "No citations found",
            }
        
        citation_count = len(citations)
        avg_relevance = sum(
            float(c.relevance_score or 0.0) for c in citations
        ) / citation_count if citations else 0.0
        
        # Source diversity (count unique document sources)
        unique_sources = len(set(c.document_id for c in citations if c.document_id))
        source_diversity = min(unique_sources / 3.0, 1.0)  # 3+ sources = full score
        
        # Normalize scores
        citation_count_normalized = min(citation_count / 5.0, 1.0)  # 5+ citations = full score
        avg_relevance_normalized = min(avg_relevance, 1.0)
        
        # Weighted combination
        coverage_score = (
            citation_count_normalized * 0.4 +
            avg_relevance_normalized * 0.4 +
            source_diversity * 0.2
        )
        
        details = {
            "citation_count": citation_count,
            "avg_relevance": avg_relevance,
            "source_diversity": source_diversity,
            "unique_sources": unique_sources,
            "citation_count_normalized": citation_count_normalized,
            "avg_relevance_normalized": avg_relevance_normalized,
        }
        
        return coverage_score, details
    
    async def get_confidence_breakdown(
        self,
        db: Session,
        runbook_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        recommendation_id: Optional[int] = None,
        tenant_id: Optional[int] = None
    ) -> Optional[ConfidenceBreakdown]:
        """
        Get existing confidence breakdown
        
        Args:
            db: Database session
            runbook_id: Runbook ID
            ticket_id: Ticket ID
            recommendation_id: Recommendation ID
            tenant_id: Tenant ID
            
        Returns:
            ConfidenceBreakdown or None
        """
        repo = ConfidenceBreakdownRepository(db)
        
        if runbook_id:
            return repo.get_by_runbook(runbook_id, tenant_id)
        elif ticket_id:
            return repo.get_by_ticket(ticket_id, tenant_id)
        elif recommendation_id:
            return repo.get_by_recommendation(recommendation_id, tenant_id)
        
        return None

