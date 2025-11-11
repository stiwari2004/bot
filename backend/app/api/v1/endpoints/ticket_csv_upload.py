"""
CSV Ticket Upload Endpoint
Allows bulk upload of tickets from CSV files
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.ticket import Ticket
from app.services.ticket_analysis_service import TicketAnalysisService
from app.services.ticket_status_service import get_ticket_status_service
from app.services.runbook_search import RunbookSearchService
from app.services.execution_engine import ExecutionEngine
from app.core.logging import get_logger
from datetime import datetime
import csv
import io

router = APIRouter()
logger = get_logger(__name__)


@router.post("/tickets/upload-csv")
async def upload_tickets_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auto_execute: bool = False
):
    """
    Upload tickets from CSV file
    
    CSV Format:
    title,description,severity,environment,service,source
    
    Example:
    Database connection timeout,Unable to connect to PostgreSQL,high,prod,database,prometheus
    """
    try:
        tenant_id = 1  # Demo tenant
        
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        tickets_created = []
        errors = []
        
        analysis_service = TicketAnalysisService()
        ticket_status_service = get_ticket_status_service()
        runbook_search_service = RunbookSearchService()
        execution_engine = ExecutionEngine()
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Create ticket
                ticket = Ticket(
                    tenant_id=tenant_id,
                    source=row.get("source", "csv_upload"),
                    title=row.get("title", "Untitled Ticket"),
                    description=row.get("description", ""),
                    severity=row.get("severity", "medium"),
                    environment=row.get("environment", "prod"),
                    service=row.get("service"),
                    status="open",
                    received_at=datetime.utcnow()
                )
                
                db.add(ticket)
                db.commit()
                db.refresh(ticket)
                
                # Analyze ticket
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
                
                # Close ticket if false positive
                if analysis_result["classification"] == "false_positive" and confidence >= 0.8:
                    ticket_status_service.update_ticket_on_false_positive(db, ticket.id)
                
                # If true positive and auto_execute enabled, try to find and execute runbook
                elif auto_execute and analysis_result["classification"] != "false_positive":
                    matching_runbooks = await runbook_search_service.search_similar_runbooks(
                        issue_description=ticket.description or ticket.title,
                        tenant_id=tenant_id,
                        db=db,
                        top_k=1,
                        min_confidence=0.7
                    )
                    
                    if matching_runbooks and len(matching_runbooks) > 0:
                        best_match = matching_runbooks[0]
                        runbook_id = best_match.get("id") or best_match.get("runbook_id")
                        match_confidence = best_match.get("confidence_score", 0.0)
                        
                        if match_confidence >= 0.8 and runbook_id:
                            try:
                                from app.models.runbook import Runbook
                                runbook = db.query(Runbook).filter(
                                    Runbook.id == runbook_id,
                                    Runbook.tenant_id == tenant_id,
                                    Runbook.status == "approved"
                                ).first()
                                
                                if runbook:
                                    session = await execution_engine.create_execution_session(
                                        db=db,
                                        runbook_id=runbook_id,
                                        tenant_id=tenant_id,
                                        ticket_id=ticket.id,
                                        issue_description=ticket.description or ticket.title,
                                        user_id=None
                                    )
                                    
                                    ticket_status_service.update_ticket_on_execution_start(db, ticket.id)
                                    
                                    if session.status == "pending":
                                        session = await execution_engine.start_execution(db, session.id)
                                    
                                    tickets_created.append({
                                        "ticket_id": ticket.id,
                                        "title": ticket.title,
                                        "status": ticket.status,
                                        "execution_session_id": session.id,
                                        "auto_executed": True
                                    })
                                else:
                                    tickets_created.append({
                                        "ticket_id": ticket.id,
                                        "title": ticket.title,
                                        "status": ticket.status,
                                        "auto_executed": False,
                                        "reason": "Runbook not found or not approved"
                                    })
                            except Exception as e:
                                logger.error(f"Failed to auto-execute for ticket {ticket.id}: {e}")
                                tickets_created.append({
                                    "ticket_id": ticket.id,
                                    "title": ticket.title,
                                    "status": ticket.status,
                                    "auto_executed": False,
                                    "error": str(e)
                                })
                        else:
                            tickets_created.append({
                                "ticket_id": ticket.id,
                                "title": ticket.title,
                                "status": ticket.status,
                                "auto_executed": False,
                                "reason": f"Low confidence match ({match_confidence:.2f})"
                            })
                    else:
                        tickets_created.append({
                            "ticket_id": ticket.id,
                            "title": ticket.title,
                            "status": ticket.status,
                            "auto_executed": False,
                            "reason": "No matching runbook found"
                        })
                else:
                    tickets_created.append({
                        "ticket_id": ticket.id,
                        "title": ticket.title,
                        "status": ticket.status,
                        "classification": ticket.classification,
                        "auto_executed": False
                    })
                
                db.commit()
                
            except Exception as e:
                errors.append({
                    "row": row_num,
                    "error": str(e),
                    "data": row
                })
                logger.error(f"Error processing CSV row {row_num}: {e}")
        
        return {
            "message": f"Processed {len(tickets_created)} tickets",
            "tickets_created": tickets_created,
            "errors": errors,
            "total": len(tickets_created) + len(errors)
        }
        
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")




