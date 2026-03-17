"""
Main runbook generator service that orchestrates all generation components
"""
import asyncio
import json
import re
import traceback
import yaml
from collections import OrderedDict
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.search import SearchResult
from app.schemas.runbook import RunbookResponse
from app.models.runbook import Runbook
from app.services.llm_service import get_llm_service
from app.services.llm_budget_manager import LLMBudgetExceeded, LLMRateLimitExceeded
from app.core.logging import get_logger

from app.services.runbook.generation.service_classifier import ServiceClassifier
from app.services.runbook.generation.ticket_classifier import TicketClassifierService, TicketClassification
from app.services.runbook.generation.tiered_generation_service import TieredGenerationService
from app.services.runbook.generation.content_builder import ContentBuilder
from app.services.runbook.generation.yaml_processor import YamlProcessor
from app.services.runbook.generation.runbook_indexer import RunbookIndexer
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.services.runbook.generation.runbook_command_validator import RunbookCommandValidator
from app.services.runbook.generation.runbook_critic_service import RunbookCriticService
from app.services.runbook.generation.yaml_extractor import YamlExtractor
from app.services.runbook.generation.yaml_parser import YamlParser
from app.services.runbook.generation.spec_post_processor import SpecPostProcessor
from app.services.runbook.generation.citation_manager import CitationManager
from app.services.runbook.generation.yaml_generation_pipeline import YamlGenerationPipeline
from app.services.runbook.generation.validation_pipeline import ValidationPipeline
from app.services.execution.command_learning_service import CommandLearningService
from app.services.runbook.generation.runbook_generator_helpers_mixin import RunbookGeneratorHelpersMixin
from app.services.runbook.generation.runbook_generator_ops_mixin import RunbookGeneratorOpsMixin
from app.config import runbook_structure
from app.core.config import settings

logger = get_logger(__name__)

# Shared keyword lists used by multiple methods (define once, reference everywhere)
_REMEDIATION_KEYWORDS = [
    "stop-process", "restart-service", "kill", "systemctl restart",
    "clear", "delete", "remove", "fix", "repair", "resolve", "restart", "stop"
]
_DIAGNOSTIC_KEYWORDS = [
    "get-process", "get-counter", "get-service", "get-eventlog",
    "top", "ps", "free", "df", "select-object", "where-object", "sort-object"
]

# Canonical section order for runbook YAML serialization
_SPEC_SECTION_ORDER = [
    "runbook_id", "version", "title", "service", "env", "risk", "description",
    "owner", "last_tested", "review_required", "inputs", "prechecks", "steps", "postchecks",
]


