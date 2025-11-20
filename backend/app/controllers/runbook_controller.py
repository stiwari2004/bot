"""
Controller for runbook endpoints - handles request/response logic
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.runbook_repository import RunbookRepository
from app.services.runbook.generation import RunbookGeneratorService
from app.services.runbook.duplicate_detection_service import DuplicateDetectionService
from app.services.runbook.ticket_cleanup_service import TicketCleanupService
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.schemas.runbook import RunbookResponse, RunbookUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookController(BaseController):
    """Controller for runbook operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.generator = RunbookGeneratorService()
        self.duplicate_service = DuplicateDetectionService()
        self.cleanup_service = TicketCleanupService()
    
    async def generate_agent_runbook(
        self,
        issue_description: str,
        service: str,
        env: str,
        risk: str,
        ticket_id: Optional[int] = None
    ) -> RunbookResponse:
        """Generate an agent-ready YAML runbook with duplicate detection"""
        try:
            # Check for duplicates
            is_duplicate, existing_runbook = self.duplicate_service.check_duplicate(
                self.db,
                issue_description,
                self.tenant_id
            )
            
            if is_duplicate and existing_runbook:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "duplicate_runbook",
                        "message": f"A runbook already exists for this issue: '{existing_runbook.title}' (ID: {existing_runbook.id})",
                        "existing_runbook_id": existing_runbook.id,
                        "existing_runbook_title": existing_runbook.title
                    }
                )
            
            # Generate runbook
            runbook = await self.generator.generate_agent_runbook(
                issue_description=issue_description,
                tenant_id=self.tenant_id,
                db=self.db,
                service=service,
                env=env,
                risk=risk
            )
            
            # Associate runbook with ticket if ticket_id provided
            if ticket_id:
                self._associate_with_ticket(runbook.id, ticket_id)
            
            return runbook
            
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            error_detail = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            logger.error(f"Runbook generation error: {error_detail}\n{traceback.format_exc()}")
            raise self.handle_error(e, "Agent runbook generation failed")
    
    def _associate_with_ticket(self, runbook_id: int, ticket_id: int):
        """Associate a runbook with a ticket"""
        try:
            ticket = self.db.query(Ticket).filter(
                Ticket.id == ticket_id,
                Ticket.tenant_id == self.tenant_id
            ).first()
            
            if ticket:
                # Initialize meta_data if needed
                if not ticket.meta_data:
                    ticket.meta_data = {}
                
                # Add runbook to matched_runbooks
                if "matched_runbooks" not in ticket.meta_data:
                    ticket.meta_data["matched_runbooks"] = []
                
                # Check if runbook already in list
                existing_ids = [rb.get("id") for rb in ticket.meta_data["matched_runbooks"] if isinstance(rb, dict)]
                if runbook_id not in existing_ids:
                    runbook = self.runbook_repo.get(runbook_id)
                    if runbook:
                        ticket.meta_data["matched_runbooks"].append({
                            "id": runbook.id,
                            "title": runbook.title,
                            "confidence_score": 1.0,  # Perfect match since it was generated for this ticket
                            "reasoning": "Runbook generated for this ticket"
                        })
                        # Trigger SQLAlchemy to detect changes
                        ticket.meta_data = dict(ticket.meta_data)
                        self.db.commit()
                        logger.info(f"Associated runbook {runbook_id} with ticket {ticket_id}")
        except Exception as e:
            logger.warning(f"Failed to associate runbook {runbook_id} with ticket {ticket_id}: {e}")
            # Don't fail the request if association fails
    
    def list_runbooks(
        self,
        skip: int = 0,
        limit: int = 10
    ) -> List[RunbookResponse]:
        """List runbooks for the tenant"""
        try:
            runbooks = self.runbook_repo.get_by_tenant(
                self.tenant_id,
                skip=skip,
                limit=limit,
                active_only=True
            )
            
            result = []
            for runbook in runbooks:
                try:
                    result.append(
                        RunbookResponse(
                            id=runbook.id,
                            title=runbook.title,
                            body_md=runbook.body_md,
                            confidence=float(runbook.confidence) if runbook.confidence else None,
                            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                            status=getattr(runbook, 'status', 'draft'),
                            created_at=runbook.created_at or datetime.now(timezone.utc),
                            updated_at=runbook.updated_at
                        )
                    )
                except Exception as e:
                    logger.error(f"Error serializing runbook {runbook.id}: {e}")
                    # Skip problematic runbooks but continue
                    continue
            return result
        except Exception as e:
            logger.error(f"Error listing runbooks: {e}", exc_info=True)
            # Return empty list instead of raising error for list endpoints
            return []
    
    def get_runbook(self, runbook_id: int) -> RunbookResponse:
        """Get a specific runbook by ID"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            return RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=float(runbook.confidence) if runbook.confidence else None,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                status=getattr(runbook, 'status', 'draft'),
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting runbook: {e}")
            raise self.handle_error(e, "Failed to get runbook")
    
    def update_runbook(
        self,
        runbook_id: int,
        runbook_update: RunbookUpdate
    ) -> RunbookResponse:
        """Update a runbook"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            # Update fields
            if runbook_update.title is not None:
                runbook.title = runbook_update.title
            if runbook_update.body_md is not None:
                runbook.body_md = runbook_update.body_md
            if runbook_update.confidence is not None:
                runbook.confidence = runbook_update.confidence
            if runbook_update.meta_data is not None:
                runbook.meta_data = json.dumps(runbook_update.meta_data)
            
            self.db.commit()
            self.db.refresh(runbook)
            
            return RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=float(runbook.confidence) if runbook.confidence else None,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating runbook: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to update runbook")
    
    def delete_runbook(self, runbook_id: int) -> Dict[str, str]:
        """Delete a runbook (soft delete)"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            # Clean up ticket references
            self.cleanup_service.cleanup_runbook_references(
                self.db,
                runbook_id,
                self.tenant_id
            )
            
            # Archive the runbook
            self.runbook_repo.archive(runbook_id, self.tenant_id)
            
            return {"message": "Runbook deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting runbook: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to delete runbook")
    
    async def approve_runbook(
        self,
        runbook_id: int,
        force_approval: bool = False
    ) -> RunbookResponse:
        """Approve and publish a draft runbook with duplicate detection"""
        try:
            from app.services.duplicate_detector import DuplicateDetectorService
            from app.services.config_service import ConfigService
            
            # Check for duplicates before approval
            if not force_approval:
                duplicate_service = DuplicateDetectorService()
                should_block, duplicates = await duplicate_service.should_block_approval(
                    runbook_id=runbook_id,
                    tenant_id=self.tenant_id,
                    db=self.db
                )
                
                if should_block:
                    threshold = ConfigService.get_duplicate_threshold(self.db, self.tenant_id)
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "duplicate_detected",
                            "message": f"Similar runbook(s) already exist. Confidence threshold not met.",
                            "similar_runbooks": duplicates,
                            "threshold": threshold
                        }
                    )
            
            runbook = await self.generator.approve_and_index_runbook(
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                db=self.db
            )
            return runbook
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error approving runbook: {e}")
            raise self.handle_error(e, "Failed to approve runbook")
    
    async def reindex_runbook(self, runbook_id: int) -> Dict[str, str]:
        """Manually reindex an already approved runbook"""
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            # Index the runbook
            await self.generator._index_runbook_for_search(runbook, self.db)
            
            return {"message": f"Successfully indexed runbook {runbook_id}"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reindexing runbook: {e}")
            raise self.handle_error(e, "Failed to index runbook")


