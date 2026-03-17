"""
Mixin: per-runbook quality metrics for QualityAnalytics
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.runbook import Runbook
from app.models.execution_session import ExecutionSession, ExecutionFeedback, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class QualityAnalyticsRunbookMixin:
    """Per-runbook quality metrics for QualityAnalytics."""

    async def get_runbook_quality_metrics(
        self,
        tenant_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive quality metrics for all runbooks."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            completed_executions = db.query(ExecutionSession).join(
                ExecutionFeedback, ExecutionSession.id == ExecutionFeedback.session_id
            ).filter(
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status.in_(['completed', 'failed']),
                ExecutionSession.started_at >= cutoff_date
            ).all()

            total_executions = len(completed_executions)
            successful_executions = sum(1 for e in completed_executions if e.feedback and e.feedback.was_successful)
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0

            durations = [e.total_duration_minutes for e in completed_executions if e.total_duration_minutes]
            avg_execution_time = sum(durations) / len(durations) if durations else 0

            ratings = [e.feedback.rating for e in completed_executions if e.feedback and e.feedback.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0

            resolved = sum(1 for e in completed_executions if e.feedback and e.feedback.issue_resolved)
            resolution_rate = (resolved / total_executions * 100) if total_executions > 0 else 0

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

            runbook_metrics.sort(key=lambda x: x['success_rate'], reverse=True)

            top_performers = [r for r in runbook_metrics if r['success_rate'] >= 70 and r['total_executions'] >= 3][:10]
            underperformers = [r for r in runbook_metrics if r['success_rate'] < 50 and r['total_executions'] >= 3][:10]

            trend_cutoff = datetime.now() - timedelta(days=7)
            trend_executions = db.query(ExecutionSession).join(
                ExecutionFeedback, ExecutionSession.id == ExecutionFeedback.session_id
            ).filter(
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status.in_(['completed', 'failed']),
                ExecutionSession.started_at >= trend_cutoff
            ).all()

            daily_stats = {}
            for execution in trend_executions:
                date_key = execution.started_at.date().isoformat()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {'date': date_key, 'total': 0, 'successful': 0, 'durations': [], 'ratings': []}
                daily_stats[date_key]['total'] += 1
                if execution.feedback:
                    if execution.feedback.was_successful:
                        daily_stats[date_key]['successful'] += 1
                    if execution.feedback.rating:
                        daily_stats[date_key]['ratings'].append(execution.feedback.rating)
                if execution.total_duration_minutes:
                    daily_stats[date_key]['durations'].append(execution.total_duration_minutes)

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
        """Get detailed metrics for a specific runbook."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id, Runbook.tenant_id == tenant_id
            ).first()
            if not runbook:
                return {}

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

            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for e in executions:
                if e.feedback and e.feedback.rating:
                    rating_distribution[e.feedback.rating] = rating_distribution.get(e.feedback.rating, 0) + 1

            daily_stats = {}
            for execution in executions:
                date_key = execution.started_at.date().isoformat()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {'date': date_key, 'total': 0, 'successful': 0, 'durations': [], 'ratings': []}
                daily_stats[date_key]['total'] += 1
                if execution.feedback and execution.feedback.was_successful:
                    daily_stats[date_key]['successful'] += 1
                if execution.feedback and execution.feedback.rating:
                    daily_stats[date_key]['ratings'].append(execution.feedback.rating)
                if execution.total_duration_minutes:
                    daily_stats[date_key]['durations'].append(execution.total_duration_minutes)

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

            step_stats = {}
            for execution in executions:
                for step in execution.steps:
                    step_key = f"{step.step_type}_{step.step_number}"
                    if step_key not in step_stats:
                        step_stats[step_key] = {
                            'step_type': step.step_type,
                            'step_number': step.step_number,
                            'total': 0, 'completed': 0, 'successful': 0, 'failed': 0
                        }
                    step_stats[step_key]['total'] += 1
                    if step.completed:
                        step_stats[step_key]['completed'] += 1
                    if step.success is True:
                        step_stats[step_key]['successful'] += 1
                    elif step.success is False:
                        step_stats[step_key]['failed'] += 1

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