def _order_spec_fields(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return spec dict with sections in canonical order."""
    ordered = OrderedDict()
    for key in _SPEC_SECTION_ORDER:
        if key in spec:
            ordered[key] = spec[key]
    for key, value in spec.items():
        if key not in ordered:
            ordered[key] = value
    return dict(ordered)


class RunbookGeneratorService(RunbookGeneratorHelpersMixin, RunbookGeneratorOpsMixin):
    """Service for generating runbooks from search results using RAG"""

    def __init__(self):
        # VectorStoreService created lazily only when needed (to avoid loading embedding model)
        self._vector_service = None
        self.service_classifier = ServiceClassifier()
        self.ticket_classifier = TicketClassifierService()
        self.tiered_service = TieredGenerationService()
        self.content_builder = ContentBuilder()
        self.yaml_processor = YamlProcessor()
        self.runbook_indexer = RunbookIndexer()
        self.command_validator = RunbookCommandValidator()
        self.quality_validator = RunbookQualityValidator()
        self.critic_service = RunbookCriticService()
        # New extraction modules
        self.yaml_extractor = YamlExtractor()
        self.yaml_parser = YamlParser()
        self.spec_post_processor = SpecPostProcessor()
        self.citation_manager = CitationManager()
        # Pipeline modules
        self.yaml_pipeline = YamlGenerationPipeline()
        self.validation_pipeline = ValidationPipeline()
        self.learning_service = CommandLearningService()

    @property
    def vector_service(self):
        """Lazy property to create VectorStoreService only when needed"""
        if self._vector_service is None:
            from app.services.vector_store import VectorStoreService
            self._vector_service = VectorStoreService()
        return self._vector_service

    async def generate_agent_runbook(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        service: str = "auto",
        env: str = "prod",
        risk: str = "low",
        top_k: int = 5,
        operational_context: Optional[str] = None,
    ) -> RunbookResponse:
        """Generate an agent-executable, atomic YAML runbook.
        Auto-detects service type from issue description if service="auto".
        """
        # Normalize service type: handle OS types (Windows/Linux) as server CI type
        # Separate CI type from OS type
        os_type = None
        ci_type = service

        if service in ["Windows", "Linux"]:
            # User provided OS type, treat as server CI type
            ci_type = "server"
            os_type = service
            logger.info(f"Detected OS type '{os_type}' from service parameter, using CI type 'server'")
        elif service == "auto":
            # Auto-detect CI type
            ci_type = await self.service_classifier.detect_service_type(issue_description)
            logger.info(f"Auto-detected CI type: {ci_type}")

            # For servers, try to detect OS type from issue description
            if ci_type == "server":
                os_type = await self.service_classifier.detect_os_type(issue_description)
                if os_type:
                    logger.info(f"Auto-detected OS type: {os_type}")

        # Use CI type for prompt selection (not OS type)
        service = ci_type

        # Extract specific issue type (free — keyword-based, zero LLM cost)
        issue_type = self.service_classifier.detect_issue_type(issue_description, service)
        logger.info(f"Detected issue_type={issue_type} for service={service}")

        # Tiered generation: check for Tier 0 (reuse) or Tier 1 (adapt) before full Tier 2 generation
        tiered_response = await self.tiered_service.select_tier_and_execute(
            issue_description=issue_description,
            tenant_id=tenant_id,
            db=db,
            service=service,
            env=env,
            risk=risk,
            os_type=os_type,
        )
        if tiered_response is not None:
            generation_mode = tiered_response.meta_data.get("generation_mode", "tier0_reuse")
            logger.info(f"Tiered generation: returning {generation_mode} result (runbook_id={tiered_response.id})")
            return tiered_response

        # Tier 2: LLM classification + RAG search run in parallel (classification
        # latency hidden behind the search round-trip).
        try:
            classification, search_results = await asyncio.gather(
                self.ticket_classifier.classify(issue_description, tenant_id),
                self.vector_service.hybrid_search(
                    query=issue_description,
                    tenant_id=tenant_id,
                    db=db,
                    top_k=10,
                    source_types=['runbook', 'document'],
                    use_reranking=True,
                ),
            )
            # Override regex-derived signals with LLM classification when confident
            if not classification.fallback_used and classification.confidence >= 0.7:
                service = classification.service
                issue_type = classification.issue_type
                if classification.os_type:
                    os_type = classification.os_type
                logger.info(
                    "LLM classification applied: service=%s issue_type=%s os=%s "
                    "entities=%s (confidence=%.2f)",
                    service, issue_type, os_type,
                    classification.format_entities(), classification.confidence,
                )
            else:
                logger.info(
                    "Using regex classification (fallback=%s confidence=%.2f)",
                    classification.fallback_used, classification.confidence,
                )
            context = self._format_runbook_context(search_results, issue_type)
            logger.info(f"RAG search found {len(search_results)} chunks (runbooks + documents) for context")
        except Exception as e:
            logger.warning(f"Parallel classify+RAG failed, generating without context: {e}")
            search_results = []
            context = ""
            classification = TicketClassification(
                service=service, issue_type=issue_type, os_type=os_type,
                confidence=0.0, fallback_used=True,
            )

        # KAG: inject proven/failed commands — query enriched with issue_type + extracted hosts
        try:
            kag_query = f"{issue_description} {issue_type}" if issue_type != "general_issue" else issue_description
            if classification.hosts:
                kag_query += f" {' '.join(classification.hosts[:2])}"
            learned_context = self._build_learned_command_context(
                db=db,
                tenant_id=tenant_id,
                issue_description=kag_query,
                os_type=os_type if service == "server" else None,
            )
            if learned_context:
                context = learned_context + ("\n\n" + context if context else "")
                logger.info("KAG: injected learned command context into generation prompt")
        except Exception as e:
            logger.debug(f"Non-critical: KAG learned context failed: {e}")

        # Phase 1: Generate YAML from LLM (structured classification + entities passed in)
        ai_yaml = await self.yaml_pipeline.generate_yaml_from_llm(
            issue_description=issue_description,
            tenant_id=tenant_id,
            service=service,
            env=env,
            risk=risk,
            context=context,
            os_type=os_type if service == "server" else None,
            operational_context=operational_context,
            issue_type=issue_type,
            entities=classification.format_entities(),
        )

        # Phase 2: Extract and clean YAML
        ai_yaml = self.yaml_pipeline.extract_and_clean_yaml(ai_yaml)

        # Phase 3: Preprocess YAML structure
        ai_yaml = self.yaml_pipeline.preprocess_yaml_structure(ai_yaml)

        # Validate YAML. If invalid, attempt auto-fix
        try:
            if not ai_yaml or not ai_yaml.strip():
                raise ValueError("empty ai yaml")

            # Parse YAML using YamlParser (handles errors and recovery internally)
            logger.debug(f"Parsing YAML ({len(ai_yaml)} chars)")
            try:
                spec = self.yaml_parser.parse_yaml(ai_yaml)
                logger.info(f"[PHASE 3 - YAML PARSING] Parse SUCCESSFUL!")
            except ValueError as e:
                logger.error(f"YAML parsing failed after all recovery attempts: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during YAML parsing: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise ValueError(f"YAML parsing failed: {e}") from e

            # Post-process spec using SpecPostProcessor
            spec = self.spec_post_processor.post_process(spec, issue_description, env, risk)

            # Critic + Refiner pipeline (replaces keyword-counting validators)
            spec, critic_result = await self.validation_pipeline.run(
                spec=spec,
                issue_description=issue_description,
                issue_type=issue_type,
                os_type=os_type,
                tenant_id=tenant_id,
            )

            runbook_yaml = yaml.safe_dump(_order_spec_fields(spec), sort_keys=False, default_flow_style=False, width=120)
            generation_mode = "ai"
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"[YAML GENERATION FAILED] Error type: {error_type}")
            logger.error(f"[YAML GENERATION FAILED] Error message: {error_msg}")
            logger.error(f"[YAML GENERATION FAILED] Raw YAML from LLM (first 2000 chars): {repr(ai_yaml[:2000]) if ai_yaml else 'None'}")
            logger.error(f"[YAML GENERATION FAILED] Raw YAML from LLM (first 2000 chars, readable): {ai_yaml[:2000] if ai_yaml else 'None'}")

            # Attempt auto-fix for common YAML structure issues
            try:
                logger.warning(f"Attempting auto-fix...")
                fixed_yaml = self.yaml_processor.attempt_yaml_autofix(ai_yaml)
                logger.debug(f"[DEBUG] Fixed YAML (first 500 chars): {fixed_yaml[:500]}")

                try:
                    spec = yaml.safe_load(fixed_yaml)
                except Exception as e2:
                    logger.debug(f"[DEBUG] First parse attempt failed, trying with SafeLoader: {e2}")
                    spec = yaml.load(fixed_yaml, Loader=yaml.SafeLoader)
                if not isinstance(spec, dict):
                    raise ValueError("invalid spec shape after autofix")
                if "steps" not in spec:
                    raise ValueError("missing steps after autofix")

                # Apply same post-processing as normal path
                spec = self.spec_post_processor.post_process(spec, issue_description, env, risk)

                spec, critic_result = await self.validation_pipeline.run(
                    spec=spec,
                    issue_description=issue_description,
                    issue_type=issue_type,
                    os_type=os_type,
                    tenant_id=tenant_id,
                )

                runbook_yaml = yaml.safe_dump(_order_spec_fields(spec), sort_keys=False, default_flow_style=False, width=120)
                generation_mode = "ai-autofix"
                logger.info("YAML auto-fix succeeded")
            except Exception as e2:
                logger.error(f"AI YAML invalid or empty – rejecting request (no fallback): {type(e).__name__}: {e}; autofix failed: {type(e2).__name__}: {e2}")
                if isinstance(e, ValueError):
                    raise ValueError(f"YAML parsing failed: {str(e)[:200]}") from e
                elif isinstance(e, HTTPException):
                    raise
                else:
                    raise ValueError(f"LLM YAML generation failed: {type(e).__name__}: {str(e)[:200]}") from e

        # Persist as Markdown (code fence) for readability while storing JSON spec in meta_data
        body_md = f"""# Agent Runbook (YAML)

```yaml
{runbook_yaml}
```
"""

        runbook_environment = "dev" if settings.ENVIRONMENT == "development" else "production"

        runbook = Runbook(
            tenant_id=tenant_id,
            title=f"Runbook: {spec.get('title')}",
            body_md=body_md,
            meta_data=json.dumps({
                "issue_description": issue_description,
                "generated_by": "agent_yaml",
                "service": service,
                "env": env,
                "risk": risk,
                "issue_type": issue_type,
                "runbook_spec": spec,
                "generation_mode": generation_mode,
                "review_required": not critic_result.passed,
                "critic_severity": critic_result.severity,
                "critic_assessment": critic_result.overall_assessment,
                "critic_gaps": [
                    {"section": g.section, "index": g.index,
                     "problem": g.problem, "fix_hint": g.fix_hint}
                    for g in critic_result.gaps
                ],
            }),
            confidence=0.75 if critic_result.passed else 0.55,
            is_active="active",
            environment=runbook_environment
        )

        db.add(runbook)
        db.commit()
        db.refresh(runbook)

        # Store citations for this runbook using CitationManager
        if search_results:
            self.citation_manager.store_citations(db, runbook, search_results)

        try:
            return RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=runbook.confidence,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
        except Exception as e:
            logger.error(f"Failed to create RunbookResponse: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
            raise
