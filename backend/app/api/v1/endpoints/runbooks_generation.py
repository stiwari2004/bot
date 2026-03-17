"""
Runbook generation endpoints — generate, detect-os, debug-yaml
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiting import rate_limit
from app.models.user import User
from app.schemas.runbook import RunbookResponse
from app.services.auth import get_current_user
from app.controllers.runbook_controller import RunbookController
from app.api.v1.endpoints.runbooks_schemas import GenerateAgentRunbookRequest

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate-agent", response_model=RunbookResponse)
@rate_limit("100/minute")
async def generate_agent_runbook(
    request: GenerateAgentRunbookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an agent-ready YAML runbook."""
    from app.services.llm_budget_manager import LLMRateLimitExceeded, LLMBudgetExceeded
    service_value = request.service.value
    try:
        controller = RunbookController(db, current_user.tenant_id)
        return await controller.generate_agent_runbook(
            request.issue_description, service_value, request.env.value, request.risk.value
        )
    except HTTPException:
        raise
    except (asyncio.TimeoutError, TimeoutError) as e:
        logger.error(f"LLM timeout error: {e}", exc_info=True)
        raise HTTPException(status_code=504, detail="Runbook generation timed out. Please try again.")
    except (LLMRateLimitExceeded, LLMBudgetExceeded) as e:
        logger.error(f"LLM budget/rate limit error: {e}", exc_info=True)
        raise HTTPException(status_code=429 if isinstance(e, LLMRateLimitExceeded) else 402, detail=str(e))
    except ValueError as e:
        error_msg = str(e).lower()
        if "yaml" in error_msg or "parsing" in error_msg or "invalid" in error_msg:
            logger.error(f"YAML parsing/validation failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate valid runbook YAML. Please try again.")
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating agent runbook: {e}", exc_info=True)
        err = str(e).lower()
        if any(k in err for k in ("connection", "refused", "failed to fetch models", "connect")):
            detail = (
                "Runbook generation failed: LLM is unreachable. "
                "In dev, set GEMINI_API_KEY in backend/.env or set LLAMACPP_BASE_URL."
            )
        else:
            detail = f"Failed to generate agent runbook: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/demo/detect-os")
async def detect_os_from_server(
    server_name: str = Query(..., min_length=1, max_length=255, description="Server/VM name to detect OS for"),
    db: Session = Depends(get_db),
):
    """Detect OS type (Windows/Linux) from Azure VM metadata (demo tenant)."""
    from app.services.cloud_discovery import CloudDiscoveryService
    try:
        vm_info = await CloudDiscoveryService.discover_azure_vm(db=db, vm_name=server_name, tenant_id=1)
        if not vm_info:
            return {"os_type": None, "detected": False, "message": f"VM '{server_name}' not found in Azure"}
        os_type = vm_info.get("os_type")
        if os_type:
            os_lower = os_type.lower()
            if "windows" in os_lower:
                return {"os_type": "Windows", "detected": True, "vm_name": vm_info.get("vm_name")}
            elif "linux" in os_lower:
                return {"os_type": "Linux", "detected": True, "vm_name": vm_info.get("vm_name")}
        return {"os_type": None, "detected": False, "message": f"OS type not available for VM '{server_name}'"}
    except Exception as e:
        return {"os_type": None, "detected": False, "error": str(e)}


@router.post("/demo/generate-agent", response_model=RunbookResponse)
async def generate_agent_runbook_demo(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev|Windows|Linux"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    ticket_id: Optional[int] = Query(None, description="Optional ticket ID to associate runbook with"),
    db: Session = Depends(get_db),
):
    """Generate an agent-ready YAML runbook (demo tenant)."""
    controller = RunbookController(db, tenant_id=1)
    env = await controller.auto_detect_os(issue_description, env)
    return await controller.generate_agent_runbook(issue_description, service, env, risk, ticket_id)


