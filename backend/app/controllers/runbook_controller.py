"""
RunbookController — CRUD, step review, inputs, and utility operations.
Generation / approval is handled by RunbookGenerationController.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.controllers.runbook_generation_controller import RunbookGenerationController
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.metadata_mapping_repository import MetadataMappingRepository
from app.services.runbook.generation import RunbookGeneratorService
from app.services.runbook.duplicate_detection_service import DuplicateDetectionService
from app.services.runbook.ticket_cleanup_service import TicketCleanupService
from app.services.runbook.runbook_spec_helper import RunbookSpecHelper
from app.models.runbook import Runbook
from app.schemas.runbook import RunbookResponse, RunbookUpdate, RunbookFeedbackRequest
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookController(BaseController):
    """CRUD, step review, inputs, mapping flags, and cleanup."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.runbook_repo = RunbookRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.mapping_repo = MetadataMappingRepository(db)
        self.generator = RunbookGeneratorService()
        self.duplicate_service = DuplicateDetectionService()
        self.cleanup_service = TicketCleanupService()
        self._gen_ctrl = RunbookGenerationController(db, tenant_id)

    # ── Delegation to generation controller ──────────────────────────────────

    async def generate_agent_runbook(self, issue_description: str, service: str, env: str,
                                     risk: str, ticket_id: Optional[int] = None) -> RunbookResponse:
        return await self._gen_ctrl.generate_agent_runbook(issue_description, service, env, risk, ticket_id)

    async def approve_runbook(self, runbook_id: int, force_approval: bool = False,
                              ticket_id: Optional[int] = None) -> RunbookResponse:
        return await self._gen_ctrl.approve_runbook(runbook_id, force_approval, ticket_id)

    async def reindex_runbook(self, runbook_id: int) -> Dict[str, str]:
        return await self._gen_ctrl.reindex_runbook(runbook_id)

    async def auto_detect_os(self, issue_description: str, env: str) -> str:
        return await self._gen_ctrl.auto_detect_os(issue_description, env)

    # ── Step review helpers ───────────────────────────────────────────────────

    def _command_review_complete(self, meta_data: Dict[str, Any]) -> Tuple[bool, int]:
        return RunbookSpecHelper.command_review_complete(meta_data)

    def _get_step_at(self, spec: Dict[str, Any], section: str, index: int) -> Optional[Dict[str, Any]]:
        return RunbookSpecHelper.get_step_at(spec, section, index)

    def _body_md_from_spec(self, spec: Dict[str, Any]) -> str:
        return RunbookSpecHelper.body_md_from_spec(spec)

    def _persist_spec_to_runbook(self, runbook: Runbook, meta_data: Dict[str, Any]) -> None:
        spec = meta_data.get("runbook_spec")
        if not spec:
            return
        runbook.meta_data = json.dumps(meta_data)
        runbook.body_md = self._body_md_from_spec(spec)
        self.db.commit()
        self.db.refresh(runbook)

    def _load_runbook_meta(self, runbook_id: int) -> Tuple[Runbook, Dict[str, Any], Dict[str, Any]]:
        """Return (runbook, meta_data, spec) or raise."""
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
        spec = meta_data.get("runbook_spec")
        if not spec:
            raise HTTPException(status_code=400, detail="Runbook has no runbook_spec")
        return runbook, meta_data, spec

    # ── Step review ───────────────────────────────────────────────────────────

    def approve_step(self, runbook_id: int, section: str, index: int) -> RunbookResponse:
        runbook, meta_data, spec = self._load_runbook_meta(runbook_id)
        step = self._get_step_at(spec, section, index)
        if not step:
            raise HTTPException(status_code=404, detail=f"Step not found: section={section}, index={index}")
        step["command_review_status"] = "approved_by_human"
        step["command_validation_status"] = "valid"
        self._persist_spec_to_runbook(runbook, meta_data)
        return self.get_runbook(runbook_id)

    def update_step_command(self, runbook_id: int, section: str, index: int, command: str) -> RunbookResponse:
        runbook, meta_data, spec = self._load_runbook_meta(runbook_id)
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
        return {"command_review_ready": ready, "steps_pending_review": pending, "steps": steps_out}

    async def regenerate_step_command(self, runbook_id: int, section: str, index: int,
                                      human_context: Optional[str] = None) -> RunbookResponse:
        runbook, meta_data, spec = self._load_runbook_meta(runbook_id)
        step = self._get_step_at(spec, section, index)
        if not step:
            raise HTTPException(status_code=404, detail=f"Step not found: section={section}, index={index}")
        issue_description = meta_data.get("issue_description", "")
        env = spec.get("env", "prod")
        os_type = "Windows" if env == "Windows" else "Linux"
        updated_spec = await self.generator.regenerate_step_command(
            spec=spec, section=section, index=index,
            issue_description=issue_description, os_type=os_type, human_context=human_context,
        )
        meta_data["runbook_spec"] = updated_spec
        self._persist_spec_to_runbook(runbook, meta_data)
        return self.get_runbook(runbook_id)

    async def apply_step_feedback(self, runbook_id: int, feedback_request: RunbookFeedbackRequest) -> RunbookResponse:
        from app.services.runbook.generation import RunbookRefinerService
        from app.services.runbook.generation.runbook_refiner_service import FeedbackItem

        runbook, meta_data, spec = self._load_runbook_meta(runbook_id)
        issue_description = meta_data.get("issue_description", "")
        os_type = spec.get("env", "Linux")
        items = [FeedbackItem(section=s.section, index=s.index, feedback=s.feedback) for s in feedback_request.steps]
        refiner = RunbookRefinerService()
        patched_spec = await refiner.apply_human_feedback(
            spec=spec, feedback_items=items, issue_description=issue_description,
            os_type=os_type, tenant_id=self.tenant_id,
        )
        meta_data["runbook_spec"] = patched_spec
        meta_data["review_required"] = True
        self._persist_spec_to_runbook(runbook, meta_data)
        logger.info("Applied %d human feedback item(s) to runbook %d", len(items), runbook_id)
        return self.get_runbook(runbook_id)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _to_response(self, runbook: Runbook) -> RunbookResponse:
        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=float(runbook.confidence) if runbook.confidence else None,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            status=getattr(runbook, "status", "draft"),
            created_at=runbook.created_at or datetime.now(timezone.utc),
            updated_at=runbook.updated_at,
        )

    def list_runbooks(self, skip: int = 0, limit: int = 10) -> List[RunbookResponse]:
        try:
            runbooks = self.runbook_repo.get_by_tenant(self.tenant_id, skip=skip, limit=limit, active_only=True)
            result = []
            for rb in runbooks:
                try:
                    result.append(self._to_response(rb))
                except Exception as e:
                    logger.error(f"Error serializing runbook {rb.id}: {e}")
            return result
        except Exception as e:
            logger.error(f"Error listing runbooks: {e}", exc_info=True)
            from sqlalchemy.exc import OperationalError, DisconnectionError
            error_str = str(e).lower()
            if isinstance(e, (OperationalError, DisconnectionError)) or any(
                k in error_str for k in ("connection", "database", "operational")
            ):
                raise
            return []

    def get_runbook(self, runbook_id: int) -> RunbookResponse:
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            return self._to_response(runbook)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting runbook: {e}")
            raise self.handle_error(e, "Failed to get runbook")

    def update_runbook(self, runbook_id: int, runbook_update: RunbookUpdate) -> RunbookResponse:
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            update_data = {}
            if runbook_update.title is not None:
                update_data["title"] = runbook_update.title
            if runbook_update.body_md is not None:
                update_data["body_md"] = runbook_update.body_md
            if runbook_update.confidence is not None:
                update_data["confidence"] = runbook_update.confidence
            if runbook_update.meta_data is not None:
                update_data["meta_data"] = json.dumps(runbook_update.meta_data)
            updated = self.runbook_repo.update(runbook_id, **update_data)
            if not updated:
                raise self.not_found("Runbook", runbook_id)
            return self._to_response(updated)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating runbook: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to update runbook")

    def delete_runbook(self, runbook_id: int) -> Dict[str, str]:
        try:
            runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            self.cleanup_service.cleanup_runbook_references(self.db, runbook_id, self.tenant_id)
            self.runbook_repo.archive(runbook_id, self.tenant_id)
            return {"message": "Runbook deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting runbook: {e}")
            self.db.rollback()
            raise self.handle_error(e, "Failed to delete runbook")

    # ── Inputs, flags, cleanup ────────────────────────────────────────────────

    async def extract_inputs(self, ticket_id: int, runbook_id: int) -> Dict[str, Any]:
        from app.services.runbook.input_extractor import RunbookInputExtractor
        ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
        if not ticket:
            raise self.not_found("Ticket", ticket_id)
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        extractor = RunbookInputExtractor()
        return await extractor.extract_inputs(ticket, runbook, self.db)

    def learn_from_user_input(self, ticket_id: int, runbook_id: int, inputs: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.runbook.input_learning_service import InputLearningService
        ticket = self.ticket_repo.get_by_id_and_tenant(ticket_id, self.tenant_id)
        if not ticket:
            raise self.not_found("Ticket", ticket_id)
        runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
        if not runbook:
            raise self.not_found("Runbook", runbook_id)
        svc = InputLearningService(self.db)
        return svc.learn_from_user_input(ticket, inputs, runbook)

    def get_mapping_flags(self, min_confidence: float) -> List[Dict[str, Any]]:
        flags = self.mapping_repo.get_low_confidence_flags(self.tenant_id, min_confidence)
        return [
            {
                "id": f.id,
                "input_name": f.input_name,
                "source": f.source,
                "metadata_path": f.metadata_path,
                "confidence": f.confidence,
                "usage_count": f.usage_count,
                "last_used_at": f.last_used_at.isoformat() if f.last_used_at else None,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in flags
        ]

    def cleanup_orphaned_runbook_references(self) -> Dict[str, Any]:
        from sqlalchemy.orm.attributes import flag_modified

        tickets = self.ticket_repo.get_all_with_metadata_for_tenant(self.tenant_id)
        active_ids = self.runbook_repo.get_active_ids_for_tenant(self.tenant_id)

        updated_count = 0
        removed_count = 0
        for ticket in tickets:
            if not ticket.meta_data:
                continue
            meta = (
                json.loads(ticket.meta_data) if isinstance(ticket.meta_data, str) else dict(ticket.meta_data)
            )
            updated = False

            if "matched_runbooks" in meta and isinstance(meta["matched_runbooks"], list):
                before = len(meta["matched_runbooks"])
                meta["matched_runbooks"] = [
                    rb for rb in meta["matched_runbooks"]
                    if isinstance(rb, dict) and rb.get("id") in active_ids
                ]
                removed = before - len(meta["matched_runbooks"])
                if removed:
                    updated = True
                    removed_count += removed

            if "runbook_id" in meta:
                rid = meta["runbook_id"]
                if isinstance(rid, int) and rid not in active_ids:
                    del meta["runbook_id"]
                    updated = True
                    removed_count += 1

            if updated:
                ticket.meta_data = meta
                flag_modified(ticket, "meta_data")
                updated_count += 1

        if updated_count:
            self.db.commit()

        return {
            "message": "Cleanup complete" if updated_count else "No orphaned references found",
            "tickets_updated": updated_count,
            "references_removed": removed_count,
        }
