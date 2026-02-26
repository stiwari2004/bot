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
from app.services import audit_log
from app.repositories.ticket_repository import TicketRepository
from app.services.runbook.generation import RunbookGeneratorService
from app.services.runbook.duplicate_detection_service import DuplicateDetectionService
from app.services.runbook.ticket_cleanup_service import TicketCleanupService
from app.models.runbook import Runbook
from app.models.ticket import Ticket
from app.schemas.runbook import RunbookResponse, RunbookUpdate
from app.core.logging import get_logger
from app.core.transactions import transaction
from typing import Tuple

logger = get_logger(__name__)


class RunbookController(BaseController):
    """Controller for runbook operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.generator = RunbookGeneratorService()
        self.duplicate_service = DuplicateDetectionService()
        self.cleanup_service = TicketCleanupService()

    def _command_review_complete(self, meta_data: Dict[str, Any]) -> Tuple[bool, int]:
        """Check if all steps with invalid/pending_review validation are approved by human.
        Returns (ready, steps_pending_review count)."""
        spec = meta_data.get("runbook_spec") or meta_data
        if not spec:
            return True, 0
        pending = 0
        for section_key in ("prechecks", "steps", "postchecks"):
            for step in spec.get(section_key, []):
                if not isinstance(step, dict):
                    continue
                status = step.get("command_validation_status")
                review = step.get("command_review_status")
                if status in ("invalid", "pending_review") and review != "approved_by_human":
                    pending += 1
        return pending == 0, pending

    def _get_step_at(self, spec: Dict[str, Any], section: str, index: int) -> Optional[Dict[str, Any]]:
        """Get step dict at section and 0-based index. Returns None if out of range."""
        section_key = section if section in ("prechecks", "steps", "postchecks") else None
        if not section_key:
            return None
        items = spec.get(section_key, [])
        if not isinstance(items, list) or index < 0 or index >= len(items):
            return None
        step = items[index]
        return step if isinstance(step, dict) else None

    def _body_md_from_spec(self, spec: Dict[str, Any]) -> str:
        """Build body_md YAML code fence from spec (same order as generator)."""
        import yaml
        from collections import OrderedDict
        order = ['runbook_id', 'version', 'title', 'service', 'env', 'risk', 'description',
                 'owner', 'last_tested', 'review_required', 'inputs', 'prechecks', 'steps', 'postchecks']
        ordered = OrderedDict()
        for key in order:
            if key in spec:
                ordered[key] = spec[key]
        for key, value in spec.items():
            if key not in ordered:
                ordered[key] = value
        spec_dict = dict(ordered)
        runbook_yaml = yaml.safe_dump(spec_dict, sort_keys=False, default_flow_style=False, width=120)
        return f"""# Agent Runbook (YAML)

