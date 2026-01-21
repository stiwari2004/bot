"""
YAML generation pipeline for agent runbooks
Handles LLM generation, extraction, and initial cleanup
"""
import asyncio
from typing import Optional, Dict, Any
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.services.llm_budget_manager import LLMBudgetExceeded, LLMRateLimitExceeded
from app.services.runbook.generation.yaml_extractor import YamlExtractor
from app.services.runbook.generation.yaml_processor import YamlProcessor
from fastapi import HTTPException

logger = get_logger(__name__)


class YamlGenerationPipeline:
    """Handles YAML generation from LLM and initial cleanup"""
    
    def __init__(self):
        self.yaml_extractor = YamlExtractor()
        self.yaml_processor = YamlProcessor()
    
    async def generate_yaml_from_llm(
        self,
        issue_description: str,
        tenant_id: int,
        service: str,
        env: str,
        risk: str,
        context: str,
        os_type: Optional[str] = None
    ) -> str:
        """
        Generate YAML from LLM with error handling
        
        Returns:
            Raw YAML string from LLM
        """
        llm = get_llm_service()
        try:
            logger.debug(
                f"LLM provider: {type(llm).__name__} "
                f"base={getattr(llm, 'base_url', None)} "
                f"model_id={getattr(llm, 'model_id', None)}"
            )
        except Exception:
            pass
        
        try:
            ai_yaml = await llm.generate_yaml_runbook(
                tenant_id=tenant_id,
                issue_description=issue_description,
                service_type=service,
                env=env,
                risk=risk,
                context=context,
                os_type=os_type if service == "server" else None,
            )
        except LLMRateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except LLMBudgetExceeded as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise HTTPException(
                status_code=504,
                detail="LLM request timed out. Please try again."
            ) from exc
        
        # Check for empty response early
        if not ai_yaml or not ai_yaml.strip():
            logger.error(f"LLM returned empty YAML response. Issue: {issue_description[:100]}...")
            raise HTTPException(
                status_code=502,
                detail="LLM returned empty response. Please check LLM connection and try again."
            )
        
        logger.info(
            f"[PHASE 1 - YAML GENERATION] LLM returned YAML length={len(ai_yaml) if ai_yaml else 0}"
        )
        logger.info(
            f"[PHASE 1 - YAML GENERATION] First 200 chars: {repr(ai_yaml[:200]) if ai_yaml else 'None'}"
        )
        
        # Check for newlines in first 200 chars
        if ai_yaml:
            for i, char in enumerate(ai_yaml[:200]):
                if char == '\n':
                    logger.error(
                        f"[PHASE 1 - YAML GENERATION] FOUND NEWLINE at position {i} in first 200 chars!"
                    )
                    logger.error(
                        f"[PHASE 1 - YAML GENERATION] Context: "
                        f"{repr(ai_yaml[max(0, i-30):i+30])}"
                    )
        
        return ai_yaml
    
    def extract_and_clean_yaml(self, ai_yaml: str) -> str:
        """
        Extract YAML from LLM response and perform initial cleanup
        
        Returns:
            Cleaned YAML string
        """
        # Extract and clean YAML using YamlExtractor
        ai_yaml = self.yaml_extractor.extract_yaml(ai_yaml)
        
        # Sanitize LLM output using YAML processor
        ai_yaml = self.yaml_processor.sanitize_description_field(ai_yaml)
        
        # Fix newlines in YAML values that break parsing
        ai_yaml = self.yaml_extractor.fix_newlines_in_yaml(ai_yaml)
        
        logger.debug(
            f"[DEBUG] YAML before parse (first 3000 chars): "
            f"{ai_yaml[:3000] if ai_yaml else 'None'}"
        )
        
        return ai_yaml
    
    def preprocess_yaml_structure(self, ai_yaml: str) -> str:
        """
        Pre-process YAML to fix common structural issues
        
        Returns:
            Preprocessed YAML string
        """
        logger.info(f"[PHASE 2 - YAML CLEANUP] Starting cleanup, length={len(ai_yaml)}")
        
        # Pre-process: Fix common structural issues before parsing
        ai_yaml = self.yaml_processor.preprocess_yaml_structure(ai_yaml)
        logger.info(
            f"[PHASE 2 - YAML CLEANUP] After preprocess_yaml_structure, "
            f"length={len(ai_yaml)}"
        )
        
        # Sanitize command strings and quote {{placeholders}}
        try:
            ai_yaml = self.yaml_processor.sanitize_command_strings(ai_yaml)
            logger.info(
                f"[PHASE 2 - YAML CLEANUP] After sanitize_command_strings, "
                f"length={len(ai_yaml)}"
            )
            # Check first line specifically
            first_line = ai_yaml.split('\n')[0] if '\n' in ai_yaml else ai_yaml
            if len(first_line) >= 101:
                logger.error(
                    f"[PHASE 2 - YAML CLEANUP] First line length={len(first_line)}, "
                    f"char at 101: {repr(first_line[100])}"
                )
                logger.error(
                    f"[PHASE 2 - YAML CLEANUP] First line (first 150 chars): "
                    f"{repr(first_line[:150])}"
                )
        except Exception as e:
            logger.warning(
                f"Command sanitization failed, continuing without it: "
                f"{type(e).__name__}: {e}"
            )
        
        # Fix YAML escape sequence issues
        ai_yaml = self.yaml_processor.fix_yaml_escape_sequences(ai_yaml)
        logger.info(
            f"[PHASE 2 - YAML CLEANUP] After fix_yaml_escape_sequences, "
            f"length={len(ai_yaml)}"
        )
        
        # Sanitize expected_output fields
        try:
            ai_yaml = self.yaml_processor.sanitize_expected_output_field(ai_yaml)
            logger.info(
                f"[PHASE 2 - YAML CLEANUP] After sanitize_expected_output_field, "
                f"length={len(ai_yaml)}"
            )
        except Exception as e:
            logger.warning(
                f"Expected output sanitization failed, continuing without it: "
                f"{type(e).__name__}: {e}"
            )
        
        # Fix standalone variable names
        try:
            ai_yaml_before_fix = ai_yaml
            logger.info(
                f"[PHASE 2 - YAML CLEANUP] BEFORE fix_standalone_variable_names, "
                f"length={len(ai_yaml)}"
            )
            
            # Log lines 50-60 before fix
            yaml_lines_before = ai_yaml_before_fix.split('\n')
            if len(yaml_lines_before) > 50:
                logger.info(f"[PHASE 2 - YAML CLEANUP] BEFORE fix - Lines 50-60:")
                for i in range(49, min(60, len(yaml_lines_before))):
                    logger.info(f"  Line {i+1:3d}: {repr(yaml_lines_before[i])}")
            
            ai_yaml = self.yaml_processor.fix_standalone_variable_names(ai_yaml)
            
            if ai_yaml != ai_yaml_before_fix:
                logger.info(
                    f"[PHASE 2 - YAML CLEANUP] After fix_standalone_variable_names, "
                    f"length={len(ai_yaml)} (CHANGED)"
                )
                # Log changes
                before_lines = ai_yaml_before_fix.split('\n')
                after_lines = ai_yaml.split('\n')
                changes_found = False
                for i, (before, after) in enumerate(zip(before_lines, after_lines)):
                    if before != after:
                        changes_found = True
                        logger.info(
                            f"[YAML FIX] Line {i+1} changed: "
                            f"{repr(before[:100])} -> {repr(after[:100])}"
                        )
                
                if not changes_found:
                    logger.warning(
                        f"[YAML FIX] YAML changed but no line differences detected "
                        f"(length changed: {len(ai_yaml_before_fix)} -> {len(ai_yaml)})"
                    )
                
                # Log lines 50-60 after fix
                if len(after_lines) > 50:
                    logger.info(f"[PHASE 2 - YAML CLEANUP] AFTER fix - Lines 50-60:")
                    for i in range(49, min(60, len(after_lines))):
                        logger.info(f"  Line {i+1:3d}: {repr(after_lines[i])}")
            else:
                logger.info(
                    f"[PHASE 2 - YAML CLEANUP] After fix_standalone_variable_names, "
                    f"length={len(ai_yaml)} (NO CHANGES)"
                )
        except Exception as e:
            logger.error(
                f"Variable name fix failed with exception: {type(e).__name__}: {e}"
            )
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return ai_yaml