@router.post("/demo/debug-yaml")
async def debug_yaml_generation(
    issue_description: str,
    service: str = Query(..., description="Service type"),
    env: str = Query(..., description="Environment"),
    risk: str = Query(..., description="Risk level"),
    db: Session = Depends(get_db),
):
    """Debug endpoint to see raw YAML at each processing phase."""
    import re
    import yaml
    from app.services.runbook.generation import RunbookGeneratorService
    from app.services.llm_service import get_llm_service

    generator = RunbookGeneratorService()
    llm = get_llm_service()

    debug_info: dict = {
        "phase1_raw_yaml": None, "phase1_length": 0, "phase1_first_200": None,
        "phase1_newlines": [], "phase2_after_preprocess": None,
        "phase2_after_sanitize_description": None, "phase2_after_sanitize_commands": None,
        "phase2_after_escape_fix": None, "phase3_parse_error": None,
        "phase3_first_line": None, "phase3_char_at_101": None,
    }

    def get_line_30_info(yaml_text: str, phase_name: str) -> dict:
        lines = yaml_text.split("\n")
        if len(lines) >= 30:
            line_30 = lines[29]
            return {
                f"{phase_name}_line_30_raw": line_30,
                f"{phase_name}_line_30_repr": repr(line_30),
                f"{phase_name}_line_30_col_36": repr(line_30[35]) if len(line_30) >= 36 else "N/A",
                f"{phase_name}_line_30_context": repr(line_30[max(0, 25):min(len(line_30), 50)]) if len(line_30) >= 36 else "N/A",
            }
        return {}

    try:
        from app.services.runbook.generation.service_classifier import ServiceClassifier
        if service == "auto":
            classifier = ServiceClassifier()
            service = await classifier.detect_service_type(issue_description)
            logger.info(f"Auto-detected service type: {service}")

        ai_yaml = await llm.generate_yaml_runbook(
            tenant_id=1, issue_description=issue_description, service_type=service, env=env, risk=risk, context=""
        )
        debug_info["phase1_raw_yaml"] = ai_yaml
        debug_info["phase1_length"] = len(ai_yaml) if ai_yaml else 0
        debug_info["phase1_first_200"] = repr(ai_yaml[:200]) if ai_yaml else None

        if ai_yaml:
            lines = ai_yaml.split("\n")
            if len(lines) >= 30:
                l30 = lines[29]
                debug_info["phase1_line_30"] = {
                    "raw": l30, "repr": repr(l30),
                    "column_36_char": repr(l30[35]) if len(l30) >= 36 else "N/A",
                    "context_around_col_36": repr(l30[max(0, 35 - 20):35 + 20]) if len(l30) >= 36 else "N/A",
                }
            for i, char in enumerate(ai_yaml[:200]):
                if char == "\n":
                    debug_info["phase1_newlines"].append({"position": i, "context": repr(ai_yaml[max(0, i - 30):i + 30])})

        processor = generator.yaml_processor
        y1 = processor.preprocess_yaml_structure(ai_yaml)
        debug_info["phase2_after_preprocess"] = y1[:500]
        debug_info.update(get_line_30_info(y1, "phase2_preprocess"))

        y2 = processor.sanitize_description_field(y1)
        debug_info["phase2_after_sanitize_description"] = y2[:500]
        debug_info.update(get_line_30_info(y2, "phase2_after_desc"))

        y3 = processor.sanitize_command_strings(y2)
        debug_info["phase2_after_sanitize_commands"] = y3[:500]
        debug_info.update(get_line_30_info(y3, "phase2_after_commands"))

        yaml_final = processor.fix_yaml_escape_sequences(y3)
        debug_info["phase2_after_escape_fix"] = yaml_final[:500]
        debug_info.update(get_line_30_info(yaml_final, "phase2_final"))

        first_line = yaml_final.split("\n")[0] if "\n" in yaml_final else yaml_final
        debug_info["phase3_first_line"] = repr(first_line)
        if len(first_line) >= 101:
            debug_info["phase3_char_at_101"] = repr(first_line[100])
            debug_info["phase3_context_around_101"] = repr(first_line[90:110])
        debug_info["phase3_full_yaml_before_parse"] = yaml_final

        try:
            yaml.safe_load(yaml_final)
            debug_info["phase3_parse_success"] = True
        except Exception as e:
            debug_info["phase3_parse_error"] = str(e)
            debug_info["phase3_parse_success"] = False
            line_match = re.search(r"line (\d+)", str(e))
            col_match = re.search(r"column (\d+)", str(e))
            if line_match and col_match:
                el = int(line_match.group(1))
                ec = int(col_match.group(1))
                lines = yaml_final.split("\n")
                if el <= len(lines):
                    debug_info["phase3_error_line_content"] = lines[el - 1]
                    debug_info["phase3_error_line_repr"] = repr(lines[el - 1])
                    if ec <= len(lines[el - 1]):
                        debug_info["phase3_error_char"] = repr(lines[el - 1][ec - 1])
                        debug_info["phase3_error_context"] = repr(lines[el - 1][max(0, ec - 20):ec + 20])
    except Exception as e:
        import traceback
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()

    return debug_info
