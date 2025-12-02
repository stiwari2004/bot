"""
Runbook API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.core.database import get_db, SessionLocal
from app.models.user import User
from app.schemas.runbook import RunbookResponse, RunbookUpdate
from app.services.auth import get_current_user
from app.controllers.runbook_controller import RunbookController
from app.controllers.runbook_version_controller import RunbookVersionController
from app.controllers.citation_controller import CitationController
from app.services.cloud_discovery import CloudDiscoveryService
from app.services.ci_extraction_service import CIExtractionService
from app.core.rate_limiting import rate_limit

router = APIRouter()


# Input validation models
class ServiceType(str, Enum):
    """CI Type enumeration"""
    SERVER = "server"
    DATABASE = "database"
    WEB = "web"
    STORAGE = "storage"
    NETWORK = "network"
    AUTO = "auto"
    # Backward compatibility
    WINDOWS = "Windows"
    LINUX = "Linux"


class EnvironmentType(str, Enum):
    """Environment enumeration"""
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"
    TESTING = "testing"


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GenerateAgentRunbookRequest(BaseModel):
    """Request model for agent runbook generation"""
    issue_description: str = Field(..., min_length=10, max_length=5000, description="Issue description")
    service: ServiceType = Field(..., description="CI Type")
    env: EnvironmentType = Field(..., description="Environment")
    risk: RiskLevel = Field(..., description="Risk level")
    
    @validator('issue_description')
    def validate_issue_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Issue description cannot be empty")
        # Sanitize: remove control characters except newlines and tabs
        sanitized = ''.join(c for c in v if ord(c) >= 32 or c in '\n\t')
        if len(sanitized) < 10:
            raise ValueError("Issue description must be at least 10 characters")
        return sanitized


## Removed legacy generation endpoint to avoid confusion; use /generate-agent only


@router.post("/generate-agent", response_model=RunbookResponse)
@rate_limit("100/minute")  # High limit for dev/test
async def generate_agent_runbook(
    request: GenerateAgentRunbookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an agent-ready YAML runbook (atomic, executable).
    
    Note: The 'service' parameter represents CI Type (server, database, web, etc.).
    For servers, OS type (Windows/Linux) is auto-detected from issue description.
    For backward compatibility, 'Windows' or 'Linux' are accepted and treated as 'server' CI type.
    """
    # Normalize service for backward compatibility
    service_value = request.service.value
    if service_value in ["Windows", "Linux"]:
        service_value = "server"
    
    controller = RunbookController(db, current_user.tenant_id)
    return await controller.generate_agent_runbook(
        request.issue_description,
        service_value,
        request.env.value,
        request.risk.value
    )


@router.get("/demo/detect-os")
async def detect_os_from_server(
    server_name: str = Query(..., min_length=1, max_length=255, description="Server/VM name to detect OS for"),
    db: Session = Depends(get_db)
):
    """Detect OS type (Windows/Linux) from Azure VM metadata (demo tenant)."""
    try:
        # Try to discover the VM from Azure
        vm_info = await CloudDiscoveryService.discover_azure_vm(
            db=db,
            vm_name=server_name,
            tenant_id=1
        )
        
        if not vm_info:
            return {"os_type": None, "detected": False, "message": f"VM '{server_name}' not found in Azure"}
        
        os_type = vm_info.get('os_type')
        if os_type:
            # Normalize OS type
            os_lower = os_type.lower()
            if 'windows' in os_lower:
                return {"os_type": "Windows", "detected": True, "vm_name": vm_info.get('vm_name')}
            elif 'linux' in os_lower:
                return {"os_type": "Linux", "detected": True, "vm_name": vm_info.get('vm_name')}
        
        return {"os_type": None, "detected": False, "message": f"OS type not available for VM '{server_name}'"}
    except Exception as e:
        return {"os_type": None, "detected": False, "error": str(e)}


