"""
Main runbook generator service that orchestrates all generation components
"""
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


class RunbookGeneratorService:
    """Service for generating runbooks from search results using RAG"""
    
    def __init__(self):
        # VectorStoreService created lazily only when needed (to avoid loading embedding model)
        self._vector_service = None
        self.service_classifier = ServiceClassifier()
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

        # RAG: retrieve runbook + document context (KAG)
        try:
            search_results = await self.vector_service.hybrid_search(
                query=issue_description,
                tenant_id=tenant_id,
                db=db,
                top_k=10,
                source_types=['runbook', 'document'],
                use_reranking=True
            )
            context = self._format_runbook_context(search_results, issue_description)
            logger.info(f"RAG search found {len(search_results)} chunks (runbooks + documents) for context")
        except Exception as e:
            logger.warning(f"RAG search failed, generating without context: {e}")
            search_results = []
            context = ""

        # KAG: inject proven/failed commands from execution learning store
        try:
            # Augment the search query with issue_type for better keyword overlap scoring
            kag_query = f"{issue_description} {issue_type}" if issue_type != "general_issue" else issue_description
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

        # Phase 1: Generate YAML from LLM
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
        )
        
        # Phase 2: Extract and clean YAML
        ai_yaml = self.yaml_pipeline.extract_and_clean_yaml(ai_yaml)
        
        # Phase 3: Preprocess YAML structure
        ai_yaml = self.yaml_pipeline.preprocess_yaml_structure(ai_yaml)

        # Validate YAML. If invalid, attempt auto-fix
        try:
            if not ai_yaml or not ai_yaml.strip():
                raise ValueError("empty ai yaml")
            
            # YAML should already be fixed by yaml_processor.sanitize_command_strings
            
            # Parse YAML using YamlParser (handles errors and recovery internally)
            logger.debug(f"Parsing YAML ({len(ai_yaml)} chars)")
            try:
                spec = self.yaml_parser.parse_yaml(ai_yaml)
                logger.info(f"[PHASE 3 - YAML PARSING] Parse SUCCESSFUL!")
            except ValueError as e:
                # YamlParser raises ValueError for unrecoverable errors
                logger.error(f"YAML parsing failed after all recovery attempts: {e}")
                raise
            except Exception as e:
                # Fallback error handling for unexpected errors
                logger.error(f"Unexpected error during YAML parsing: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise ValueError(f"YAML parsing failed: {e}") from e

            # Post-process spec using SpecPostProcessor
            spec = self.spec_post_processor.post_process(spec, issue_description, env, risk)
            
            # Post-processing: Detect and flag diagnostic-only sequences
            spec = self._detect_and_flag_diagnostic_only(spec)
            
            # Phase 1: Validate runbook structure (issue_type-aware)
            is_valid, validation_errors = self.validation_pipeline.validate_structure(
                spec, issue_description, issue_type=issue_type
            )
            
            # Phase 2: Validate commands
            os_type_for_validation = env if env in ["Windows", "Linux"] else os_type
            await self.validation_pipeline.validate_commands(
                spec, issue_description, env, os_type_for_validation
            )
            
            # Phase 3: LLM critique
            await self.validation_pipeline.critique_runbook(
                spec, issue_description, tenant_id
            )
            
            # Validate runbook structure (existing validation)
            try:
                from app.schemas.runbook_yaml import RunbookValidator
                validated_spec, warnings = RunbookValidator.validate_runbook(spec, auto_assign_severity=True)
                if warnings:
                    logger.warning(f"Runbook validation warnings: {warnings}")
                spec = validated_spec.model_dump(mode='json', exclude_none=True)
                logger.info(f"Runbook validated: {len(spec.get('steps', []))} steps, all commands checked")
            except Exception as e:
                logger.warning(f"Runbook validation failed but continuing: {type(e).__name__}: {e}")
            
            runbook_yaml = yaml.safe_dump(_order_spec_fields(spec), sort_keys=False, default_flow_style=False, width=120)
            generation_mode = "ai"
        except Exception as e:
            # Log the full error with context
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

                try:
                    from app.schemas.runbook_yaml import RunbookValidator
                    validated_spec, warnings = RunbookValidator.validate_runbook(spec, auto_assign_severity=True)
                    if warnings:
                        logger.warning(f"Runbook validation warnings after autofix: {warnings}")
                    spec = validated_spec.model_dump(mode='json', exclude_none=True)
                except Exception as ve:
                    logger.warning(f"Validation after autofix failed but continuing: {type(ve).__name__}: {ve}")

                runbook_yaml = yaml.safe_dump(_order_spec_fields(spec), sort_keys=False, default_flow_style=False, width=120)
                generation_mode = "ai-autofix"
                logger.info("YAML auto-fix succeeded")
            except Exception as e2:
                logger.error(f"AI YAML invalid or empty – rejecting request (no fallback): {type(e).__name__}: {e}; autofix failed: {type(e2).__name__}: {e2}")
                # Re-raise ValueError as-is so endpoint can convert to 500
                # Re-raise HTTPException as-is (from pipeline)
                # Convert other exceptions to ValueError for consistent handling
                if isinstance(e, ValueError):
                    raise ValueError(f"YAML parsing failed: {str(e)[:200]}") from e
                elif isinstance(e, HTTPException):
                    raise  # Re-raise HTTPException from pipeline
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
                "generation_mode": generation_mode
            }),
            confidence=0.75,
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
    
    # _post_process_spec method removed - now handled by SpecPostProcessor
    
    def _detect_and_flag_diagnostic_only(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-processing: Detect diagnostic-only step sequences and add remediation if missing.
        This is a safety net to catch runbooks that passed validation but are still diagnostic-heavy.
        """
        steps = spec.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 3:
            return spec
        
        remediation_count = 0
        diagnostic_only_count = 0
        
        for step in steps:
            if not isinstance(step, dict):
                continue
            
            cmd = str(step.get("command", "")).lower()
            name = str(step.get("name", "")).lower()
            
            has_remediation = any(kw in cmd or kw in name for kw in _REMEDIATION_KEYWORDS)
            is_diagnostic = any(kw in cmd or kw in name for kw in _DIAGNOSTIC_KEYWORDS)
            
            if has_remediation:
                remediation_count += 1
            elif is_diagnostic:
                diagnostic_only_count += 1
        
        # If we have less than 2 remediation steps, log a warning
        # (Validation should catch this, but this is a safety net)
        if remediation_count < 2:
            logger.warning(
                f"Post-processing detected diagnostic-heavy runbook: "
                f"{remediation_count} remediation steps, {diagnostic_only_count} diagnostic-only steps. "
                f"Runbook may need manual review."
            )
            # Add a metadata flag for review
            if "meta_data" not in spec:
                spec["meta_data"] = {}
            if isinstance(spec["meta_data"], dict):
                spec["meta_data"]["diagnostic_heavy"] = True
                spec["meta_data"]["remediation_count"] = remediation_count
                spec["meta_data"]["diagnostic_count"] = diagnostic_only_count
        
        return spec
    
    def _format_runbook_context(self, search_results: List[SearchResult], issue_description: str) -> str:
        """
        Format retrieved runbooks and documents into structured context (KAG).
        Labels sources so the model can distinguish runbook vs document chunks.
        """
        if not search_results:
            return "No similar runbooks or documents found."

        def _is_document(result: SearchResult) -> bool:
            src = getattr(result, "document_source", "") or ""
            return str(src).lower() == "document"

        runbook_results = [r for r in search_results if not _is_document(r)]
        document_results = [r for r in search_results if _is_document(r)]

        context_parts = []

        # Runbook section: filter and prioritize runbooks with remediation
        filtered_results = []
        for result in runbook_results[:6]:
            text = result.text.lower()
            remediation_count = sum(1 for kw in _REMEDIATION_KEYWORDS if kw in text)
            diagnostic_count = sum(1 for kw in _DIAGNOSTIC_KEYWORDS if kw in text)
            if remediation_count >= 1:
                filtered_results.append((result, remediation_count, diagnostic_count))
        filtered_results.sort(key=lambda x: x[1], reverse=True)

        for i, (result, rem_count, _) in enumerate(filtered_results[:3], 1):
            title = result.document_title or "Untitled Runbook"
            score = result.score
            text = result.text
            relevant_parts = []
            command_pattern = r'(?:command|Command):\s*(.+?)(?:\n|$)'
            all_commands = re.findall(command_pattern, text, re.IGNORECASE)
            remediation_commands = [
                cmd.strip() for cmd in all_commands[:8]
                if any(kw in cmd.lower() for kw in _REMEDIATION_KEYWORDS)
            ]
            if remediation_commands:
                relevant_parts.extend([f"  Remediation Command: {cmd}" for cmd in remediation_commands[:3]])
            step_pattern = r'(?:name|Name|step|Step):\s*(.+?)(?:\n|$)'
            steps = re.findall(step_pattern, text, re.IGNORECASE)
            remediation_steps = [
                step.strip() for step in steps[:5]
                if any(kw in step.lower() for kw in ["remediate", "fix", "kill", "restart", "stop", "clear", "repair"])
            ]
            if remediation_steps:
                relevant_parts.extend([f"  Remediation Step: {step}" for step in remediation_steps[:2]])
            if relevant_parts:
                golden_tag = ""
                try:
                    import json as _json
                    rb_meta = result.meta_data if hasattr(result, "meta_data") else {}
                    if isinstance(rb_meta, str):
                        rb_meta = _json.loads(rb_meta)
                    if isinstance(rb_meta, dict) and rb_meta.get("golden_example"):
                        success_count = rb_meta.get("success_count", 1)
                        avg_mins = rb_meta.get("avg_resolution_minutes")
                        golden_tag = f" ✓ PROVEN ({success_count}x"
                        if avg_mins:
                            golden_tag += f", avg {avg_mins:.0f}min"
                        golden_tag += ")"
                except Exception:
                    pass
                context_parts.append(f"[Runbook] {i}: {title} (similarity: {score:.2f}, remediation steps: {rem_count}{golden_tag})")
                context_parts.extend(relevant_parts)
                context_parts.append("")

        if not any("[Runbook]" in p for p in context_parts) and runbook_results:
            context_parts.append("Note: Similar runbooks found; focus on REMEDIATION steps.")
            for i, result in enumerate(runbook_results[:2], 1):
                context_parts.append(f"[Runbook] {i}: {result.document_title or 'Untitled'} (similarity: {result.score:.2f})")
            context_parts.append("")

        # Document section: knowledge chunks clearly labeled
        if document_results:
            context_parts.append("Document knowledge (reference only):")
            for i, result in enumerate(document_results[:5], 1):
                title = result.document_title or "Untitled Document"
                snippet = (result.text or "").strip()[:400]
                if snippet:
                    context_parts.append(f"  [Document] {i}: {title} (similarity: {result.score:.2f})")
                    context_parts.append(f"    {snippet}")
                    context_parts.append("")

        return "\n".join(context_parts).strip() if context_parts else "No similar runbooks or documents with remediation found."

    def _build_learned_command_context(
        self,
        db,
        tenant_id: int,
        issue_description: str,
        os_type: Optional[str] = None,
    ) -> str:
        """
        Build KAG context from the execution learning store.
        Returns known-good and known-bad commands for the given issue type.
        Called separately from _format_runbook_context so it can be injected
        into the generation context alongside RAG runbook context.
        """
        if db is None:
            return ""

        learning = self.learning_service
        parts = []

        try:
            good_cmds = learning.get_known_good_commands(
                db=db,
                tenant_id=tenant_id,
                issue_description=issue_description,
                os_type=os_type,
                limit=6,
            )
            if good_cmds:
                parts.append("Commands proven to work in past executions for similar issues (prefer these):")
                for entry in good_cmds:
                    parts.append(f"  [PROVEN] {entry['command']}")
                    if entry.get("issue_description"):
                        parts.append(f"    (context: {entry['issue_description'][:80]})")
                parts.append("")
        except Exception as e:
            logger.debug(f"Could not fetch known-good commands: {e}")

        try:
            bad_cmds = learning.get_known_bad_commands(
                db=db,
                tenant_id=tenant_id,
                issue_description=issue_description,
                os_type=os_type,
                limit=4,
            )
            if bad_cmds:
                parts.append("Commands known to FAIL for similar issues (avoid these):")
                for entry in bad_cmds:
                    parts.append(f"  [AVOID] {entry['command']}")
                    if entry.get("error_text"):
                        parts.append(f"    (error: {entry['error_text'][:80]})")
                parts.append("")
        except Exception as e:
            logger.debug(f"Could not fetch known-bad commands: {e}")

        return "\n".join(parts).strip()

    def _validate_generated_runbook(
        self, 
        spec: Dict[str, Any], 
        issue_description: str
    ) -> tuple[bool, List[str]]:
        return self.quality_validator.validate(spec, issue_description)
    
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

