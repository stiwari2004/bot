"""
Change Window Service
Handles ticket suppression during change windows
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.change_ticket import ChangeTicket
from app.models.ticket import Ticket
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChangeWindowService:
    """Service for managing change windows and ticket suppression"""
    
    def get_active_change_windows(
        self,
        db: Session,
        tenant_id: int,
        service_name: Optional[str] = None,
        environment: Optional[str] = None
    ) -> List[ChangeTicket]:
        """
        Get active change windows for a tenant
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            service_name: Optional service name to filter by
            environment: Optional environment to filter by
            
        Returns:
            List of active ChangeTicket objects
        """
        now = datetime.now(timezone.utc)
        
        # Query for active change windows
        query = db.query(ChangeTicket).filter(
            ChangeTicket.tenant_id == tenant_id,
            ChangeTicket.status.in_(['scheduled', 'in_progress']),
            ChangeTicket.suppression_enabled == True,
            ChangeTicket.start_time <= now,
            ChangeTicket.end_time >= now
        )
        
        # Filter by service if provided
        if service_name:
            # Check if change affects this service (or all services if none specified)
            query = query.filter(
                or_(
                    ChangeTicket.affected_services == None,  # Affects all services
                    ChangeTicket.affected_services.contains([service_name])  # PostgreSQL array contains
                )
            )
        
        # Filter by environment if provided
        if environment:
            query = query.filter(
                or_(
                    ChangeTicket.affected_environments == None,  # Affects all environments
                    ChangeTicket.affected_environments.contains([environment])  # PostgreSQL array contains
                )
            )
        
        return query.all()
    
    def should_suppress_ticket(
        self,
        db: Session,
        ticket: Ticket
    ) -> tuple[bool, Optional[ChangeTicket], Optional[str]]:
        """
        Check if a ticket should be suppressed based on active change windows
        
        Args:
            db: Database session
            ticket: Ticket to check
            
        Returns:
            (should_suppress, change_ticket, reason)
        """
        # Get active change windows for this tenant
        active_changes = self.get_active_change_windows(
            db=db,
            tenant_id=ticket.tenant_id,
            service_name=ticket.service,
            environment=ticket.environment
        )
        
        if not active_changes:
            return (False, None, None)
        
        # Check if any change window matches
        for change in active_changes:
            # Check service match
            if change.affected_services and ticket.service:
                if not change.affects_service(ticket.service):
                    continue
            
            # Check environment match
            if change.affected_environments and ticket.environment:
                if not change.affects_environment(ticket.environment):
                    continue
            
            # Match found - suppress ticket
            reason = f"Suppressed due to change window: {change.title} ({change.external_id})"
            return (True, change, reason)
        
        return (False, None, None)
    
    def suppress_ticket(
        self,
        db: Session,
        ticket: Ticket,
        change_ticket: ChangeTicket,
        reason: str
    ) -> None:
        """
        Suppress a ticket due to a change window
        
        Args:
            db: Database session
            ticket: Ticket to suppress
            change_ticket: Change ticket causing suppression
            reason: Suppression reason
        """
        ticket.suppressed = True
        ticket.suppressed_by_change_ticket_id = change_ticket.id
        ticket.suppressed_at = datetime.now(timezone.utc)
        ticket.suppression_reason = reason
        
        db.commit()
        logger.info(f"Suppressed ticket {ticket.id} due to change window {change_ticket.external_id}")
    
    def unsuppress_ticket(
        self,
        db: Session,
        ticket: Ticket
    ) -> None:
        """
        Unsuppress a ticket (when change window ends)
        
        Args:
            db: Database session
            ticket: Ticket to unsuppress
        """
        ticket.suppressed = False
        ticket.suppressed_by_change_ticket_id = None
        ticket.suppressed_at = None
        ticket.suppression_reason = None
        
        db.commit()
        logger.info(f"Unsuppressed ticket {ticket.id}")
    
    def check_and_suppress_ticket(
        self,
        db: Session,
        ticket: Ticket
    ) -> bool:
        """
        Check if ticket should be suppressed and suppress it if needed
        
        Args:
            db: Database session
            ticket: Ticket to check
            
        Returns:
            True if ticket was suppressed, False otherwise
        """
        should_suppress, change_ticket, reason = self.should_suppress_ticket(db, ticket)
        
        if should_suppress and change_ticket:
            self.suppress_ticket(db, ticket, change_ticket, reason)
            return True
        
        return False
    
    def auto_unsuppress_expired_changes(
        self,
        db: Session,
        tenant_id: Optional[int] = None
    ) -> int:
        """
        Auto-unsuppress tickets when their change windows expire
        
        Args:
            db: Database session
            tenant_id: Optional tenant ID to filter by (None = all tenants)
            
        Returns:
            Number of tickets unsuppressed
        """
        now = datetime.now(timezone.utc)
        
        # Find tickets that are suppressed but their change window has ended
        query = db.query(Ticket).filter(
            Ticket.suppressed == True,
            Ticket.suppressed_by_change_ticket_id.isnot(None)
        )
        
        if tenant_id:
            query = query.filter(Ticket.tenant_id == tenant_id)
        
        suppressed_tickets = query.all()
        
        unsuppressed_count = 0
        
        for ticket in suppressed_tickets:
            if not ticket.suppressed_by_change_ticket_id:
                continue
            
            # Get the change ticket
            change_ticket = db.query(ChangeTicket).filter(
                ChangeTicket.id == ticket.suppressed_by_change_ticket_id
            ).first()
            
            if not change_ticket:
                # Change ticket was deleted - unsuppress
                self.unsuppress_ticket(db, ticket)
                unsuppressed_count += 1
                continue
            
            # Check if change window has ended
            if change_ticket.end_time < now or change_ticket.status in ['completed', 'cancelled']:
                self.unsuppress_ticket(db, ticket)
                unsuppressed_count += 1
        
        if unsuppressed_count > 0:
            logger.info(f"Auto-unsuppressed {unsuppressed_count} tickets after change windows expired")
        
        return unsuppressed_count


    async def retrigger_expired_suppressions(self, db: Session) -> int:
        """
        Called by ChangeWindowMonitor every N minutes.

        For each suppressed ticket whose change window has now ended:
          - Alert still firing in DB  → create a new execution session that
            references the original suppressed session, then fire the agent.
          - Alert no longer firing    → close the ticket as resolved during
            the change window (the change itself fixed the issue).

        Returns the number of new sessions created.
        """
        from app.models.alert import Alert
        from app.models.change_ticket import ChangeTicket
        from app.models.execution_session import ExecutionSession
        from app.models.ticket import Ticket
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        retriggered = 0

        suppressed_tickets = (
            db.query(Ticket)
            .filter(
                Ticket.suppressed == True,
                Ticket.suppressed_by_change_ticket_id.isnot(None),
            )
            .all()
        )

        for ticket in suppressed_tickets:
            change_ticket = db.query(ChangeTicket).filter(
                ChangeTicket.id == ticket.suppressed_by_change_ticket_id
            ).first()

            if not change_ticket:
                # Orphaned suppression — clean up and move on
                self.unsuppress_ticket(db, ticket)
                continue

            if change_ticket.is_active():
                continue  # Change window still running — leave it alone

            # Change window has ended — release the suppression
            self.unsuppress_ticket(db, ticket)

            # Is the alert still firing?
            alert_firing = (
                db.query(Alert)
                .filter(
                    Alert.matched_ticket_id == ticket.id,
                    Alert.status == "firing",
                )
                .first()
            )

            if not alert_firing:
                # Issue resolved during the change window — close ticket cleanly
                ticket.status     = "closed"
                ticket.resolved_at = now
                db.commit()
                logger.info(
                    "Ticket %d closed — alert resolved during change window '%s'",
                    ticket.id, change_ticket.external_id,
                )
                continue

            # Alert still firing — find the original suppressed session
            original_session = (
                db.query(ExecutionSession)
                .filter(
                    ExecutionSession.ticket_id == ticket.id,
                    ExecutionSession.status    == "suppressed",
                )
                .order_by(ExecutionSession.created_at.desc())
                .first()
            )

            if not original_session:
                logger.warning(
                    "No suppressed session for ticket %d — cannot retrigger", ticket.id
                )
                continue

            await self._create_retrigger_session(db, ticket, original_session, change_ticket)
            retriggered += 1

        return retriggered

    async def _create_retrigger_session(
        self,
        db: Session,
        ticket,
        original_session,
        change_ticket,
    ) -> None:
        """
        Create a new execution session after a change window expires,
        with a back-reference to the original suppressed session.
        """
        import asyncio
        from app.core.database import SessionLocal
        from app.models.execution_session import ExecutionSession

        original_meta     = original_session.meta_data or {}
        issue_description = (
            original_meta.get("issue_description")
            or ticket.title
            or ticket.description
            or ""
        )

        new_session = ExecutionSession(
            tenant_id  = original_session.tenant_id,
            runbook_id = original_session.runbook_id,  # None for agent sessions
            ticket_id  = ticket.id,
            user_id    = original_session.user_id,
            status     = "pending",
            meta_data  = {
                "agent_session":                    original_meta.get("agent_session", True),
                "issue_description":                issue_description,
                "connection_id":                    original_meta.get("connection_id"),
                "retriggered_after_change_window":  True,
                "original_suppressed_session_id":   original_session.id,
                "change_ticket_id":                 change_ticket.id,
                "change_ticket_ext":                change_ticket.external_id,
            },
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        is_agent = original_meta.get("agent_session", True) and not original_session.runbook_id

        if is_agent:
            # Fire the agent executor in a managed background task
            from app.services.execution.connection_service import ConnectionService
            from app.services.execution.agent_executor import get_agent_executor

            try:
                conn_service      = ConnectionService()
                _conn_db          = SessionLocal()
                try:
                    connection_config = await conn_service.get_connection_config(
                        _conn_db, new_session, None
                    )
                finally:
                    _conn_db.close()

                agent         = get_agent_executor()
                _session_id   = new_session.id
                _issue        = issue_description
                _config       = connection_config

                async def _run() -> None:
                    _db = SessionLocal()
                    try:
                        await agent.run(
                            db               = _db,
                            session_id       = _session_id,
                            connection_config = _config,
                            issue_description = _issue,
                        )
                    except Exception as exc:
                        logger.exception(
                            "Retrigger agent task failed session=%d: %s", _session_id, exc
                        )
                    finally:
                        _db.close()

                asyncio.create_task(_run())
                logger.info(
                    "Retrigger: agent session %d started for ticket %d "
                    "(after change window '%s')",
                    new_session.id, ticket.id, change_ticket.external_id,
                )

            except Exception as exc:
                logger.error(
                    "Retrigger: failed to start agent for ticket %d: %s", ticket.id, exc
                )
        else:
            # Runbook session — session is created and visible; execution is
            # triggered by the normal runbook execution flow (or the UI).
            logger.info(
                "Retrigger: runbook session %d created for ticket %d "
                "(after change window '%s') — awaiting execution trigger",
                new_session.id, ticket.id, change_ticket.external_id,
            )


# Global instance
_change_window_service: Optional[ChangeWindowService] = None


def get_change_window_service() -> ChangeWindowService:
    """Get or create change window service instance"""
    global _change_window_service
    if _change_window_service is None:
        _change_window_service = ChangeWindowService()
    return _change_window_service

