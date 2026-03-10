"""
Session management service - CLEAN REWRITE
Simple service for creating execution sessions
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.services.runbook_parser import RunbookParser
from app.core.logging import get_logger

logger = get_logger(__name__)

# Sandbox profile is derived from the highest step severity in the runbook:
# critical -> prod-critical, high/dangerous -> prod-standard, moderate -> staging-standard, else -> default/dev-flex
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
    
    def _create_step(
        self,
        db: Session,
        session_id: int,
        step_number: int,
        step_type: str,
        step_data: dict,
        session_profile_rank: int
    ) -> int:
        """Create a single execution step and return updated profile rank"""
        profile, blast_radius = PROFILE_BY_SEVERITY.get(
            (step_data.get("severity") or "").lower(), DEFAULT_PROFILE
        )
        new_rank = max(session_profile_rank, PROFILE_RANK.get(profile, 0))
        
        # Store branching and timeout in command_payload JSON field
        command_payload = {}
        if step_data.get("step_number") is not None:
            command_payload["step_number"] = step_data.get("step_number")
        if step_data.get("on_success") is not None:
            command_payload["on_success"] = step_data.get("on_success")
        if step_data.get("on_failure") is not None:
            command_payload["on_failure"] = step_data.get("on_failure")
        elif step_data.get("on_fail") is not None:
            # Support legacy on_fail field
            command_payload["on_failure"] = step_data.get("on_fail")
        if step_data.get("timeout") is not None:
            try:
                command_payload["timeout_seconds"] = int(step_data["timeout"])
            except (TypeError, ValueError):
                pass

        # Store purpose for learning loop (diagnose/remediate/verify)
        if step_data.get("purpose"):
            command_payload["purpose"] = step_data.get("purpose")

        step = ExecutionStep(
            session_id=session_id,
            step_number=step_number,
            step_type=step_type,
            command=step_data.get("command", ""),
            notes=step_data.get("description", ""),
            requires_approval=step_data.get("requires_approval", False),
            blast_radius=blast_radius,
            command_payload=command_payload if command_payload else None,
        )
        db.add(step)
        return new_rank
    
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
        # Check if runbook is quarantined
        from app.services.execution.quarantine_service import QuarantineService
        quarantine_service = QuarantineService()
        
        # Get runbook version if available
        runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
        runbook_version_id = None
        if runbook:
            from app.services.runbook.versioning_service import VersioningService
            versioning_service = VersioningService()
            current_version = versioning_service.get_current_version(
                db=db,
                runbook_id=runbook_id,
                tenant_id=tenant_id
            )
            if current_version:
                runbook_version_id = current_version.id
        
        is_quarantined = quarantine_service.is_quarantined(
            db=db,
            runbook_id=runbook_id,
            runbook_version_id=runbook_version_id,
            tenant_id=tenant_id
        )
        
        if is_quarantined:
            raise ValueError(
                f"Runbook {runbook_id} is quarantined and cannot be executed. "
                "Please review and release from quarantine before execution."
            )
        
        # Create session
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
        
        # Track billing: execution session created
        try:
            from app.services.billing.billing_tracker import BillingTracker
            tracker = BillingTracker(db)
            tracker.track_execution_session(tenant_id, session.id)
        except Exception as e:
            logger.warning(f"Failed to track execution session for billing: {e}")
        
        # Get runbook
        runbook = db.query(Runbook).filter(Runbook.id == runbook_id).first()
        if not runbook:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        # Parse runbook (normalize if ticket provided)
        if ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket:
                from app.services.runbook_normalizer import RunbookNormalizer
                # Try to get extracted inputs from ticket metadata
                extracted_inputs = None
                if ticket.meta_data and isinstance(ticket.meta_data, dict):
                    extracted_inputs = ticket.meta_data.get("extracted_inputs")
                
                # If no extracted inputs in metadata, try to extract them now
                if not extracted_inputs:
                    try:
                        from app.services.runbook.input_extractor import RunbookInputExtractor
                        extractor = RunbookInputExtractor()
                        extraction_result = await extractor.extract_inputs(ticket, runbook, db)
                        extracted_inputs = extraction_result.get("extracted", {})
                        # Store in ticket metadata for future use
                        if ticket.meta_data is None:
                            ticket.meta_data = {}
                        if isinstance(ticket.meta_data, dict):
                            ticket.meta_data["extracted_inputs"] = extracted_inputs
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(ticket, "meta_data")
                            db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to extract inputs from ticket {ticket_id}: {e}")
                
                parsed = RunbookNormalizer.normalize_runbook_for_ticket(
                    runbook, ticket, db, extracted_inputs=extracted_inputs
                )
            else:
                parsed = self.parser.parse_runbook(runbook.body_md)
        else:
            parsed = self.parser.parse_runbook(runbook.body_md)
        
        # Validate parsed result
        if not parsed or not isinstance(parsed, dict):
            raise ValueError(f"Failed to parse runbook {runbook_id}")
        
        # Create steps
        step_number = 1
        session_profile_rank = PROFILE_RANK.get("default", 0)
        
        # Prechecks
        for precheck in parsed.get("prechecks", []):
            session_profile_rank = self._create_step(
                db, session.id, step_number, "precheck", precheck, session_profile_rank
            )
            step_number += 1
        
        # Main steps
        for main_step in parsed.get("main_steps", []):
            session_profile_rank = self._create_step(
                db, session.id, step_number, "main", main_step, session_profile_rank
            )
            step_number += 1
        
        # Postchecks
        for postcheck in parsed.get("postchecks", []):
            session_profile_rank = self._create_step(
                db, session.id, step_number, "postcheck", postcheck, session_profile_rank
            )
            step_number += 1
        
        # Determine session profile
        session_profile = "default"
        for profile_name, rank in PROFILE_RANK.items():
            if rank == session_profile_rank:
                session_profile = profile_name
                break
        
        session.sandbox_profile = session_profile
        session.total_steps = step_number - 1
        
        # Verify steps were created
        if session.total_steps == 0:
            raise ValueError(f"No steps could be created from runbook {runbook_id}")
        
        # Commit and verify
        db.commit()
        db.refresh(session)
        
        saved_steps = db.query(ExecutionStep).filter(ExecutionStep.session_id == session.id).count()
        if saved_steps != session.total_steps:
            raise ValueError(f"Failed to save all steps: expected {session.total_steps}, saved {saved_steps}")
        
        logger.info(f"Created session {session.id} with {saved_steps} steps")
        return session
