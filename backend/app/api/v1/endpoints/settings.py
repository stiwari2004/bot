"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal, Optional

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.config_service import ConfigService
from app.core.logging import get_logger
from app.services.llm_budget_manager import budget_manager

router = APIRouter()
logger = get_logger(__name__)


class ExecutionModeRequest(BaseModel):
    mode: Literal['hil', 'auto']


class ExecutionModeResponse(BaseModel):
    mode: str
    description: str


class LLMBudgetPolicyRequest(BaseModel):
    budget_tokens: Optional[int] = Field(default=None, ge=0)
    window_seconds: Optional[int] = Field(default=None, ge=60)
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=0)
    alert_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class LLMBudgetPolicyResponse(BaseModel):
    tenant_id: int
    budget_tokens: int
    window_seconds: int
    rate_limit_per_minute: int
    alert_threshold: float
    usage_tokens: int
    window_start: int


@router.get("/execution-mode", response_model=ExecutionModeResponse)
async def get_execution_mode(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current execution mode"""
    try:
        mode = ConfigService.get_execution_mode(db, current_user.tenant_id)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=mode, description=description)
    except Exception as e:
        logger.error(f"Error getting execution mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution mode: {str(e)}")


@router.post("/execution-mode", response_model=ExecutionModeResponse)
async def set_execution_mode(
    request: ExecutionModeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set execution mode"""
    try:
        ConfigService.set_execution_mode(db, current_user.tenant_id, request.mode)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if request.mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=request.mode, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting execution mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set execution mode: {str(e)}")


@router.get("/execution-mode/demo", response_model=ExecutionModeResponse)
async def get_execution_mode_demo(db: Session = Depends(get_db)):
    """Get execution mode (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        mode = ConfigService.get_execution_mode(db, tenant_id)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=mode, description=description)
    except Exception as e:
        logger.error(f"Error getting execution mode (demo): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution mode: {str(e)}")


@router.post("/execution-mode/demo", response_model=ExecutionModeResponse)
async def set_execution_mode_demo(
    request: ExecutionModeRequest,
    db: Session = Depends(get_db)
):
    """Set execution mode (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        ConfigService.set_execution_mode(db, tenant_id, request.mode)
        description = (
            "Human-in-the-Loop: Always require manual approval before execution"
            if request.mode == 'hil'
            else "Auto: Use confidence threshold for auto-execution"
        )
        return ExecutionModeResponse(mode=request.mode, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting execution mode (demo): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set execution mode: {str(e)}")


async def _ensure_authorised(tenant_id: int, current_user: User) -> None:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied for requested tenant.")


@router.get("/llm-budgets/{tenant_id}", response_model=LLMBudgetPolicyResponse)
async def get_llm_budget_policy(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
):
    await _ensure_authorised(tenant_id, current_user)
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.post("/llm-budgets/{tenant_id}", response_model=LLMBudgetPolicyResponse)
async def set_llm_budget_policy(
    tenant_id: int,
    request: LLMBudgetPolicyRequest,
    current_user: User = Depends(get_current_user),
):
    await _ensure_authorised(tenant_id, current_user)
    await budget_manager.set_policy(
        tenant_id=tenant_id,
        budget_tokens=request.budget_tokens,
        window_seconds=request.window_seconds,
        rate_limit_per_minute=request.rate_limit_per_minute,
        alert_threshold=request.alert_threshold,
    )
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.get("/llm-budgets/demo", response_model=LLMBudgetPolicyResponse)
async def get_llm_budget_policy_demo():
    tenant_id = 1
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


@router.post("/llm-budgets/demo", response_model=LLMBudgetPolicyResponse)
async def set_llm_budget_policy_demo(request: LLMBudgetPolicyRequest):
    tenant_id = 1
    await budget_manager.set_policy(
        tenant_id=tenant_id,
        budget_tokens=request.budget_tokens,
        window_seconds=request.window_seconds,
        rate_limit_per_minute=request.rate_limit_per_minute,
        alert_threshold=request.alert_threshold,
    )
    policy = await budget_manager.get_policy(tenant_id)
    usage = await budget_manager.get_usage(tenant_id=tenant_id)
    return LLMBudgetPolicyResponse(
        tenant_id=tenant_id,
        budget_tokens=policy["budget_tokens"],
        window_seconds=policy["window_seconds"],
        rate_limit_per_minute=policy["rate_limit_per_minute"],
        alert_threshold=policy["alert_threshold"],
        usage_tokens=usage["usage_tokens"],
        window_start=usage["window_start"],
    )


class BenchmarkConfigItem(BaseModel):
    config_key: str
    config_value: str
    description: str


class BenchmarkConfigResponse(BaseModel):
    configs: list[BenchmarkConfigItem]


class UpdateBenchmarkConfigRequest(BaseModel):
    config_key: str
    config_value: str


@router.get("/benchmark-config/demo", response_model=BenchmarkConfigResponse)
async def get_benchmark_config_demo(db: Session = Depends(get_db)):
    """Get benchmark configuration values (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        configs = ConfigService.get_all_configs(db, tenant_id)
        
        # Filter to only benchmark-related configs
        benchmark_keys = [
            'confidence_threshold_existing',
            'confidence_threshold_duplicate',
            'min_runbook_success_rate'
        ]
        
        from app.models.system_config import SystemConfig
        benchmark_configs = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == tenant_id,
            SystemConfig.config_key.in_(benchmark_keys)
        ).all()
        
        items = []
        for config in benchmark_configs:
            items.append(BenchmarkConfigItem(
                config_key=config.config_key,
                config_value=config.config_value,
                description=config.description or ""
            ))
        
        # Ensure all benchmark keys exist with defaults
        existing_keys = {item.config_key for item in items}
        defaults = {
            'confidence_threshold_existing': ('0.75', 'Minimum similarity to suggest existing runbook'),
            'confidence_threshold_duplicate': ('0.80', 'Similarity threshold to flag as duplicate'),
            'min_runbook_success_rate': ('0.70', 'Minimum success rate for high-quality runbook')
        }
        
        for key, (value, desc) in defaults.items():
            if key not in existing_keys:
                ConfigService.set_config(db, tenant_id, key, value, desc)
                items.append(BenchmarkConfigItem(
                    config_key=key,
                    config_value=value,
                    description=desc
                ))
        
        return BenchmarkConfigResponse(configs=sorted(items, key=lambda x: x.config_key))
    except Exception as e:
        logger.error(f"Error getting benchmark config (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get benchmark config: {str(e)}")


@router.post("/benchmark-config/demo", response_model=BenchmarkConfigResponse)
async def update_benchmark_config_demo(
    request: UpdateBenchmarkConfigRequest,
    db: Session = Depends(get_db)
):
    """Update benchmark configuration value (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        
        # Validate config_key
        valid_keys = [
            'confidence_threshold_existing',
            'confidence_threshold_duplicate',
            'min_runbook_success_rate'
        ]
        if request.config_key not in valid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid config_key. Must be one of: {', '.join(valid_keys)}"
            )
        
        # Validate config_value (must be a float between 0 and 1)
        try:
            value = float(request.config_value)
            if not (0.0 <= value <= 1.0):
                raise ValueError("Value must be between 0.0 and 1.0")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid config_value: {str(e)}. Must be a number between 0.0 and 1.0"
            )
        
        # Get description from existing config or use default
        from app.models.system_config import SystemConfig
        existing = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == tenant_id,
            SystemConfig.config_key == request.config_key
        ).first()
        
        description = existing.description if existing else ""
        if not description:
            descriptions = {
                'confidence_threshold_existing': 'Minimum similarity to suggest existing runbook',
                'confidence_threshold_duplicate': 'Similarity threshold to flag as duplicate',
                'min_runbook_success_rate': 'Minimum success rate for high-quality runbook'
            }
            description = descriptions.get(request.config_key, "")
        
        # Update config
        ConfigService.set_config(db, tenant_id, request.config_key, request.config_value, description)
        
        # Return updated configs
        return await get_benchmark_config_demo(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating benchmark config (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update benchmark config: {str(e)}")


# Infrastructure Threshold Configuration (for precheck analysis)
class InfrastructureThresholdItem(BaseModel):
    metric: str  # cpu, memory, disk, network
    environment: str  # prod, staging, dev
    warning_threshold: float
    critical_threshold: float


class InfrastructureThresholdResponse(BaseModel):
    thresholds: list[InfrastructureThresholdItem]


class UpdateInfrastructureThresholdRequest(BaseModel):
    metric: str
    environment: str
    warning_threshold: float = Field(ge=0.0, le=100.0)
    critical_threshold: float = Field(ge=0.0, le=100.0)


@router.get("/infrastructure-thresholds/demo", response_model=InfrastructureThresholdResponse)
async def get_infrastructure_thresholds_demo(db: Session = Depends(get_db)):
    """Get infrastructure threshold configuration (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        
        # Get all infrastructure threshold configs
        from app.models.system_config import SystemConfig
        threshold_configs = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == tenant_id,
            SystemConfig.config_key.like('infra_threshold_%')
        ).all()
        
        # Parse configs into threshold items
        thresholds_dict = {}
        for config in threshold_configs:
            # Format: infra_threshold_{metric}_{environment}_warning or _critical
            # e.g., infra_threshold_cpu_prod_warning
            parts = config.config_key.split('_')
            if len(parts) >= 5:
                metric = parts[2]  # cpu, memory, disk, network
                environment = parts[3]  # prod, staging, dev
                threshold_type = parts[4]  # warning or critical
                
                key = f"{metric}_{environment}"
                if key not in thresholds_dict:
                    thresholds_dict[key] = {
                        "metric": metric,
                        "environment": environment,
                        "warning_threshold": None,
                        "critical_threshold": None
                    }
                
                try:
                    value = float(config.config_value)
                    if threshold_type == "warning":
                        thresholds_dict[key]["warning_threshold"] = value
                    elif threshold_type == "critical":
                        thresholds_dict[key]["critical_threshold"] = value
                except (ValueError, TypeError):
                    logger.warning(f"Invalid threshold value for {config.config_key}: {config.config_value}")
        
        # Convert to list and ensure all required thresholds exist with defaults
        items = []
        metrics = ["cpu", "memory", "disk", "network"]
        environments = ["prod", "staging", "dev"]
        defaults = {
            "cpu": {"prod": {"warning": 70.0, "critical": 90.0}, "staging": {"warning": 80.0, "critical": 95.0}, "dev": {"warning": 90.0, "critical": 98.0}},
            "memory": {"prod": {"warning": 75.0, "critical": 90.0}, "staging": {"warning": 85.0, "critical": 95.0}, "dev": {"warning": 90.0, "critical": 98.0}},
            "disk": {"prod": {"warning": 80.0, "critical": 90.0}, "staging": {"warning": 85.0, "critical": 95.0}, "dev": {"warning": 90.0, "critical": 98.0}},
            "network": {"prod": {"warning": 70.0, "critical": 85.0}, "staging": {"warning": 80.0, "critical": 90.0}, "dev": {"warning": 90.0, "critical": 95.0}}
        }
        
        for metric in metrics:
            for env in environments:
                key = f"{metric}_{env}"
                if key in thresholds_dict:
                    item = thresholds_dict[key]
                    # Ensure both warning and critical are set
                    if item["warning_threshold"] is None:
                        item["warning_threshold"] = defaults[metric][env]["warning"]
                        ConfigService.set_config(
                            db, tenant_id,
                            f"infra_threshold_{metric}_{env}_warning",
                            str(defaults[metric][env]["warning"]),
                            f"{metric.upper()} warning threshold for {env} environment"
                        )
                    if item["critical_threshold"] is None:
                        item["critical_threshold"] = defaults[metric][env]["critical"]
                        ConfigService.set_config(
                            db, tenant_id,
                            f"infra_threshold_{metric}_{env}_critical",
                            str(defaults[metric][env]["critical"]),
                            f"{metric.upper()} critical threshold for {env} environment"
                        )
                    items.append(InfrastructureThresholdItem(**item))
                else:
                    # Create default thresholds
                    warning = defaults[metric][env]["warning"]
                    critical = defaults[metric][env]["critical"]
                    ConfigService.set_config(
                        db, tenant_id,
                        f"infra_threshold_{metric}_{env}_warning",
                        str(warning),
                        f"{metric.upper()} warning threshold for {env} environment"
                    )
                    ConfigService.set_config(
                        db, tenant_id,
                        f"infra_threshold_{metric}_{env}_critical",
                        str(critical),
                        f"{metric.upper()} critical threshold for {env} environment"
                    )
                    items.append(InfrastructureThresholdItem(
                        metric=metric,
                        environment=env,
                        warning_threshold=warning,
                        critical_threshold=critical
                    ))
        
        return InfrastructureThresholdResponse(thresholds=sorted(items, key=lambda x: (x.metric, x.environment)))
    except Exception as e:
        logger.error(f"Error getting infrastructure thresholds (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get infrastructure thresholds: {str(e)}")


@router.post("/infrastructure-thresholds/demo", response_model=InfrastructureThresholdResponse)
async def update_infrastructure_threshold_demo(
    request: UpdateInfrastructureThresholdRequest,
    db: Session = Depends(get_db)
):
    """Update infrastructure threshold configuration (demo - no auth)"""
    try:
        tenant_id = 1  # Demo tenant
        
        # Validate metric
        valid_metrics = ["cpu", "memory", "disk", "network"]
        if request.metric not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
            )
        
        # Validate environment
        valid_environments = ["prod", "staging", "dev"]
        if request.environment not in valid_environments:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid environment. Must be one of: {', '.join(valid_environments)}"
            )
        
        # Validate warning < critical
        if request.warning_threshold >= request.critical_threshold:
            raise HTTPException(
                status_code=400,
                detail="Warning threshold must be less than critical threshold"
            )
        
        # Update warning threshold
        ConfigService.set_config(
            db, tenant_id,
            f"infra_threshold_{request.metric}_{request.environment}_warning",
            str(request.warning_threshold),
            f"{request.metric.upper()} warning threshold for {request.environment} environment"
        )
        
        # Update critical threshold
        ConfigService.set_config(
            db, tenant_id,
            f"infra_threshold_{request.metric}_{request.environment}_critical",
            str(request.critical_threshold),
            f"{request.metric.upper()} critical threshold for {request.environment} environment"
        )
        
        # Return updated thresholds
        return await get_infrastructure_thresholds_demo(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating infrastructure threshold (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update infrastructure threshold: {str(e)}")



