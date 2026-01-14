"""
Validation pipeline for generated runbooks
Handles structure validation, command validation, and LLM critique
"""
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from app.core.logging import get_logger
from app.config import runbook_structure
from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.services.runbook.generation.runbook_command_validator import RunbookCommandValidator
from app.services.runbook.generation.runbook_critic_service import RunbookCriticService

logger = get_logger(__name__)


class ValidationPipeline:
    """Handles all validation phases for generated runbooks"""
    
    def __init__(self):
        self.quality_validator = RunbookQualityValidator()
        self.command_validator = RunbookCommandValidator()
        self.critic_service = RunbookCriticService()
    
    def validate_structure(
        self,
        spec: Dict[str, Any],
        issue_description: str
    ) -> tuple[bool, List[str]]:
        """
        Phase 1: Validate runbook structure and content
        
        Returns:
            (is_valid, validation_errors)
        """
        logger.info("Running runbook validation (structure, inputs, branching)...")
        is_valid, validation_errors = self.quality_validator.validate(spec, issue_description)
        logger.info(
            f"Validation complete: is_valid={is_valid}, "
            f"error_count={len(validation_errors)}"
        )
        
        if not is_valid:
            # Check for CRITICAL errors
            critical_errors = [e for e in validation_errors if "CRITICAL" in e.upper()]
            remediation_errors = [
                e for e in validation_errors
                if "remediation" in e.lower() or "REMEDIATE" in e.upper()
            ]
            
            if remediation_errors:
                critical_errors.extend(remediation_errors)
            
            if critical_errors:
                logger.error("CRITICAL validation failures - runbook structure is incorrect:")
                for error in critical_errors:
                    logger.error(f"  - {error}")
                logger.error(f"Full validation errors: {validation_errors}")
                logger.error(f"Runbook spec keys: {list(spec.keys())}")
                logger.error(f"Prechecks count: {len(spec.get('prechecks', []))}")
                logger.error(f"Steps count: {len(spec.get('steps', []))}")
                logger.error(f"Postchecks count: {len(spec.get('postchecks', []))}")
                
                # Check if structure is severely broken
                prechecks_count = len(spec.get("prechecks", []))
                steps_count = len(spec.get("steps", []))
                postchecks_count = len(spec.get("postchecks", []))
                
                has_remediation_error = any(
                    "remediation" in e.lower() or "REMEDIATE" in e.upper()
                    for e in critical_errors
                )
                
                if (steps_count < 2 or prechecks_count == 0 or
                    postchecks_count == 0 or has_remediation_error):
                    error_detail = (
                        f"LLM generated invalid runbook structure. "
                        f"Prechecks: {prechecks_count} "
                        f"(required: {runbook_structure.PRECHECKS_COUNT}), "
                        f"Steps: {steps_count} "
                        f"(required: {runbook_structure.STEPS_MIN}-{runbook_structure.STEPS_MAX}), "
                        f"Postchecks: {postchecks_count} "
                        f"(required: {runbook_structure.POSTCHECKS_COUNT})."
                    )
                    if has_remediation_error:
                        error_detail += (
                            f" CRITICAL: Runbook missing required REMEDIATION steps. "
                            f"Runbooks must include at least 4 remediation actions "
                            f"(kill, restart, stop, clear, fix, etc.) to actually SOLVE "
                            f"the problem, not just investigate it."
                        )
                    error_detail += " Please try again or check LLM configuration."
                    
                    logger.error(
                        f"Runbook structure is severely incorrect - rejecting. "
                        f"Prechecks: {prechecks_count} (need 3), "
                        f"Steps: {steps_count} (need 5-6), "
                        f"Postchecks: {postchecks_count} (need 1), "
                        f"Has remediation: {not has_remediation_error}"
                    )
                    raise HTTPException(status_code=502, detail=error_detail)
                
                logger.warning(
                    "Runbook has structure issues but may be recoverable. "
                    "Consider regenerating for better results."
                )
            else:
                logger.warning(
                    f"Runbook validation warnings (non-critical): "
                    f"{len(validation_errors)} error(s)"
                )
                for error in validation_errors:
                    logger.warning(f"  - {error}")
                    if ("undefined input" in error.lower() or
                        "references undefined" in error.lower()):
                        logger.error(f"  ⚠️ INPUT VALIDATION ERROR: {error}")
        
        return is_valid, validation_errors
    
    async def validate_commands(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        env: str,
        os_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Phase 2: Validate runbook commands via web search for grounding
        
        Returns:
            Command validation result dictionary
        """
        logger.info("Validating runbook commands via web search for grounding...")
        
        try:
            if os_type is None:
                os_type = env if env in ["Windows", "Linux"] else None
            
            command_validation = await self.command_validator.validate_runbook_commands(
                spec, issue_description, os_type
            )
            
            if not command_validation["is_valid"]:
                logger.warning(
                    f"Command validation found issues: "
                    f"{command_validation['validation_summary']}"
                )
                
                # Log detailed issues
                if command_validation["invalid_commands"]:
                    logger.error(
                        f"Found {len(command_validation['invalid_commands'])} "
                        f"invalid command(s):"
                    )
                    for invalid in command_validation["invalid_commands"]:
                        logger.error(
                            f"  - {invalid['section']} {invalid['index']}: "
                            f"{invalid['command'][:80]}... "
                            f"Issue: {invalid['issue']}"
                        )
                
                if command_validation["diagnostic_mislabeled"]:
                    logger.error(
                        f"Found {len(command_validation['diagnostic_mislabeled'])} "
                        f"mislabeled command(s):"
                    )
                    for mislabeled in command_validation["diagnostic_mislabeled"]:
                        logger.error(
                            f"  - {mislabeled['section']} {mislabeled['index']}: "
                            f"{mislabeled['command'][:80]}... "
                            f"Issue: {mislabeled['issue']}"
                        )
                
                # CRITICAL: Missing remediation is a hard failure
                if command_validation["missing_remediation"]:
                    error_detail = (
                        f"CRITICAL: Command validation found only "
                        f"{len(command_validation.get('remediation_commands_found', []))} "
                        f"actual remediation command(s), need at least 4. "
                        f"Runbook commands must include actual fix actions "
                        f"(kill, restart, stop, clear, etc.), not just diagnostic commands. "
                    )
                    if command_validation["suggestions"]:
                        error_detail += " ".join(command_validation["suggestions"])
                    error_detail += " Please regenerate with proper remediation steps."
                    
                    logger.error(error_detail)
                    raise HTTPException(status_code=502, detail=error_detail)
                
                # For invalid commands or mislabeled, add warnings to metadata
                if (command_validation["invalid_commands"] or
                    command_validation["diagnostic_mislabeled"]):
                    if "meta_data" not in spec:
                        spec["meta_data"] = {}
                    spec["meta_data"]["command_validation_warnings"] = (
                        command_validation["suggestions"]
                    )
                    spec["meta_data"]["invalid_commands"] = (
                        command_validation["invalid_commands"]
                    )
                    spec["meta_data"]["diagnostic_mislabeled"] = (
                        command_validation["diagnostic_mislabeled"]
                    )
                    logger.warning(
                        f"Command validation found issues but runbook structure is valid. "
                        f"Warnings added to metadata. Consider regenerating for better results."
                    )
            else:
                logger.info(
                    f"Command validation passed: "
                    f"{command_validation['validation_summary']}. "
                    f"Found {len(command_validation.get('remediation_commands_found', []))} "
                    f"valid remediation command(s)."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                f"Command validation failed (non-fatal): {e}. "
                f"Continuing with runbook generation."
            )
            command_validation = {"is_valid": True}  # Default to valid on error
        
        return command_validation
    
    async def critique_runbook(
        self,
        spec: Dict[str, Any],
        issue_description: str,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Phase 3: LLM critique for logical flow validation (optional)
        
        Returns:
            Critique result dictionary
        """
        import os
        enable_critique = os.getenv("ENABLE_LLM_CRITIQUE", "true").lower() == "true"
        
        if not enable_critique:
            return {"is_valid": True}
        
        logger.info("Running LLM critique for logical flow validation...")
        
        try:
            critique_result = await self.critic_service.critique_runbook(
                spec, issue_description, tenant_id
            )
            
            if not critique_result["is_valid"]:
                logger.warning(
                    f"LLM critique found issues "
                    f"(confidence: {critique_result['confidence']:.2f}): "
                    f"{len(critique_result['issues'])} critical, "
                    f"{len(critique_result['warnings'])} warnings"
                )
                
                if critique_result["issues"]:
                    logger.error("Critical issues found:")
                    for issue in critique_result["issues"]:
                        logger.error(f"  - {issue}")
                
                if critique_result["regeneration_needed"]:
                    if "meta_data" not in spec:
                        spec["meta_data"] = {}
                    spec["meta_data"]["critique_issues"] = critique_result["issues"]
                    spec["meta_data"]["critique_warnings"] = critique_result["warnings"]
                    spec["meta_data"]["critique_suggestions"] = (
                        critique_result["suggestions"]
                    )
                    logger.warning(
                        "LLM critique suggests regeneration, but runbook passed "
                        "structural validation. Consider reviewing before approval."
                    )
                else:
                    if "meta_data" not in spec:
                        spec["meta_data"] = {}
                    spec["meta_data"]["critique_warnings"] = critique_result["warnings"]
                    spec["meta_data"]["critique_suggestions"] = (
                        critique_result["suggestions"]
                    )
            else:
                logger.info(
                    f"LLM critique passed (confidence: {critique_result['confidence']:.2f}). "
                    f"Runbook logic is sound."
                )
        except Exception as e:
            logger.warning(
                f"LLM critique failed (non-fatal): {e}. "
                f"Continuing with runbook generation."
            )
            critique_result = {"is_valid": True}
        
        return critique_result

