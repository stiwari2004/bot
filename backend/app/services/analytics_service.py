"""
Analytics and observability service for runbook usage and quality metrics
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, case, and_
from datetime import datetime, timedelta

from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.models.runbook_citation import RunbookCitation
from app.models.runbook_similarity import RunbookSimilarity
from app.models.document import Document
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Service for analytics and observability"""
    
    async def get_usage_statistics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics.
        
        Returns:
        - Total runbooks used
        - Most popular runbooks
        - Average confidence scores
        - Success rates
        - User activity
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Total usage count
            total_uses = db.query(func.count(RunbookUsage.id)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).scalar()
            
            # Most popular runbooks (top 10)
            popular_runbooks = db.query(
                Runbook.id,
                Runbook.title,
                func.count(RunbookUsage.id).label('usage_count'),
                func.avg(RunbookUsage.confidence_score).label('avg_confidence')
            ).join(
                RunbookUsage, Runbook.id == RunbookUsage.runbook_id
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).group_by(
                Runbook.id, Runbook.title
            ).order_by(
                func.count(RunbookUsage.id).desc()
            ).limit(10).all()
            
            # Average confidence
            avg_confidence = db.query(func.avg(RunbookUsage.confidence_score)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date
            ).scalar()
            
            # Success rate
            success_stats = db.query(
                func.count(RunbookUsage.id).label('total'),
                func.sum(case((RunbookUsage.was_helpful == True, 1), else_=0)).label('successful')
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.created_at >= cutoff_date,
                RunbookUsage.was_helpful.isnot(None)
            ).first()
            
            success_rate = 0.0
            if success_stats and success_stats.total > 0:
                success_rate = (success_stats.successful / success_stats.total) * 100
            
            return {
                'period_days': days,
                'total_uses': total_uses or 0,
                'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
                'success_rate': round(success_rate, 2),
                'popular_runbooks': [
                    {
                        'id': rb.id,
                        'title': rb.title,
                        'usage_count': rb.usage_count,
                        'avg_confidence': float(rb.avg_confidence) if rb.avg_confidence else 0.0
                    }
                    for rb in popular_runbooks
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}")
            return {}
    
    async def get_quality_metrics(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get quality metrics for runbooks.
        
        Returns:
        - Confidence distribution
        - Success rate distribution
        - High-quality runbooks (>70% success)
        - Underperforming runbooks (<50% success)
        - Average execution time
        """
        try:
            # Confidence distribution
            confidence_ranges = db.query(
                case(
                    (RunbookUsage.confidence_score >= 0.9, 'high_90-100'),
                    (RunbookUsage.confidence_score >= 0.75, 'medium_75-89'),
                    (RunbookUsage.confidence_score >= 0.50, 'low_50-74'),
                    else_='very_low_0-49'
                ).label('range'),
                func.count(RunbookUsage.id).label('count')
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.confidence_score.isnot(None)
            ).group_by('range').all()
            
            # Success rate by runbook
            runbook_success = db.query(
                Runbook.id,
                Runbook.title,
                func.count(RunbookUsage.id).label('total_uses'),
                func.avg(case((RunbookUsage.was_helpful == True, 1), else_=0)).label('success_rate')
            ).join(
                RunbookUsage, Runbook.id == RunbookUsage.runbook_id
            ).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.was_helpful.isnot(None)
            ).group_by(
                Runbook.id, Runbook.title
            ).having(
                func.count(RunbookUsage.id) >= 3  # At least 3 uses
            ).order_by(
                func.avg(case((RunbookUsage.was_helpful == True, 1), else_=0)).desc()
            ).all()
            
            # High-quality runbooks (>70% success)
            high_quality = [
                {
                    'id': rb.id,
                    'title': rb.title,
                    'total_uses': rb.total_uses,
                    'success_rate': round(float(rb.success_rate) * 100, 2)
                }
                for rb in runbook_success
                if rb.success_rate >= 0.70
            ]
            
            # Underperforming runbooks (<50% success)
            underperforming = [
                {
                    'id': rb.id,
                    'title': rb.title,
                    'total_uses': rb.total_uses,
                    'success_rate': round(float(rb.success_rate) * 100, 2)
                }
                for rb in runbook_success
                if rb.success_rate < 0.50
            ]
            
            # Average execution time
            avg_execution = db.query(func.avg(RunbookUsage.execution_time_minutes)).filter(
                RunbookUsage.tenant_id == tenant_id,
                RunbookUsage.execution_time_minutes.isnot(None)
            ).scalar()
            
            return {
                'confidence_distribution': {
                    rng.range: rng.count for rng in confidence_ranges
                },
                'high_quality_runbooks': high_quality[:10],  # Top 10
                'underperforming_runbooks': underperforming[:10],
                'avg_execution_time_minutes': round(float(avg_execution), 2) if avg_execution else 0,
                'total_runbooks_with_stats': len(runbook_success)
            }
            
        except Exception as e:
            logger.error(f"Error getting quality metrics: {e}")
            return {}
    
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
            import json
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
    
    async def record_runbook_usage(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        issue_description: str,
        confidence_score: float,
        was_helpful: Optional[bool] = None,
        feedback_text: Optional[str] = None,
        execution_time_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record when a runbook is used.
        
        This should be called when a user executes or reviews a runbook.
        """
        try:
            usage = RunbookUsage(
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                issue_description=issue_description[:500],  # Truncate if too long
                confidence_score=confidence_score,
                was_helpful=was_helpful,
                feedback_text=feedback_text,
                execution_time_minutes=execution_time_minutes
            )
            
            db.add(usage)
            db.commit()
            db.refresh(usage)
            
            logger.info(f"Recorded usage for runbook {runbook_id}")
            
            return {
                'usage_id': usage.id,
                'message': 'Usage recorded successfully'
            }
            
        except Exception as e:
            logger.error(f"Error recording runbook usage: {e}")
            db.rollback()
            return {}

