"""
Quality analytics service - tracks runbook quality metrics
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.models.execution_session import ExecutionSession, ExecutionFeedback, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class QualityAnalytics:
    """Service for tracking runbook quality metrics"""
    
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
    
    async def get_runbook_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive quality metrics for all runbooks.
        
        Returns:
        - Overall statistics (total runbooks, executions, success rate, avg time, avg rating)
        - Top performing runbooks
        - Underperforming runbooks
        - Recent trends
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all completed executions with feedback
            completed_executions = db.query(ExecutionSession).join(
                ExecutionFeedback, ExecutionSession.id == ExecutionFeedback.session_id
            ).filter(
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status.in_(['completed', 'failed']),
                ExecutionSession.started_at >= cutoff_date
            ).all()
            
            # Overall statistics
            total_executions = len(completed_executions)
            successful_executions = sum(1 for e in completed_executions if e.feedback and e.feedback.was_successful)
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            # Average execution time
            durations = [e.total_duration_minutes for e in completed_executions if e.total_duration_minutes]
            avg_execution_time = sum(durations) / len(durations) if durations else 0
            
            # Average rating
            ratings = [e.feedback.rating for e in completed_executions if e.feedback and e.feedback.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            # Issue resolution rate
            resolved = sum(1 for e in completed_executions if e.feedback and e.feedback.issue_resolved)
            resolution_rate = (resolved / total_executions * 100) if total_executions > 0 else 0
            
            # Per-runbook statistics
            runbook_stats = {}
            for execution in completed_executions:
                runbook_id = execution.runbook_id
                if runbook_id not in runbook_stats:
                    runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
                    runbook_stats[runbook_id] = {
                        'runbook_id': runbook_id,
                        'title': runbook.title if runbook else 'Unknown',
                        'executions': [],
                        'successful': 0,
                        'failed': 0,
                        'durations': [],
                        'ratings': [],
                        'resolved': 0
                    }
                
                stats = runbook_stats[runbook_id]
                stats['executions'].append(execution)
                if execution.feedback:
                    if execution.feedback.was_successful:
                        stats['successful'] += 1
                    else:
                        stats['failed'] += 1
                    if execution.feedback.issue_resolved:
                        stats['resolved'] += 1
                    if execution.feedback.rating:
                        stats['ratings'].append(execution.feedback.rating)
                if execution.total_duration_minutes:
                    stats['durations'].append(execution.total_duration_minutes)
            
            # Calculate per-runbook metrics
            runbook_metrics = []
            for runbook_id, stats in runbook_stats.items():
                total = len(stats['executions'])
                if total == 0:
                    continue
                
                success_rate_rb = (stats['successful'] / total * 100) if total > 0 else 0
                avg_time_rb = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
                avg_rating_rb = sum(stats['ratings']) / len(stats['ratings']) if stats['ratings'] else 0
                resolution_rate_rb = (stats['resolved'] / total * 100) if total > 0 else 0
                
                runbook_metrics.append({
                    'runbook_id': runbook_id,
                    'title': stats['title'],
                    'total_executions': total,
                    'success_rate': round(success_rate_rb, 2),
                    'avg_execution_time_minutes': round(avg_time_rb, 2),
                    'avg_rating': round(avg_rating_rb, 2),
                    'resolution_rate': round(resolution_rate_rb, 2),
                    'successful': stats['successful'],
                    'failed': stats['failed']
                })
            
            # Sort by success rate
            runbook_metrics.sort(key=lambda x: x['success_rate'], reverse=True)
            
            # Top performers (>70% success rate, at least 3 executions)
            top_performers = [
                r for r in runbook_metrics
                if r['success_rate'] >= 70 and r['total_executions'] >= 3
            ][:10]
            
            # Underperformers (<50% success rate, at least 3 executions)
            underperformers = [
                r for r in runbook_metrics
                if r['success_rate'] < 50 and r['total_executions'] >= 3
            ][:10]
            
            # Time trends (last 7 days)
            trend_days = 7
            trend_cutoff = datetime.now() - timedelta(days=trend_days)
            trend_executions = db.query(ExecutionSession).join(
                ExecutionFeedback, ExecutionSession.id == ExecutionFeedback.session_id
            ).filter(
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status.in_(['completed', 'failed']),
                ExecutionSession.started_at >= trend_cutoff
            ).all()
            
            # Group by date
            daily_stats = {}
            for execution in trend_executions:
                date_key = execution.started_at.date().isoformat()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        'date': date_key,
                        'total': 0,
                        'successful': 0,
                        'durations': [],
                        'ratings': []
                    }
                
                daily_stats[date_key]['total'] += 1
                if execution.feedback:
                    if execution.feedback.was_successful:
                        daily_stats[date_key]['successful'] += 1
                    if execution.feedback.rating:
                        daily_stats[date_key]['ratings'].append(execution.feedback.rating)
                if execution.total_duration_minutes:
                    daily_stats[date_key]['durations'].append(execution.total_duration_minutes)
            
            # Calculate daily metrics
            daily_trends = []
            for date_key in sorted(daily_stats.keys()):
                stats = daily_stats[date_key]
                success_rate_daily = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
                avg_time_daily = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
                avg_rating_daily = sum(stats['ratings']) / len(stats['ratings']) if stats['ratings'] else 0
                
                daily_trends.append({
                    'date': date_key,
                    'total_executions': stats['total'],
                    'success_rate': round(success_rate_daily, 2),
                    'avg_execution_time_minutes': round(avg_time_daily, 2),
                    'avg_rating': round(avg_rating_daily, 2)
                })
            
            return {
                'period_days': days,
                'overall_stats': {
                    'total_runbooks_with_executions': len(runbook_metrics),
                    'total_executions': total_executions,
                    'success_rate': round(success_rate, 2),
                    'avg_execution_time_minutes': round(avg_execution_time, 2),
                    'avg_rating': round(avg_rating, 2),
                    'resolution_rate': round(resolution_rate, 2)
                },
                'top_performers': top_performers,
                'underperformers': underperformers,
                'all_runbooks': runbook_metrics,
                'daily_trends': daily_trends
            }
            
        except Exception as e:
            logger.error(f"Error getting runbook quality metrics: {e}")
            return {}
    
    async def get_runbook_metrics(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed metrics for a specific runbook.
        
        Returns:
        - Overall statistics
        - Success rate trends over time
        - Execution time trends
        - Feedback breakdown
        - Step-level statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get runbook
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            ).first()
            
            if not runbook:
                return {}
            
            # Get all executions for this runbook
            executions = db.query(ExecutionSession).join(
                ExecutionFeedback, ExecutionSession.id == ExecutionFeedback.session_id
            ).filter(
                ExecutionSession.runbook_id == runbook_id,
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status.in_(['completed', 'failed']),
                ExecutionSession.started_at >= cutoff_date
            ).order_by(ExecutionSession.started_at.desc()).all()
            
            if not executions:
                return {
                    'runbook_id': runbook_id,
                    'title': runbook.title,
                    'period_days': days,
                    'message': 'No executions found for this runbook'
                }
            
            # Overall statistics
            total_executions = len(executions)
            successful = sum(1 for e in executions if e.feedback and e.feedback.was_successful)
            failed = total_executions - successful
            success_rate = (successful / total_executions * 100) if total_executions > 0 else 0
            
            durations = [e.total_duration_minutes for e in executions if e.total_duration_minutes]
            avg_execution_time = sum(durations) / len(durations) if durations else 0
            min_execution_time = min(durations) if durations else 0
            max_execution_time = max(durations) if durations else 0
            
            ratings = [e.feedback.rating for e in executions if e.feedback and e.feedback.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            resolved = sum(1 for e in executions if e.feedback and e.feedback.issue_resolved)
            resolution_rate = (resolved / total_executions * 100) if total_executions > 0 else 0
            
            # Rating distribution
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for e in executions:
                if e.feedback and e.feedback.rating:
                    rating_distribution[e.feedback.rating] = rating_distribution.get(e.feedback.rating, 0) + 1
            
            # Time trends (daily)
            daily_stats = {}
            for execution in executions:
                date_key = execution.started_at.date().isoformat()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        'date': date_key,
                        'total': 0,
                        'successful': 0,
                        'durations': [],
                        'ratings': []
                    }
                
                daily_stats[date_key]['total'] += 1
                if execution.feedback and execution.feedback.was_successful:
                    daily_stats[date_key]['successful'] += 1
                if execution.feedback and execution.feedback.rating:
                    daily_stats[date_key]['ratings'].append(execution.feedback.rating)
                if execution.total_duration_minutes:
                    daily_stats[date_key]['durations'].append(execution.total_duration_minutes)
            
            # Calculate daily metrics
            daily_trends = []
            for date_key in sorted(daily_stats.keys()):
                stats = daily_stats[date_key]
                success_rate_daily = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
                avg_time_daily = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
                avg_rating_daily = sum(stats['ratings']) / len(stats['ratings']) if stats['ratings'] else 0
                
                daily_trends.append({
                    'date': date_key,
                    'total_executions': stats['total'],
                    'success_rate': round(success_rate_daily, 2),
                    'avg_execution_time_minutes': round(avg_time_daily, 2),
                    'avg_rating': round(avg_rating_daily, 2)
                })
            
            # Step-level statistics
            step_stats = {}
            for execution in executions:
                for step in execution.steps:
                    step_key = f"{step.step_type}_{step.step_number}"
                    if step_key not in step_stats:
                        step_stats[step_key] = {
                            'step_type': step.step_type,
                            'step_number': step.step_number,
                            'total': 0,
                            'completed': 0,
                            'successful': 0,
                            'failed': 0
                        }
                    
                    stats = step_stats[step_key]
                    stats['total'] += 1
                    if step.completed:
                        stats['completed'] += 1
                    if step.success is True:
                        stats['successful'] += 1
                    elif step.success is False:
                        stats['failed'] += 1
            
            # Calculate step-level metrics
            step_metrics = []
            for step_key, stats in step_stats.items():
                completion_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                success_rate_step = (stats['successful'] / stats['completed'] * 100) if stats['completed'] > 0 else 0
                
                step_metrics.append({
                    'step_type': stats['step_type'],
                    'step_number': stats['step_number'],
                    'total_attempts': stats['total'],
                    'completion_rate': round(completion_rate, 2),
                    'success_rate': round(success_rate_step, 2),
                    'successful': stats['successful'],
                    'failed': stats['failed']
                })
            
            # Recent executions (last 10)
            recent_executions = []
            for execution in executions[:10]:
                recent_executions.append({
                    'id': execution.id,
                    'issue_description': execution.issue_description,
                    'status': execution.status,
                    'started_at': execution.started_at.isoformat(),
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                    'duration_minutes': execution.total_duration_minutes,
                    'was_successful': execution.feedback.was_successful if execution.feedback else None,
                    'rating': execution.feedback.rating if execution.feedback else None,
                    'issue_resolved': execution.feedback.issue_resolved if execution.feedback else None
                })
            
            return {
                'runbook_id': runbook_id,
                'title': runbook.title,
                'period_days': days,
                'overall_stats': {
                    'total_executions': total_executions,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round(success_rate, 2),
                    'avg_execution_time_minutes': round(avg_execution_time, 2),
                    'min_execution_time_minutes': round(min_execution_time, 2),
                    'max_execution_time_minutes': round(max_execution_time, 2),
                    'avg_rating': round(avg_rating, 2),
                    'resolution_rate': round(resolution_rate, 2)
                },
                'rating_distribution': rating_distribution,
                'daily_trends': daily_trends,
                'step_metrics': sorted(step_metrics, key=lambda x: (x['step_type'], x['step_number'])),
                'recent_executions': recent_executions
            }
            
        except Exception as e:
            logger.error(f"Error getting runbook metrics: {e}")
            return {}


