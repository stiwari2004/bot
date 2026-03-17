"""
Mixin: operational methods for RunbookGeneratorService
(generate_runbook, regenerate_step_command, approve_and_index_runbook)
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.schemas.runbook import RunbookResponse
from app.models.runbook import Runbook
from app.services.llm_service import get_llm_service
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class RunbookGeneratorOpsMixin:
    """Operational runbook methods for RunbookGeneratorService."""

    async def generate_runbook(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        top_k: int = 5,
        source_types: Optional[List[str]] = None
    ) -> RunbookResponse:
        """Generate a runbook from issue description using RAG"""

        # Step 1: Search for relevant knowledge (using hybrid search)
        search_results = await self.vector_service.hybrid_search(
            query=issue_description,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=source_types,
            use_reranking=True
        )

        # Step 2: Generate runbook content using retrieved knowledge
        runbook_content = await self.content_builder.generate_content(issue_description, search_results)

        # Step 3: Calculate confidence score
        confidence = self.content_builder.calculate_confidence(search_results)

        # Step 4: Create runbook record
        runbook_environment = "dev" if settings.ENVIRONMENT == "development" else "production"

        runbook = Runbook(
            tenant_id=tenant_id,
            title=f"Runbook: {issue_description[:100]}...",
            body_md=runbook_content,
            meta_data=json.dumps({
                "issue_description": issue_description,
                "sources_used": len(search_results),
                "search_query": issue_description,
                "generated_by": "rag_pipeline"
            }),
            confidence=confidence,
            is_active="active",
            environment=runbook_environment
        )

        db.add(runbook)
        db.commit()
        db.refresh(runbook)

        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )

    async def regenerate_step_command(
        self,
        spec: Dict[str, Any],
        section: str,
        index: int,
        issue_description: str,
        os_type: str,
        human_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Regenerate a single step's command using LLM. Returns updated spec (mutates and returns spec)."""
        section_key = section if section in ("prechecks", "steps", "postchecks") else None
        if not section_key:
            raise ValueError(f"Invalid section: {section}")
        items = spec.get(section_key, [])
        if not isinstance(items, list) or index < 0 or index >= len(items):
            raise ValueError(f"Step index out of range: {section_key}[{index}]")
        step = items[index]
        if not isinstance(step, dict):
            raise ValueError("Step is not a dict")
        current_command = step.get("command", "")
        step_name = step.get("name", f"Step {index + 1}")
        validation_issue = step.get("command_validation_issue", "")
        shell_hint = "PowerShell" if os_type == "Windows" else "bash/Linux"
        human_ctx = (human_context or "").strip()
        prompt = f"""Regenerate ONLY the command for this runbook step. Return nothing but the new command line (no markdown, no explanation).

Issue being addressed: {issue_description[:500]}
Step name: {step_name}
Current command (invalid or to replace): {current_command}
Validation error (if any): {validation_issue or "None"}
Target environment: {shell_hint}
"""
        if human_ctx:
            prompt += f"\nHuman context (MUST follow): {human_ctx}"
        prompt += "\n\nReturn only the new command line, no code fence or explanation."

        llm = get_llm_service()
        if hasattr(llm, "_chat_once"):
            response = await llm._chat_once(prompt, tenant_id=1)
        elif hasattr(llm, "_chat_once_with_system"):
            response = await llm._chat_once_with_system(
                "You are a runbook step assistant. Output only the new command line.",
                prompt,
                tenant_id=1,
            )
        else:
            logger.warning("LLM has no _chat_once; cannot regenerate step command")
            return spec
        if not response or not response.strip():
            logger.warning("LLM returned empty response for step regeneration, keeping original command")
            return spec
        new_command = response.strip()
        if new_command.startswith("```"):
            lines = new_command.split("\n")
            new_command = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        if new_command:
            step["command"] = new_command
            step["command_validation_status"] = "pending_review"
            step["command_review_status"] = "pending"
            step.pop("command_validation_issue", None)
            step.pop("command_suggested_fix", None)
        return spec

    async def approve_and_index_runbook(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> RunbookResponse:
        """Approve a draft runbook and index it for search"""
        return await self.runbook_indexer.approve_and_index_runbook(runbook_id, tenant_id, db)
