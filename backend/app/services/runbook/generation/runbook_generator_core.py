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
            is_active="active"
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

        # Ask LLM to produce YAML runbook per schema
        llm = get_llm_service()
        try:
            logger.debug(f"LLM provider: {type(llm).__name__} base={getattr(llm, 'base_url', None)} model_id={getattr(llm, 'model_id', None)}")
        except Exception:
            pass
        try:
            # Pass OS type as a separate parameter for cleaner prompt
            ai_yaml = await llm.generate_yaml_runbook(
                tenant_id=tenant_id,
                issue_description=issue_description,
                service_type=service,  # Use CI type (server, database, web, etc.)
                env=env,
                risk=risk,
                context=context,
                os_type=os_type if service == "server" else None,  # Pass OS type separately
            )
        except LLMRateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except LLMBudgetExceeded as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        
        # Check for empty response early and provide better error
        if not ai_yaml or not ai_yaml.strip():
            logger.error(f"LLM returned empty YAML response. Issue: {issue_description[:100]}...")
            raise HTTPException(
                status_code=502, 
                detail="LLM returned empty response. Please check LLM connection and try again."
            )
        
        logger.info(f"[PHASE 1 - YAML GENERATION] LLM returned YAML length={len(ai_yaml) if ai_yaml else 0}")
        logger.info(f"[PHASE 1 - YAML GENERATION] First 200 chars: {repr(ai_yaml[:200]) if ai_yaml else 'None'}")
        # Check for newlines in first 200 chars
        if ai_yaml:
            for i, char in enumerate(ai_yaml[:200]):
                if char == '\n':
                    logger.error(f"[PHASE 1 - YAML GENERATION] FOUND NEWLINE at position {i} in first 200 chars!")
                    logger.error(f"[PHASE 1 - YAML GENERATION] Context: {repr(ai_yaml[max(0, i-30):i+30])}")
        logger.debug(f"LLM returned YAML length={len(ai_yaml) if ai_yaml else 0}, first 500 chars: {ai_yaml[:500] if ai_yaml else 'None'}")

        # CRITICAL: Strip ALL non-YAML content before processing
        # The LLM sometimes includes markdown headers, explanatory text, etc.
        import re
        
        # Strip code fences if present
        if ai_yaml and ai_yaml.strip().startswith("```"):
            lines = ai_yaml.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            ai_yaml = "\n".join(lines)
            logger.debug(f"After stripping fences: length={len(ai_yaml)}, first 200: {ai_yaml[:200]}")
        
        # CRITICAL: FIRST extract YAML starting from "runbook_id:", THEN clean it
        # This ensures we don't try to clean markdown that's before the actual YAML
        if ai_yaml and "runbook_id:" in ai_yaml:
            runbook_id_idx = ai_yaml.find("runbook_id:")
            if runbook_id_idx > 0:
                logger.warning(f"[YAML EXTRACTION] Found 'runbook_id:' at position {runbook_id_idx}, extracting YAML from there")
                logger.warning(f"[YAML EXTRACTION] Content before runbook_id: {repr(ai_yaml[:min(runbook_id_idx, 200)])}")
                # Find the start of the line containing "runbook_id:"
                start_idx = runbook_id_idx
                while start_idx > 0 and ai_yaml[start_idx - 1] not in ['\n', '\r']:
                    start_idx -= 1
                # Also check if there's a newline before this - if so, start from that newline
                if start_idx > 0 and ai_yaml[start_idx - 1] in ['\n', '\r']:
                    start_idx = start_idx - 1
                ai_yaml = ai_yaml[start_idx:].lstrip()  # Remove leading whitespace
                logger.info(f"[YAML EXTRACTION] Extracted YAML starting from position {start_idx}, length={len(ai_yaml)}")
        
        # NOW clean the extracted YAML - remove any remaining markdown
        lines = ai_yaml.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            
            # Skip markdown headers
            if stripped.startswith('#'):
                continue
            # Skip markdown list items (starts with * followed by space)
            if stripped.startswith('* '):
                continue
            # Skip lines with tabs that contain markdown syntax
            if '\t' in line and (stripped.startswith('*') or stripped.startswith('- Use:') or 'Use:' in stripped):
                continue
            # Skip lines with common markdown/explanatory patterns
            stripped_lower = stripped.lower()
            if any(pattern in stripped_lower for pattern in [
                'use: get-process',
                'use: get-counter',
                'never use:',
                'examples allowed:',
                'examples:'
            ]):
                continue
            # Skip lines that are just plain text without YAML structure
            if stripped and ':' not in stripped and not stripped.startswith('-') and not re.match(r'^\s*-\s+[a-z_][a-z0-9_]*:', line):
                # Skip if it doesn't look like YAML at all
                if not re.match(r'^[a-z_][a-z0-9_]*:', stripped):
                    continue
            
            cleaned_lines.append(line)
        
        ai_yaml = '\n'.join(cleaned_lines)
        
        # Remove markdown formatting (bold, italic, code blocks, list markers)
        # Remove markdown code blocks: `code` (but preserve content)
        ai_yaml = re.sub(r'`([^`]+)`', r'\1', ai_yaml)
        # Remove markdown list markers at start of lines: * item, - item (but keep YAML list items)
        # Only remove if it's not part of a YAML structure (not followed by a key:)
        lines = ai_yaml.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines that are clearly markdown (start with * or - but not YAML list items)
            stripped = line.strip()
            if stripped.startswith('* ') and ':' not in line[:20]:  # Markdown list, not YAML
                cleaned_lines.append(line.replace('* ', '', 1).lstrip())
            elif stripped.startswith('- ') and not re.match(r'^\s*-\s+[a-z_][a-z0-9_]*:', line):  # Markdown, not YAML list item
                # Check if it looks like a YAML list item (has key: value structure)
                if ':' not in line or not re.search(r'[a-z_][a-z0-9_]*:\s', line):
                    cleaned_lines.append(line.replace('- ', '', 1).lstrip())
                else:
                    cleaned_lines.append(line)  # Keep YAML list items
            elif re.match(r'^\s*\d+\.\s+', stripped):  # Numbered list
                cleaned_lines.append(re.sub(r'^\s*\d+\.\s+', '', line))
            elif stripped.startswith('#'):  # Markdown header
                continue  # Skip header lines
            else:
                cleaned_lines.append(line)
        ai_yaml = '\n'.join(cleaned_lines)
        
        # Remove markdown bold/italic: **text**, *text* (but be careful not to break YAML)
        ai_yaml = re.sub(r'\*\*([^*]+)\*\*', r'\1', ai_yaml)
        # Only remove single asterisks if they're not part of YAML syntax
        ai_yaml = re.sub(r'(?<![a-z0-9_])\*([^*\n:]+)\*(?![*a-z0-9_])', r'\1', ai_yaml)
        
        # YAML extraction already done above - just verify runbook_id exists
        if ai_yaml and "runbook_id:" not in ai_yaml:
            logger.error(f"[YAML EXTRACTION] ERROR: 'runbook_id:' not found in LLM output after extraction!")
            logger.error(f"[YAML EXTRACTION] First 500 chars: {repr(ai_yaml[:500]) if ai_yaml else 'None'}")
        
        # Final cleanup: Remove any remaining non-YAML lines at the start
        lines = ai_yaml.split('\n')
        yaml_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            # If we find a line that looks like YAML (has a colon and looks like a key-value pair)
            if ':' in stripped and re.match(r'^[a-z_][a-z0-9_]*:', stripped.split(':')[0]):
                yaml_start_idx = i
                break
        if yaml_start_idx > 0:
            logger.warning(f"Removing {yaml_start_idx} non-YAML lines from start")
            ai_yaml = '\n'.join(lines[yaml_start_idx:])
        
        # Sanitize LLM output using YAML processor
        ai_yaml = self.yaml_processor.sanitize_description_field(ai_yaml)
        
        # CRITICAL: Fix newlines in YAML values that break parsing
        # Scan all lines and fix any value containing a literal newline character
        lines = ai_yaml.split('\n')
        fixed_lines = []
        for line in lines:
            # Match any key-value pair with potential newline in value
            match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*):\s+(.+)$', line)
            if match:
                indent = match.group(1)
                key = match.group(2)
                value = match.group(3)
                
                # Check if value contains a literal newline character (illegal in unquoted YAML)
                if '\n' in value or '\r' in value:
                    # Replace newlines with spaces or use block scalar
                    # For short values, replace newline with space
                    # For longer values, use block scalar
                    value_clean = value.replace('\r', '').replace('\n', ' ').strip()
                    if len(value_clean) > 100:  # Long value - use block scalar
                        value_parts = value.replace('\r', '').split('\n')
                        fixed_lines.append(f"{indent}{key}: |")
                        for part in value_parts:
                            if part.strip():
                                fixed_lines.append(f"{indent}  {part.strip()}")
                    else:  # Short value - quote with escaped newline
                        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                        fixed_lines.append(f"{indent}{key}: \"{escaped}\"")
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        ai_yaml = '\n'.join(fixed_lines)
        
        logger.debug(f"[DEBUG] YAML before parse (first 3000 chars): {ai_yaml[:3000] if ai_yaml else 'None'}")

        # Pre-process: Fix common structural issues before parsing
        logger.info(f"[PHASE 2 - YAML CLEANUP] Starting cleanup, length={len(ai_yaml)}")
        ai_yaml = self.yaml_processor.preprocess_yaml_structure(ai_yaml)
        logger.info(f"[PHASE 2 - YAML CLEANUP] After preprocess_yaml_structure, length={len(ai_yaml)}")
        
        # Sanitize command strings and quote {{placeholders}} to prevent YAML parsing errors
        # This must be done after preprocessing but before parsing
        try:
            ai_yaml_before_sanitize = ai_yaml
            ai_yaml = self.yaml_processor.sanitize_command_strings(ai_yaml)
            logger.info(f"[PHASE 2 - YAML CLEANUP] After sanitize_command_strings, length={len(ai_yaml)}")
            # Check first line specifically
            first_line = ai_yaml.split('\n')[0] if '\n' in ai_yaml else ai_yaml
            if len(first_line) >= 101:
                logger.error(f"[PHASE 2 - YAML CLEANUP] First line length={len(first_line)}, char at 101: {repr(first_line[100])}")
                logger.error(f"[PHASE 2 - YAML CLEANUP] First line (first 150 chars): {repr(first_line[:150])}")
        except Exception as e:
            logger.warning(f"Command sanitization failed, continuing without it: {type(e).__name__}: {e}")
        
        # Fix YAML escape sequence issues
        ai_yaml = self.yaml_processor.fix_yaml_escape_sequences(ai_yaml)
        logger.info(f"[PHASE 2 - YAML CLEANUP] After fix_yaml_escape_sequences, length={len(ai_yaml)}")

        # Validate YAML. If invalid, attempt auto-fix
        try:
            if not ai_yaml or not ai_yaml.strip():
                raise ValueError("empty ai yaml")
            
            # YAML should already be fixed by yaml_processor.sanitize_command_strings
            
            # Try parsing YAML
            logger.info(f"[PHASE 3 - YAML PARSING] Attempting to parse YAML, length={len(ai_yaml)}")
            # Final check before parsing
            first_line = ai_yaml.split('\n')[0] if '\n' in ai_yaml else ai_yaml
            if len(first_line) >= 101:
                logger.error(f"[PHASE 3 - YAML PARSING] BEFORE PARSE - First line length={len(first_line)}")
                logger.error(f"[PHASE 3 - YAML PARSING] Character at position 101: {repr(first_line[100])}")
                logger.error(f"[PHASE 3 - YAML PARSING] First line full: {repr(first_line)}")
            try:
                spec = yaml.safe_load(ai_yaml)
                logger.info(f"[PHASE 3 - YAML PARSING] Parse SUCCESSFUL!")
            except yaml.YAMLError as e:
                error_msg = str(e)
                logger.error(f"YAML parse error: {error_msg}")
                # Log the exact YAML content that's causing the error
                # First, log the full YAML for debugging
                logger.error(f"[YAML PARSE ERROR] Full YAML content (first 5000 chars):\n{ai_yaml[:5000]}")
                if 'line' in error_msg and 'column' in error_msg:
                    import re
                    line_match = re.search(r'line (\d+)', error_msg)
                    col_match = re.search(r'column (\d+)', error_msg)
                    
                    if line_match and col_match:
                        error_line_num = int(line_match.group(1))
                        error_col_num = int(col_match.group(1))
                        yaml_lines = ai_yaml.split('\n')
                        if error_line_num <= len(yaml_lines):
                            problematic_line = yaml_lines[error_line_num - 1]
                            logger.error(f"[YAML PARSE ERROR] Problematic line {error_line_num}, column {error_col_num}:")
                            logger.error(f"[YAML PARSE ERROR] Full line: {repr(problematic_line)}")
                            logger.error(f"[YAML PARSE ERROR] Line content: {problematic_line}")
                            if error_col_num <= len(problematic_line):
                                logger.error(f"[YAML PARSE ERROR] Character at error position: {repr(problematic_line[error_col_num - 1])}")
                                logger.error(f"[YAML PARSE ERROR] Context around error: {repr(problematic_line[max(0, error_col_num-20):error_col_num+20])}")
                            
                            # Try to fix this specific line
                            if '\\' in problematic_line and not (problematic_line.strip().startswith("'") or problematic_line.strip().startswith('"')):
                                logger.warning(f"[YAML PARSE ERROR] Line {error_line_num} contains backslash but is not quoted - attempting fix")
                                # This should have been caught by fix_unescaped_backslashes_before_parse
                                # Log it for debugging
                                logger.error(f"[YAML PARSE ERROR] This line should have been fixed by pre-parse fix!")
                    if line_match and col_match:
                        line_num = int(line_match.group(1))
                        col_num = int(col_match.group(1))
                        lines_list = ai_yaml.split('\n')
                        if line_num <= len(lines_list):
                            problem_line = lines_list[line_num - 1]
                            logger.error(f"PROBLEMATIC LINE {line_num}: {repr(problem_line)}")
                            logger.error(f"Character at column {col_num}: {repr(problem_line[col_num-1:col_num+5] if col_num <= len(problem_line) else 'N/A')}")
                            # Show first 200 chars of first line if it's line 1
                            if line_num == 1:
                                logger.error(f"First line full content (first 200 chars): {repr(problem_line[:200])}")
                logger.error(f"YAML content causing error (first 1000 chars): {repr(ai_yaml[:1000])}")
                logger.debug(f"First parse attempt failed: {e}, trying with document marker")
                if not ai_yaml.strip().startswith('---'):
                    yaml_with_marker = '---\n' + ai_yaml.lstrip()
                else:
                    yaml_with_marker = ai_yaml
                spec = yaml.safe_load(yaml_with_marker)
            
            # Handle None or empty results
            if spec is None:
                logger.error(f"YAML parsed to None. YAML content (first 2000 chars): {ai_yaml[:2000]}")
                raise ValueError("YAML parsed to None - check YAML syntax")
            
            # Handle non-dict results - try multiple recovery strategies
            if not isinstance(spec, dict):
                logger.error(f"YAML did not parse to dict: type={type(spec)}, value={str(spec)[:500]}")
                logger.error(f"YAML content that failed to parse (first 2000 chars): {ai_yaml[:2000]}")
                
                # Strategy 1: If it's a list, try to extract the first dict element
                if isinstance(spec, list) and len(spec) > 0 and isinstance(spec[0], dict):
                    logger.warning("YAML parsed to list, using first element as dict")
                    spec = spec[0]
                # Strategy 2: If it's a string, try to find YAML in it
                elif isinstance(spec, str):
                    logger.warning("YAML parsed to string, attempting to extract YAML dict from string")
                    # Try to find and parse YAML from the string
                    if "runbook_id:" in spec:
                        yaml_start = spec.find("runbook_id:")
                        # Try to extract a reasonable chunk
                        yaml_chunk = spec[yaml_start:yaml_start+5000]  # Get 5000 chars
                        try:
                            spec = yaml.safe_load(yaml_chunk)
                            if isinstance(spec, dict):
                                logger.info("Successfully extracted dict from string")
                            else:
                                raise ValueError(f"YAML parsed to string instead of dict. Content: {spec[:200]}")
                        except Exception as e:
                            logger.error(f"Failed to extract YAML from string: {e}")
                            raise ValueError(f"YAML parsed to string instead of dict. Content: {spec[:200]}")
                    else:
                        raise ValueError(f"YAML parsed to string instead of dict. Content: {spec[:200]}")
                # Strategy 3: Try loading all documents if it's a multi-document YAML
                elif isinstance(spec, list) and len(spec) == 0:
                    logger.warning("YAML parsed to empty list, trying to load all documents")
                    try:
                        all_docs = list(yaml.safe_load_all(ai_yaml))
                        if all_docs and len(all_docs) > 0 and isinstance(all_docs[0], dict):
                            spec = all_docs[0]
                            logger.info("Successfully extracted dict from multi-document YAML")
                        else:
                            raise ValueError(f"invalid spec shape - not a dict (got {type(spec).__name__})")
                    except Exception as e:
                        logger.error(f"Failed to load multi-document YAML: {e}")
                        raise ValueError(f"invalid spec shape - not a dict (got {type(spec).__name__})")
                else:
                    raise ValueError(f"invalid spec shape - not a dict (got {type(spec).__name__})")
            if "steps" not in spec:
                logger.error(f"[MISSING STEPS] YAML dict missing 'steps' key")
                logger.error(f"[MISSING STEPS] Keys found in spec: {list(spec.keys())}")
                logger.error(f"[MISSING STEPS] Full spec content (first 2000 chars): {str(spec)[:2000]}")
                logger.error(f"[MISSING STEPS] Raw YAML that failed (first 2000 chars): {repr(ai_yaml[:2000])}")
                logger.error(f"[MISSING STEPS] Raw YAML that failed (first 2000 chars, readable): {ai_yaml[:2000]}")
                
                # Check if "steps" appears in the raw YAML but wasn't parsed
                if "steps:" in ai_yaml or "steps" in ai_yaml.lower():
                    logger.error(f"[MISSING STEPS] 'steps' keyword found in raw YAML but not in parsed spec!")
                    # Find where steps: appears
                    steps_idx = ai_yaml.lower().find("steps:")
                    if steps_idx >= 0:
                        logger.error(f"[MISSING STEPS] Found 'steps:' at position {steps_idx} in raw YAML")
                        logger.error(f"[MISSING STEPS] Context around steps: {repr(ai_yaml[max(0, steps_idx-100):steps_idx+500])}")
                
                # Try to recover - check if steps might be in inputs (common LLM mistake)
                steps_from_inputs = []
                if "inputs" in spec and isinstance(spec["inputs"], list):
                    for inp in spec["inputs"]:
                        if isinstance(inp, dict) and (inp.get("type") == "command" or "command" in inp):
                            logger.warning(f"[MISSING STEPS] Found command in inputs, converting to step: {inp.get('name', 'unknown')}")
                            step = {
                                "name": inp.get("name", "Unknown step"),
                                "type": "command",
                                "command": inp.get("command", ""),
                                "expected_output": inp.get("expected_output", "Command executed successfully"),
                                "skip_in_auto_mode": False,
                                "severity": inp.get("severity", "safe")
                            }
                            steps_from_inputs.append(step)
                
                # Try to recover - check if steps is named differently or if we can infer it
                possible_step_keys = [k for k in spec.keys() if 'step' in k.lower() or 'action' in k.lower() or 'command' in k.lower()]
                if possible_step_keys:
                    logger.warning(f"[MISSING STEPS] Found possible step keys: {possible_step_keys}, attempting to rename")
                    spec['steps'] = spec[possible_step_keys[0]]
                elif steps_from_inputs:
                    logger.warning(f"[MISSING STEPS] Recovered {len(steps_from_inputs)} steps from inputs section")
                    spec['steps'] = steps_from_inputs
                    # Clean up inputs to remove the commands
                    spec['inputs'] = [inp for inp in spec.get('inputs', []) 
                                     if isinstance(inp, dict) and inp.get("type") != "command" and "command" not in inp]
                else:
                    # If no steps at all, this is a critical error
                    logger.error("[MISSING STEPS] No steps found in YAML - LLM generated incomplete runbook")
                    logger.error(f"[MISSING STEPS] Available keys: {list(spec.keys())}")
                    logger.error(f"[MISSING STEPS] Full spec dump: {yaml.safe_dump(spec, default_flow_style=False)}")
                    raise ValueError("invalid spec shape - missing steps. LLM generated incomplete YAML without steps section. Check backend logs for details.")
            
            # Post-process spec
            spec = self._post_process_spec(spec, issue_description, env, risk)
            
            # Validate runbook structure and content (Phase 1: Structure enforcement)
            is_valid, validation_errors = self._validate_generated_runbook(spec, issue_description)
            if not is_valid:
                # Check for CRITICAL errors that should cause regeneration
                critical_errors = [e for e in validation_errors if "CRITICAL" in e.upper()]
                if critical_errors:
                    logger.error(f"CRITICAL validation failures - runbook structure is incorrect:")
                    for error in critical_errors:
                        logger.error(f"  - {error}")
                    logger.error(f"Full validation errors: {validation_errors}")
                    logger.error(f"Runbook spec keys: {list(spec.keys())}")
                    logger.error(f"Prechecks count: {len(spec.get('prechecks', []))}")
                    logger.error(f"Steps count: {len(spec.get('steps', []))}")
                    logger.error(f"Postchecks count: {len(spec.get('postchecks', []))}")
                    
                    # Check if structure is so broken that we should reject
                    prechecks_count = len(spec.get("prechecks", []))
                    steps_count = len(spec.get("steps", []))
                    postchecks_count = len(spec.get("postchecks", []))
                    
                    # Reject if structure is severely wrong (e.g., 0 or 1 step when we need 5-6)
                    if steps_count < 2 or prechecks_count == 0 or postchecks_count == 0:
                        logger.error(
                            f"Runbook structure is severely incorrect - rejecting. "
                            f"Prechecks: {prechecks_count} (need 3), Steps: {steps_count} (need 5-6), "
                            f"Postchecks: {postchecks_count} (need 1)"
                        )
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                f"LLM generated invalid runbook structure. "
                                f"Prechecks: {prechecks_count} (required: 3), "
                                f"Steps: {steps_count} (required: 5-6), "
                                f"Postchecks: {postchecks_count} (required: 1). "
                                f"Please try again or check LLM configuration."
                            )
                        )
                    # For less severe issues, log but continue
                    logger.warning(
                        "Runbook has structure issues but may be recoverable. "
                        "Consider regenerating for better results."
                    )
                else:
                    logger.warning(f"Runbook validation warnings (non-critical): {validation_errors}")
                    for error in validation_errors:
                        logger.warning(f"  - {error}")
            
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
            
            runbook_yaml = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
            
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
                spec = self._post_process_spec(spec, issue_description, env, risk)

                try:
                    from app.schemas.runbook_yaml import RunbookValidator
                    validated_spec, warnings = RunbookValidator.validate_runbook(spec, auto_assign_severity=True)
                    if warnings:
                        logger.warning(f"Runbook validation warnings after autofix: {warnings}")
                    spec = validated_spec.model_dump(mode='json', exclude_none=True)
                except Exception as ve:
                    logger.warning(f"Validation after autofix failed but continuing: {type(ve).__name__}: {ve}")

                runbook_yaml = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
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
            is_active="active"
        )

        db.add(runbook)
        db.commit()
        db.refresh(runbook)

        # Store citations for this runbook (from search results)
        if search_results:
            from app.models.runbook_citation import RunbookCitation
            for result in search_results:
                if hasattr(result, 'document_id'):
                    citation = RunbookCitation(
                        runbook_id=runbook.id,
                        document_id=result.document_id,
                        chunk_id=getattr(result, 'chunk_id', None),
                        relevance_score=result.score
                    )
                    db.add(citation)
            try:
                db.commit()
                logger.info(f"Stored {len(search_results)} citations for runbook {runbook.id}")
            except Exception as e:
                logger.warning(f"Failed to store citations: {e}")
                db.rollback()

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
    
    def _post_process_spec(self, spec: Dict[str, Any], issue_description: str, env: str, risk: str) -> Dict[str, Any]:
        """Post-process YAML spec to fix common LLM formatting issues"""
        # CRITICAL: Fix inputs section if it contains commands (LLM sometimes puts commands here)
        if "inputs" in spec and isinstance(spec["inputs"], list):
            valid_inputs = []
            commands_to_move = []
            
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    # Check if this input is actually a command (has type: command or has a command field)
                    if inp.get("type") == "command" or "command" in inp:
                        logger.warning(
                            f"CRITICAL: Found command in inputs section: '{inp.get('name', 'unknown')}'. "
                            f"Moving to steps section."
                        )
                        # Convert to a step
                        step = {
                            "name": inp.get("name", "Unknown step"),
                            "type": "command",
                            "command": inp.get("command", ""),
                            "expected_output": inp.get("expected_output", "Command executed successfully"),
                            "skip_in_auto_mode": False,
                            "severity": inp.get("severity", "safe")
                        }
                        commands_to_move.append(step)
                    else:
                        # Valid input parameter
                        valid_inputs.append(inp)
            
            # Update inputs to only contain valid parameters
            spec["inputs"] = valid_inputs
            
            # Move commands from inputs to steps
            if commands_to_move:
                if "steps" not in spec:
                    spec["steps"] = []
                if not isinstance(spec["steps"], list):
                    spec["steps"] = []
                # Prepend the moved commands to steps (they should be at the beginning)
                spec["steps"] = commands_to_move + spec["steps"]
                logger.warning(
                    f"Moved {len(commands_to_move)} command(s) from inputs to steps section. "
                    f"Total steps now: {len(spec['steps'])}"
                )
        
        # Fix inputs if it's a dict instead of list
        if "inputs" in spec and isinstance(spec["inputs"], dict):
            fixed_inputs = []
            for name, value in spec["inputs"].items():
                fixed_inputs.append({
                    "name": name,
                    "type": "string",
                    "required": True,
                    "description": f"Parameter: {name}"
                })
            spec["inputs"] = fixed_inputs
            logger.debug(f"Fixed inputs: converted dict to list format with {len(fixed_inputs)} items")
        
        # Fix postchecks if it's a single dict instead of a list
        if "postchecks" in spec and isinstance(spec["postchecks"], dict):
            spec["postchecks"] = [spec["postchecks"]]
            logger.debug("Fixed postchecks: converted single dict to list format")
        
        # Fix incomplete commands and ensure expected_output for checks
        for section_name in ["prechecks", "postchecks"]:
            if section_name in spec and isinstance(spec[section_name], list):
                cleaned_checks = []
                for check in spec[section_name]:
                    if isinstance(check, dict):
                        command = check.get("command")
                        if not command or not command.strip():
                            logger.warning(f"Removing {section_name} item with missing command: {check.get('description', 'N/A')}")
                            continue
                        if not check.get("expected_output"):
                            check["expected_output"] = "Command executed successfully"
                            logger.warning(f"Added default expected_output to {section_name} item: {check.get('description', 'N/A')}")
                        cleaned_checks.append(check)
                spec[section_name] = cleaned_checks
        
        # Fix incomplete steps
        if "steps" in spec and isinstance(spec["steps"], list):
            cleaned_steps = []
            for step in spec["steps"]:
                if isinstance(step, dict):
                    step_type = step.get("type", "command")
                    command_value = step.get("command")
                    
                    if step_type == "command":
                        if not command_value or (isinstance(command_value, str) and not command_value.strip()):
                            logger.warning(f"Removing step with missing/empty command: {step.get('name', 'N/A')}")
                            continue
                    
                    if step_type == "command" and command_value and not step.get("expected_output"):
                        step["expected_output"] = "Command executed successfully"
                        logger.warning(f"Added default expected_output to step: {step.get('name', 'N/A')}")
                    
                    cleaned_steps.append(step)
                else:
                    logger.warning(f"Skipping invalid step entry: {step}")
                    continue
            
            if not cleaned_steps:
                raise ValueError("All steps were removed due to missing commands")
            spec["steps"] = cleaned_steps
        
        # Ensure required fields with defaults
        if "env" not in spec:
            spec["env"] = env
        if "risk" not in spec:
            spec["risk"] = risk
        
        # Fix description field if it's copying from inputs
        if "description" in spec:
            description = str(spec["description"]).strip()
            input_description_texts = [
                "Database name (input parameter for execution)",
                "Name of the database to troubleshoot",
                "Target server hostname or IP address",
                "Database name (required for database issues)",
                "Parameter: server_name",
                "Parameter: database_name"
            ]
            if any(text in description for text in input_description_texts) or len(description) < 50:
                logger.warning(f"Fixing description field: was '{description[:100]}'")
                spec["description"] = f"The {issue_description.lower()}. This issue requires immediate attention to prevent service disruption and data loss."
                logger.info(f"Fixed description to: {spec['description'][:100]}...")
        
        # Ensure server_name is in inputs if commands use it
        if "inputs" in spec and isinstance(spec["inputs"], list):
            input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict)]
            all_commands = []
            for section in ["prechecks", "steps", "postchecks"]:
                if section in spec and isinstance(spec[section], list):
                    for item in spec[section]:
                        if isinstance(item, dict) and "command" in item:
                            all_commands.append(str(item["command"]))
            
            uses_server_name = any("{{server_name}}" in cmd or "__SERVER_NAME__" in cmd for cmd in all_commands)
            if uses_server_name and "server_name" not in input_names:
                logger.warning(f"Adding missing server_name input (commands use {{server_name}})")
                spec["inputs"].insert(0, {
                    "name": "server_name",
                    "type": "string",
                    "required": True,
                    "description": "Target server hostname or IP address"
                })
        
        # Ensure database_name is in inputs if commands use it
        if "inputs" in spec and isinstance(spec["inputs"], list):
            input_names = [inp.get("name") for inp in spec["inputs"] if isinstance(inp, dict)]
            all_commands = []
            for section in ["prechecks", "steps", "postchecks"]:
                if section in spec and isinstance(spec[section], list):
                    for item in spec[section]:
                        if isinstance(item, dict) and "command" in item:
                            all_commands.append(str(item["command"]))
            
            uses_database_name = any("{{database_name}}" in cmd or "__DATABASE_NAME__" in cmd for cmd in all_commands)
            if uses_database_name and "database_name" not in input_names:
                logger.warning(f"Adding missing database_name input (commands use {{database_name}})")
                spec["inputs"].append({
                    "name": "database_name",
                    "type": "string",
                    "required": True,
                    "description": "Database name (input parameter for execution)"
                })
        
        # Ensure all inputs have proper description fields
        if "inputs" in spec and isinstance(spec["inputs"], list):
            default_descriptions = {
                "server_name": "Target server hostname or IP address",
                "database_name": "Database name (input parameter for execution)"
            }
            for inp in spec["inputs"]:
                if isinstance(inp, dict):
                    name = inp.get("name")
                    if name and not inp.get("description") and name in default_descriptions:
                        logger.warning(f"Adding missing description for input '{name}'")
                        inp["description"] = default_descriptions[name]
        
        # Ensure runbook_id is properly formatted
        if "runbook_id" not in spec or not spec["runbook_id"]:
            title_slug = re.sub(r'[^a-z0-9]+', '-', spec.get("title", "runbook").lower()).strip('-')
            spec["runbook_id"] = f"rb-{spec.get('service', 'unknown')}-{title_slug[:30]}"
            logger.warning(f"Generated missing runbook_id: {spec['runbook_id']}")
        elif not spec["runbook_id"].startswith("rb-"):
            spec["runbook_id"] = f"rb-{spec['runbook_id'].lstrip('rb-')}"
            logger.warning(f"Fixed runbook_id format: {spec['runbook_id']}")
        
        return spec
    
    def _format_runbook_context(self, search_results: List[SearchResult], issue_description: str) -> str:
        """
        Format retrieved runbooks into structured context that guides LLM generation.
        Extracts only relevant sections to keep context focused.
        
        Args:
            search_results: List of SearchResult objects from vector search
            issue_description: The original issue description
            
        Returns:
            Formatted context string to include in LLM prompt
        """
        if not search_results:
            return "No similar runbooks found."
        
        context_parts = []
        
        # Limit to top 2-3 most relevant runbooks
        for i, result in enumerate(search_results[:3], 1):
            title = result.document_title or "Untitled Runbook"
            score = result.score
            
            # Extract only relevant parts from the chunk
            text = result.text
            
            # Try to extract key information: commands, structure
            relevant_parts = []
            
            # Extract commands (most useful for LLM)
            import re
            # Find command lines
            command_pattern = r'(?:command|Command):\s*(.+?)(?:\n|$)'
            commands = re.findall(command_pattern, text, re.IGNORECASE)
            if commands:
                relevant_parts.extend([f"  Command: {cmd.strip()}" for cmd in commands[:5]])  # Limit to 5 commands
            
            # Extract step names
            step_pattern = r'(?:name|Name|step|Step):\s*(.+?)(?:\n|$)'
            steps = re.findall(step_pattern, text, re.IGNORECASE)
            if steps:
                relevant_parts.extend([f"  Step: {step.strip()}" for step in steps[:3]])  # Limit to 3 steps
            
            if relevant_parts:
                context_parts.append(f"Runbook {i}: {title} (similarity: {score:.2f})")
                context_parts.extend(relevant_parts)
                context_parts.append("")
        
        if not context_parts:
            # Fallback: just show titles
            for i, result in enumerate(search_results[:3], 1):
                context_parts.append(f"Runbook {i}: {result.document_title or 'Untitled'} (similarity: {result.score:.2f})")
        
        return "\n".join(context_parts) if context_parts else "No similar runbooks found."
    
    def _validate_generated_runbook(
        self, 
        spec: Dict[str, Any], 
        issue_description: str
    ) -> tuple[bool, List[str]]:
        """
        Validate generated runbook structure and content.
        
        Args:
            spec: Parsed YAML runbook specification
            issue_description: Original issue description
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # CRITICAL: Validate inputs section doesn't contain commands
        inputs = spec.get("inputs", [])
        if isinstance(inputs, list):
            for inp in inputs:
                if isinstance(inp, dict):
                    # Check if input has a "command" field - this is WRONG
                    if "command" in inp:
                        errors.append(
                            f"CRITICAL: inputs section contains a command '{inp.get('name', 'unknown')}' - "
                            f"commands belong in prechecks/steps/postchecks, NOT in inputs! "
                            f"Inputs should only have: name, type, required, description"
                        )
                    # Check if input has "type: command" - this is WRONG
                    if inp.get("type") == "command":
                        errors.append(
                            f"CRITICAL: input '{inp.get('name', 'unknown')}' has type='command' - "
                            f"inputs should have type='string', not 'command'! "
                            f"Commands belong in prechecks/steps/postchecks sections"
                        )
        
        # Validate structure: prechecks must be exactly 3
        prechecks = spec.get("prechecks", [])
        if not isinstance(prechecks, list):
            errors.append("CRITICAL: prechecks must be a list")
        elif len(prechecks) != 3:
            errors.append(
                f"CRITICAL: prechecks must have EXACTLY 3 steps, found {len(prechecks)}. "
                f"This is a hard requirement - the runbook will be rejected if not exactly 3."
            )
        
        # Validate structure: steps must be 5-6
        steps = spec.get("steps", [])
        if not isinstance(steps, list):
            errors.append("CRITICAL: steps must be a list")
        elif len(steps) < 5 or len(steps) > 6:
            errors.append(
                f"CRITICAL: steps must have EXACTLY 5-6 steps, found {len(steps)}. "
                f"This is a hard requirement - the runbook will be rejected if not 5-6 steps."
            )
        
        # Validate structure: postchecks must be exactly 1
        postchecks = spec.get("postchecks", [])
        if not isinstance(postchecks, list):
            errors.append("CRITICAL: postchecks must be a list")
        elif len(postchecks) != 1:
            errors.append(
                f"CRITICAL: postchecks must have EXACTLY 1 step, found {len(postchecks)}. "
                f"This is a hard requirement - the runbook will be rejected if not exactly 1."
            )
        
        # Validate that precheck checks the actual metric from issue
        issue_lower = issue_description.lower()
        metric_keywords = {
            "cpu": ["cpu", "processor", "processor time"],
            "memory": ["memory", "ram", "available mbytes", "committed bytes"],
            "disk": ["disk", "disk space", "free space", "logicaldisk"],
            "network": ["network", "bytes received", "bytes sent"],
            "transaction log": ["transaction log", "log_reuse_wait", "log space"],
            "connection pool": ["connection pool", "connections", "pg_stat_activity"]
        }
        
        detected_metric = None
        for metric, keywords in metric_keywords.items():
            if any(keyword in issue_lower for keyword in keywords):
                detected_metric = metric
                break
        
        if detected_metric:
            # Check if any precheck command mentions the metric
            precheck_commands = [str(p.get("command", "")).lower() for p in prechecks if isinstance(p, dict)]
            metric_found = False
            for keyword in metric_keywords.get(detected_metric, []):
                if any(keyword in cmd for cmd in precheck_commands):
                    metric_found = True
                    break
            
            if not metric_found:
                errors.append(
                    f"precheck should check the actual metric '{detected_metric}' mentioned in issue, "
                    f"but no precheck command mentions it"
                )
        
        # Validate that postcheck verifies resolution of the same metric
        if detected_metric and postchecks:
            postcheck_commands = [str(p.get("command", "")).lower() for p in postchecks if isinstance(p, dict)]
            metric_found = False
            for keyword in metric_keywords.get(detected_metric, []):
                if any(keyword in cmd for cmd in postcheck_commands):
                    metric_found = True
                    break
            
            if not metric_found:
                errors.append(
                    f"postcheck should verify resolution of '{detected_metric}', "
                    f"but postcheck command doesn't mention it"
                )
        
        # Validate that main steps include remediation (not just diagnostics)
        remediation_keywords = [
            "restart", "stop", "kill", "start", "clear", "delete", "remove",
            "backup", "shrink", "terminate", "fix", "repair", "resolve"
        ]
        
        step_commands = [str(s.get("command", "")).lower() for s in steps if isinstance(s, dict)]
        has_remediation = any(
            any(keyword in cmd for keyword in remediation_keywords)
            for cmd in step_commands
        )
        
        if not has_remediation:
            errors.append(
                "main steps should include remediation (restart, kill, fix, etc.), "
                "not just diagnostic commands"
            )
        
        # Validate title matches issue description
        title = spec.get("title", "").lower()
        if title and issue_description:
            # Check if title contains key words from issue
            issue_words = set(issue_description.lower().split())
            title_words = set(title.split())
            # Remove common stop words
            stop_words = {"fix", "resolve", "troubleshoot", "the", "a", "an", "on", "for", "to", "of"}
            issue_keywords = issue_words - stop_words
            title_keywords = title_words - stop_words
            
            if issue_keywords and not (issue_keywords & title_keywords):
                errors.append(
                    f"title '{spec.get('title')}' doesn't match issue description keywords"
                )
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    async def approve_and_index_runbook(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> RunbookResponse:
        """Approve a draft runbook and index it for search"""
        return await self.runbook_indexer.approve_and_index_runbook(runbook_id, tenant_id, db)

