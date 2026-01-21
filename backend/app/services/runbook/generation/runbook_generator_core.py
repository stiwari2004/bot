"""
Main runbook generator service that orchestrates all generation components
"""
import json
import re
import traceback
import yaml
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
from app.config import runbook_structure

logger = get_logger(__name__)


class RunbookGeneratorService:
    """Service for generating runbooks from search results using RAG"""
    
    def __init__(self):
        # VectorStoreService created lazily only when needed (to avoid loading embedding model)
        self._vector_service = None
        self.service_classifier = ServiceClassifier()
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
        # Determine environment based on ENVIRONMENT config
        from app.core.config import settings
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
        top_k: int = 5
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

        # RAG: retrieve top context to condition the LLM (using hybrid search)
        try:
            search_results = await self.vector_service.hybrid_search(
                query=issue_description,
                tenant_id=tenant_id,
                db=db,
                top_k=5,
                source_types=['runbook'],  # Only search runbooks
                use_reranking=True
            )
            context = self._format_runbook_context(search_results, issue_description)
            logger.info(f"RAG search found {len(search_results)} similar runbooks for context")
        except Exception as e:
            logger.warning(f"RAG search failed, generating without context: {e}")
            search_results = []
            context = ""

        # Phase 1: Generate YAML from LLM
        ai_yaml = await self.yaml_pipeline.generate_yaml_from_llm(
            issue_description=issue_description,
            tenant_id=tenant_id,
            service=service,
            env=env,
            risk=risk,
            context=context,
            os_type=os_type if service == "server" else None
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
            
            # Try parsing YAML using YamlParser
            logger.info(f"[PHASE 3 - YAML PARSING] Attempting to parse YAML, length={len(ai_yaml)}")
            
            # CRITICAL: Log the actual YAML content before parsing to diagnose issues
            yaml_lines = ai_yaml.split('\n')
            logger.info(f"[PHASE 3 - YAML PARSING] Total lines: {len(yaml_lines)}")
            logger.info(f"[PHASE 3 - YAML PARSING] First 10 lines:")
            for i, line in enumerate(yaml_lines[:10], 1):
                logger.info(f"  Line {i:3d}: {repr(line)}")
            
            # Log lines 50-60 (where the error typically occurs)
            if len(yaml_lines) > 50:
                logger.info(f"[PHASE 3 - YAML PARSING] Lines 50-60 (error zone):")
                for i in range(49, min(60, len(yaml_lines))):
                    logger.info(f"  Line {i+1:3d}: {repr(yaml_lines[i])}")
            
            # Parse YAML using YamlParser (handles errors and recovery internally)
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
            
            # Legacy error handling block removed - now handled by YamlParser
            # Keeping this comment block for reference during transition
            if False:  # Disabled - using YamlParser now
                pass
            # Original error handling code was here (lines 319-583)
            # Now handled by YamlParser.parse_yaml()
            
            # Post-process spec using SpecPostProcessor
            spec = self.spec_post_processor.post_process(spec, issue_description, env, risk)
            
            # Post-processing: Detect and flag diagnostic-only sequences
            spec = self._detect_and_flag_diagnostic_only(spec)
            
            # Phase 1: Validate runbook structure
            is_valid, validation_errors = self.validation_pipeline.validate_structure(
                spec, issue_description
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
            
            # Ensure correct section order: prechecks → steps → postchecks
            from collections import OrderedDict
            ordered_spec = OrderedDict()
            
            # Add all fields in correct order
            for key in ['runbook_id', 'version', 'title', 'service', 'env', 'risk', 'description', 
                       'owner', 'last_tested', 'review_required', 'inputs', 'prechecks', 'steps', 'postchecks']:
                if key in spec:
                    ordered_spec[key] = spec[key]
            
            # Add any remaining fields
            for key, value in spec.items():
                if key not in ordered_spec:
                    ordered_spec[key] = value
            
            # Convert OrderedDict to regular dict for YAML serialization
            # (yaml.safe_dump can't serialize OrderedDict directly)
            spec_dict = dict(ordered_spec)
            
            runbook_yaml = yaml.safe_dump(spec_dict, sort_keys=False, default_flow_style=False, width=120)
            
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

                # Ensure correct section order: prechecks → steps → postchecks
                from collections import OrderedDict
                ordered_spec = OrderedDict()
                
                # Add all fields in correct order
                for key in ['runbook_id', 'version', 'title', 'service', 'env', 'risk', 'description', 
                           'owner', 'last_tested', 'review_required', 'inputs', 'prechecks', 'steps', 'postchecks']:
                    if key in spec:
                        ordered_spec[key] = spec[key]
                
                # Add any remaining fields
                for key, value in spec.items():
                    if key not in ordered_spec:
                        ordered_spec[key] = value
                
                # Convert OrderedDict to regular dict for YAML serialization
                # (yaml.safe_dump can't serialize OrderedDict directly)
                spec_dict = dict(ordered_spec)
                
                runbook_yaml = yaml.safe_dump(spec_dict, sort_keys=False, default_flow_style=False, width=120)
                generation_mode = "ai-autofix"
                logger.info("YAML auto-fix succeeded")
            except Exception as e2:
                logger.error(f"AI YAML invalid or empty – rejecting request (no fallback): {type(e).__name__}: {e}; autofix failed: {type(e2).__name__}: {e2}")
                raise HTTPException(status_code=502, detail=f"LLM YAML generation failed: {type(e).__name__}: {str(e)[:200]}")

        # Persist as Markdown (code fence) for readability while storing JSON spec in meta_data
        body_md = f"""# Agent Runbook (YAML)

```yaml
{runbook_yaml}
```
"""

        # Determine environment based on ENVIRONMENT config
        from app.core.config import settings
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

        # Create response with error handling
        try:
            logger.info(f"[DEBUG] Creating RunbookResponse object")
            meta_data_parsed = json.loads(runbook.meta_data) if runbook.meta_data else {}
            response = RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=runbook.confidence,
                meta_data=meta_data_parsed,
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
            logger.info(f"[DEBUG] RunbookResponse created successfully")
            return response
        except Exception as e:
            logger.error(f"[DEBUG] Failed to create RunbookResponse: {type(e).__name__}: {str(e)}")
            logger.error(f"[DEBUG] Runbook fields: id={runbook.id}, title={runbook.title}, confidence={runbook.confidence}")
            logger.error(f"[DEBUG] RunbookResponse creation traceback: {traceback.format_exc()}")
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
        
        remediation_keywords = [
            "stop-process", "restart-service", "kill", "systemctl restart",
            "clear", "delete", "remove", "fix", "repair", "resolve", "restart", "stop"
        ]
        diagnostic_keywords = [
            "get-process", "get-counter", "get-service", "get-eventlog",
            "top", "ps", "free", "df", "select-object", "where-object", "sort-object"
        ]
        
        remediation_count = 0
        diagnostic_only_count = 0
        
        for step in steps:
            if not isinstance(step, dict):
                continue
            
            cmd = str(step.get("command", "")).lower()
            name = str(step.get("name", "")).lower()
            
            has_remediation = any(kw in cmd or kw in name for kw in remediation_keywords)
            is_diagnostic = any(kw in cmd or kw in name for kw in diagnostic_keywords)
            
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
        Format retrieved runbooks into structured context that guides LLM generation.
        Filters out diagnostic-only runbooks and extracts only relevant remediation examples.
        
        Args:
            search_results: List of SearchResult objects from vector search
            issue_description: The original issue description
            
        Returns:
            Formatted context string to include in LLM prompt
        """
        if not search_results:
            return "No similar runbooks found."
        
        context_parts = []
        remediation_keywords = [
            "stop-process", "restart-service", "kill", "systemctl restart",
            "clear", "delete", "remove", "fix", "repair", "resolve"
        ]
        diagnostic_keywords = [
            "get-process", "get-counter", "get-service", "top", "ps", "free", "df"
        ]
        
        # Filter and prioritize runbooks with remediation steps
        filtered_results = []
        for result in search_results[:5]:  # Check top 5
            text = result.text.lower()
            commands = text
            
            # Count remediation vs diagnostic commands
            remediation_count = sum(1 for kw in remediation_keywords if kw in commands)
            diagnostic_count = sum(1 for kw in diagnostic_keywords if kw in commands)
            
            # Prefer runbooks with remediation (at least 2 remediation indicators)
            if remediation_count >= 2:
                filtered_results.append((result, remediation_count, diagnostic_count))
            elif remediation_count >= 1:
                # Include if has at least some remediation
                filtered_results.append((result, remediation_count, diagnostic_count))
        
        # Sort by remediation count (descending)
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit to top 2-3 runbooks with remediation
        for i, (result, rem_count, diag_count) in enumerate(filtered_results[:3], 1):
            title = result.document_title or "Untitled Runbook"
            score = result.score
            text = result.text
            
            # Extract only remediation commands and step names
            relevant_parts = []
            
            import re
            # Find remediation commands specifically
            command_pattern = r'(?:command|Command):\s*(.+?)(?:\n|$)'
            all_commands = re.findall(command_pattern, text, re.IGNORECASE)
            
            # Filter to show remediation commands
            remediation_commands = []
            for cmd in all_commands[:8]:  # Check up to 8 commands
                cmd_lower = cmd.lower()
                if any(kw in cmd_lower for kw in remediation_keywords):
                    remediation_commands.append(cmd.strip())
            
            if remediation_commands:
                relevant_parts.extend([f"  Remediation Command: {cmd}" for cmd in remediation_commands[:3]])
            
            # Extract step names that mention remediation
            step_pattern = r'(?:name|Name|step|Step):\s*(.+?)(?:\n|$)'
            steps = re.findall(step_pattern, text, re.IGNORECASE)
            remediation_steps = [
                step.strip() for step in steps[:5]
                if any(kw in step.lower() for kw in ["remediate", "fix", "kill", "restart", "stop", "clear", "repair"])
            ]
            
            if remediation_steps:
                relevant_parts.extend([f"  Remediation Step: {step}" for step in remediation_steps[:2]])
            
            if relevant_parts:
                context_parts.append(f"Runbook {i}: {title} (similarity: {score:.2f}, remediation steps: {rem_count})")
                context_parts.extend(relevant_parts)
                context_parts.append("")
        
        if not context_parts:
            # Fallback: show titles but warn about diagnostic-only
            context_parts.append("Note: Similar runbooks found but they may be diagnostic-only. Focus on REMEDIATION steps.")
            for i, result in enumerate(search_results[:2], 1):
                context_parts.append(f"Runbook {i}: {result.document_title or 'Untitled'} (similarity: {result.score:.2f})")
        
        return "\n".join(context_parts) if context_parts else "No similar runbooks with remediation found."
    
    def _validate_generated_runbook(
        self, 
        spec: Dict[str, Any], 
        issue_description: str
    ) -> tuple[bool, List[str]]:
        return self.quality_validator.validate(spec, issue_description)
    
    async def approve_and_index_runbook(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> RunbookResponse:
        """Approve a draft runbook and index it for search"""
        return await self.runbook_indexer.approve_and_index_runbook(runbook_id, tenant_id, db)