# Demo endpoints (no authentication required) - MUST come before /{runbook_id} routes!
@router.post("/demo/generate-agent", response_model=RunbookResponse)
async def generate_agent_runbook_demo(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev|Windows|Linux"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    ticket_id: Optional[int] = Query(None, description="Optional ticket ID to associate runbook with"),
    db: Session = Depends(get_db)
):
    """Generate an agent-ready YAML runbook (demo tenant)."""
    # Auto-detect OS if env is not explicitly Windows/Linux
    if env not in ["Windows", "Linux"]:
        # Try to extract server name from issue description
        server_name = CIExtractionService._extract_from_text(issue_description)
        if server_name:
            try:
                vm_info = await CloudDiscoveryService.discover_azure_vm(
                    db=db,
                    vm_name=server_name,
                    tenant_id=1
                )
                if vm_info and vm_info.get('os_type'):
                    os_type = vm_info.get('os_type', '').lower()
                    if 'windows' in os_type:
                        env = "Windows"
                    elif 'linux' in os_type:
                        env = "Linux"
            except Exception:
                pass  # If detection fails, use original env value
    
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    runbook = await controller.generate_agent_runbook(issue_description, service, env, risk, ticket_id)
    
    # Associate with ticket AFTER controller returns (separate transaction to avoid rollback)
    # The controller may have already tried, but we do it here to ensure it's in a clean transaction
    if ticket_id:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        try:
            # Ensure we're in a clean state - commit any pending changes first
            db.commit()
            # Now associate
            controller._associate_with_ticket(runbook.id, ticket_id)
            # Commit the association
            db.commit()
            logger.info(f"✅ Association committed in endpoint: runbook {runbook.id} with ticket {ticket_id}")
        except Exception as e:
            logger.warning(f"Association failed in endpoint (non-critical): {e}")
            db.rollback()
            # Don't fail the request - association can happen later during approval
    
    return runbook


@router.post("/demo/debug-yaml")
async def debug_yaml_generation(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev|Windows|Linux"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    db: Session = Depends(get_db)
):
    """Debug endpoint to see raw YAML at each phase - USE THIS TO FIND THE ISSUE."""
    from app.services.runbook.generation import RunbookGeneratorService
    from app.services.llm_service import get_llm_service
    import yaml
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    generator = RunbookGeneratorService()
    llm = get_llm_service()
    
    debug_info = {
        "phase1_raw_yaml": None,
        "phase1_length": 0,
        "phase1_first_200": None,
        "phase1_newlines": [],
        "phase2_after_preprocess": None,
        "phase2_after_sanitize_description": None,
        "phase2_after_sanitize_commands": None,
        "phase2_after_escape_fix": None,
        "phase3_parse_error": None,
        "phase3_first_line": None,
        "phase3_char_at_101": None,
    }
    
    try:
        # Phase 1: Get raw YAML from LLM
        # Auto-detect service type if "auto"
        from app.services.runbook.generation.service_classifier import ServiceClassifier
        if service == "auto":
            classifier = ServiceClassifier()
            service = await classifier.detect_service_type(issue_description)
            logger.info(f"Auto-detected service type: {service}")
        
        # Context is empty string (RAG is disabled)
        context = ""
        ai_yaml = await llm.generate_yaml_runbook(
            tenant_id=1,
            issue_description=issue_description,
            service_type=service,
            env=env,
            risk=risk,
            context=context,
        )
        
        debug_info["phase1_raw_yaml"] = ai_yaml
        debug_info["phase1_length"] = len(ai_yaml) if ai_yaml else 0
        debug_info["phase1_first_200"] = repr(ai_yaml[:200]) if ai_yaml else None
        
        # Show line 30 specifically (where the error occurs)
        if ai_yaml:
            lines = ai_yaml.split('\n')
            if len(lines) >= 30:
                debug_info["phase1_line_30"] = {
                    "raw": lines[29],  # 0-indexed
                    "repr": repr(lines[29]),
                    "column_36_char": repr(lines[29][35]) if len(lines[29]) >= 36 else "N/A",
                    "context_around_col_36": repr(lines[29][max(0, 35-20):35+20]) if len(lines[29]) >= 36 else "N/A"
                }
        
        # Check for newlines in first 200 chars
        if ai_yaml:
            for i, char in enumerate(ai_yaml[:200]):
                if char == '\n':
                    debug_info["phase1_newlines"].append({
                        "position": i,
                        "context": repr(ai_yaml[max(0, i-30):i+30])
                    })
        
        # Phase 2: Process through yaml_processor
        processor = generator.yaml_processor
        
        # After preprocess
        yaml_after_preprocess = processor.preprocess_yaml_structure(ai_yaml)
        debug_info["phase2_after_preprocess"] = yaml_after_preprocess[:500]
        
        # After sanitize_description
        yaml_after_desc = processor.sanitize_description_field(yaml_after_preprocess)
        debug_info["phase2_after_sanitize_description"] = yaml_after_desc[:500]
        
        # After sanitize_commands
        yaml_after_commands = processor.sanitize_command_strings(yaml_after_desc)
        debug_info["phase2_after_sanitize_commands"] = yaml_after_commands[:500]
        
        # Track line 30 through each phase
        def get_line_30_info(yaml_text, phase_name):
            """Extract line 30 information from YAML text"""
            lines = yaml_text.split('\n')
            if len(lines) >= 30:
                line_30 = lines[29]  # 0-indexed
                return {
                    f"{phase_name}_line_30_raw": line_30,
                    f"{phase_name}_line_30_repr": repr(line_30),
                    f"{phase_name}_line_30_col_36": repr(line_30[35]) if len(line_30) >= 36 else "N/A",
                    f"{phase_name}_line_30_context": repr(line_30[max(0, 25):min(len(line_30), 50)]) if len(line_30) >= 36 else "N/A"
                }
            return {}
        
        # Add line 30 info for each phase
        debug_info.update(get_line_30_info(yaml_after_preprocess, "phase2_preprocess"))
        debug_info.update(get_line_30_info(yaml_after_desc, "phase2_after_desc"))
        debug_info.update(get_line_30_info(yaml_after_commands, "phase2_after_commands"))
        
        # After escape fix
        yaml_final = processor.fix_yaml_escape_sequences(yaml_after_commands)
        debug_info["phase2_after_escape_fix"] = yaml_final[:500]
        debug_info.update(get_line_30_info(yaml_final, "phase2_final"))
        
        # Phase 3: Try to parse
        first_line = yaml_final.split('\n')[0] if '\n' in yaml_final else yaml_final
        debug_info["phase3_first_line"] = repr(first_line)
        if len(first_line) >= 101:
            debug_info["phase3_char_at_101"] = repr(first_line[100])
            debug_info["phase3_context_around_101"] = repr(first_line[90:110])
        
        # Show full YAML before parsing attempt
        debug_info["phase3_full_yaml_before_parse"] = yaml_final
        
        try:
            spec = yaml.safe_load(yaml_final)
            debug_info["phase3_parse_success"] = True
        except Exception as e:
            debug_info["phase3_parse_error"] = str(e)
            debug_info["phase3_parse_success"] = False
            # Extract line number from error if available
            import re
            line_match = re.search(r'line (\d+)', str(e))
            col_match = re.search(r'column (\d+)', str(e))
            if line_match and col_match:
                error_line = int(line_match.group(1))
                error_col = int(col_match.group(1))
                lines = yaml_final.split('\n')
                if error_line <= len(lines):
                    debug_info["phase3_error_line_content"] = lines[error_line - 1]
                    debug_info["phase3_error_line_repr"] = repr(lines[error_line - 1])
                    if error_col <= len(lines[error_line - 1]):
                        debug_info["phase3_error_char"] = repr(lines[error_line - 1][error_col - 1])
                        debug_info["phase3_error_context"] = repr(lines[error_line - 1][max(0, error_col-20):error_col+20])
        
    except Exception as e:
        import traceback
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
    
    return debug_info


