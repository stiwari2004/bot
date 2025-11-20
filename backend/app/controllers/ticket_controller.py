"""
Controller for ticket endpoints - handles request/response logic
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from app.controllers.base_controller import BaseController
from app.repositories.ticket_repository import TicketRepository
from app.models.ticket import Ticket
from app.services.ticket_analysis_service import TicketAnalysisService
from app.services.ticket_status_service import get_ticket_status_service
from app.services.ticket.ticket_normalizer import TicketNormalizer
from app.services.ticket.runbook_matching_service import RunbookMatchingService
from app.services.execution import ExecutionEngine
from app.services.config_service import ConfigService
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketController(BaseController):
    """Controller for ticket operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.ticket_repo = TicketRepository(db)
        self.normalizer = TicketNormalizer()
        self.matching_service = RunbookMatchingService()
        self.analysis_service = TicketAnalysisService()
        self.ticket_status_service = get_ticket_status_service()
        self.execution_engine = ExecutionEngine()
    
    async def receive_webhook(
        self,
        source: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Receive webhook from monitoring tools"""
        try:
            # Normalize ticket data
            ticket_data = self.normalizer.normalize(payload, source)
            
            # Create ticket
            ticket = Ticket(
                tenant_id=self.tenant_id,
                source=source,
                external_id=ticket_data.get("external_id"),
                title=ticket_data.get("title", "Untitled Alert"),
                description=ticket_data.get("description", ""),
                severity=ticket_data.get("severity", "medium"),
                environment=ticket_data.get("environment", "prod"),
                service=ticket_data.get("service"),
                status="open",
                raw_payload=payload,
                meta_data=ticket_data.get("metadata", {}),
                received_at=datetime.utcnow()
            )
            
            self.db.add(ticket)
            self.db.commit()
            self.db.refresh(ticket)
            
            # Analyze ticket
            analysis_result = await self._analyze_ticket(ticket)
            
            return {
                "ticket_id": ticket.id,
                "status": ticket.status,
                "classification": ticket.classification,
                "confidence": analysis_result["confidence"],
                "message": "Ticket received and analyzed"
            }
        except Exception as e:
            logger.error(f"Error receiving webhook: {e}")
            raise self.handle_error(e, "Failed to process webhook")
    
    async def create_demo_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a demo ticket for testing"""
        try:
            ticket = Ticket(
                tenant_id=self.tenant_id,
                source=ticket_data.get("source", "custom"),
                external_id=ticket_data.get("external_id"),
                title=ticket_data.get("title", "Demo Ticket"),
                description=ticket_data.get("description", ""),
                severity=ticket_data.get("severity", "medium"),
                environment=ticket_data.get("environment", "prod"),
                service=ticket_data.get("service"),
                status="open",
                raw_payload=ticket_data,
                meta_data=ticket_data.get("metadata", {}),
                received_at=datetime.utcnow()
            )
            
            self.db.add(ticket)
            self.db.commit()
            self.db.refresh(ticket)
            
            # Analyze ticket
            analysis_result = await self._analyze_ticket(ticket)
            
            # Find and store matching runbooks
            await self._find_and_store_matched_runbooks(ticket, analysis_result)
            
            # Auto-execute if conditions are met
            await self._auto_execute_if_eligible(ticket)
            
            self.db.commit()
            
            return {
                "ticket_id": ticket.id,
                "status": ticket.status,
                "classification": ticket.classification,
                "confidence": analysis_result["confidence"],
                "reasoning": analysis_result.get("reasoning")
            }
        except Exception as e:
            logger.error(f"Error creating demo ticket: {e}")
            raise self.handle_error(e, "Failed to create ticket")
    
    async def _analyze_ticket(self, ticket: Ticket) -> Dict[str, Any]:
        """Analyze ticket for false positive"""
        analysis_result = await self.analysis_service.analyze_ticket({
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity,
            "source": ticket.source
        })
        
        # Update ticket with analysis
        ticket.classification = analysis_result["classification"]
        confidence = analysis_result["confidence"]
        if confidence >= 0.8:
            ticket.classification_confidence = "high"
        elif confidence >= 0.5:
            ticket.classification_confidence = "medium"
        else:
            ticket.classification_confidence = "low"
        
        ticket.analyzed_at = datetime.utcnow()
        ticket.status = "analyzing"
        
        # Close ticket if false positive
        if analysis_result["classification"] == "false_positive" and confidence >= 0.8:
            self.ticket_status_service.update_ticket_on_false_positive(self.db, ticket.id)
        
        return analysis_result
    
    async def _find_and_store_matched_runbooks(
        self,
        ticket: Ticket,
        analysis_result: Dict[str, Any]
    ):
        """Find matching runbooks and store them in ticket meta_data"""
        if not ticket.meta_data:
            ticket.meta_data = {}
        
        # Only search if not false positive
        if analysis_result["classification"] != "false_positive":
            matched_runbooks = await self.matching_service.find_matching_runbooks(
                self.db,
                ticket.description or "",
                ticket.title,
                self.tenant_id,
                analysis_result["classification"]
            )
            
            if matched_runbooks:
                ticket.meta_data["matched_runbooks"] = matched_runbooks
                logger.info(f"Found {len(matched_runbooks)} matching runbooks for ticket {ticket.id}")
    
    async def _auto_execute_if_eligible(self, ticket: Ticket):
        """Auto-start execution if conditions are met"""
        if not ticket.meta_data or not isinstance(ticket.meta_data, dict):
            return
        
        matched_runbooks = ticket.meta_data.get("matched_runbooks", [])
        if not matched_runbooks or len(matched_runbooks) == 0:
            return
        
        best_match = matched_runbooks[0]
        runbook_id = best_match.get("id")
        match_confidence = best_match.get("confidence_score", 0.0)
        
        # Check execution mode
        execution_mode = ConfigService.get_execution_mode(self.db, self.tenant_id)
        
        # Auto-start execution only if:
        # 1. Mode is 'auto' (not 'hil')
        # 2. Confidence is high enough (>=0.8)
        # 3. Runbook is approved
        if execution_mode == 'auto' and match_confidence >= 0.8 and runbook_id:
            try:
                from app.models.runbook import Runbook
                runbook = self.db.query(Runbook).filter(
                    Runbook.id == runbook_id,
                    Runbook.tenant_id == self.tenant_id,
                    Runbook.status == "approved"
                ).first()
                
                if runbook:
                    session = await self.execution_engine.create_execution_session(
                        db=self.db,
                        runbook_id=runbook_id,
                        tenant_id=self.tenant_id,
                        ticket_id=ticket.id,
                        issue_description=ticket.description or ticket.title,
                        user_id=None
                    )
                    
                    # Update ticket status
                    self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket.id)
                    
                    # Start execution if no approval needed
                    if session.status == "pending":
                        session = await self.execution_engine.start_execution(self.db, session.id)
                    
                    logger.info(
                        f"Auto-started execution session {session.id} for ticket {ticket.id} "
                        f"with runbook {runbook_id} (confidence: {match_confidence:.2f})"
                    )
            except Exception as e:
                logger.error(f"Failed to auto-start execution for ticket {ticket.id}: {e}")
    
    def list_tickets(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List tickets"""
        try:
            tickets = self.ticket_repo.get_by_tenant(
                self.tenant_id,
                status=status,
                limit=limit
            )
            
            return {
                "tickets": [
                    {
                        "id": t.id,
                        "source": t.source,
                        "title": t.title,
                        "description": t.description,
                        "severity": t.severity,
                        "status": t.status,
                        "classification": t.classification,
                        "classification_confidence": t.classification_confidence,
                        "environment": t.environment,
                        "service": t.service,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "analyzed_at": t.analyzed_at.isoformat() if t.analyzed_at else None,
                        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
                    }
                    for t in tickets
                ]
            }
        except Exception as e:
            logger.error(f"Error listing tickets: {e}", exc_info=True)
            # Return empty result instead of raising error for list endpoints
            return {"tickets": []}
    
    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get ticket details including matched runbooks"""
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            
            if not ticket:
                raise self.not_found("Ticket", ticket_id)
            
            # Get matched runbooks from meta_data
            matched_runbooks = self.matching_service.get_matched_runbooks_from_meta(
                self.db,
                ticket.meta_data or {},
                self.tenant_id
            )
            
            # Also perform semantic search for additional matches
            if not ticket.classification or ticket.classification != "false_positive":
                semantic_matches = await self.matching_service.find_matching_runbooks(
                    self.db,
                    ticket.description or "",
                    ticket.title,
                    self.tenant_id,
                    ticket.classification
                )
                
                # Add semantic search results, avoiding duplicates
                existing_ids = {rb["id"] for rb in matched_runbooks}
                for rb in semantic_matches:
                    if rb["id"] not in existing_ids:
                        matched_runbooks.append(rb)
            
            # Get execution sessions
            from app.models.execution_session import ExecutionSession
            execution_sessions = self.db.query(ExecutionSession).filter(
                ExecutionSession.ticket_id == ticket_id
            ).order_by(ExecutionSession.created_at.desc()).all()
            
            return {
                "id": ticket.id,
                "source": ticket.source,
                "title": ticket.title,
                "description": ticket.description,
                "severity": ticket.severity,
                "status": ticket.status,
                "classification": ticket.classification,
                "classification_confidence": ticket.classification_confidence,
                "environment": ticket.environment,
                "service": ticket.service,
                "meta_data": ticket.meta_data,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "analyzed_at": ticket.analyzed_at.isoformat() if ticket.analyzed_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "matched_runbooks": matched_runbooks,
                "execution_sessions": [
                    {
                        "id": es.id,
                        "status": es.status,
                        "created_at": es.created_at.isoformat() if es.created_at else None
                    }
                    for es in execution_sessions
                ]
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to get ticket")
    
    async def execute_ticket_runbook(
        self,
        ticket_id: int,
        runbook_id: int
    ) -> Dict[str, Any]:
        """Execute a runbook for a ticket"""
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            
            if not ticket:
                raise self.not_found("Ticket", ticket_id)
            
            # Verify runbook exists and is approved
            from app.models.runbook import Runbook
            runbook = self.db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == self.tenant_id,
                Runbook.status == "approved"
            ).first()
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            # Create execution session
            session = await self.execution_engine.create_execution_session(
                db=self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                ticket_id=ticket.id,
                issue_description=ticket.description or ticket.title,
                user_id=None
            )
            
            # Update ticket status
            self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket.id)
            
            # Check execution mode
            execution_mode = ConfigService.get_execution_mode(self.db, self.tenant_id)
            
            # Start execution if mode is auto and no approval needed
            if execution_mode == 'auto':
                if session.status == "pending":
                    session = await self.execution_engine.start_execution(self.db, session.id)
            
            return {
                "session_id": session.id,
                "status": session.status,
                "message": "Execution session created" + (" and started" if execution_mode == 'auto' else " - waiting for approval")
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing runbook for ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to execute runbook")
    
    def cleanup_demo_tickets(self, sources: List[str]) -> Dict[str, Any]:
        """Delete demo/test tickets"""
        try:
            deleted = self.ticket_repo.delete_by_source(self.tenant_id, sources)
            logger.info(f"Deleted {deleted} demo tickets")
            return {
                "message": f"Deleted {deleted} demo tickets",
                "deleted_count": deleted
            }
        except Exception as e:
            logger.error(f"Error cleaning up demo tickets: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to clean up demo tickets")


