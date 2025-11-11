"""
Runbook execution engine with human validation checkpoints
POC version - simplified implementation
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.models.credential import Credential, InfrastructureConnection
from app.models.user import User
from app.services.runbook_parser import RunbookParser
from app.services.infrastructure_connectors import get_connector
from app.services.ticket_status_service import get_ticket_status_service
from app.services.resolution_verification_service import get_resolution_verification_service
from app.services.ci_extraction_service import CIExtractionService
from app.core.logging import get_logger
from app.services.security import redact_sensitive_text
from app.core import metrics
from app.core.tracing import tracing_span
import json

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


class ExecutionEngine:
    """Execute runbooks with human validation checkpoints"""
    
    def __init__(self):
        self.parser = RunbookParser()
        self.ticket_status_service = get_ticket_status_service()
        self.resolution_verification_service = get_resolution_verification_service()
    
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
            current_rank = PROFILE_RANK.get(profile, 0)
            if current_rank > session_profile_rank:
                session_profile_rank = current_rank
                session_profile = profile

            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="precheck",
                command=precheck.get("command", ""),
                requires_approval=True,  # Prechecks require approval
                sandbox_profile=profile,
                blast_radius=blast_radius,
                approval_policy="per_step",
                command_payload=precheck,
            )
            db.add(step)
            step_number += 1
        
        # Main steps
        for main_step in parsed.get("main_steps", []):
            severity = main_step.get("severity", "safe")
            requires_approval = severity in ["destructive", "high_risk", "critical"]
            profile, blast_radius = PROFILE_BY_SEVERITY.get(
                (severity or "").lower(), DEFAULT_PROFILE
            )
            session_profile_rank = max(session_profile_rank, PROFILE_RANK.get(profile, 0))
            current_rank = PROFILE_RANK.get(profile, 0)
            if current_rank > session_profile_rank:
                session_profile_rank = current_rank
                session_profile = profile

            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="main",
                command=main_step.get("command", ""),
                rollback_command=main_step.get("rollback_command", ""),  # Store rollback command
                requires_approval=requires_approval,
                sandbox_profile=profile,
                blast_radius=blast_radius,
                approval_policy="per_step" if requires_approval else "auto",
                command_payload=main_step,
                rollback_payload={"command": main_step.get("rollback_command")} if main_step.get("rollback_command") else None,
            )
            db.add(step)
            step_number += 1
        
        # Postchecks
        for postcheck in parsed.get("postchecks", []):
            profile, blast_radius = DEFAULT_PROFILE
            current_rank = PROFILE_RANK.get(profile, 0)
            if current_rank > session_profile_rank:
                session_profile_rank = current_rank
                session_profile = profile
            step = ExecutionStep(
                session_id=session.id,
                step_number=step_number,
                step_type="postcheck",
                command=postcheck.get("command", ""),
                requires_approval=False,  # Postchecks usually don't require approval
                sandbox_profile=profile,
                blast_radius=blast_radius,
                approval_policy="auto",
                command_payload=postcheck,
            )
            db.add(step)
            step_number += 1
        
        db.commit()

        # Update session sandbox profile based on highest severity encountered
        session.sandbox_profile = session_profile
        db.commit()
        
        # Set status to waiting_approval if first step requires approval
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.step_number == 1
        ).first()
        
        if first_step and first_step.requires_approval:
            session.status = "waiting_approval"
            session.waiting_for_approval = True
            session.approval_step_number = 1
            db.commit()
        
        return session
    
    async def approve_step(
        self,
        db: Session,
        session_id: int,
        step_number: int,
        user_id: int,
        approve: bool
    ) -> ExecutionSession:
        """Approve or reject a step"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_number
        ).first()
        
        if not step:
            raise ValueError(f"Step {step_number} not found")
        
        if not step.requires_approval:
            raise ValueError(f"Step {step_number} does not require approval")
        
        if step.approved is not None:
            raise ValueError(f"Step {step_number} already approved/rejected")
        
        # Record approval
        step.approved = approve
        step.approved_by = user_id
        step.approved_at = datetime.utcnow()
        
        if not approve:
            # Rejected - mark session as failed
            session.status = "failed"
            session.waiting_for_approval = False
            session.completed_at = datetime.utcnow()
            
            # Update ticket status
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, session.ticket_id, "rejected", issue_resolved=False
                )
            
            db.commit()
            return session
        
        # Approved - continue execution
        session.waiting_for_approval = False
        session.approval_step_number = None
        
        # Execute the step
        await self._execute_step(db, session, step)
        
        # Check if there are more steps
        next_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_number + 1
        ).first()
        
        if next_step:
            if next_step.requires_approval:
                session.status = "waiting_approval"
                session.waiting_for_approval = True
                session.approval_step_number = step_number + 1
                session.current_step = step_number + 1
            else:
                # Auto-execute next step
                session.status = "in_progress"
                session.current_step = step_number + 1
                await self._execute_step(db, session, next_step)
        else:
            # All steps completed
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            if session.started_at:
                duration = (session.completed_at - session.started_at).total_seconds() / 60
                session.total_duration_minutes = int(duration)
            
            # Verify resolution and update ticket status
            if session.ticket_id:
                verification_result = await self.resolution_verification_service.verify_resolution(
                    db, session.id, session.ticket_id
                )
                logger.info(
                    f"Resolution verification for session {session.id}: "
                    f"resolved={verification_result['resolved']}, "
                    f"confidence={verification_result['confidence']:.2f}"
                )
            else:
                # If no ticket, just mark as completed
                pass
        
        db.commit()
        return session
    
    async def _execute_step(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ):
        """Execute a single step"""
        if session.status != "in_progress" and session.status != "waiting_approval":
            session.status = "in_progress"
        
        if not session.started_at:
            session.started_at = datetime.utcnow()
        
        start_time = datetime.utcnow()
        connector_type = "local"
        previous_status = session.status or "unknown"

        with tracing_span(
            "execution.step",
            {
                "session_id": session.id,
                "step_number": step.step_number,
                "step_type": step.step_type or "main",
            },
        ):
            try:
                # Get connection configuration from runbook metadata or step metadata
                # For POC, we'll use a simple approach - get credentials from session's ticket or default
                connection_config = await self._get_connection_config(db, session, step)

                # Determine connector type from connection config or step type
                connector_type = connection_config.get("connector_type", "local")

                # Get connector
                connector = get_connector(connector_type)

                # Execute command
                result = await connector.execute_command(
                    command=step.command,
                    connection_config=connection_config,
                    timeout=30,
                )

                # Update step
                step.credentials_used = []
                credential_id = connection_config.get("credential_id")
                if credential_id:
                    step.credentials_used = [credential_id]
                step.completed = True
                step.success = result["success"]
                step.output = redact_sensitive_text(result.get("output"))
                step.error = redact_sensitive_text(result.get("error"))
                step.completed_at = datetime.utcnow()

                # If step failed, mark session as failed and trigger rollback
                if not result["success"]:
                    session.status = "failed"
                    session.completed_at = datetime.utcnow()

                    # Trigger rollback of all executed steps
                    await self._rollback_execution(db, session)

                    # Update ticket status on failure
                    if session.ticket_id:
                        self.ticket_status_service.update_ticket_on_execution_complete(
                            db, session.ticket_id, "failed", issue_resolved=False
                        )

            except Exception as e:
                logger.error(f"Error executing step {step.step_number}: {e}")
                step.completed = True
                step.success = False
                step.error = redact_sensitive_text(str(e))
                step.completed_at = datetime.utcnow()
                session.status = "failed"
                session.completed_at = datetime.utcnow()

                # Trigger rollback on exception
                await self._rollback_execution(db, session)

                # Update ticket status on exception
                if session.ticket_id:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, session.ticket_id, "failed", issue_resolved=False
                    )

        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics.observe_step_duration(connector_type, duration)
        if previous_status != session.status:
            metrics.record_state_transition(previous_status, session.status or "unknown")
        
        db.commit()
    
    async def _rollback_execution(
        self,
        db: Session,
        session: ExecutionSession
    ):
        """
        Rollback all executed steps in reverse order
        
        Executes rollback commands for all completed steps, starting from the last one
        """
        try:
            # Get all completed steps, ordered by step_number descending
            completed_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.completed == True,
                ExecutionStep.success == True  # Only rollback successful steps
            ).order_by(ExecutionStep.step_number.desc()).all()
            
            if not completed_steps:
                logger.info(f"No completed steps to rollback for session {session.id}")
                return
            
            logger.info(f"Starting rollback for session {session.id}: {len(completed_steps)} steps to rollback")
            
            # Get connection config (use same config as execution)
            connection_config = await self._get_connection_config(db, session, completed_steps[0])
            connector_type = connection_config.get("connector_type", "local")
            connector = get_connector(connector_type)
            
            rollback_failed = False
            
            # Execute rollback commands in reverse order
            for step in completed_steps:
                if not step.rollback_command:
                    logger.warning(f"Step {step.step_number} has no rollback command, skipping")
                    continue
                
                try:
                    logger.info(f"Rolling back step {step.step_number}: {step.rollback_command[:50]}...")
                    
                    # Execute rollback command
                    result = await connector.execute_command(
                        command=step.rollback_command,
                        connection_config=connection_config,
                        timeout=30
                    )
                    
                    if not result["success"]:
                        logger.error(
                            f"Rollback failed for step {step.step_number}: {result.get('error', 'Unknown error')}"
                        )
                        rollback_failed = True
                        # Continue with other rollbacks even if one fails
                    else:
                        logger.info(f"Successfully rolled back step {step.step_number}")
                        
                except Exception as e:
                    logger.error(f"Exception during rollback of step {step.step_number}: {e}")
                    rollback_failed = True
                    # Continue with other rollbacks
            
            if rollback_failed:
                logger.warning(f"Some rollback commands failed for session {session.id}")
            else:
                logger.info(f"Successfully rolled back all steps for session {session.id}")
                
        except Exception as e:
            logger.error(f"Error during rollback execution: {e}")
            # Don't raise - rollback failure shouldn't prevent error reporting
    
    async def _get_connection_config(
        self,
        db: Session,
        session: ExecutionSession,
        step: ExecutionStep
    ) -> Dict[str, Any]:
        """Get connection configuration for executing a step"""
        # Priority:
        # 1. Extract CI/server from ticket and match to infrastructure connection
        # 2. Use connection config from ticket metadata
        # 3. Use connection config from runbook metadata
        # 4. Default to local execution
        
        # Try to extract CI and match to infrastructure connection
        if session.ticket_id:
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                # Extract CI/server name from ticket
                ticket_dict = {
                    'id': ticket.id,
                    'meta_data': ticket.meta_data,
                    'description': ticket.description,
                    'service': ticket.service,
                    'title': ticket.title
                }
                ci_name = CIExtractionService.extract_ci_from_ticket(ticket_dict)
                
                if ci_name:
                    # Try to find matching infrastructure connection
                    connection = CIExtractionService.find_infrastructure_connection(
                        db, ci_name, session.tenant_id
                    )
                    
                    if connection:
                        # Get credential
                        credential = None
                        if connection.credential_id:
                            credential = db.query(Credential).filter(
                                Credential.id == connection.credential_id
                            ).first()
                        
                        # Build connection config from infrastructure connection
                        config = {
                            "connector_type": connection.connection_type,
                            "host": connection.target_host,
                            "port": connection.target_port,
                            "ci_name": ci_name,
                            "connection_id": connection.id,
                            "credential_id": credential.id if credential else None,
                        }
                        
                        # Add credential info if available
                        if credential:
                            from app.services.credential_service import get_credential_service
                            credential_service = get_credential_service()
                            decrypted = credential_service.get_credential(db, credential.id, session.tenant_id)
                            if decrypted:
                                config.update({
                                    "username": decrypted.get("username"),
                                    "password": decrypted.get("password"),
                                    "api_key": decrypted.get("api_key"),
                                    "database_name": decrypted.get("database_name")
                                })
                        
                        logger.info(f"Using infrastructure connection for CI: {ci_name}")
                        return config
                
                # Fallback: Check ticket meta_data for connection_config
                ticket_meta = ticket.meta_data or {}
                if isinstance(ticket_meta, str):
                    try:
                        ticket_meta = json.loads(ticket_meta)
                    except:
                        ticket_meta = {}
                
                if ticket_meta.get("connection_config"):
                    logger.info("Using connection config from ticket metadata")
                    config = ticket_meta["connection_config"]
                    if isinstance(config, dict) and "credential_id" not in config:
                        config["credential_id"] = ticket_meta.get("credential_id")
                    return config
        
        # Try runbook metadata
        runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        if runbook and runbook.metadata:
            runbook_meta = runbook.metadata
            if isinstance(runbook_meta, dict) and runbook_meta.get("connection_config"):
                logger.info("Using connection config from runbook metadata")
                config = runbook_meta["connection_config"]
                if isinstance(config, dict) and "credential_id" not in config:
                    config["credential_id"] = runbook_meta.get("credential_id")
                return config
        
        # Default to local execution
        logger.info("Using default local connector")
        return {
            "connector_type": "local",
            "credential_id": None,
        }
    
    async def start_execution(
        self,
        db: Session,
        session_id: int
    ) -> ExecutionSession:
        """Start execution (if no approval needed)"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        if session.status != "pending":
            raise ValueError(f"Session {session_id} is not in pending status")
        
        # Get first step
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            session.status = "failed"
            db.commit()
            return session
        
        if first_step.requires_approval:
            session.status = "waiting_approval"
            session.waiting_for_approval = True
            session.approval_step_number = 1
            
            # Update ticket status to in_progress when execution starts
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_start(db, session.ticket_id)
        else:
            session.status = "in_progress"
            session.current_step = 1
            
            # Update ticket status to in_progress when execution starts
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_start(db, session.ticket_id)
            
            await self._execute_step(db, session, first_step)
        
        db.commit()
        return session

