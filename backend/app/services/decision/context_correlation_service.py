"""
Context Correlation Service
Correlates tickets, alerts, and execution history to build comprehensive context
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.ticket import Ticket
from app.models.alert import Alert
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContextCorrelationService:
    """Service for correlating tickets, alerts, and execution history"""
    
    def __init__(self):
        pass
    
    def correlate_ticket_context(
        self,
        ticket_id: int,
        db: Session,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Correlate a ticket with alerts and execution history to build context
        
        Args:
            ticket_id: Ticket ID
            db: Database session
            time_window_hours: Time window for correlation (default 24 hours)
            
        Returns:
            Context object with correlated data
        """
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Get correlated alerts
        alerts = self._find_correlated_alerts(ticket, db, time_window_hours)
        
        # Get related executions
        executions = self._find_related_executions(ticket, db, time_window_hours)
        
        # Extract context signals
        signals = self._extract_context_signals(ticket, alerts, executions)
        
        return {
            "ticket": ticket,
            "alerts": alerts,
            "executions": executions,
            "signals": signals,
            "correlation_time_window_hours": time_window_hours,
            "correlated_at": datetime.now(timezone.utc)
        }
    
    def _find_correlated_alerts(
        self,
        ticket: Ticket,
        db: Session,
        time_window_hours: int
    ) -> List[Alert]:
        """Find alerts correlated with the ticket"""
        # Time window for correlation
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        # Build correlation criteria
        conditions = [
            Alert.tenant_id == ticket.tenant_id,
            Alert.received_at >= time_threshold,
        ]
        
        # Match by service if available
        if ticket.service:
            conditions.append(Alert.service == ticket.service)
        
        # Match by environment
        if ticket.environment:
            conditions.append(Alert.environment == ticket.environment)
        
        # Match by severity (same or higher)
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        ticket_severity_level = severity_order.get(ticket.severity.lower(), 0)
        
        # Get alerts that match
        alerts = db.query(Alert).filter(
            and_(*conditions)
        ).order_by(Alert.received_at.desc()).limit(50).all()
        
        # Filter by severity if needed (optional - can be relaxed)
        # For now, we'll include all alerts in the time window
        
        logger.info(f"Found {len(alerts)} correlated alerts for ticket {ticket.id}")
        return alerts
    
    def _find_related_executions(
        self,
        ticket: Ticket,
        db: Session,
        time_window_hours: int
    ) -> List[ExecutionSession]:
        """Find execution sessions related to the ticket"""
        # Time window for correlation
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        conditions = [
            ExecutionSession.tenant_id == ticket.tenant_id,
            ExecutionSession.created_at >= time_threshold,
        ]
        
        # Match by ticket ID (direct link)
        ticket_condition = ExecutionSession.ticket_id == ticket.id
        
        # Match by service/environment if available
        service_condition = None
        if ticket.service:
            # We need to check runbook service or issue description
            # For now, we'll match by ticket_id primarily
            pass
        
        # Get executions for this ticket
        executions = db.query(ExecutionSession).filter(
            and_(
                *conditions,
                or_(
                    ticket_condition,
                    # Could add more conditions here for service/environment matching
                )
            )
        ).order_by(ExecutionSession.created_at.desc()).limit(20).all()
        
        logger.info(f"Found {len(executions)} related executions for ticket {ticket.id}")
        return executions
    
    def _extract_context_signals(
        self,
        ticket: Ticket,
        alerts: List[Alert],
        executions: List[ExecutionSession]
    ) -> Dict[str, Any]:
        """Extract key context signals from correlated data"""
        signals = {
            "severity": ticket.severity,
            "environment": ticket.environment,
            "service": ticket.service,
            "status": ticket.status,
            "alert_count": len(alerts),
            "execution_count": len(executions),
            "has_active_alerts": any(a.status == "firing" for a in alerts),
            "has_recent_executions": len(executions) > 0,
            "recent_execution_success_rate": None,
            "affected_services": set(),
            "alert_severities": [],
            "execution_statuses": [],
        }
        
        # Extract affected services from alerts
        for alert in alerts:
            if alert.service:
                signals["affected_services"].add(alert.service)
            signals["alert_severities"].append(alert.severity)
        
        # Extract execution statuses and calculate success rate
        if executions:
            success_count = sum(
                1 for e in executions 
                if e.status in ["completed", "completed_with_errors"]
            )
            signals["recent_execution_success_rate"] = success_count / len(executions) if executions else 0
            signals["execution_statuses"] = [e.status for e in executions]
        
        # Convert set to list for JSON serialization
        signals["affected_services"] = list(signals["affected_services"])
        
        # Add classification info if available
        if ticket.classification:
            signals["classification"] = ticket.classification
            signals["classification_confidence"] = ticket.classification_confidence
        
        return signals
    
    def find_related_executions(
        self,
        ticket: Ticket,
        db: Session,
        limit: int = 10
    ) -> List[ExecutionSession]:
        """
        Find execution sessions related to a ticket
        
        Args:
            ticket: Ticket object
            db: Database session
            limit: Maximum number of executions to return
            
        Returns:
            List of related execution sessions
        """
        # Direct link by ticket_id
        executions = db.query(ExecutionSession).filter(
            ExecutionSession.ticket_id == ticket.id
        ).order_by(ExecutionSession.created_at.desc()).limit(limit).all()
        
        return executions
    
    def find_similar_issues(
        self,
        ticket: Ticket,
        db: Session,
        limit: int = 10
    ) -> List[Ticket]:
        """
        Find tickets with similar issues (same service, similar description)
        
        Args:
            ticket: Ticket object
            db: Database session
            limit: Maximum number of similar tickets to return
            
        Returns:
            List of similar tickets
        """
        conditions = [
            Ticket.tenant_id == ticket.tenant_id,
            Ticket.id != ticket.id,  # Exclude self
        ]
        
        # Match by service if available
        if ticket.service:
            conditions.append(Ticket.service == ticket.service)
        
        # Match by environment
        if ticket.environment:
            conditions.append(Ticket.environment == ticket.environment)
        
        # Get similar tickets
        similar_tickets = db.query(Ticket).filter(
            and_(*conditions)
        ).order_by(Ticket.created_at.desc()).limit(limit).all()
        
        logger.info(f"Found {len(similar_tickets)} similar tickets for ticket {ticket.id}")
        return similar_tickets
