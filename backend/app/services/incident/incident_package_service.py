"""
Incident Package Service
Generates comprehensive incident documentation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.incident_package import IncidentPackage
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep, ExecutionEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


class IncidentPackageService:
    """Service for generating incident packages"""
    
    def generate_package(
        self,
        db: Session,
        ticket_id: int,
        session_id: Optional[int],
        generated_by: int,
        tenant_id: int
    ) -> IncidentPackage:
        """
        Generate complete incident package
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            session_id: Optional execution session ID
            generated_by: User ID generating package
            tenant_id: Tenant ID
            
        Returns:
            IncidentPackage object
        """
        # Get ticket
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == tenant_id
        ).first()
        
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Get session if provided
        session = None
        if session_id:
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id,
                ExecutionSession.tenant_id == tenant_id
            ).first()
        
        # Build timeline
        timeline = self.build_timeline(db, ticket_id, session_id, tenant_id)
        
        # Analyze root cause
        root_cause = self.analyze_root_cause(db, ticket_id, session_id, tenant_id)
        
        # Extract lessons learned
        lessons_learned = self.extract_lessons_learned(db, ticket_id, session_id, tenant_id)
        
        # Generate compliance data
        compliance_data = self.generate_compliance_report(db, ticket_id, session_id, tenant_id)
        
        # Calculate resolution time
        resolution_time_minutes = None
        incident_start = ticket.created_at
        incident_end = None
        
        if session and session.completed_at:
            incident_end = session.completed_at
            if incident_start:
                resolution_time_minutes = int(
                    (incident_end - incident_start).total_seconds() / 60
                )
        
        # Get actions taken
        actions_taken = []
        if session:
            steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id
            ).order_by(ExecutionStep.step_number).all()
            
            actions_taken = [
                {
                    "step_number": step.step_number,
                    "command": step.command,
                    "success": step.success,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": step.error
                }
                for step in steps
            ]
        
        # Create package
        package = IncidentPackage(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            session_id=session_id,
            runbook_id=session.runbook_id if session else None,
            incident_start_time=incident_start or datetime.now(timezone.utc),
            incident_end_time=incident_end,
            resolution_time_minutes=resolution_time_minutes,
            root_cause_analysis=root_cause,
            timeline=timeline,
            actions_taken=actions_taken,
            lessons_learned=lessons_learned,
            recommendations=self._generate_recommendations(ticket, session),
            compliance_data=compliance_data,
            generated_by=generated_by
        )
        
        db.add(package)
        db.commit()
        db.refresh(package)
        
        logger.info(f"Generated incident package {package.id} for ticket {ticket_id}")
        
        return package
    
    def build_timeline(
        self,
        db: Session,
        ticket_id: int,
        session_id: Optional[int],
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """Build chronological timeline of events"""
        timeline = []
        
        # Get ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            timeline.append({
                "timestamp": ticket.created_at.isoformat() if ticket.created_at else None,
                "event": "Incident reported",
                "description": ticket.description or ticket.title
            })
        
        # Get session events
        if session_id:
            events = db.query(ExecutionEvent).filter(
                ExecutionEvent.session_id == session_id
            ).order_by(ExecutionEvent.created_at).all()
            
            for event in events:
                timeline.append({
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                    "event": event.event_type,
                    "description": str(event.payload)
                })
            
            # Get session completion
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id
            ).first()
            
            if session and session.completed_at:
                timeline.append({
                    "timestamp": session.completed_at.isoformat(),
                    "event": "Incident resolved",
                    "description": f"Status: {session.status}"
                })
        
        return sorted(timeline, key=lambda x: x["timestamp"] or "")
    
    def analyze_root_cause(
        self,
        db: Session,
        ticket_id: int,
        session_id: Optional[int],
        tenant_id: int
    ) -> str:
        """Generate root cause analysis"""
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            return "Unable to analyze root cause - ticket not found"
        
        # Simple analysis based on ticket description and execution errors
        root_cause_parts = []
        
        if session_id:
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id
            ).first()
            
            if session and session.status == "failed":
                failed_steps = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session_id,
                    ExecutionStep.success == False
                ).all()
                
                if failed_steps:
                    error_types = set()
                    for step in failed_steps:
                        if step.error:
                            error_lower = step.error.lower()
                            if "timeout" in error_lower:
                                error_types.add("Timeout issues")
                            elif "connection" in error_lower:
                                error_types.add("Connection problems")
                            elif "permission" in error_lower:
                                error_types.add("Permission/authorization issues")
                    
                    if error_types:
                        root_cause_parts.append(f"Execution failures: {', '.join(error_types)}")
        
        if ticket.description:
            root_cause_parts.append(f"Reported issue: {ticket.description[:200]}")
        
        return ". ".join(root_cause_parts) if root_cause_parts else "Root cause analysis pending"
    
    def extract_lessons_learned(
        self,
        db: Session,
        ticket_id: int,
        session_id: Optional[int],
        tenant_id: int
    ) -> str:
        """Extract lessons learned from incident"""
        lessons = []
        
        if session_id:
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id
            ).first()
            
            if session:
                # Check if manual intervention was needed
                manual_steps = db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session_id,
                    ExecutionStep.requires_approval == True
                ).count()
                
                if manual_steps > 0:
                    lessons.append(
                        f"Manual intervention required at {manual_steps} step(s) - "
                        "consider improving automation or runbook reliability"
                    )
                
                # Check execution time
                if session.total_duration_minutes:
                    if session.total_duration_minutes > 60:
                        lessons.append(
                            f"Resolution took {session.total_duration_minutes} minutes - "
                            "consider optimizing runbook steps"
                        )
        
        return ". ".join(lessons) if lessons else "No specific lessons identified"
    
    def generate_compliance_report(
        self,
        db: Session,
        ticket_id: int,
        session_id: Optional[int],
        tenant_id: int
    ) -> Dict[str, Any]:
        """Generate compliance data"""
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        session = None
        
        if session_id:
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id
            ).first()
        
        return {
            "incident_id": ticket_id,
            "reported_at": ticket.created_at.isoformat() if ticket and ticket.created_at else None,
            "resolved_at": session.completed_at.isoformat() if session and session.completed_at else None,
            "severity": ticket.severity if ticket else None,
            "resolution_method": "automated" if session and not session.waiting_for_approval else "manual",
            "audit_trail_available": True,
            "compliance_metadata": {
                "ticket_created": ticket.created_at.isoformat() if ticket and ticket.created_at else None,
                "execution_started": session.started_at.isoformat() if session and session.started_at else None,
                "execution_completed": session.completed_at.isoformat() if session and session.completed_at else None
            }
        }
    
    def _generate_recommendations(
        self,
        ticket: Optional[Ticket],
        session: Optional[ExecutionSession]
    ) -> str:
        """Generate recommendations based on incident"""
        recommendations = []
        
        if session:
            if session.status == "failed":
                recommendations.append(
                    "Review and improve runbook reliability to prevent future failures"
                )
            
            if session.waiting_for_approval:
                recommendations.append(
                    "Consider automating approval steps where safe to reduce MTTR"
                )
        
        return ". ".join(recommendations) if recommendations else "Continue monitoring and improvement"
