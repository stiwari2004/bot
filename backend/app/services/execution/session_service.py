"""
Session management service for execution sessions
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.services.runbook_parser import RunbookParser
from app.core.logging import get_logger

logger = get_logger(__name__)

PROFILE_BY_SEVERITY = {
    "critical": ("prod-critical", "high"),
    "high": ("prod-standard", "medium"),
    "dangerous": ("prod-standard", "medium"),
    "moderate": ("staging-standard", "medium"),
}
DEFAULT_PROFILE = ("dev-flex", "low")
PROFILE_RANK = {
    "dev-flex": 0,
    "staging-standard": 1,
    "prod-standard": 2,
    "prod-critical": 3,
    "default": 0,
}


class SessionService:
    """Manages execution session creation and step initialization"""
    
    def __init__(self):
        self.parser = RunbookParser()
    
    async def create_execution_session(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        ticket_id: Optional[int] = None,
        issue_description: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> ExecutionSession:
        """Create a new execution session"""
        session = ExecutionSession(
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            user_id=user_id,
            issue_description=issue_description,
            status="pending",
            sandbox_profile="default",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Parse runbook and create execution steps
        runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Normalize runbook with ticket-specific details if ticket is provided
        if ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket:
                from app.services.runbook_normalizer import RunbookNormalizer
                parsed = RunbookNormalizer.normalize_runbook_for_ticket(runbook, ticket, db)
                logger.info(f"Normalized runbook {runbook_id} for ticket {ticket_id} with server: {parsed.get('metadata', {}).get('server_name', 'N/A')}")
            else:
                parsed = self.parser.parse_runbook(runbook.body_md)
        else:
            parsed = self.parser.parse_runbook(runbook.body_md)
        
        # Create steps
        step_number = 1
        session_profile_rank = PROFILE_RANK.get("default", 0)
        session_profile = "default"
        
        # Prechecks
        for precheck in parsed.get("prechecks", []):
            profile, blast_radius = PROFILE_BY_SEVERITY.get(
                (precheck.get("severity") or "").lower(), DEFAULT_PROFILE
            )
            session_profile_rank = max(session_profile_rank, PROFILE_RANK.get(profile, 0))
            
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="precheck",
                command=precheck.get("command", ""),
                description=precheck.get("description", ""),
                requires_approval=precheck.get("requires_approval", False),
                severity=precheck.get("severity", "low"),
                blast_radius=blast_radius,
            )
            db.add(step)
            step_number += 1
        
        # Main steps
        for main_step in parsed.get("main_steps", []):
            profile, blast_radius = PROFILE_BY_SEVERITY.get(
                (main_step.get("severity") or "").lower(), DEFAULT_PROFILE
            )
            session_profile_rank = max(session_profile_rank, PROFILE_RANK.get(profile, 0))
            
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="main",
                command=main_step.get("command", ""),
                description=main_step.get("description", ""),
                requires_approval=main_step.get("requires_approval", False),
                severity=main_step.get("severity", "low"),
                blast_radius=blast_radius,
            )
            db.add(step)
            step_number += 1
        
        # Postchecks
        for postcheck in parsed.get("postchecks", []):
            profile, blast_radius = PROFILE_BY_SEVERITY.get(
                (postcheck.get("severity") or "").lower(), DEFAULT_PROFILE
            )
            session_profile_rank = max(session_profile_rank, PROFILE_RANK.get(profile, 0))
            
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="postcheck",
                command=postcheck.get("command", ""),
                description=postcheck.get("description", ""),
                requires_approval=postcheck.get("requires_approval", False),
                severity=postcheck.get("severity", "low"),
                blast_radius=blast_radius,
            )
            db.add(step)
            step_number += 1
        
        # Determine session profile based on highest severity step
        for profile_name, rank in PROFILE_RANK.items():
            if rank == session_profile_rank:
                session_profile = profile_name
                break
        
        session.sandbox_profile = session_profile
        session.total_steps = step_number - 1
        db.commit()
        db.refresh(session)
        
        return session