@router.get("/demo", response_model=List[RunbookResponse])
@router.get("/demo/", response_model=List[RunbookResponse])
async def list_runbooks_demo(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List runbooks for demo tenant"""
    try:
        controller = RunbookController(db, tenant_id=1)  # Demo tenant
        result = controller.list_runbooks(skip, limit)
        # Ensure result is a list
        if not isinstance(result, list):
            result = []
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.exception(f"Error in list_runbooks_demo: {e}", exc_info=True)
        # Return empty list instead of crashing
        return []


@router.get("/demo/{runbook_id}", response_model=RunbookResponse)
async def get_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific runbook by ID for demo tenant"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return controller.get_runbook(runbook_id)


@router.delete("/demo/{runbook_id}")
async def delete_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Delete a runbook for demo tenant (soft delete)"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return controller.delete_runbook(runbook_id)


@router.post("/demo/{runbook_id}/approve", response_model=RunbookResponse)
async def approve_runbook_demo(
    runbook_id: int,
    force_approval: bool = False,
    ticket_id: Optional[int] = Query(None, description="Optional ticket ID to associate runbook with"),
    db: Session = Depends(get_db)
):
    """Approve and publish a draft runbook for demo tenant with duplicate detection"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return await controller.approve_runbook(runbook_id, force_approval, ticket_id)


@router.post("/demo/{runbook_id}/reindex")
async def reindex_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Manually reindex an already approved runbook (for fixing missing indexes)"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return await controller.reindex_runbook(runbook_id)


@router.post("/demo/{runbook_id}/associate-ticket")
async def associate_runbook_with_ticket_demo(
    runbook_id: int,
    ticket_id: int = Query(..., description="Ticket ID to associate with"),
    db: Session = Depends(get_db)
):
    """Manually associate a runbook with a ticket (for fixing missing associations)"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    success = controller._associate_with_ticket(runbook_id, ticket_id)
    if success:
        return {
            "message": f"Runbook {runbook_id} successfully associated with ticket {ticket_id}",
            "runbook_id": runbook_id,
            "ticket_id": ticket_id,
            "success": True
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to associate runbook {runbook_id} with ticket {ticket_id}. Check logs for details."
        )


@router.get("/demo/{runbook_id}/debug")
async def debug_runbook_meta_data(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Debug endpoint to inspect runbook meta_data and ticket associations"""
    from app.models.runbook import Runbook
    import json
    
    runbook = db.query(Runbook).filter(
        Runbook.id == runbook_id,
        Runbook.tenant_id == 1
    ).first()
    
    if not runbook:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Runbook {runbook_id} not found")
    
    meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
    
    return {
        "runbook_id": runbook.id,
        "runbook_title": runbook.title,
        "status": runbook.status,
        "is_active": runbook.is_active,
        "meta_data": meta_data,
        "meta_data_type": type(runbook.meta_data).__name__,
        "ticket_id_in_meta": meta_data.get("ticket_id"),
        "meta_data_raw": runbook.meta_data
    }


# Authenticated endpoints
@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List runbooks for the current tenant"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.list_runbooks(skip, limit)


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific runbook by ID"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.get_runbook(runbook_id)


@router.put("/{runbook_id}", response_model=RunbookResponse)
async def update_runbook(
    runbook_id: int,
    runbook_update: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a runbook"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.update_runbook(runbook_id, runbook_update)


@router.delete("/{runbook_id}")
async def delete_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a runbook (soft delete)"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.delete_runbook(runbook_id)


# Module 3: Runbook Versioning Endpoints
@router.get("/demo/{runbook_id}/versions")
@rate_limit("60/minute")
async def get_runbook_versions(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get version history for a runbook"""
    controller = RunbookVersionController(db, current_user.tenant_id)
    return await controller.get_version_history(runbook_id)


@router.post("/demo/{runbook_id}/versions")
@rate_limit("30/minute")
async def create_runbook_version(
    runbook_id: int,
    title: Optional[str] = None,
    body_md: Optional[str] = None,
    body_yaml: Optional[str] = None,
    change_summary: Optional[str] = None,
    change_type: str = Query("minor", regex="^(major|minor|patch)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of a runbook"""
    controller = RunbookVersionController(db, current_user.tenant_id)
    return await controller.create_version(
        runbook_id=runbook_id,
        title=title,
        body_md=body_md,
        body_yaml=body_yaml,
        change_summary=change_summary,
        change_type=change_type,
        created_by=current_user.id
    )


@router.get("/demo/{runbook_id}/versions/{version_id_1}/diff/{version_id_2}")
@rate_limit("60/minute")
async def get_version_diff(
    runbook_id: int,
    version_id_1: int,
    version_id_2: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get diff between two versions"""
    controller = RunbookVersionController(db, current_user.tenant_id)
    return await controller.get_version_diff(runbook_id, version_id_1, version_id_2)


@router.post("/demo/versions/{version_id}/set-current")
@rate_limit("30/minute")
async def set_current_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set a version as the current version"""
    controller = RunbookVersionController(db, current_user.tenant_id)
    return await controller.set_current_version(version_id)


# Module 5: Citation Verification Endpoints
@router.post("/demo/{runbook_id}/citations/verify")
@rate_limit("30/minute")
async def verify_runbook_citations(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify all citations for a runbook"""
    controller = CitationController(db, current_user.tenant_id)
    return await controller.verify_runbook_citations(runbook_id)


@router.get("/demo/{runbook_id}/citations/health")
@rate_limit("60/minute")
async def get_citation_health(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get citation health summary for a runbook"""
    controller = CitationController(db, current_user.tenant_id)
    return await controller.get_citation_health(runbook_id)


@router.post("/demo/citations/{citation_id}/verify")
@rate_limit("30/minute")
async def verify_single_citation(
    citation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify a single citation"""
    controller = CitationController(db, current_user.tenant_id)
    return await controller.verify_single_citation(citation_id)