```yaml
{runbook_yaml}
```
"""

    def _persist_spec_to_runbook(self, runbook: Runbook, meta_data: Dict[str, Any]) -> None:
        """Update runbook.meta_data and runbook.body_md from meta_data (with runbook_spec) and commit."""
        spec = meta_data.get("runbook_spec")
        if not spec:
            return
        runbook.meta_data = json.dumps(meta_data)
        runbook.body_md = self._body_md_from_spec(spec)
        self.db.commit()
        self.db.refresh(runbook)

    def approve_step(self, runbook_id: int, section: str, index: int) -> RunbookResponse:
        """Mark step at (section, 0-based index) as approved_by_human."""
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
        spec = meta_data.get("runbook_spec")
        if not spec:
            raise HTTPException(status_code=400, detail="Runbook has no runbook_spec")
        step = self._get_step_at(spec, section, index)
        if not step:
            raise HTTPException(status_code=404, detail=f"Step not found: section={section}, index={index}")
        step["command_review_status"] = "approved_by_human"
        step["command_validation_status"] = "valid"
        self._persist_spec_to_runbook(runbook, meta_data)
        return self.get_runbook(runbook_id)

    def update_step_command(self, runbook_id: int, section: str, index: int, command: str) -> RunbookResponse:
        """Set step command (e.g. apply suggested fix) and mark pending_review."""
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
        spec = meta_data.get("runbook_spec")
        if not spec:
            raise HTTPException(status_code=400, detail="Runbook has no runbook_spec")
        step = self._get_step_at(spec, section, index)
        if not step:
            raise HTTPException(status_code=404, detail=f"Step not found: section={section}, index={index}")
        step["command"] = command
        step["command_validation_status"] = "pending_review"
        step["command_review_status"] = "pending"
        step.pop("command_validation_issue", None)
        step.pop("command_suggested_fix", None)
        self._persist_spec_to_runbook(runbook, meta_data)
        return self.get_runbook(runbook_id)

    def get_review_status(self, runbook_id: int) -> Dict[str, Any]:
        """Return command_review_ready, steps_pending_review, and steps list for UI."""
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
        ready, pending = self._command_review_complete(meta_data)
        spec = meta_data.get("runbook_spec") or {}
        steps_out = []
        for section_key in ("prechecks", "steps", "postchecks"):
            for idx, step in enumerate(spec.get(section_key, [])):
                if not isinstance(step, dict):
                    continue
                steps_out.append({
                    "section": section_key,
                    "index": idx,
                    "command_validation_status": step.get("command_validation_status"),
                    "command_review_status": step.get("command_review_status"),
                    "command_validation_issue": step.get("command_validation_issue"),
                    "command_suggested_fix": step.get("command_suggested_fix"),
                    "command": (step.get("command") or "")[:200],
                })
        return {
            "command_review_ready": ready,
            "steps_pending_review": pending,
            "steps": steps_out,
        }

    async def regenerate_step_command(
        self, runbook_id: int, section: str, index: int, human_context: Optional[str] = None
    ) -> RunbookResponse:
        """Regenerate a single step's command using LLM with optional human context."""
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
        spec = meta_data.get("runbook_spec")
        if not spec:
            raise HTTPException(status_code=400, detail="Runbook has no runbook_spec")
        step = self._get_step_at(spec, section, index)
        if not step:
            raise HTTPException(status_code=404, detail=f"Step not found: section={section}, index={index}")
        issue_description = meta_data.get("issue_description", "")
        env = spec.get("env", "prod")
        os_type = "Windows" if env == "Windows" else "Linux"
        updated_spec = await self.generator.regenerate_step_command(
            spec=spec,
            section=section,
            index=index,
            issue_description=issue_description,
            os_type=os_type,
            human_context=human_context,
        )
        meta_data["runbook_spec"] = updated_spec
        self._persist_spec_to_runbook(runbook, meta_data)
        return self.get_runbook(runbook_id)

    def _build_operational_context(self, ticket_id: Optional[int]) -> Optional[str]:
        """Build a short operational context string from ticket (and optional alert) for CAG."""
        if not ticket_id:
            return None
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            if not ticket:
                return None
            parts = [
                f"Ticket: {ticket.title or 'Untitled'}",
                f"Source: {ticket.source or 'unknown'}",
                f"Severity: {ticket.severity or 'unknown'}",
                f"Service: {ticket.service or 'unknown'}",
                f"Environment: {ticket.environment or 'unknown'}",
            ]
            if ticket.description:
                snippet = (ticket.description or "").strip()[:500]
                if snippet:
                    parts.append(f"Description: {snippet}")
            if ticket.raw_payload and isinstance(ticket.raw_payload, dict):
                alert = ticket.raw_payload.get("alert", ticket.raw_payload.get("alerts", []))
                if isinstance(alert, list) and alert:
                    alert = alert[0]
                if isinstance(alert, dict):
                    summary = alert.get("annotations", {}).get("summary") or alert.get("labels", {}).get("alertname") or str(alert)[:200]
                    if summary:
                        parts.append(f"Alert: {summary}")
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"Could not build operational context for ticket {ticket_id}: {e}")
            return None

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
            
            # Audit log (non-blocking - don't fail request if audit logging fails)
            try:
                await audit_log.record_event(
                    session_id=0,
                    event_type="runbook_generation_started",
                    payload={
                        "runbook_id": None,
                        "ticket_id": ticket_id,
                        "issue_description_preview": (issue_description or "")[:200],
                        "tenant_id": self.tenant_id,
                    },
                    tenant_id=self.tenant_id,
                )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed (non-critical): {audit_err}")
            operational_context = self._build_operational_context(ticket_id)
            # Generate runbook
            runbook = await self.generator.generate_agent_runbook(
                issue_description=issue_description,
                tenant_id=self.tenant_id,
                db=self.db,
                service=service,
                env=env,
                risk=risk,
                operational_context=operational_context,
            )
            
            # Store ticket_id in runbook meta_data for later association during approval
            # Do this AFTER runbook generation is complete and committed
            if ticket_id:
                import json
                try:
                    # Get latest runbook state and update metadata using repository
                    runbook_obj = self.runbook_repo.get_by_id_and_tenant(runbook.id, self.tenant_id)
                    if runbook_obj:
                        meta_data = json.loads(runbook_obj.meta_data) if runbook_obj.meta_data else {}
                        meta_data["ticket_id"] = ticket_id
                        # Use repository update method
                        self.runbook_repo.update(runbook.id, meta_data=json.dumps(meta_data))
                        logger.info(f"Stored ticket_id {ticket_id} in runbook {runbook.id} meta_data")
                    
                    # Associate with ticket AFTER everything is committed
                    # Use a separate try/except so association failure doesn't break the response
                    try:
                        self._associate_with_ticket(runbook.id, ticket_id)
                        logger.info(f"Committed association of runbook {runbook.id} with ticket {ticket_id}")
                    except Exception as assoc_err:
                        logger.warning(f"Association failed but runbook was created: {assoc_err}")
                        # Don't fail the request - association can happen later during approval
                except Exception as e:
                    logger.warning(f"Failed to store ticket_id in meta_data: {e}")
                    # Don't fail the request - this is not critical
            
            # Audit log success (non-blocking)
            try:
                await audit_log.record_event(
                    session_id=0,
                    event_type="runbook_generation_completed",
                    payload={
                        "runbook_id": runbook.id,
                        "ticket_id": ticket_id,
                        "tenant_id": self.tenant_id,
                        "status": "success",
                    },
                    tenant_id=self.tenant_id,
                )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed (non-critical): {audit_err}")
            return runbook
            
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            error_detail = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            # Audit log failure (non-blocking - don't fail if audit logging itself fails)
            try:
                await audit_log.record_event(
                    session_id=0,
                    event_type="runbook_generation_completed",
                    payload={
                        "runbook_id": None,
                        "ticket_id": ticket_id,
                        "tenant_id": self.tenant_id,
                        "status": "failed",
                        "error_preview": error_detail[:500],
                    },
                    tenant_id=self.tenant_id,
                )
            except Exception:
                pass
            logger.error(f"Runbook generation error: {error_detail}\n{traceback.format_exc()}")
            raise self.handle_error(e, "Agent runbook generation failed")
    
    def _associate_with_ticket(self, runbook_id: int, ticket_id: int):
        """Associate a runbook with a ticket"""
        try:
            from sqlalchemy.orm.attributes import flag_modified
            
            # Use repository to get ticket
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for association with runbook {runbook_id}")
                return False
            
            # Initialize meta_data if needed (JSON column handles dict automatically)
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
                    # Create a new dict to ensure SQLAlchemy detects the change
                    new_meta_data = dict(ticket.meta_data)
                    new_meta_data["matched_runbooks"] = list(new_meta_data.get("matched_runbooks", []))
                    new_meta_data["matched_runbooks"].append({
                        "id": runbook.id,
                        "title": runbook.title,
                        "confidence_score": 1.0,  # Perfect match since it was generated for this ticket
                        "reasoning": "Runbook generated for this ticket"
                    })
                    
                    # Update ticket metadata using repository
                    self.ticket_repo.update_ticket_metadata(
                        ticket_id=ticket_id,
                        tenant_id=self.tenant_id,
                        meta_data=new_meta_data
                    )
                    
                    # Verify the change was saved
                    updated_ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
                    if updated_ticket:
                        matched_count = len(updated_ticket.meta_data.get("matched_runbooks", [])) if updated_ticket.meta_data else 0
                        logger.info(f"✅ Successfully associated runbook {runbook_id} ({runbook.title}) with ticket {ticket_id}")
                        logger.info(f"✅ Ticket {ticket_id} now has {matched_count} matched runbook(s) in database")
                    
                    return True
                else:
                    logger.warning(f"Runbook {runbook_id} not found for association with ticket {ticket_id}")
                    return False
            else:
                logger.info(f"Runbook {runbook_id} already associated with ticket {ticket_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to associate runbook {runbook_id} with ticket {ticket_id}: {type(e).__name__}: {e}", exc_info=True)
            self.db.rollback()
            return False
    
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
            # Re-raise database connection errors so endpoint can handle them
            from sqlalchemy.exc import OperationalError, DisconnectionError
            error_str = str(e).lower()
            if isinstance(e, (OperationalError, DisconnectionError)) or \
               "connection" in error_str or "database" in error_str or "operational" in error_str:
                raise  # Re-raise database errors
            # Return empty list for other errors (e.g., serialization issues)
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
            
            # Update fields using repository
            update_data = {}
            if runbook_update.title is not None:
                update_data["title"] = runbook_update.title
            if runbook_update.body_md is not None:
                update_data["body_md"] = runbook_update.body_md
            if runbook_update.confidence is not None:
                update_data["confidence"] = runbook_update.confidence
            if runbook_update.meta_data is not None:
                update_data["meta_data"] = json.dumps(runbook_update.meta_data)
            
            updated_runbook = self.runbook_repo.update(runbook_id, **update_data)
            if not updated_runbook:
                raise self.not_found("Runbook", runbook_id)
            runbook = updated_runbook
            
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
        force_approval: bool = False,
        ticket_id: Optional[int] = None
    ) -> RunbookResponse:
        """Approve and publish a draft runbook with duplicate detection"""
        try:
            from app.services.duplicate_detector import DuplicateDetectorService
            from app.services.config_service import ConfigService
            import json
            
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
            
            # Get runbook to check for ticket_id in meta_data
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            # Check if ticket_id is in meta_data (from generation) or passed as parameter
            ticket_id_to_associate = ticket_id
            meta_data = None
            if runbook.meta_data:
                try:
                    meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                    if not ticket_id_to_associate:
                        ticket_id_to_associate = meta_data.get("ticket_id")
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Command review gate: require all invalid/pending_review steps to be approved_by_human
            if not force_approval and meta_data:
                ready, steps_pending = self._command_review_complete(meta_data)
                if not ready:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "detail": "Command review required",
                            "code": "command_review_required",
                            "message": (
                                f"{steps_pending} step(s) have invalid or unreviewed commands. "
                                "Review or approve each step before approving the runbook."
                            ),
                            "steps_pending_review": steps_pending,
                        },
                    )
            
            # Approve the runbook
            approved_runbook = await self.generator.approve_and_index_runbook(
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                db=self.db
            )
            
            # Associate with ticket if ticket_id found
            if ticket_id_to_associate:
                logger.info(f"Associating approved runbook {runbook_id} with ticket {ticket_id_to_associate}")
                self._associate_with_ticket(runbook_id, ticket_id_to_associate)
            
            return approved_runbook
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


