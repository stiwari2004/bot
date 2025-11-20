"""
Coverage analytics service - analyzes runbook coverage for different issue types
"""
import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
from app.models.runbook import Runbook
from app.models.runbook_citation import RunbookCitation
from app.models.document import Document
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoverageAnalytics:
    """Service for analyzing runbook coverage"""
    
    async def get_coverage_analysis(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Analyze runbook coverage for different issue types.
        
        Returns:
        - Service type distribution
        - Risk level distribution
        - Environment coverage
        - Issue pattern frequency
        """
        try:
            # Get all approved runbooks and parse JSON
            approved_runbooks = db.query(Runbook).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.status == 'approved',
                Runbook.meta_data.isnot(None)
            ).all()
            
            # Parse and aggregate service types
            service_counts = {}
            risk_counts = {}
            issue_counts = {}
            
            for runbook in approved_runbooks:
                try:
                    metadata = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                    
                    # Service distribution
                    service = metadata.get('service', 'unknown')
                    service_counts[service] = service_counts.get(service, 0) + 1
                    
                    # Risk distribution
                    risk = metadata.get('risk', 'unknown')
                    risk_counts[risk] = risk_counts.get(risk, 0) + 1
                    
                    # Issue patterns
                    issue = metadata.get('issue_description', '')
                    if issue:
                        issue_counts[issue] = issue_counts.get(issue, 0) + 1
                except:
                    pass
            
            # Total approved runbooks
            total_approved = db.query(func.count(Runbook.id)).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.status == 'approved'
            ).scalar()
            
            # Total drafts
            total_drafts = db.query(func.count(Runbook.id)).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.status == 'draft'
            ).scalar()
            
            # Sort issue patterns by frequency
            common_issues = sorted(
                [{'issue': issue, 'runbook_count': count} for issue, count in issue_counts.items()],
                key=lambda x: x['runbook_count'],
                reverse=True
            )[:20]
            
            return {
                'total_approved': total_approved or 0,
                'total_drafts': total_drafts or 0,
                'service_distribution': service_counts,
                'risk_distribution': risk_counts,
                'common_issue_patterns': common_issues
            }
            
        except Exception as e:
            logger.error(f"Error getting coverage analysis: {e}")
            return {}
    
    async def get_search_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Track search quality and recommendation accuracy.
        
        Returns:
        - Total searches
        - Recommendation types (existing vs generate new)
        - Average confidence scores
        - Citation source distribution
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Citation source distribution
            source_distribution = db.query(
                Document.source_type,
                func.count(distinct(RunbookCitation.runbook_id)).label('runbook_count')
            ).join(
                RunbookCitation, Document.id == RunbookCitation.document_id
            ).filter(
                RunbookCitation.id.in_(
                    db.query(func.max(RunbookCitation.id))
                    .group_by(RunbookCitation.runbook_id)
                    .subquery()
                )
            ).group_by(Document.source_type).all()
            
            # Average relevance scores
            avg_relevance = db.query(func.avg(RunbookCitation.relevance_score)).filter(
                RunbookCitation.id.in_(
                    db.query(RunbookCitation.runbook_id)
                    .filter(Runbook.id == RunbookCitation.runbook_id)
                    .join(Runbook, Runbook.id == RunbookCitation.runbook_id)
                    .filter(Runbook.tenant_id == tenant_id)
                )
            ).scalar()
            
            return {
                'period_days': days,
                'source_distribution': {
                    src.source_type: src.runbook_count
                    for src in source_distribution
                },
                'avg_citation_relevance': round(float(avg_relevance), 4) if avg_relevance else 0.0,
                'total_citations': db.query(func.count(RunbookCitation.id)).scalar() or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting search quality metrics: {e}")
            return {}


