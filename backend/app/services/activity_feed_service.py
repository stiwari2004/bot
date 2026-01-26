"""
Activity Feed Service
Provides end-to-end visibility into agentic operations
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession
from app.models.execution_pattern import ExecutionPattern
from app.models.runbook import Runbook

logger = get_logger(__name__)


class ActivityFeedService:
    """Service for generating activity feed and incident timeline"""
    
    def __init__(self, db: Session, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id
    
    def get_activity_feed(
        self,
        limit: int = 50,
        ticket_id: Optional[int] = None,
        execution_session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activity feed showing end-to-end agentic operations
        
        Returns:
            List of activity events in chronological order
        """
        activities = []
        
        # Get tickets (correlation events)
        ticket_query = self.db.query(Ticket)
        if self.tenant_id:
            ticket_query = ticket_query.filter(Ticket.tenant_id == self.tenant_id)
        if ticket_id:
            ticket_query = ticket_query.filter(Ticket.id == ticket_id)
        
        tickets = ticket_query.order_by(desc(Ticket.created_at)).limit(limit).all()
        
        for ticket in tickets:
            # Ticket created event
            activities.append({
                "type": "ticket_created",
                "timestamp": ticket.created_at.isoformat() if ticket.created_at else None,
                "ticket_id": ticket.id,
                "title": ticket.title,
                "severity": ticket.severity,
                "status": ticket.status,
                "description": "Ticket created",
            })
            
            # Get associated execution sessions
            executions = self.db.query(ExecutionSession).filter(
                ExecutionSession.ticket_id == ticket.id
            ).order_by(desc(ExecutionSession.created_at)).all()
            
            for execution in executions:
                # Pattern selection event
                if execution.runbook_id:
                    runbook = self.db.query(Runbook).filter(Runbook.id == execution.runbook_id).first()
                    if runbook:
                        # Find pattern that led to this runbook
                        pattern = self.db.query(ExecutionPattern).filter(
                            ExecutionPattern.runbook_id == execution.runbook_id
                        ).order_by(desc(ExecutionPattern.usage_count)).first()
                        
                        activities.append({
                            "type": "pattern_selected",
                            "timestamp": execution.created_at.isoformat() if execution.created_at else None,
                            "ticket_id": ticket.id,
                            "execution_id": execution.id,
                            "runbook_id": execution.runbook_id,
                            "runbook_title": runbook.title,
                            "pattern_id": pattern.id if pattern else None,
                            "pattern_confidence": pattern.success_rate if pattern else None,
                            "description": f"Pattern selected: {runbook.title}",
                        })
                
                # Approval events
                if execution.waiting_for_approval:
                    activities.append({
                        "type": "approval_requested",
                        "timestamp": execution.started_at.isoformat() if execution.started_at else None,
                        "ticket_id": ticket.id,
                        "execution_id": execution.id,
                        "step_number": execution.approval_step_number,
                        "description": f"Approval requested for step {execution.approval_step_number}",
                    })
                
                # Execution status changes
                if execution.status == "completed":
                    activities.append({
                        "type": "execution_completed",
                        "timestamp": execution.completed_at.isoformat() if execution.completed_at else None,
                        "ticket_id": ticket.id,
                        "execution_id": execution.id,
                        "duration_minutes": execution.total_duration_minutes,
                        "description": f"Execution completed in {execution.total_duration_minutes or 0} minutes",
                    })
                elif execution.status == "failed":
                    activities.append({
                        "type": "execution_failed",
                        "timestamp": execution.completed_at.isoformat() if execution.completed_at else None,
                        "ticket_id": ticket.id,
                        "execution_id": execution.id,
                        "description": "Execution failed",
                    })
        
        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        
        return activities[:limit]
    
    def get_incident_timeline(self, ticket_id: int) -> Dict[str, Any]:
        """
        Get detailed timeline for a specific incident/ticket
        
        Returns:
            Dict with timeline events and correlation data
        """
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"error": "Ticket not found"}
        
        timeline = {
            "ticket_id": ticket_id,
            "ticket_title": ticket.title,
            "events": [],
            "correlations": [],
            "executions": [],
        }
        
        # Get all execution sessions for this ticket
        executions = self.db.query(ExecutionSession).filter(
            ExecutionSession.ticket_id == ticket_id
        ).order_by(ExecutionSession.created_at).all()
        
        for execution in executions:
            execution_data = {
                "execution_id": execution.id,
                "runbook_id": execution.runbook_id,
                "status": execution.status,
                "created_at": execution.created_at.isoformat() if execution.created_at else None,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "steps": [],
            }
            
            # Get execution steps
            for step in execution.steps:
                execution_data["steps"].append({
                    "step_number": step.step_number,
                    "status": step.status,
                    "command": step.command,
                    "output": step.output[:200] if step.output else None,  # Truncate
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                })
            
            timeline["executions"].append(execution_data)
        
        # Get activity feed for this ticket
        timeline["events"] = self.get_activity_feed(limit=100, ticket_id=ticket_id)
        
        return timeline
