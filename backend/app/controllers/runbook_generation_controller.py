"""
RunbookGenerationController — runbook generation, approval, and indexing
"""
import json
import traceback
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.ticket_repository import TicketRepository
from app.services import audit_log
from app.services.runbook.generation import RunbookGeneratorService
from app.services.runbook.duplicate_detection_service import DuplicateDetectionService
from app.services.runbook.runbook_spec_helper import RunbookSpecHelper
from app.schemas.runbook import RunbookResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookGenerationController(BaseController):
    """Handles runbook generation, approval, and reindexing."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.generator = RunbookGeneratorService()
        self.duplicate_service = DuplicateDetectionService()

    def _command_review_complete(self, meta_data: Dict[str, Any]):
        return RunbookSpecHelper.command_review_complete(meta_data)

    def _build_operational_context(self, ticket_id: Optional[int]) -> Optional[str]:
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
                    summary = (
                        alert.get("annotations", {}).get("summary")
                        or alert.get("labels", {}).get("alertname")
                        or str(alert)[:200]
                    )
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
        ticket_id: Optional[int] = None,
    ) -> RunbookResponse:
        try:
            is_duplicate, existing_runbook = self.duplicate_service.check_duplicate(
                self.db, issue_description, self.tenant_id
            )
            if is_duplicate and existing_runbook:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "duplicate_runbook",
                        "message": f"A runbook already exists for this issue: '{existing_runbook.title}' (ID: {existing_runbook.id})",
                        "existing_runbook_id": existing_runbook.id,
                        "existing_runbook_title": existing_runbook.title,
                    },
                )

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
            runbook = await self.generator.generate_agent_runbook(
                issue_description=issue_description,
                tenant_id=self.tenant_id,
                db=self.db,
                service=service,
                env=env,
                risk=risk,
                operational_context=operational_context,
            )

            if ticket_id:
                try:
                    runbook_obj = self.runbook_repo.get_by_id_and_tenant(runbook.id, self.tenant_id)
                    if runbook_obj:
                        meta_data = json.loads(runbook_obj.meta_data) if runbook_obj.meta_data else {}
                        meta_data["ticket_id"] = ticket_id
                        self.runbook_repo.update(runbook.id, meta_data=json.dumps(meta_data))
                        logger.info(f"Stored ticket_id {ticket_id} in runbook {runbook.id} meta_data")
                    try:
                        self._associate_with_ticket(runbook.id, ticket_id)
                        logger.info(f"Committed association of runbook {runbook.id} with ticket {ticket_id}")
                    except Exception as assoc_err:
                        logger.warning(f"Association failed but runbook was created: {assoc_err}")
                except Exception as e:
                    logger.warning(f"Failed to store ticket_id in meta_data: {e}")

            try:
                await audit_log.record_event(
                    session_id=0,
                    event_type="runbook_generation_completed",
                    payload={
                        "runbook_id": runbook.id,
                        "ticket_id": ticket_id,
                        "tenant_id": self.tenant_id,
                        "status": "success",
                        "generation_mode": (runbook.meta_data or {}).get("generation_mode", "tier2_generated"),
                    },
                    tenant_id=self.tenant_id,
                )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed (non-critical): {audit_err}")

            return runbook
        except HTTPException:
            raise
        except Exception as e:
            error_detail = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
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

    def _associate_with_ticket(self, runbook_id: int, ticket_id: int) -> bool:
        try:
            ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for association with runbook {runbook_id}")
                return False

            if not ticket.meta_data:
                ticket.meta_data = {}
            if "matched_runbooks" not in ticket.meta_data:
                ticket.meta_data["matched_runbooks"] = []

            existing_ids = [rb.get("id") for rb in ticket.meta_data["matched_runbooks"] if isinstance(rb, dict)]
            if runbook_id not in existing_ids:
                runbook = self.runbook_repo.get(runbook_id)
                if runbook:
                    new_meta = dict(ticket.meta_data)
                    new_meta["matched_runbooks"] = list(new_meta.get("matched_runbooks", []))
                    new_meta["matched_runbooks"].append({
                        "id": runbook.id,
                        "title": runbook.title,
                        "confidence_score": 1.0,
                        "reasoning": "Runbook generated for this ticket",
                    })
                    self.ticket_repo.update_ticket_metadata(
                        ticket_id=ticket_id, tenant_id=self.tenant_id, meta_data=new_meta
                    )
                    updated = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
                    if updated:
                        count = len(updated.meta_data.get("matched_runbooks", [])) if updated.meta_data else 0
                        logger.info(f"Successfully associated runbook {runbook_id} with ticket {ticket_id} ({count} total matches)")
                    return True
                else:
                    logger.warning(f"Runbook {runbook_id} not found for association with ticket {ticket_id}")
                    return False
            else:
                logger.info(f"Runbook {runbook_id} already associated with ticket {ticket_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to associate runbook {runbook_id} with ticket {ticket_id}: {type(e).__name__}: {e}", exc_info=True)
            self.db.rollback()
            return False

    async def approve_runbook(
        self, runbook_id: int, force_approval: bool = False, ticket_id: Optional[int] = None
    ) -> RunbookResponse:
        try:
            from app.services.duplicate_detector import DuplicateDetectorService
            from app.services.config_service import ConfigService

            if not force_approval:
                duplicate_service = DuplicateDetectorService()
                should_block, duplicates = await duplicate_service.should_block_approval(
                    runbook_id=runbook_id, tenant_id=self.tenant_id, db=self.db
                )
                if should_block:
                    threshold = ConfigService.get_duplicate_threshold(self.db, self.tenant_id)
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "duplicate_detected",
                            "message": "Similar runbook(s) already exist. Confidence threshold not met.",
                            "similar_runbooks": duplicates,
                            "threshold": threshold,
                        },
                    )

            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)

            ticket_id_to_associate = ticket_id
            meta_data = None
            if runbook.meta_data:
                try:
                    meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                    if not ticket_id_to_associate:
                        ticket_id_to_associate = meta_data.get("ticket_id")
                except (json.JSONDecodeError, AttributeError):
                    pass

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

            approved_runbook = await self.generator.approve_and_index_runbook(
                runbook_id=runbook_id, tenant_id=self.tenant_id, db=self.db
            )

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
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            await self.generator._index_runbook_for_search(runbook, self.db)
            return {"message": f"Successfully indexed runbook {runbook_id}"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reindexing runbook: {e}")
            raise self.handle_error(e, "Failed to index runbook")

    async def auto_detect_os(self, issue_description: str, env: str) -> str:
        from app.services.cloud_discovery import CloudDiscoveryService
        from app.services.ci_extraction_service import CIExtractionService
        if env in ("Windows", "Linux"):
            return env
        server_name = CIExtractionService._extract_from_text(issue_description)
        if server_name:
            try:
                vm_info = await CloudDiscoveryService.discover_azure_vm(
                    db=self.db, vm_name=server_name, tenant_id=self.tenant_id
                )
                if vm_info and vm_info.get("os_type"):
                    os_lower = vm_info["os_type"].lower()
                    if "windows" in os_lower:
                        return "Windows"
                    elif "linux" in os_lower:
                        return "Linux"
            except Exception:
                pass
        return env
