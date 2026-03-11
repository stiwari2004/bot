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
        os_type: Optional[str] = None,
        operational_context: Optional[str] = None,
        issue_type: Optional[str] = None,
        entities: Optional[str] = None,
    ) -> str:
        """
        Generate YAML from LLM with error handling.

        Returns:
            Raw YAML string from LLM
        """
        if operational_context and operational_context.strip():
            context = (context or "") + "\n\nCurrent context (ticket/alert):\n" + operational_context.strip()
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
                issue_type=issue_type,
                entities=entities,
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
        
        logger.info(f"LLM returned YAML ({len(ai_yaml)} chars)")
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
        
        logger.debug(f"YAML after extraction ({len(ai_yaml)} chars)")
        
        return ai_yaml
    
    def preprocess_yaml_structure(self, ai_yaml: str) -> str:
        """
        Pre-process YAML to fix common structural issues
        
        Returns:
            Preprocessed YAML string
        """
        logger.debug(f"YAML cleanup start ({len(ai_yaml)} chars)")

        # Pre-process: Fix common structural issues before parsing
        ai_yaml = self.yaml_processor.preprocess_yaml_structure(ai_yaml)
        
        # Sanitize command strings and quote {{placeholders}}
        try:
            ai_yaml = self.yaml_processor.sanitize_command_strings(ai_yaml)
        except Exception as e:
            logger.warning(f"Command sanitization failed, continuing: {type(e).__name__}: {e}")

        ai_yaml = self.yaml_processor.fix_yaml_escape_sequences(ai_yaml)

        try:
            ai_yaml = self.yaml_processor.sanitize_expected_output_field(ai_yaml)
        except Exception as e:
            logger.warning(f"Expected output sanitization failed, continuing: {type(e).__name__}: {e}")

        try:
            ai_yaml = self.yaml_processor.fix_standalone_variable_names(ai_yaml)
        except Exception as e:
            logger.error(f"Variable name fix failed: {type(e).__name__}: {e}", exc_info=True)

        return ai_yaml

