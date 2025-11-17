"""
Ticket ingestion endpoints - Webhook receiver
POC version - simplified
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.core.database import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.services.auth import get_current_user
from app.services.ticket_analysis_service import TicketAnalysisService
from app.services.ticket_status_service import get_ticket_status_service
# RunbookSearchService imported lazily only when needed (to avoid loading embedding model on startup)
from app.services.execution_engine import ExecutionEngine
from app.services.config_service import ConfigService
from app.core.logging import get_logger
from datetime import datetime

router = APIRouter()
logger = get_logger(__name__)


@router.post("/webhook/{source}")
async def receive_webhook(
    source: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Receive webhook from monitoring tools
    
    Sources: prometheus, datadog, pagerduty, servicenow, jira, custom
    """
    try:
        # Use demo tenant for POC (tenant_id = 1)
        tenant_id = 1
        
        # Normalize ticket data
        ticket_data = _normalize_ticket(payload, source)
        
        # Create ticket
        ticket = Ticket(
            tenant_id=tenant_id,
            source=source,
            external_id=ticket_data.get("external_id"),
            title=ticket_data.get("title", "Untitled Alert"),
            description=ticket_data.get("description", ""),
            severity=ticket_data.get("severity", "medium"),
            environment=ticket_data.get("environment", "prod"),
            service=ticket_data.get("service"),
            status="open",
            raw_payload=payload,
            meta_data=ticket_data.get("metadata", {}),  # Renamed from metadata to meta_data
            received_at=datetime.utcnow()
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        # Analyze ticket for false positive
        analysis_service = TicketAnalysisService()
        analysis_result = await analysis_service.analyze_ticket({
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
            ticket_status_service = get_ticket_status_service()
            ticket_status_service.update_ticket_on_false_positive(db, ticket.id)
        
        db.commit()
        
        logger.info(f"Ticket {ticket.id} received from {source}, classification: {analysis_result['classification']}")
        
        return {
            "ticket_id": ticket.id,
            "status": ticket.status,
            "classification": ticket.classification,
            "confidence": confidence,
            "message": "Ticket received and analyzed"
        }
        
    except Exception as e:
        logger.error(f"Error receiving webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/demo/ticket")
async def create_demo_ticket(
    ticket_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Create a demo ticket for testing"""
    try:
        tenant_id = 1
        
        ticket = Ticket(
            tenant_id=tenant_id,
            source=ticket_data.get("source", "custom"),
            external_id=ticket_data.get("external_id"),
            title=ticket_data.get("title", "Demo Ticket"),
            description=ticket_data.get("description", ""),
            severity=ticket_data.get("severity", "medium"),
            environment=ticket_data.get("environment", "prod"),
            service=ticket_data.get("service"),
            status="open",
            raw_payload=ticket_data,
            meta_data=ticket_data.get("metadata", {}),  # Renamed from metadata to meta_data
            received_at=datetime.utcnow()
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        # Analyze ticket
        analysis_service = TicketAnalysisService()
        analysis_result = await analysis_service.analyze_ticket({
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity,
            "source": ticket.source
        })
        
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
        
        # If true positive, try to find matching runbook
        if analysis_result["classification"] != "false_positive":
            # Import lazily to avoid loading embedding model unless needed
            from app.services.runbook_search import RunbookSearchService
            runbook_search_service = RunbookSearchService()
            matching_runbooks = await runbook_search_service.search_similar_runbooks(
                issue_description=ticket.description or ticket.title,
                tenant_id=tenant_id,
                db=db,
                top_k=1,
                min_confidence=0.7
            )
            
            if matching_runbooks and len(matching_runbooks) > 0:
                best_match = matching_runbooks[0]
                runbook_id = best_match.get("id") or best_match.get("runbook_id")  # Handle both formats
                match_confidence = best_match.get("confidence_score", 0.0)
                
                # Check execution mode
                execution_mode = ConfigService.get_execution_mode(db, tenant_id)
                
                # Auto-start execution only if:
                # 1. Mode is 'auto' (not 'hil')
                # 2. Confidence is high enough (>=0.8)
                # 3. Runbook is approved
                if execution_mode == 'auto' and match_confidence >= 0.8 and runbook_id:
                    try:
                        # Verify runbook exists and is approved
                        from app.models.runbook import Runbook
                        runbook = db.query(Runbook).filter(
                            Runbook.id == runbook_id,
                            Runbook.tenant_id == tenant_id,
                            Runbook.status == "approved"
                        ).first()
                        
                        if runbook:
                            execution_engine = ExecutionEngine()
                            session = await execution_engine.create_execution_session(
                                db=db,
                                runbook_id=runbook_id,
                                tenant_id=tenant_id,
                                ticket_id=ticket.id,
                                issue_description=ticket.description or ticket.title,
                                user_id=None
                            )
                            
                            # Update ticket status to in_progress
                            ticket_status_service = get_ticket_status_service()
                            ticket_status_service.update_ticket_on_execution_start(db, ticket.id)
                            
                            # Start execution if no approval needed
                            if session.status == "pending":
                                session = await execution_engine.start_execution(db, session.id)
                            
                            logger.info(
                                f"Auto-started execution session {session.id} for ticket {ticket.id} "
                                f"with runbook {runbook_id} (confidence: {match_confidence:.2f})"
                            )
                        else:
                            logger.warning(f"Runbook {runbook_id} not found or not approved, skipping auto-execution")
                    except Exception as e:
                        logger.error(f"Failed to auto-start execution for ticket {ticket.id}: {e}")
        
        db.commit()
        
        return {
            "ticket_id": ticket.id,
            "status": ticket.status,
            "classification": ticket.classification,
            "confidence": confidence,
            "reasoning": analysis_result.get("reasoning")
        }
        
    except Exception as e:
        logger.error(f"Error creating demo ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.get("/demo/tickets")
async def list_tickets(
    db: Session = Depends(get_db),
    status: str = None,
    limit: int = 50
):
    """List tickets (demo)"""
    try:
        tenant_id = 1
        
        query = db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Ticket.status == status)
        
        tickets = query.order_by(Ticket.created_at.desc()).limit(limit).all()
        
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
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tickets: {str(e)}")


@router.delete("/demo/tickets/cleanup-demo")
async def cleanup_demo_tickets(
    db: Session = Depends(get_db)
):
    """Delete demo/test tickets (prometheus and custom sources)"""
    try:
        tenant_id = 1
        
        # Delete tickets with demo sources
        deleted = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.source.in_(["prometheus", "custom"])
        ).delete()
        
        db.commit()
        
        logger.info(f"Deleted {deleted} demo tickets")
        
        return {
            "message": f"Deleted {deleted} demo tickets",
            "deleted_count": deleted
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up demo tickets: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clean up demo tickets: {str(e)}")


@router.get("/demo/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    """Get ticket details including matched runbooks"""
    try:
        tenant_id = 1
        
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get matched runbooks if ticket is analyzed
        matched_runbooks = []
        if ticket.classification and ticket.classification != "false_positive":
            try:
                # Import lazily to avoid loading embedding model unless needed
                from app.services.runbook_search import RunbookSearchService
                runbook_search_service = RunbookSearchService()
                matching_runbooks = await runbook_search_service.search_similar_runbooks(
                    issue_description=ticket.description or ticket.title,
                    tenant_id=tenant_id,
                    db=db,
                    top_k=5,
                    min_confidence=0.5
                )
                matched_runbooks = [
                    {
                        "id": rb.get("id") or rb.get("runbook_id"),
                        "title": rb.get("title"),
                        "confidence_score": rb.get("confidence_score", 0.0),
                        "reasoning": rb.get("reasoning", "")
                    }
                    for rb in matching_runbooks
                ]
            except Exception as e:
                logger.warning(f"Failed to get matched runbooks for ticket {ticket_id}: {e}")
        
        # Get execution sessions for this ticket
        from app.models.execution_session import ExecutionSession
        execution_sessions = db.query(ExecutionSession).filter(
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
        raise HTTPException(status_code=500, detail=f"Failed to get ticket: {str(e)}")


@router.post("/demo/tickets/{ticket_id}/execute")
async def execute_ticket_runbook(
    ticket_id: int,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Execute a runbook for a ticket"""
    try:
        tenant_id = 1
        runbook_id = request.get("runbook_id")
        
        if not runbook_id:
            raise HTTPException(status_code=400, detail="runbook_id is required")
        
        # Verify ticket exists
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == tenant_id
        ).first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Verify runbook exists and is approved
        from app.models.runbook import Runbook
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == tenant_id,
            Runbook.status == "approved"
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found or not approved")
        
        # Create execution session
        execution_engine = ExecutionEngine()
        session = await execution_engine.create_execution_session(
            db=db,
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            ticket_id=ticket.id,
            issue_description=ticket.description or ticket.title,
            user_id=None
        )
        
        # Update ticket status
        ticket_status_service = get_ticket_status_service()
        ticket_status_service.update_ticket_on_execution_start(db, ticket.id)
        
        # Check execution mode
        execution_mode = ConfigService.get_execution_mode(db, tenant_id)
        
        # Start execution if mode is auto and no approval needed
        if execution_mode == 'auto':
            if session.status == "pending":
                session = await execution_engine.start_execution(db, session.id)
        # In HIL mode, execution will wait for approval
        
        return {
            "session_id": session.id,
            "status": session.status,
            "message": "Execution session created" + (" and started" if execution_mode == 'auto' else " - waiting for approval")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing runbook for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute runbook: {str(e)}")


def _normalize_ticket(payload: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Normalize ticket data from various sources"""
    normalized = {
        "external_id": None,
        "title": "",
        "description": "",
        "severity": "medium",
        "environment": "prod",
        "service": None,
        "metadata": {}
    }
    
    if source == "prometheus":
        normalized["title"] = payload.get("groupLabels", {}).get("alertname", "Alert")
        normalized["description"] = payload.get("annotations", {}).get("description", "")
        normalized["severity"] = payload.get("labels", {}).get("severity", "medium")
        normalized["external_id"] = payload.get("fingerprint")
    
    elif source == "datadog":
        normalized["title"] = payload.get("title", "Datadog Alert")
        normalized["description"] = payload.get("text", "")
        normalized["severity"] = payload.get("priority", "normal")
        normalized["external_id"] = payload.get("id")
    
    elif source == "pagerduty":
        normalized["title"] = payload.get("summary", "PagerDuty Incident")
        normalized["description"] = payload.get("description", "")
        normalized["severity"] = payload.get("urgency", "medium")
        normalized["external_id"] = payload.get("id")
    
    else:
        # Generic format
        normalized["title"] = payload.get("title", payload.get("summary", "Alert"))
        normalized["description"] = payload.get("description", payload.get("body", ""))
        normalized["severity"] = payload.get("severity", payload.get("priority", "medium"))
        normalized["external_id"] = payload.get("id", payload.get("external_id"))
    
    normalized["metadata"] = payload
    
    return normalized

